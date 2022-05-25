#!/usr/bin/env python
import os

from flask import g

from app import create_app, celery
from celery import Celery, Task
from decouple import config
from config import config_dict

# WARNING: Don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)


# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:

    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app(app_config)
app.app_context().push()

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
    # celery.conf.update(app.config)

    class ContextTask(Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.test_request_context():
                g.in_celery_task = True
                res = self.run(*args, **kwargs)
                return res

    celery.Task = ContextTask
    celery.config_from_object(__name__)
    return celery

celery = make_celery(app)