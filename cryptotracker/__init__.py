import datetime, functools, os, requests, statistics, sqlite3, urllib.parse
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, jsonify

# TODO use production server e.g. waitress

# TODO support multiple simultaneous exchanges
# TODO unit test processing logic
# TODO: support only fetching data since last fetch as fetching every 24 hours
# every minute is overkill
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
  i = 0
  for d in response_json["result"]:
    if not d["active"]:
      continue
    with sqlite3.connect("cryptotracker.db") as con:
      cur = con.cursor()
      i+=1
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

      for c in candles:
        cur.execute("INSERT INTO timeseries VALUES (NULL, ?, ?, ?)", (pair_name, c[0], c[4]))
      con.commit()
      
      stddevs[pair_name] = statistics.stdev(volumes)
      if i > 3:
        break

  # compute rank
  stddevs = {k: v for k, v in sorted(stddevs.items(), key=lambda item: item[1])}
  rank_count = 1
  for name in stddevs.keys():
    cur.execute("INSERT OR REPLACE INTO ranks VALUES (?, ?)", (pair_name, rank_count))
    rank_count += 1
  con.commit()
  con.close()


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
    
    with sqlite3.connect("cryptotracker.db") as con:
      cur = con.cursor()
      # TODO: init DB in schema file
      cur.execute('''CREATE TABLE IF NOT EXISTS ranks (pair text primary key unique, rank integer)''')
      cur.execute('''CREATE TABLE IF NOT EXISTS timeseries
        (id integer primary key autoincrement NOT NULL, pair text, timestamp integer, value real)''')
      con.commit()
    # prevent double scheduling when in debug mode
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
      bound_fetch_pairs = functools.partial(fetch_pairs,
        app.config.get("EXCHANGE_NAME"), public_key)
      bound_fetch_pairs()
      sched = BackgroundScheduler(daemon=True)
      # TODO make interval a config value
      sched.add_job(bound_fetch_pairs,"interval",
        seconds=app.config.get("FETCH_INTERVAL"))
      sched.start()

    @app.route("/pairs", methods=["GET"])
    def list_pairs():
      with sqlite3.connect("cryptotracker.db") as con:
        cur = con.cursor()
        pairs = cur.execute("SELECT pair FROM ranks").fetchall()
        return jsonify({
          "pairs": [pair[0] for pair in pairs]
        })

    @app.route("/pairs/<name>", methods=["GET"])
    def get_pair(name):
      with sqlite3.connect("cryptotracker.db") as con:
        cur = con.cursor()
        rank = cur.execute("SELECT rank FROM ranks WHERE pair=?", (name,)).fetchone()

        since_ts = (datetime.datetime.now() - datetime.timedelta(1)).timestamp()

        timeseries = cur.execute("SELECT timestamp, value FROM timeseries WHERE pair=? AND timestamp > ?", (name, since_ts)).fetchall()
        if not rank:
          # TODO: set 404 status code
          return jsonify({"error": "name {} not found".format(name)})
        # TODO: use own data model rather than depending upon external format
        output_json = {
          "name": name,
          "timeseries": timeseries,
          "rank": rank[0],
        }
        return jsonify(output_json)

    return app




