#!/bin/sh

flask db init
#flask db revision --rev-id 622180f5499e

flask db migrate -m "Nov 28.2021"
flask db upgrade

exec gunicorn -b :5000 --workers 3 --timeout 90 --access-logfile - --error-logfile - run:app