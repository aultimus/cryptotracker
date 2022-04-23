import functools, os, requests, statistics, urllib.parse
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, jsonify

# TODO use production server e.g. waitress

# TODO: use a database rather than this global state
# read/writes to pairs could possibly be unthreadsafe
pairs = {}

# TODO support multiple simultaneous exchanges
# TODO unit test processing logic
def fetch_pairs(exchange_name, api_key):
  # seeing as we are only requesting data once per minute then we do not
  # need to utilise streaming
  # TODO: make timeout a config value
  stddevs = {}

  try:
    url = "https://api.cryptowat.ch/markets/{}?".format(exchange_name.lower())
    if api_key:
        params = {"apikey": api_key}
        url = url + urllib.parse.urlencode(params)
    response = requests.get(url, timeout=(3,10))
  except requests.exceptions.RequestException as e:
    print(e)
    return

  response_json = response.json()
  if response.status_code >= 300:
    print("status:{}".format(response.status_code), "error:",response_json["error"]) # TODO: more sophisticated logging
    # TODO: more sophisticated retry/backoff policy
    return

  # collect list of active pairs on this exchange
  for d in response_json["result"]:
    if d["active"]:
      pair_name = d["pair"]
      try:
        url = "https://api.cryptowat.ch/markets/{}/{}/ohlc?".format(exchange_name.lower(), pair_name)
        if api_key:
            params = {"apikey": api_key}
            url = url + urllib.parse.urlencode(params)
        response = requests.get(url, timeout=(3,10))
        if response.status_code >= 300:
          err = ""
          try:
            err = response_json["error"]
          except KeyError:
            pass
          print("status:{}".format(response.status_code), "error:", err) # TODO: more sophisticated logging
          # TODO: more sophisticated retry/backoff policy
          return
      except requests.exceptions.RequestException as e:
        print(e)
        continue
      candles = response.json()["result"]["60"]
      # candlestick response order:
      # 0 CloseTime, 1 OpenPrice, 2 HighPrice, 3 LowPrice,
      # 4 ClosePrice, 5 Volume, 6 QuoteVolume
      volumes = [c[5] for c in candles]

      if not pairs.get(pair_name):
        pairs[pair_name] = {}
      pairs[pair_name]["volumes"] = volumes
      stddevs[pair_name] = statistics.stdev(volumes)
      pairs[pair_name]["timeseries"] = [[c[0], c[4]] for c in candles]

  # compute rank
  stddevs = {k: v for k, v in sorted(stddevs.items(), key=lambda item: item[1])}
  rank_count = 1
  for name in stddevs.keys():
    pairs[name]["rank"] = rank_count
    rank_count += 1


# TODO use production server e.g. waitress
def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    public_key = os.environ.get('CRYPTOWATCH_PUBLIC_KEY')

    app.config.from_mapping(
        SECRET_KEY="dev", # TODO: override when going to prod
        EXCHANGE_NAME="KRAKEN",
        FETCH_INTERVAL = 60,
    )
    
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # prevent double scheduling when in debug mode
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
      fetch_pairs(app.config.get("EXCHANGE_NAME"), public_key)
      sched = BackgroundScheduler(daemon=True)
      # TODO make interval a config value
      bound_fetch_pairs = functools.partial(fetch_pairs,
        app.config.get("EXCHANGE_NAME"), public_key)
      sched.add_job(bound_fetch_pairs,"interval",
        seconds=app.config.get("FETCH_INTERVAL"))
      sched.start()

    @app.route("/pairs", methods=["GET"])
    def list_pairs():
      d = {"pairs":  list(pairs.keys())}
      return jsonify(d)

    @app.route("/pairs/<name>", methods=["GET"])
    def get_pair(name):
      # TODO implement
      pair = pairs.get(name)
      if not pair:
        # TODO: set 404 status code
        return jsonify({"error": "name {} not found".format(name)})
      # TODO: use own data model rather than depending upon external format
      output_json = {
        "name": name,
        "timeseries": pair["timeseries"],
        "rank": pair["rank"],
      }
      return jsonify(output_json)

    return app




