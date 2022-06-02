# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from decouple import config


class Config(object):

    basedir = os.path.abspath(os.path.dirname(__file__))
    # Set up the App SECRET_KEY
    SECRET_KEY = config('SECRET_KEY', default='S#perS3crEt_008')
    # ADMINS=config('ADMINS', default='chaikide@mail.ru')

    # This will create a file in <app> FOLDER
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'sqlite3.db')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    DOMAIN_NAME = 'http://rezinos.ru/'

    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'base', 'static', 'assets', 'img', 'tire_photos')
    PERSO_PHOTO_FOLDER = os.path.join(basedir, 'app', 'base', 'static', 'assets', 'img', 'team')
    PERSO_PHOTO = os.path.join('assets', 'img', 'team')

    PHOTOS_FOLDER = os.path.join('assets', 'img', 'tire_photos')
    PHOTOS_FOLDER_FULL = os.path.join(DOMAIN_NAME, 'static', 'assets', 'img', 'tire_photos')
    XML_FOLDER = os.path.join('static', 'assets', 'xml')
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
    # TIREREGIONPRICES = os.path.join(basedir, 'RossiyaAllTires_Result.csv')
    THORNPRICE_FILE = os.path.join(basedir, 'thorns.csv')
    WEARDISCOUNTS_FILE = os.path.join(basedir, 'wear_discounts.csv')
    AVITOZONES_FILE = os.path.join(basedir, 'Areas.csv')
    TIREPRICES_FILE = os.path.join(basedir, 'RossiyaAllTires_Result.csv')
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'sqlite3.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY  = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

    # PostgreSQL database
    # SQLALCHEMY_DATABASE_URI = '{}://{}:{}@{}:{}/{}'.format(
    #     os.getenv('DB_ENGINE'   , 'mysql'),
    #     os.getenv('DB_USERNAME' , 'appseed_db_usr'),
    #     os.getenv('DB_PASS'     , 'pass'),
    #     os.getenv('DB_HOST'     , 'localhost'),
    #     os.getenv('DB_PORT'     , 3306),
    #     os.getenv('DB_NAME'     , 'appseed_db')
    # )
    #MySQL database - переопределяем на переменную
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    CELERY_BROKER_URL = 'redis://rezinos.ru:6379/0'
    CELERY_RESULT_BACKEND = 'redis://rezinos.ru:6379/0'



class DebugConfig(Config):
    DEBUG = True


# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}
