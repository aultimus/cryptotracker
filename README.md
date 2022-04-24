# cryptotracker

cryptotracker is a RESTful webservice implemented in python using flask. You can use cryptotracker to request historical data about cryptocurrencies.

cryptotracker can be ran in development mode via
`./rundev.sh`

you can set the environment variable `CRYPTOWATCH_PUBLIC_KEY` in order to use a
cryptowatch api key with this service, not setting the env var will result in
using the free api allowance.

The exchange used by the server can be configured before running the server,
default is kraken.

## /pairs endpoint
cryptotracker exposes the pairs endpoint which can be used to request a list of available pairs.
Example usage:
`curl localhost:5000/pairs`
```
{
  "pairs": [
    "1incheur",
    "1inchusd",
    "aaveaud",
    "aavebtc",
    "aaveeth",
    ...
  ]
}
```

## /pairs/<pair> endpoint
The pairs/<pair> endpoint allows retrieving of historical and statistical data for a given pair.
`curl localhost:5000/pairs/<pair_name>`
where `pairname` is a value returned by the `/pairs` endpoint
e.g.: `curl localhost:5000/pairs/btceur`
```
{
  "name": "btceur",
  "rank": 1,
  "timeseries": [
    [
      1650691980,
      36695.2
    ],
    [
      1650692040,
      36697.4
    ],
  ...
}
```
where timeseries is an array of [timestamp (seconds since epoch), price].

## TODO
* exponential backoff / retry policy on HTTP errors
* Add more sophisticated logging with levels
* Add metrics - rate, error, duration of inbound and outbound HTTP requests
* Add integration tests
* Support user requesting data from specific exchange
* Dockerise
* Implement unit tests for parsing and processing of http responses
* TODO: use postgres instead of sqlite
* TODO: add more async so requests dont hang whilst fetch_pairs is being executed
