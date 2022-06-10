# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
# from sqlalchemy import Binary, Column, Integer, String, Boolean
from sqlalchemy.types import Integer
from datetime import datetime, timedelta
from app import db, login_manager
from app.base.util import hash_pass
import xml.etree.ElementTree as ET
import os
from flask import current_app as app
from flask import url_for
from flask import Flask
from time import time
import jwt
import pandas as pd
from sqlalchemy import and_
from sqlalchemy import event
import numpy as np


class User(db.Model, UserMixin):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.Binary)
    tires = db.relationship('Tire', backref='owner', lazy='dynamic')
    rims = db.relationship('Rim', backref='owner', lazy='dynamic')
    wheels = db.relationship('Wheel', backref='owner', lazy='dynamic')
    about_me = db.Column(db.String(140))
    store=db.Column(db.String(64))  #Номер магазина в Авто.ру
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    avito_client_id=db.Column(db.String(40))    #Client_ID со страницы https://www.avito.ru/professionals/api
    avito_client_secret=db.Column(db.String(100)) #Client_Secret со страницы https://www.avito.ru/professionals/api
    avito_profile_idNum=db.Column(db.String(40)) #Номер профиля в Авито
    avito_profile_url=db.Column(db.String(256))
    avito_balance_real=db.Column(db.Float, default=0)
    avito_balance_bonus=db.Column(db.Float, default=0)
    def_allow_email = db.Column(db.Boolean, default=True)  # Разрешение писать по умолчанию
    def_manager_name = db.Column(db.String(140))        # Контактное лицо по умолчанию
    def_contact_phone = db.Column(db.String(20))       # Российский Телефон по умолчанию
    def_contact_mail = db.Column(db.String(100))     #email контакта с Авито
    def_adress = db.Column(db.String(256))         # полный адрес объекта — строка до 256 символов, обязательное поле
    def_latitude = db.Column(db.Float)             # альтернатива Адрес
    def_longitude = db.Column(db.Float)            # альтернатива Адрес
    def_display_area1 = db.Column(db.String(256))
    def_display_area2 = db.Column(db.String(256))
    def_display_area3 = db.Column(db.String(256))
    def_display_area4 = db.Column(db.String(256))
    def_display_area5 = db.Column(db.String(256))
    avito_path = db.Column(db.String(256))
    autoru_path = db.Column(db.String(256))
    drom_path = db.Column(db.String(256))
    avatar_photo = db.Column(db.String(100))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass( value ) # we need bytes here (not plain str)
                
            setattr(self, property, value)

    def set_password(self, value):
        if not isinstance(value, str):
            value = value[0]
        value = hash_pass(value)  # we need bytes here (not plain str)
        setattr (self, 'password', value)

    def __repr__(self):
        return str(self.username)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


    def to_avito_xml(self):
        root = ET.Element("Ads")
        root.set('formatVersion', "3")
        root.set('target', "Avito.ru")
        tires=self.tires.filter(Tire.avito_show == True).all()
        rims=self.rims.filter(Rim.avito_show == True).all()
        for tire in tires:
            ad = ET.SubElement(root, 'Ad')
            tire.add_avito_tire(ad)
        for rim in rims:
            ad = ET.SubElement(root, 'Ad')
            rim.add_avito_rim(ad)
        message = ET.tostring(root, "utf-8")

        # print(message)url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example1.jpg'
        myfile = open(os.path.join(app.config['XML_FOLDER_FULL'], self.avito_path), "w")
        myfile.write(ET.tostring(root).decode('UTF-8'))
        myfile.close()
        # file.save(os.path.join(app.config['XML_FOLDER'], new_filename))
        return message

    def to_avtoru_xml(self):
        root = ET.Element("parts")
        #Показываем только не снятые с продажи шины
        tires=self.tires.filter(and_(Tire.date_end>=datetime.utcnow()+timedelta(seconds=1), Tire.avtoru_show == True)).all()
        rims=self.rims.filter(and_(Rim.date_end>=datetime.utcnow()+timedelta(seconds=1), Rim.avtoru_show == True)).all()
        # print(datetime.utcnow)
        for tire in tires:
            tire.add_avtoru_tire(root)
        for rim in rims:
            rim.add_avtoru_rim(root)
        message = ET.tostring(root, "utf-8")
        myfile = open(os.path.join(app.config['XML_FOLDER_FULL'], self.autoru_path), "w")
        # myfile = open(os.path.join(app.config['XML_FOLDER'], self.avito_path).replace('\\', '/'), "w")
        # myfile = open(os.path.join(app.config['XML_FOLDER'],  self.username + '_' + 'auto_ru.xml'), "w")
        myfile.write(ET.tostring(root).decode('UTF-8'))
        myfile.close()
        # file.save(os.path.join(app.config['XML_FOLDER'], new_filename))
        return message

    def to_drom_xml(self):
        # root = ET.Element("?xml")
        # root.set('version', "1.0")
        # root.set('encoding', "UTF-8")
        root = ET.Element('offers')
        tires = self.tires.filter(Tire.drom_show == True).all()
        rims = self.rims.filter(Rim.drom_show == True).all()
        for tire in tires:
            ad = ET.SubElement(adOffers, 'offer')
            tire.add_drom_tire(ad)
        # for rim in rims:
        #     ad = ET.SubElement(adOffers, 'offer')
            # rim.add_avito_rim(ad)
        message = ET.tostring(root, "utf-8")

        # print(message)url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example1.jpg'
        # myfile = open(os.path.join(app.config['XML_FOLDER_FULL'], self.drom_path), "w")
        root.write(os.path.join(app.config['XML_FOLDER_FULL'], self.drom_path), encoding = "UTF-8", xml_declaration = True)
        # myfile.close()
        # file.save(os.path.join(app.config['XML_FOLDER'], new_filename))
        return message



@login_manager.user_loader
def user_loader(id):
    return User.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    return user if user else None

def add_avito_element(root, elem_name, elem_value):  #Подходит так же и для дрома
    if (elem_value is not None) and (elem_value!=''):
        elem=ET.SubElement(root, elem_name)
        elem.text=str(elem_value)
    return root

def add_autoru_property(root, elem_name, elem_value, attribname, attribvalue):
    if elem_value is not None:
        elem=ET.SubElement(root, elem_name)
        elem.set(attribname, str(attribvalue))
        elem.text=str(elem_value)
    return root


class AvitoZones(db.Model):
    __tablename__ = 'avito_zones'
    id = db.Column(db.Integer, primary_key=True)
    zone=db.Column(db.String(250))
    engzone=db.Column(db.String(250))
    def __repr__(self):
        return '<{},{},{}>'.format(self.id, self.zone, self.engzone)
    def load_avitozones(self):
        price_data = pd.read_csv(app.config['AVITOZONES_FILE'], encoding='cp1251', sep=';', index_col='id')
        price_data.index.name='id'
        price_data.to_sql('avito_zones', con=db.engine, if_exists='append', index=False)


class TirePrices(db.Model):
    __tablename__ = 'tire_prices'
    id = db.Column(db.Integer, primary_key=True)
    diametr = db.Column(db.String(3))
    size = db.Column(db.String(6))
    brand = db.Column(db.String(20))
    price_min = db.Column(db.Integer)
    price_med = db.Column(db.Integer)
    def __repr__(self):
        return '<Шины {} {} {} {}>'.format(self.brand, self.diametr, self.size, self.price_min)
    def load_prices_base(self):
        price_data = pd.read_csv(app.config['PRICES_FILE'], encoding='cp1251', sep=';', index_col='id')
        price_data.index.name='id'
        price_data.to_sql('tire_prices', con=db.engine, if_exists='append', index=False)
        # print(price_data.head())

class RimPrices(db.Model):
    __tablename__ = 'rim_prices'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(30))
    model = db.Column(db.String(60))
    reference =db.Column(db.String(30))
    price = db.Column(db.Integer)
    rimType = db.Column(db.String(15))
    compatibility = db.Column(db.String(200))
    diametr = db.Column(db.String(3))
    ET = db.Column(db.String(8))
    width = db.Column(db.Float)
    bolts = db.Column(db.Integer)
    dia = db.Column(db.Float) #Диаметр сверловки болтов
    CO = db.Column(db.Float)    #Диаметр центрального отверстия
    color = db.Column(db.String(20))
    original = db.Column(db.Boolean)

    def __repr__(self):
        return '<{} диски {} {} {} {}xR{} / {}x{} ET{} D{} {} Руб.>'.format(self.rimType, self.brand, self.model,   self.width, self.diametr, self.bolts, self.bolts_diametr, self.ET, self.CO, self.price)
    def load_prices_base(self):
        chunksize=500
        with pd.read_csv(app.config['RIMS_FILE'], encoding='cp1251', index_col='id', sep=';', dtype={'diametr':'Int64', 'bolts':'Int64', 'original':'bool'}, chunksize=chunksize) as reader:
            for chunk in reader:
                chunk.index.name='id'
                chunk.to_sql('rim_prices', con=db.engine, if_exists='append', index=False)

class TireGuide(db.Model):
    __tablename__ = 'tire_guide'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(20))
    model = db.Column(db.String(100))
    diametr = db.Column(db.String(3))
    width = db.Column(db.String(3))
    height = db.Column(db.String(2))
    price = db.Column(db.Integer)
    photolink = db.Column(db.String(200))
    reference = db.Column(db.String(50))
    description = db.Column(db.String(200))
    purpose = db.Column(db.String(50))
    season = db.Column(db.String(20))
    thorns = db.Column(db.Boolean)
    def __repr__(self):
        return [self.brand, self.model, self.diametr, self.width, self.height, self.photolink, self.reference, self.description,
                self.purpose, self.season, self.thorns]

    def load_tireguide_base(self):
        chunksize=1000
        with pd.read_csv(app.config['TIREGUIDE_FILE'], encoding='cp1251', sep=';', chunksize=chunksize, index_col='id') as reader:
            for chunk in reader:
                chunk.index.name = 'id'
                chunk.to_sql('tire_guide', con=db.engine, if_exists='append', index=False)
        # price_data = pd.read_csv(app.config['TIREGUIDE_FILE'], encoding='cp1251', sep=';')
        # price_data.index.name='id'
        # price_data.to_sql('tire_guide', con=db.engine, if_exists='replace', dtype={'id': Integer})


class CarsGuide(db.Model):
    __tablename__ = 'cars_guide'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(20))
    model = db.Column(db.String(100))
    year = db.Column (db.Integer)
    ET = db.Column(db.Float)
    CO = db.Column(db.Float)
    rimDiametr = db.Column(db.Integer)
    rimWidth = db.Column(db.Float)
    rimBolts = db.Column(db.Integer)
    rimDia = db.Column(db.Integer)
    tireDiametr = db.Column(db.Integer)
    tireWidth = db.Column(db.Integer)
    tireHeight = db.Column(db.Integer)

    def __repr__(self):
        return [self.brand, self.model, self.year, self.ET, self.CO, self.rimDiametr, self.rimWidth, self.rimBolts,
                self.rimDia, self.tireDiametr, self.tireWidth, self.tireHeight]

    def load_carsguide_base(self):
        chunksize=1000
        with pd.read_csv(app.config['CARSGUIDE_FILE'], encoding='cp1251', sep=';', chunksize=chunksize, index_col='id') as reader:
            for chunk in reader:
                chunk.index.name = 'id'
                chunk.to_sql('cars_guide', con=db.engine, if_exists='append', index=False)
        # cars_data = pd.read_csv(app.config['CARSGUIDE_FILE'], encoding='cp1251', sep=';')
        # cars_data.index.name='id'
        # cars_data.to_sql('cars_guide', con=db.engine, if_exists='replace', dtype={'id': Integer}, chunksize=5000)

class ThornPrices(db.Model):
    __tablename__ = 'thorn_prices'

    id = db.Column(db.Integer, primary_key=True)
    diametr = db.Column(db.String(3))
    thorn_price = db.Column(db.Float)
    def __repr__(self):
        return '<Диаметр R{} {}>'.format(self.diametr, self.thorn_price)
    def load_thornprices(self):
        thorn_data=pd.read_csv(app.config['THORNPRICE_FILE'], encoding='cp1251', sep=';', index_col='id')
        thorn_data.index.name='id'
        # print(thorn_data.head())
        thorn_data.to_sql('thorn_prices', con=db.engine, if_exists='append', index=False)

class WearDiscounts(db.Model):
    __tablename__ = 'wear_discounts'

    id = db.Column(db.Integer, primary_key=True)
    protector_height = db.Column(db.Integer)
    summer_discount = db.Column(db.Float)
    winter_discount = db.Column(db.Float)
    def __repr__(self):
        return '<id={}, protector height {}, % summer discount {}, % winter discount {}>'.format(self.id,
                        self.protector_height, self.summer_discount, self.winter_discount)

    def load_weardiscounts(self):
        wear_data=pd.read_csv(app.config['WEARDISCOUNTS_FILE'], encoding='cp1251', sep=';', index_col='id')
        wear_data.index.name='id'
        wear_data.to_sql('wear_discounts', con=db.engine, if_exists='append', index=False )


class Tire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baseid = db.Column(db.String(20)) #Уникальный идентификатор на все базы, шины диски и колеса, =d+id для дисков или t+id для tire или r+id для колес
    sold=db.Column(db.Boolean, default=False)
    sold_date=db.Column(db.DateTime())
    store=db.Column(db.String(64))  #Номер магазина в Авто.ру
    brand=db.Column(db.String(70))
    model=db.Column(db.String(70))
    qte = db.Column(db.Integer)   #Количество комплектов для продажи
    inSet = db.Column(db.Integer)  #Количество в комплекте
    inStock = db.Column(db.Boolean, default=True) #В наличии (или под заказ)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow) #Дата создания объявления
    date_begin=db.Column(db.DateTime, default=datetime.utcnow) #Дата и время публикации объявления
    date_end=db.Column(db.DateTime, default=datetime.today()+timedelta(days=120)) #Дата и время снятия публикации объявления
    listing_fee=db.Column(db.String(20))  #Пакет размещения: Package, PackageSingle или Single
    ad_status=db.Column(db.String(15), default='Free') #«Free», «Highlight», «XL», «x2_1», «x2_7», «x5_1», «x5_7», «x10_1», «x10_7»
    is_for_priority=db.Column(db.Boolean, default=False) #Для Авто.ру признак продвижения
    avito_id=db.Column(db.String(50)) #Номер объявления на Авито, для связки с объявлением вручную
    user_id = db.Column(db.Integer, db.ForeignKey('User.id')) #Привязка к владельцу
    avito_show = db.Column(db.Boolean, default=False)
    avtoru_show = db.Column(db. Boolean, default=False)
    drom_show = db.Column(db.Boolean, default=False)
    #Забрать настройки объявления из настроек пользователя
    allow_email = db.Column(db.Boolean) #Разрешено написать сообщение через сайт
    manager_name = db.Column(db.String(100))     #Имя контактного лица по данному объявлению
    contact_phone =db.Column (db.String(20))    #Телефон контактного лица, только один российский телефон
    address=db.Column(db.String(256))         #полный адрес объекта — строка до 256 символов, обязательное поле
    latitude=db.Column(db.Float)    #альтернатива Адрес
    longitude=db.Column(db.Float)       #альтернатива Адрес
    display_area1=db.Column(db.String(256))
    display_area2=db.Column(db.String(256))
    display_area3=db.Column(db.String(256))
    display_area4=db.Column(db.String(156))
    display_area5=db.Column(db.String(256))
    category=db.Column(db.String(50), default='Запчасти и аксессуары')
    # type_id=db.Column(db.String(6), default='10-048'  )   #10-048 — Шины, 10-047 — Мотошины, 10-046 — Диски, 10-045 —  Колёса, 10-044 — Колпаки
    ad_type=db.Column(db.String(50), default='Товар приобретен на продажу')  #'Товар от производителя' или 'Товар приобретен на продажу'
    title=db.Column(db.String(50))  #Название объявления — строка до 50 символов.
    description=db.Column(db.String(5000))    #Текстовое описание объявления в соответствии с правилами Авито — строка не более 5000 символов.
                                        #Если у вас есть оплаченная Подписка, то поместив описание внутрь CDATA, вы можете использовать дополнительное форматирование с помощью HTML-тегов — строго из указанного списка: p, br, strong, em, ul, ol, li.
    price = db.Column(db.Integer)
    recommended_price = db.Column(db.Integer)

    condition=db.Column(db.String(10), default='Б/у')       #Новое или Б/у
    oem=db.Column(db.String(10))    #номер делтали OEM, REFERENCE
    shirina_profilya=db.Column(db.String(10))  #TireSectionWidth
    vysota_profilya=db.Column(db.String(10))   #TireAspectRatio
    diametr=db.Column(db.String(10))   #в файле xml RimDiameter
    sezonnost=db.Column(db.String(40)) #TireType Всесезонные / Летние /  Зимние нешипованные / Зимние шипованные
    videourl=db.Column(db.String(256))   #VideoURL Формат ссылки на видео должен соответствовать - https://www.youtube.com/watch?v=***
    protector_height=db.Column(db.Integer)  #Высота протектора
    protector_wear = db.Column(db.Integer) #Износ протектора
    product_year = db.Column(db.Integer)  #год производства
    comment=db.Column(db.String(120))  #комментарий
    photos = db.relationship('TirePhoto', backref='tire', lazy='dynamic', passive_deletes=True)
    withDelivery=db.Column(db.Boolean)  #с доставкой
    isShop=db.Column(db.Boolean)       #Магазин
    locationId=db.Column(db.Boolean)    #расположение

    def __repr__(self):
        return '<Шины {} {} {} {} R{}>'.format(self.brand, self.model, self.shirina_profilya, self.vysota_profilya, self.diametr)

    def first_photo(self):
        return self.photos.first().photo
        # return os.path.join(app.config['tire_photos'], self.photos.first().photo)

    def add_avtoru_tire(self, ads):
        # columns=['id', 'Заголовок', 'Брэнд', 'Описание', 'Новизна',
        #          'Цена', 'Состояние', 'Диаметр', 'Тип резины', 'Ширина', 'Высота профиля',
        #          'images', 'Количество', 'Отверстий', 'Диаметр отверстий', 'Вылет']
        ad = ET.SubElement(ads, 'part')
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'title', self.title)
        #магазины
        if self.store is not None:
            stores = ET.SubElement(ad, 'stores')
            add_avito_element(stores, 'store', self.store)
        #снова характеристики объявления
        # add_avito_element(ad, 'part_number', self.OEM)
        add_avito_element(ad, 'manufacturer', self.brand)
        add_avito_element(ad, 'description', self.description)
        if self.condition =='Б/у':
            add_avito_element(ad, 'is_new', 'false')
        else:
            add_avito_element(ad, 'is_new', 'true')
        add_avito_element(ad, 'price', round(self.price, 0))
        #Раздел Доступность
        avail = ET.SubElement(ad, 'availability')
        add_avito_element(avail, 'isAvailable', 'True')
        # add_avito_element(avail, 'daysFrom', '0')
        # add_avito_element(avail, 'daysTo', '1')
        properties = ET.SubElement(ad, 'properties')
        add_autoru_property(properties, 'property', self.shirina_profilya, 'name', 'Ширина профиля')  #Ширина профиля
        add_autoru_property(properties, 'property', self.vysota_profilya, 'name', 'Высота профиля')  #Высота профиля
        add_autoru_property(properties, 'property', self.diametr,'name', 'Диаметр')  #Диаметр
        add_autoru_property(properties, 'property', self.sezonnost, 'name', 'Сезонность')  #Сезонность
        add_autoru_property(properties, 'property', self.protector_height, 'name', 'Высота протектора')  #Сезонность
        #Раздел images
        if self.photos.first() is not None:
            imagezone = ET.SubElement(ad, 'images')
            for photo in self.photos:
                if photo is not None:
                    add_avito_element(imagezone, 'image', "url=" + os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        #Раздел properties
        add_avito_element(ad, 'count', self.qte)
        add_avito_element(ad, 'is_for_priority', self.is_for_priority)
        return ads

    def add_avito_tire(self, ad):
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'DateBegin', self.date_begin.isoformat())
        #Дату окончания публикации пока не указываем, в будущем возможно понадобится функциональность
        add_avito_element(ad, 'DateEnd', self.date_end.isoformat())
        add_avito_element(ad, 'ListingFee', self.listing_fee)
        add_avito_element(ad, 'AdStatus', self.ad_status)
        if self.avito_id != '':
            add_avito_element(ad, 'AvitoId', self.avito_id)
        if self.allow_email:
            add_avito_element(ad, 'ContactMethod', 'По телефону и в сообщениях')
        else:
            add_avito_element(ad, 'ContactMethod', 'По телефону')
        if self.manager_name:
            add_avito_element(ad, 'ManagerName', self.manager_name)
        if self.contact_phone:
            add_avito_element(ad, 'ContactPhone', self.contact_phone)
        if self.address is not None:
            add_avito_element(ad, 'Address', self.address)
        if self.address is None and self.latitude is not None:
            add_avito_element(ad, 'Latitude', self.latitude)
            add_avito_element(ad, 'Longitude', self.longitude)
        if self.display_area1 is not None:
            avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).filter(AvitoZones.id == int(self.display_area1)).first()
            areazone = ET.SubElement(ad, 'DisplayAreas')
            add_avito_element(areazone, 'Area', avito_zones[1])
        add_avito_element(ad, 'Category', self.category)
        # dict_types={'Шины':'10-048', 'Мотошины':'10-047', 'Диски':'10-046', 'Колёса':'10-045', 'Колпаки':'10-044'}
        add_avito_element(ad, 'TypeId', '10-048')
        add_avito_element(ad, 'AdType', self.ad_type)
        add_avito_element(ad, 'Title', self.title)
        add_avito_element(ad, 'Description', self.description)
        add_avito_element(ad, 'Price', self.price)
        add_avito_element(ad, 'Condition', self.condition)
        # add_avito_element(ad, 'OEM', self.oem)
        add_avito_element(ad, 'Brand', self.brand)
        add_avito_element(ad, 'RimDiameter', self.diametr)
        add_avito_element(ad, 'TireType', self.sezonnost)
        add_avito_element(ad, 'TireSectionWidth', self.shirina_profilya)
        add_avito_element(ad, 'TireAspectRatio', self.vysota_profilya)
        add_avito_element(ad, 'Model', self.model)
        add_avito_element(ad, 'ResidualTread', self.protector_height)
        add_avito_element(ad, 'Quantity', self.qte)
        add_avito_element(ad, 'VideoURL', self.videourl)
        #Осталось собрать фотки
        if self.photos.first() is not None:
            imagezone = ET.SubElement(ad, 'Images')
            for photo in self.photos:
                if photo is not None:
                    add_autoru_property(imagezone, 'Image', '', 'url', os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
                    # add_avito_element(imagezone, 'Image', "url=" + os.path.join(app.config['DOMAIN_NAME'], 'photos', str(photo)).replace('\\', '/'))
                # print(os.path.join(app.config['DOMAIN_NAME'], str(photo)))

        return ad

    def add_drom_tire(self, ad):
        add_avito_element(ad, 'name', self.title)
        add_avito_element(ad, 'manufacturer', self.brand)
        add_avito_element(ad, 'model', self.model)
        add_avito_element(ad, 'mark', self.brand + self.model + self.shirina_profilya + '/' + self.vysota_profilya +
                          self.diametr)
        add_avito_element(ad, 'inSet', self.inSet)
        add_avito_element(ad, 'price', self.price)
        add_avito_element(ad, 'inStock', 'true' if self.inStock else 'false')
        add_avito_element(ad, 'condition', 'used' if self.condition=='Б/у' else 'new')
        add_avito_element(ad, 'wear', self.protector_wear)
        add_avito_element(ad, 'season', 'Зимняя' if 'Зимн' in self.sezonnost else ('Летняя' if 'Летн' in self.sezonnost else 'Всесезонная'))
        add_avito_element(ad, 'quantity', self.qte)
        add_avito_element(ad, 'year', self.product_year)
        add_avito_element(ad, 'spike', 'Шипованная' if 'ипован' in self.sezonnost else 'Без шипов')
        add_avito_element(ad, 'quantity', self.qte)
        #Осталось собрать фотки
        if self.photos.first() is not None:
            for photo in self.photos:
                if photo is not None:
                    add_avito_element(ad, 'picture', os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        return ad

class Rim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baseid = db.Column(db.String(20)) #Уникальный идентификатор на все базы, шины диски и колеса, =r+id для дисков (rim) или t+id для tire или w+id для колес (wheel)
    store = db.Column(db.String(64))  # Номер магазина в Авто.ру
    carbrand=db.Column(db.String(30))
    carmodel=db.Column(db.String(30))
    # carYear=db.Column(db.Integer)
    rimbrand = db.Column(db.String(70))
    rimmodel = db.Column(db.String(70))
    qte = db.Column(db.Float)  # Количество для продажи
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)  # Дата создания объявления
    date_begin = db.Column(db.DateTime, default=datetime.today())  # Дата и время публикации объявления
    date_end = db.Column(db.DateTime, default=datetime.today() + timedelta(
        days=120))  # Дата и время снятия публикации объявления
    listing_fee = db.Column(db.String(20))  # Пакет размещения: Package, PackageSingle или Single
    ad_status = db.Column(db.String(15),
                          default='Free')  # «Free», «Highlight», «XL», «x2_1», «x2_7», «x5_1», «x5_7», «x10_1», «x10_7»
    is_for_priority=db.Column(db.Boolean, default=False) #Для Авто.ру признак продвижения
    avito_id = db.Column(db.String(50))  # Номер объявления на Авито, для связки с объявлением вручную
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # Привязка к владельцу
    avito_show = db.Column(db.Boolean, default=False)
    avtoru_show = db.Column(db. Boolean, default=False)
    drom_show = db.Column(db.Boolean, default=False)
    sold=db.Column(db.Boolean, default=False)
    sold_date=db.Column(db.DateTime())

    # Забрать настройки объявления из настроек пользователя
    allow_email = db.Column(db.Boolean)  # Разрешено написать сообщение через сайт
    manager_name = db.Column(db.String(100))  # Имя контактного лица по данному объявлению
    contact_phone = db.Column(db.String(20))  # Телефон контактного лица, только один российский телефон
    address = db.Column(db.String(256))  # полный адрес объекта — строка до 256 символов, обязательное поле
    latitude = db.Column(db.Float)  # альтернатива Адрес
    longitude = db.Column(db.Float)  # альтернатива Адрес
    display_area1 = db.Column(db.String(256))
    display_area2 = db.Column(db.String(256))
    display_area3 = db.Column(db.String(256))
    display_area4 = db.Column(db.String(256))
    display_area5 = db.Column(db.String(256))
    category = db.Column(db.String(50), default='Запчасти и аксессуары')
    # type_id = db.Column(db.String(6),
    #                     default='10-046')  # 10-048 — Шины, 10-047 — Мотошины, 10-046 — Диски, 10-045 —  Колёса, 10-044 — Колпаки
    ad_type = db.Column(db.String(50),
                        default='Товар приобретен на продажу')  # 'Товар от производителя' или 'Товар приобретен на продажу'
    title = db.Column(db.String(50))  # Название объявления — строка до 50 символов.
    description = db.Column(db.String(
        5000))  # Текстовое описание объявления в соответствии с правилами Авито — строка не более 5000 символов.
    # Если у вас есть оплаченная Подписка, то поместив описание внутрь CDATA, вы можете использовать дополнительное форматирование с помощью HTML-тегов — строго из указанного списка: p, br, strong, em, ul, ol, li.
    price = db.Column(db.Integer)
    condition = db.Column(db.String(10), default='Б/у')  # Новое или Б/у

    oem = db.Column(db.String(10))  # номер делтали OEM, REFERENCE
    recommended_price = db.Column(db.Integer)

    rimtype =db.Column(db.String(20)) #тип диска: Кованные, литые, штампованные, спицованные, сборные
    rimwidth = db.Column(db.String(10))  #Ширина обода
    rimdiametr = db.Column(db.String(10))  # в файле xml RimDiameter
    rimbolts=db.Column(db.Integer)  #количество болтов 3..10
    rimboltsdiametr=db.Column(db.Float) #Диаметр отверстий
    rimoffset=db.Column(db.Float) #Вылет
    rimoriginal=db.Column(db.Boolean, default=False)
    videourl = db.Column(
        db.String(256))  # VideoURL Формат ссылки на видео должен соответствовать - https://www.youtube.com/watch?v=***
    rimyear = db.Column(db.Integer)
    comment = db.Column(db.String(120))  # комментарий
    photos = db.relationship('RimPhoto', backref='rim', lazy='dynamic')
    withDelivery = db.Column(db.Boolean)  # с доставкой
    isShop = db.Column(db.Boolean)  # Магазин
    locationId = db.Column(db.Boolean)  # расположение
    def __repr__(self):
        return '<Диски тип: {} ширина: {} диаметр: {} вылет: {}>'.format(self.rimtype, self.rimwidth, self.rimdiametr, self.rimoffset)

    def add_avtoru_rim(self, ads):
        # columns=['id', 'Заголовок', 'Брэнд', 'Описание', 'Новизна',
        #          'Цена', 'Состояние', 'Диаметр', 'Тип резины', 'Ширина', 'Высота профиля',
        #          'images', 'Количество', 'Отверстий', 'Диаметр отверстий', 'Вылет']
        ad = ET.SubElement(ads, 'part')
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'title', self.title)
        #магазины
        if self.store is not None:
            stores = ET.SubElement(ad, 'stores')
            add_avito_element(stores, 'store', self.store)
        #снова характеристики объявления
        # add_avito_element(ad, 'part_number', self.OEM)
        add_avito_element(ad, 'manufacturer', self.rimbrand)
        add_avito_element(ad, 'description', self.description)
        if self.condition =='Б/у':
            add_avito_element(ad, 'is_new', 'false')
        else:
            add_avito_element(ad, 'is_new', 'true')
        add_avito_element(ad, 'price', round(self.price, 0))
        #Раздел Доступность
        avail = ET.SubElement(ad, 'availability')
        add_avito_element(avail, 'isAvailable', 'True')
        # add_avito_element(avail, 'daysFrom', '0')
        # add_avito_element(avail, 'daysTo', '1')
        properties = ET.SubElement(ad, 'properties')
        add_autoru_property(properties, 'property', self.rimtype, 'name', 'Тип дисков')  #Ширина профиля
        if self.rimoriginal:
            add_autoru_property(properties, 'property', 'Да', 'name', 'Оригинал')  # Ширина профиля

        add_autoru_property(properties, 'property', self.rimtype, 'name', 'Тип дисков')
        add_autoru_property(properties, 'property', self.rimwidth, 'name', 'Ширина диска')
        add_autoru_property(properties, 'property', self.rimdiametr,'name', 'Диаметр диска')
        add_autoru_property(properties, 'property', self.rimbolts, 'name', 'Количество болтов')
        add_autoru_property(properties, 'property', self.rimboltsdiametr, 'name', 'Диаметр сверловки')
        add_autoru_property(properties, 'property', self.rimoffset, 'name', 'Вылет диска')
        add_autoru_property(properties, 'property', self.rimyear, 'name', 'Год производства')
        #Раздел images
        if self.photos.first() is not None:
            imagezone = ET.SubElement(ad, 'images')
            for photo in self.photos:
                if photo is not None:
                    add_avito_element(imagezone, 'image', "url=" + os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        #Раздел properties
        add_avito_element(ad, 'count', self.qte)
        add_avito_element(ad, 'is_for_priority', self.is_for_priority)
        return ads

    def add_avito_rim(self, ad):
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'DateBegin', self.date_begin.isoformat())
        #Дату окончания публикации пока не указываем, в будущем возможно понадобится функциональность
        add_avito_element(ad, 'DateEnd', self.date_end.isoformat())
        add_avito_element(ad, 'ListingFee', self.listing_fee)
        add_avito_element(ad, 'AdStatus', self.ad_status)
        if self.avito_id != '':
            add_avito_element(ad, 'AvitoId', self.avito_id)
        if self.allow_email:
            add_avito_element(ad, 'ContactMethod', 'По телефону и в сообщениях')
        else:
            add_avito_element(ad, 'ContactMethod', 'По телефону')
        if self.manager_name:
            add_avito_element(ad, 'ManagerName', self.manager_name)
        if self.contact_phone:
            add_avito_element(ad, 'ContactPhone', self.contact_phone)
        if self.address is not None:
            add_avito_element(ad, 'Address', self.address)
        if self.address is None and self.latitude is not None:
            add_avito_element(ad, 'Latitude', self.latitude)
            add_avito_element(ad, 'Longitude', self.longitude)

        if self.display_area1 is not None:
            avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).filter(AvitoZones.id == int(self.display_area1)).first()
            areazone = ET.SubElement(ad, 'DisplayAreas')
            add_avito_element(areazone, 'Area', avito_zones[1])
        add_avito_element(ad, 'Category', self.category)
        # dict_types={'Шины':'10-048', 'Мотошины':'10-047', 'Диски':'10-046', 'Колёса':'10-045', 'Колпаки':'10-044'}
        add_avito_element(ad, 'TypeId', '10-046')
        add_avito_element(ad, 'AdType', self.ad_type)
        add_avito_element(ad, 'Title', self.title)
        add_avito_element(ad, 'Description', self.description)
        add_avito_element(ad, 'Price', self.price)
        add_avito_element(ad, 'Condition', self.condition)
        # add_avito_element(ad, 'OEM', self.oem)
        add_avito_element(ad, 'Brand', self.rimbrand)

        add_avito_element(ad, 'RimDiameter', self.rimdiametr)
        add_avito_element(ad, 'RimType', self.rimtype)
        add_avito_element(ad, 'RimWidth', self.rimwidth)
        add_avito_element(ad, 'RimBolts', self.rimbolts)
        add_avito_element(ad, 'RimBoltsDiameter', self.rimboltsdiametr)
        add_avito_element(ad, 'RimOffset', self.rimoffset)
        add_avito_element(ad, 'Quantity', self.qte)
        if not self.videourl is None:
            add_avito_element(ad, 'VideoURL', self.videourl)
        #Осталось собрать фотки
        if self.photos.first() is not None:
            imagezone = ET.SubElement(ad, 'Images')
            for photo in self.photos:
                if photo is not None:
                    add_autoru_property(imagezone, 'Image', '', 'url', os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        return ad

class Wheel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baseid = db.Column(db.String(20)) #Уникальный идентификатор на все базы, шины диски и колеса, =r+id для дисков (rim) или t+id для tire или w+id для колес (wheel)
    store = db.Column(db.String(64))  # Номер магазина в Авто.ру
    carbrand=db.Column(db.String(30))
    carmodel=db.Column(db.String(30))
    rimbrand = db.Column(db.String(70)) #бренд диска
    rimmodel = db.Column(db.String(70)) #модель диска
    qte = db.Column(db.Float)  # Количество для продажи
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)  # Дата создания объявления
    date_begin = db.Column(db.DateTime, default=datetime.today())  # Дата и время публикации объявления
    date_end = db.Column(db.DateTime, default=datetime.today() + timedelta(
        days=120))  # Дата и время снятия публикации объявления
    listing_fee = db.Column(db.String(20))  # Пакет размещения: Package, PackageSingle или Single
    ad_status = db.Column(db.String(15),
                          default='Free')  # «Free», «Highlight», «XL», «x2_1», «x2_7», «x5_1», «x5_7», «x10_1», «x10_7»
    is_for_priority=db.Column(db.Boolean, default=False) #Для Авто.ру признак продвижения
    avito_id = db.Column(db.String(50))  # Номер объявления на Авито, для связки с объявлением вручную
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # Привязка к владельцу
    avito_show = db.Column(db.Boolean, default=False)
    avtoru_show = db.Column(db. Boolean, default=False)
    drom_show = db.Column(db.Boolean, default=False)
    sold=db.Column(db.Boolean, default=False)
    sold_date=db.Column(db.DateTime())

    # Забрать настройки объявления из настроек пользователя
    allow_email = db.Column(db.Boolean)  # Разрешено написать сообщение через сайт
    manager_name = db.Column(db.String(100))  # Имя контактного лица по данному объявлению
    contact_phone = db.Column(db.String(20))  # Телефон контактного лица, только один российский телефон
    address = db.Column(db.String(256))  # полный адрес объекта — строка до 256 символов, обязательное поле
    latitude = db.Column(db.Float)  # альтернатива Адрес
    longitude = db.Column(db.Float)  # альтернатива Адрес
    display_area1 = db.Column(db.String(256))
    display_area2 = db.Column(db.String(256))
    display_area3 = db.Column(db.String(256))
    display_area4 = db.Column(db.String(256))
    display_area5 = db.Column(db.String(256))
    category = db.Column(db.String(50), default='Запчасти и аксессуары')
    # type_id = db.Column(db.String(6),
    #                     default='10-046')  # 10-048 — Шины, 10-047 — Мотошины, 10-046 — Диски, 10-045 —  Колёса, 10-044 — Колпаки
    ad_type = db.Column(db.String(50),
                        default='Товар приобретен на продажу')  # 'Товар от производителя' или 'Товар приобретен на продажу'
    title = db.Column(db.String(50))  # Название объявления — строка до 50 символов.
    description = db.Column(db.String(
        5000))  # Текстовое описание объявления в соответствии с правилами Авито — строка не более 5000 символов.
    # Если у вас есть оплаченная Подписка, то поместив описание внутрь CDATA, вы можете использовать дополнительное форматирование с помощью HTML-тегов — строго из указанного списка: p, br, strong, em, ul, ol, li.
    price = db.Column(db.Integer)
    condition = db.Column(db.String(10), default='Б/у')  # Новое или Б/у

    oem = db.Column(db.String(10))  # номер делтали OEM, REFERENCE
    recommended_price = db.Column(db.Integer)

    rimtype =db.Column(db.String(20)) #тип диска: Кованные, литые, штампованные, спицованные, сборные
    rimwidth = db.Column(db.String(10))  #Ширина обода
    # wrimdiametr = db.Column(db.String(10))  # в файле xml RimDiameter
    rimbolts=db.Column(db.Integer)  #количество болтов 3..10
    rimboltsdiametr=db.Column(db.Float) #Диаметр отверстий
    rimoffset=db.Column(db.Float) #Вылет, ET
    rimoriginal=db.Column(db.Boolean, default=False)
    tirebrand=db.Column(db.String(70)) #бренд шин
    tiremodel=db.Column(db.String(70)) #модель шин
    shirina_profilya=db.Column(db.String(10))  #TireSectionWidth
    vysota_profilya=db.Column(db.String(10))   #TireAspectRatio
    rimdiametr=db.Column(db.String(10))   #в файле xml RimDiameter
    sezonnost=db.Column(db.String(40)) #TireType Всесезонные / Летние /  Зимние нешипованные / Зимние шипованные
    protector_height=db.Column(db.Integer)  #Высота протектора
    protector_wear = db.Column(db.Integer) #Износ протектора
    tireproduct_year = db.Column(db.Integer)  #год производства шин
    differentwidthtires = db.Column(db.Boolean) #Разноширокий комплект шин.
    backrimdiameter =db.Column(db.String(10)) #Диаметр на задней оси если wdifferentwidthtires=True

    videourl = db.Column(
        db.String(256))  # VideoURL Формат ссылки на видео должен соответствовать - https://www.youtube.com/watch?v=***
    rimyear = db.Column(db.Integer)
    comment = db.Column(db.String(120))  # комментарий
    photos = db.relationship('WheelPhoto', backref='wheel', lazy='dynamic')
    withDelivery = db.Column(db.Boolean)  # с доставкой
    isShop = db.Column(db.Boolean)  # Магазин
    locationId = db.Column(db.Boolean)  # расположение
    def __repr__(self):
        return '<Колеса: диски тип {}, ширина: {} диаметр: {} вылет: {} шины диаметр: {} ширина {} высота профиля {}>'.format(self.rimtype, self.rimwidth, self.rimdiametr, self.rimoffset,
                                                                                                                              self.rimdiametr, self.shirina_profilya, self.vysota_profilya)

    def add_avtoru_wheel(self, ads):
        # columns=['id', 'Заголовок', 'Брэнд', 'Описание', 'Новизна',
        #          'Цена', 'Состояние', 'Диаметр', 'Тип резины', 'Ширина', 'Высота профиля',
        #          'images', 'Количество', 'Отверстий', 'Диаметр отверстий', 'Вылет']
        ad = ET.SubElement(ads, 'part')
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'title', self.title)
        #магазины
        if self.store is not None:
            stores = ET.SubElement(ad, 'stores')
            add_avito_element(stores, 'store', self.store)
        #снова характеристики объявления
    #Вернуться и доделать отсюда
        # add_avito_element(ad, 'manufacturer', self.wrimbrand)
        # add_avito_element(ad, 'description', self.description)
        # if self.condition =='Б/у':
        #     add_avito_element(ad, 'is_new', 'false')
        # else:
        #     add_avito_element(ad, 'is_new', 'true')
        # add_avito_element(ad, 'price', round(self.price, 0))
        # #Раздел Доступность
        # avail = ET.SubElement(ad, 'availability')
        # add_avito_element(avail, 'isAvailable', 'True')
        # properties = ET.SubElement(ad, 'properties')
        # add_autoru_property(properties, 'property', self.rimtype, 'name', 'Тип дисков')  #Ширина профиля
        # if self.rimoriginal:
        #     add_autoru_property(properties, 'property', 'Да', 'name', 'Оригинал')  # Ширина профиля
        # add_autoru_property(properties, 'property', self.rimtype, 'name', 'Тип дисков')
        # add_autoru_property(properties, 'property', self.rimwidth, 'name', 'Ширина диска')
        # add_autoru_property(properties, 'property', self.rimdiametr,'name', 'Диаметр диска')
        # add_autoru_property(properties, 'property', self.rimbolts, 'name', 'Количество болтов')
        # add_autoru_property(properties, 'property', self.rimboltsdiametr, 'name', 'Диаметр сверловки')
        # add_autoru_property(properties, 'property', self.rimoffset, 'name', 'Вылет диска')
        # add_autoru_property(properties, 'property', self.rimyear, 'name', 'Год производства')
        # #Раздел images
        # if self.photos.first() is not None:
        #     imagezone = ET.SubElement(ad, 'images')
        #     for photo in self.photos:
        #         if photo is not None:
        #             add_avito_element(imagezone, 'image', "url=" + os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        # #Раздел properties
        # add_avito_element(ad, 'count', self.qte)
        # add_avito_element(ad, 'is_for_priority', self.is_for_priority)
        return ads

    def add_avito_wheel(self, ad):
        add_avito_element(ad, 'Id', self.baseid)
        add_avito_element(ad, 'DateBegin', self.date_begin.isoformat())
        #Дату окончания публикации пока не указываем, в будущем возможно понадобится функциональность
        add_avito_element(ad, 'DateEnd', self.date_end.isoformat())
        add_avito_element(ad, 'ListingFee', self.listing_fee)
        add_avito_element(ad, 'AdStatus', self.ad_status)
        if self.avito_id != '':
            add_avito_element(ad, 'AvitoId', self.avito_id)
        if self.allow_email:
            add_avito_element(ad, 'ContactMethod', 'По телефону и в сообщениях')
        else:
            add_avito_element(ad, 'ContactMethod', 'По телефону')
        if self.manager_name:
            add_avito_element(ad, 'ManagerName', self.manager_name)
        if self.contact_phone:
            add_avito_element(ad, 'ContactPhone', self.contact_phone)
        if self.address is not None:
            add_avito_element(ad, 'Address', self.address)
        if self.address is None and self.latitude is not None:
            add_avito_element(ad, 'Latitude', self.latitude)
            add_avito_element(ad, 'Longitude', self.longitude)

        if self.display_area1 is not None:
            avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).filter(AvitoZones.id == int(self.display_area1)).first()
            areazone = ET.SubElement(ad, 'DisplayAreas')
            add_avito_element(areazone, 'Area', avito_zones[1])
        add_avito_element(ad, 'Category', self.category)
        # dict_types={'Шины':'10-048', 'Мотошины':'10-047', 'Диски':'10-046', 'Колёса':'10-045', 'Колпаки':'10-044'}
        add_avito_element(ad, 'TypeId', '10-045')
        add_avito_element(ad, 'AdType', self.ad_type)
        add_avito_element(ad, 'Title', self.title)
        add_avito_element(ad, 'Description', self.description)
        add_avito_element(ad, 'Price', self.price)
        add_avito_element(ad, 'Condition', self.condition)
        # add_avito_element(ad, 'OEM', self.oem)
        add_avito_element(ad, 'Brand', self.wrimbrand)

        # add_avito_element(ad, 'RimDiameter', self.wrimdiametr)
        add_avito_element(ad, 'RimType', self.wrimtype)
        add_avito_element(ad, 'RimWidth', self.wrimwidth)
        add_avito_element(ad, 'RimBolts', self.wrimbolts)
        add_avito_element(ad, 'RimBoltsDiameter', self.wrimboltsdiametr)
        add_avito_element(ad, 'RimOffset', self.wrimoffset)
        if self.wdifferentwidthtires:
            add_avito_element(ad, 'BackRimDiameter', self.wbackrimdiameter)
        add_avito_element(ad, 'Quantity', self.qte)
#Вернуться и добавить все про шины
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        if not self.videourl is None:
            add_avito_element(ad, 'VideoURL', self.videourl)
        #Осталось собрать фотки
        if self.photos.first() is not None:
            imagezone = ET.SubElement(ad, 'Images')
            for photo in self.photos:
                if photo is not None:
                    add_autoru_property(imagezone, 'Image', '', 'url', os.path.join(app.config['PHOTOS_FOLDER_FULL'], photo.photo).replace('\\', '/'))
        return ad


class TirePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tire_id = db.Column(db.Integer, db.ForeignKey('tire.id', ondelete='CASCADE')) #Привязка к владельцу
    photo=db.Column(db.String(120))
    def __repr__(self):
        return self.photo
    def photos_id(self):
        return self.photo, self.id

class RimPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rim_id = db.Column(db.Integer, db.ForeignKey('rim.id')) #Привязка к владельцу
    photo=db.Column(db.String(120))
    def __repr__(self):
        return self.photo
    def photos_id(self):
        return self.photo, self.id

class WheelPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wheel_id = db.Column(db.Integer, db.ForeignKey('wheel.id')) #Привязка к владельцу
    photo=db.Column(db.String(120))
    def __repr__(self):
        return self.photo
    def photos_id(self):
        return self.photo, self.id