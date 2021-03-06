# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_migrate import Migrate
from os import environ
from sys import exit
from decouple import config
import logging

from config import config_dict
from app import create_app, db
from app.base.models import  User, Tire, Rim, Wheel

from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# WARNING: Don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)
# print(DEBUG)


# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:
    
    # Load the configuration using the default values 
    app_config = config_dict[get_config_mode.capitalize()]
    # print(get_config_mode.capitalize())

except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app( app_config )
Migrate(app, db, render_as_batch=True)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Tire': Tire, 'Rim':Rim, 'Wheel':Wheel}


if DEBUG:
    app.logger.info('DEBUG       = ' + str(DEBUG)      )
    app.logger.info('Environment = ' + get_config_mode )
    app.logger.info('DBMS        = ' + app_config.SQLALCHEMY_DATABASE_URI )

if __name__ == "__main__":
    app.run()


