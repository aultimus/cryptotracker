# cryptotracker

cryptotracker is a RESTful webservice implemented in python using flask. You can use cryptotracker to request historical data about cryptocurrencies.

cryptotracker can be ran in development mode via
`./rundev.sh`

you can set the environment variable `CRYPTOWATCH_PUBLIC_KEY` in order to use a
cryptowatch api key with this service, not setting the env var will result in
using the free api allowance.

## /pairs endpoint
cryptotracker exposes the pairs endpoint which can be used to request a list of available pairs.
Example usage:
`curl localhost:5000/pairs`

## /pairs/<pair> endpoint
The pairs/<pair> endpoint allows retrieving of historical and statistical data for a given pair.
`curl localhost:5000/pairs/<pair_name>`
where `pairname` is a value returned by the `/pairs` endpoint

## TODO
* exponential backoff / retry policy on HTTP errors
* Add more sophisticated logging with levels
* Add metrics - rate, error, duration of inbound and outbound HTTP requests
* Add integration tests
* Support user requesting data from specific exchange
* Dockerise
* Implement unit tests for parsing and processing of http responses
