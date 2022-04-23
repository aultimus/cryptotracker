#!/bin/bash
export FLASK_APP=cryptotracker
export FLASK_ENV=development
pipenv shell
flask run
