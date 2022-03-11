# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from   decouple import config

class Config(object):

    basedir    = os.path.abspath(os.path.dirname(__file__))
    # Set up the App SECRET_KEY
    SECRET_KEY = config('SECRET_KEY', default='S#perS3crEt_008')
    ADMINS=config('ADMINS', default='chaikide@mail.ru')

    # This will create a file in <app> FOLDER
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'sqlite3.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    DOMAIN_NAME='http://rezinos.ru/'

    UPLOAD_FOLDER=os.path.join(basedir, 'app', 'base', 'static', 'assets', 'img', 'tire_photos')
    PERSO_PHOTO_FOLDER=os.path.join(basedir, 'app', 'base', 'static', 'assets', 'img', 'team')
    PERSO_PHOTO=os.path.join('assets', 'img', 'team')

    PHOTOS_FOLDER=os.path.join('assets', 'img', 'tire_photos')
    PHOTOS_FOLDER_FULL = os.path.join(DOMAIN_NAME, 'static', 'assets', 'img', 'tire_photos')
    XML_FOLDER=os.path.join('static', 'assets', 'xml')
    XML_FOLDER_FULL = os.path.join(basedir, 'app', 'base', 'static', 'assets', 'xml')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['chaikide@mail.ru']
    PRICES_FILE = os.path.join(basedir, 'TirePricesBase.csv')
    RIMS_FILE = os.path.join(basedir, 'RimPricesBase.csv')
    TIREGUIDE_FILE = os.path.join(basedir, 'TireGide.csv')
    CARSGUIDE_FILE = os.path.join(basedir, 'RimsCatalogue.csv')
    TIREREGIONPRICES = os.path.join(basedir, 'RossiyaAllTires_Result.csv')
    THORNPRICE_FILE = os.path.join(basedir, 'thorns.csv')
    WEARDISCOUNTS_FILE = os.path.join(basedir, 'wear_discounts.csv')
    AVITOZONES_FILE =  os.path.join(basedir, 'Areas.csv')

class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY  = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

    # PostgreSQL database
    # SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
    #     config( 'DB_ENGINE'   , default='postgresql'    ),
    #     config( 'DB_USERNAME' , default='appseed'       ),
    #     config( 'DB_PASS'     , default='pass'          ),
    #     config( 'DB_HOST'     , default='localhost'     ),
    #     config( 'DB_PORT'     , default=5432            ),
    #     config( 'DB_NAME'     , default='appseed-flask' )

    #MySQL database
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL')


class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}
