import functools, os, requests
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask

# TODO: use a database rather than this global state
# read/writes to pairs could possibly be unthreadsafe
pairs = {}

# TODO support multiple simultaneous exchanges
def fetch_pairs(exchange_name):
  # seeing as we are only requesting data once per minute then we do not
  # need to utilise streaming
  # TODO: make timeout a config value
  try:
   response = requests.get("https://api.cryptowat.ch/markets/{}".format(exchange_name.lower()), timeout=(3,10))
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
      pairs[d["pair"]] = {}
  print(pairs)

# TODO use production server e.g. waitress
def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
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
      fetch_pairs(app.config.get("EXCHANGE_NAME"))
      sched = BackgroundScheduler(daemon=True)
      # TODO make interval a config value
      bound_fetch_pairs = functools.partial(fetch_pairs,
        app.config.get("EXCHANGE_NAME"))
      sched.add_job(bound_fetch_pairs,"interval",
        seconds=app.config.get("FETCH_INTERVAL"))
      sched.start()

    @app.route("/pairs", methods=["GET"])
    def list_pairs():
      # TODO: implement
      return "list_pairs"
      
    @app.route("/pairs/<name>", methods=["GET"])
    def get_pair(name):
      # TODO implement
      return name

    return app




