#!/bin/bash
export FLASK_APP=cryptotracker
export FLASK_ENV=development
source $(pipenv --venv)/bin/activate
flask run
