from app import db
from flask import current_app as app
import pandas as pd
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import jwt


class ApiTire(db.Model):
    __tablename__ = 'tire_api'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_type = db.Column(db.Integer, default=0)  #0=prices scan, 1=scan for nearest offerts
    brand = db.Column(db.String(200))
    price = db.Column(db.Float)
    season = db.Column(db.String(20))
    region = db.Column(db.String(20))
    regionReal = db.Column(db.String(20))
    diametr = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    wear= db.Column(db.String(10))
    qte= db.Column(db.Integer)
    unitPrice = db.Column(db.Float)
    wear_num = db.Column(db.Float)
    source_id = db.Column(db.Integer, db.ForeignKey('api_source.id'))
    # source = db.relationship('ApiSource', foreign_keys=[source_id])

    avito_link = db.Column(db.String(200)) #Ссылка на объявление
    avito_id = db.Column(db.String(15)) #id объявления на Авито
    avito_lon = db.Column(db.Float) #Координаты владельца объявления
    avito_lat=db.Column(db.Float)
    avito_imgLink = db.Column(db.String(200)) #Ссылка на картинку объявления

    update_date = db.Column(db.DateTime, default=datetime.utcnow()) #Дата и время обновления

    def __repr__(self):
        return '<ApiTire {} {}>'.format(self.id, self.brand)

    def load_tireprices(self):
        tirePrices = pd.read_csv(app.config['TIREPRICES_FILE'], encoding='utf-8', sep=';')
        tirePrices.index.name='id'
        tirePrices['update_date']=datetime.utcnow()
        tirePrices.to_sql('tire_api', con=db.engine, if_exists='replace', dtype={'id': db.Integer}, chunksize=5000)

    def addTires(self, df):
        df.index.name='id'
        df['update_date']=datetime.utcnow()
        df.to_sql('tire_api', con=db.engine, if_exists='append', dtype={'id': db.Integer})

class ApiSource(db.Model):
    __tablename__ = 'api_source'
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(15))  #avito, youla, ..
    tires = db.relationship('ApiTire', backref='source', lazy='dynamic')
    def __repr__(self):
        return self.source

class ApiUser(db.Model):
    __tablename__ = 'users_api'
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(32), index = True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=600):
        return jwt.encode(
            {'id': self.id, 'exp': time.time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')


    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except:
            return
        return ApiUser.query.get(data['id'])
