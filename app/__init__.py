# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from logging import basicConfig, DEBUG, getLogger, StreamHandler
from os import path
from flask_wtf.csrf import CSRFProtect
from flask_restful import Api

db = SQLAlchemy()
login_manager = LoginManager()


def register_extensions(app):
    db.init_app(app)
    csrf = CSRFProtect()
    csrf.init_app(app)
    login_manager.init_app(app)
    return csrf


def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def configure_database(app):

    @app.before_first_request
    def initialize_database():
        db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def create_app(config):
    global mail

    app = Flask(__name__, static_folder='base/static')
    app.config.from_object(config)
    csrf=register_extensions(app)
    register_blueprints(app)
    configure_database(app)

    from app.api import bp as api_bp
    # csrf.exempt(api_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    api = Api(app, decorators=[csrf.exempt])

    from app.api.apiroutes import TirePrices, NewUser, GetUser
    api.add_resource(NewUser, '/api/users')
    api.add_resource(GetUser, '/api/users/<int:id>')
    api.add_resource(TirePrices, '/api/tires/<string:region>')
    csrf.exempt("NewUser")

    return app
