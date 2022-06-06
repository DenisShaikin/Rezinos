#!/bin/sh

until nc -z -v $DB_HOST 3306 
do
  echo "Waiting for database connection..."
  # wait for 5 seconds before check again
  sleep 2
done

flask db init
#flask db revision --rev-id 622180f5499e

flask db migrate -m "Mar 15.2022"
flask db upgrade

exec celery -A celery_worker.celery worker -P gevent --loglevel=INFO &

exec gunicorn -b :5000 --workers 3 --threads 100 --timeout 90 --access-logfile - --error-logfile - run:app
