# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from app.home import blueprint
from flask import render_template, redirect, url_for, request,  jsonify
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
import requests
from app import db
from app.base.forms import EditProfileForm, TirePrepareForm, RimPrepareForm, EditTireForm, WheelPrepareForm, AvitoScanForm
from app.base.models import Tire, TirePhoto, TirePrices, ThornPrices, WearDiscounts, TireGuide, AvitoZones, \
    CarsGuide, Wheel, WheelPhoto, DromGuide
from app.api.apimodels import ApiSource
from app.base.models import Rim, RimPhoto, RimPrices
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import MultiDict
from sqlalchemy.sql import func
from sqlalchemy import insert
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
import os
from flask import current_app as app
from datetime import datetime, timedelta
# from decimal import Decimal
import plotly.figure_factory as ff
import plotly
# import plotly.express as px
from scipy.stats import mstats
import json
from app.api.apiroutes import abort_if_param_doesnt_exist
from app.api.apimodels import ApiTire
import plotly.express as px
import threading
# from threading import Timer
from app.api.avitoutils import  getAvitoTirePricesByLocale, getAvitoTirePrices, calculateTheDistance
from time import sleep

# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def is_not_blank(s):
    return bool(s and not s.isspace())

#Процедура ывчисления рекомендованной цены
def calc_recommended_tireprice(args): #brand, model, diametr, size, thorns, is_winter, protector_height

    protector_height=args['protector_height']
    del args['protector_height']
    if 'имние' in args['season']: #Зимние
        coef_wear = db.session.query(WearDiscounts.winter_discount).filter(WearDiscounts.protector_height.__eq__(protector_height)).scalar()
    else: #Летние и всесезонные
        coef_wear = db.session.query(WearDiscounts.summer_discount).filter(WearDiscounts.protector_height.__eq__(protector_height)).scalar()

    # print(args)
    query = db.session.query(func.avg(TireGuide.price).label('average')).filter_by(**args)
    df = pd.read_sql(query.statement, query.session.bind)
    if df.iloc[0][0] is None:
        for key in args.keys() - ['brand']:
            del args[key]
            query = db.session.query(func.avg(TireGuide.price).label('average')).filter_by(**args)
            df = pd.read_sql(query.statement, query.session.bind)
            if not df.iloc[0][0] is None: break #Выходим из цикла как только нашли не нулевое значение
    # print(df.head())

    if not df.iloc[0][0] is None:
        avg_price=df.iloc[0][0]
    else:
        avg_price=0
    protector_height=round(float(protector_height), 0)
    if not coef_wear: coef_wear=0.
    newTire_price = round(avg_price, 0)
    avg_price = round(float(avg_price) * (1.-coef_wear), 0)
    # print('Износ={}, новая цена {}'.format(coef_wear, avg_price))
    return avg_price, newTire_price

#Процедура вычисления рекомендованной стоимости диска
def calc_recommended_rimprice(brand, model, original, diametr, width, ET, bolts, dia, age):
    # Подбираем цену только по Бренду, диаметру и ширине
    wear={0:0.2, 1:0.2, 2:0.3, 3:0.4, 4:0.5, 5:0.6, 6:0.7, 7:0.8, 8:0.9}
    diametr=diametr
    avg_price = 0.
    bBrand=False
    bWidth=False
    bDiametr=False
    strSelectString = 'SELECT avg(price) AS avg_price FROM rim_prices '
    if brand is None:
        brand=''
    brandCondition = 'CASE brand WHEN "' + brand + '" THEN 1 ELSE 0 END '
    if width is None:
        width=''
    widthCondition = 'CASE width WHEN "' + width + '" THEN 1 ELSE 0 END '
    # if original is False:
    #     original=''
    # originalCondition = 'CASE original WHEN ' + original + ' THEN 1 ELSE 0 END'
    if diametr is None:
        diametr=''
    diametrCondition = 'CASE diametr WHEN "' + diametr + '" THEN 1 ELSE 0 END '

    # print('brand={} model={}'.format(brand, model))
    if brand or width or diametr:
        strSelectString = strSelectString + ' WHERE '
    strDiametrWidth = strSelectString #Без бренда
    strDiametr = strSelectString #Только по диаметру
    strWidth = strSelectString #Только по ширине

    if len(brand)>0:
        bBrand=True
        strSelectString = strSelectString + brandCondition
        strBrandDiametr = strSelectString #Без ширины
        strBrandWidth = strSelectString #Без Диаметра

    if len(diametr)>0:
        if bBrand:
            strSelectString = strSelectString + ' AND '
            strBrandDiametr = strBrandDiametr + ' AND ' + diametrCondition # Без ширины
        strSelectString = strSelectString + diametrCondition
        strDiametrWidth = strDiametrWidth + diametrCondition # Без бренда
        strDiametr = strDiametr + diametrCondition  # Только по диаметру
        bDiametr=True

    if len(width)>0:
        if bDiametr:
            strSelectString = strSelectString + ' AND ' + widthCondition
            strDiametrWidth = strDiametrWidth + ' AND ' + widthCondition
        if bBrand:
            strBrandWidth = strBrandWidth + ' AND ' + widthCondition # Без Диаметра
        bWidth=True

    strSelectString = strSelectString + ';'
    if bBrand:
        strBrandDiametr = strBrandDiametr + ';'
        strBrandWidth = strBrandWidth + ';'
    if bDiametr:
        strDiametrWidth = strDiametrWidth + ';'
        strDiametr = strDiametr + ';'

    # print('strSelectString=', str(strSelectString))
    dfavg_price = pd.read_sql(strSelectString, db.session.bind)
    # print(dfavg_price)
    if dfavg_price.iloc[0, 0] is None and (bBrand and bDiametr): #Ищем без ширины профиля
        # print('strBrandDiametr=', str(strBrandDiametr))
        dfavg_price = pd.read_sql(strBrandDiametr, db.session.bind)
    if dfavg_price.iloc[0, 0] is None and (bBrand and bWidth): #Ищем без диаметра
        # print('strBrandWidth=', str(strBrandWidth))
        dfavg_price = pd.read_sql(strBrandWidth, db.session.bind)
    if dfavg_price.iloc[0, 0] is None and (bDiametr and bWidth): #Ищем без бренда
        # print('strDiametrWidth=', str(strDiametrWidth))
        dfavg_price = pd.read_sql(strDiametrWidth, db.session.bind)
    if dfavg_price.iloc[0, 0] is None and bDiametr: #Ищем только по диаметру
        # print('strDiametr=', str(strDiametr))
        dfavg_price = pd.read_sql(strDiametr, db.session.bind)

    if not dfavg_price.iloc[0, 0] is None:
        avg_price=dfavg_price.iloc[0, 0]
        # print(avg_price)
    #вычисляем износ от возраста
    if age>8: age=8 #Старше 8 лет всегда 90% износ
    coef_wear = wear[age]
    if not coef_wear:
        coef_wear=0.
    newRim_price = round(avg_price, 0)
    avg_price = round(float(avg_price) * (1.-coef_wear), 0)
    # print(newRim_price, avg_price)
    return avg_price, newRim_price

def get_avito_data(avito_client_id, avito_client_secret):
    avito_object = {'id' :'', 'name':'', 'email':'', 'phone':'', 'profile_url':'', 'balance_real':'', 'balance_bonus':''}
    tokenurl = 'https://api.avito.ru/token/'
    headers = {'Accept': 'application/json'}
    params = {'grant_type': 'client_credentials',
              'client_id': avito_client_id,
              'client_secret': avito_client_secret}
    # print('Client ID={}, Secret={}'.format(avito_client_id, avito_client_secret))
    res = requests.get(tokenurl, headers=headers, params=params)  # , proxies=proxies
    # print(res.json())
    if res.status_code==200:
        token = res.json()['access_token']
        url = 'https://api.avito.ru/core/v1/accounts/self'
        headers = {'Accept': 'application/json', 'Authorization': 'Bearer ' + token}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            avito_object['id'] = res.json()['id']
            avito_object['name'] = res.json()['name']
            avito_object['email'] = res.json()['email']
            avito_object['phone'] = res.json()['phone']
            avito_object['profile_url'] = res.json()['profile_url']
        #Баланс кошелька
        url='https://api.avito.ru/core/v1/accounts/' + str(avito_object['id']) +'/balance/'
        res = requests.get(url, headers=headers)
        # print(res.json())
        if res.status_code == 200:
            avito_object['balance_real'] = res.json()['real']
            avito_object['balance_bonus'] = res.json()['bonus']
    return avito_object

@blueprint.route('/init_tire_prix', methods=['GET'])
@login_required
def init_tire_prix():

    if ApiSource.query.get(1) is None:
        db.session.add_all([ApiSource(source='Avito'), ApiSource(source='Drom')])

    if TirePrices.query.get(1) is None: #Загружаем только если пустые таблицы
        prices = TirePrices()
        prices.load_prices_base()
    if RimPrices.query.get(1) is None:
        rims_prices = RimPrices()
        rims_prices.load_prices_base()
    if ThornPrices.query.get(1) is None:
        thorns = ThornPrices()
        thorns.load_thornprices()
    if WearDiscounts.query.get(1) is None:
        wear = WearDiscounts()
        wear.load_weardiscounts()
    if TireGuide.query.get(1) is None:
        tireguide=TireGuide()
        tireguide.load_tireguide_base()
    if CarsGuide.query.get(1) is None:
        carsguide=CarsGuide()
        carsguide.load_carsguide_base()
    if AvitoZones.query.get(1) is None:
        avitozones=AvitoZones()
        avitozones.load_avitozones()
    if DromGuide.query.get(1) is None:
        dromGuide=DromGuide()
        dromGuide.load_dromguide()


    return render_template('index.html', segment='index')


@blueprint.route('/load_rim_prix', methods=['POST'])
@login_required
def load_rim_prix():
    # tire_price=''
    s = request.get_json(force=True)

    brand = '' if str(s['brand']).find('Выберите')>=0 else s['brand']
    model = '' if str(s['model']).find('Выберите')>=0 else s['model']
    diametr = s['diametr']
    original=s['original']
    # print('rimyear=', s['rimyear'])
    age=datetime.today().year - int(s['rimyear'])
    # print(age)
    ET = s['ET']
    width=s['width']
    bolts=s['bolts']
    dia=s['dia']
    qte= s['qte']
    avgPrice, newRim_price = calc_recommended_rimprice(brand = brand, model=model, original=original, diametr = diametr, ET = ET, width = width,
                                            bolts= bolts, dia = dia, age=age)
    # print(avgPrice, newRim_price)
    rim_price = int(avgPrice * int(qte))
    # print(rim_price)
    return jsonify({'rim_price': rim_price, 'newRimPrice': newRim_price,'brand': brand, 'model':model, 'diametr':diametr})

#Снимаем с или ставим на продажу
@blueprint.route('/stock_tables/change_tire_state', methods=['POST'])
@login_required
def change_tire_state():
    sites_dict={'idSold':'sold',
                'idAvito':'avito_show',
                'idYoula':'youla_show',
                'idDrom':'drom_show'
    }
    s = request.get_json(force=True)
    field_toChange = str(sites_dict.get(s['id'].split('_')[0]))
    id_field = str(s['id'].split('_')[1])
    currObject=(Tire if id_field[0]=='t' else (Rim if id_field[0]=='r' else Wheel) ) # Rim if id_field[0]=='r' else Wheel
    # print(id_field)
    blSold = False
    curr_tire = db.session.query(currObject).filter(currObject.baseid == id_field).first()
    # print(curr_tire)
    if field_toChange!='sold':  #Здесь просто меняем статус каждой площадки
        new_value=s['value']  #Потому что только sold !=в Продаже, а остальные поля соответствуют checked
        db.session.query(currObject).filter(currObject.baseid == id_field). \
            update({field_toChange: new_value}, synchronize_session="evaluate")

        if field_toChange=='avito_show':
            if  not new_value:  #Снимаем с продажи на площадке Avito
                db.session.query(currObject).filter(currObject.baseid == id_field). \
                    update({'sold_date': datetime.utcnow()}, synchronize_session="evaluate")
                db.session.query(currObject).filter(currObject.baseid == id_field). \
                    update({'date_end': datetime.utcnow()}, synchronize_session="evaluate")
            else: #Возвращаем в продажу
                curr_tire.date_end=curr_tire.date_begin+timedelta(days=120)
                curr_tire.sold_date = None
    else: #Если снимаем с продажи - то выключаем все маркеры!
        new_value = not s['value']
        db.session.query(currObject).filter(currObject.baseid == id_field). \
            update({field_toChange : new_value}, synchronize_session="evaluate")
        curr_tire.sold_date=None

        if field_toChange=='sold' and new_value == True: #Значит снимаем с продажи на всех площадках!
            blSold = True
            for ploschadka in ['avito_show', 'youla_show', 'drom_show']:
                db.session.query(currObject).filter(currObject.baseid == id_field). \
                    update({ploschadka: False}, synchronize_session="evaluate")
                # И дату снятия с публикации меняем
                db.session.query(currObject).filter(currObject.baseid == id_field). \
                    update({'sold_date': datetime.utcnow()}, synchronize_session="evaluate")
                db.session.query(currObject).filter(currObject.baseid == id_field). \
                    update({'date_end': datetime.utcnow()}, synchronize_session="evaluate")

    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    return jsonify({'id': id_field, 'sold':blSold})


#Снимаем с или ставим продвижение Авито
@blueprint.route('/stock_tables/change_promo_state', methods=['POST'])
@login_required
def change_promo_state():
    # Проверяем статус: 'Free', 'Highlight', 'XL', 'x2_1', 'x2_7', 'x5_1', 'x5_7', 'x10_1', 'x10_7'
    sites_dict={'idFree':'Free',
                'idHighlight':'Highlight',
                'idx2-1':'x2_1',
                'idx5-1':'x5_1',
                'idx10-1':'x10_1',
                'idXL':'XL',
                'idx2-7':'x2_7',
                'idx5-7':'x5_7',
                'idx10-7':'x10_7'
    }
    s = request.get_json(force=True)
    promo_status = str(sites_dict.get(s['id'].split('_')[0]))
    id_field = str(s['id'].split('_')[1])
    #Меняем статус публикации объявления в базе данных
    currObject=(Tire if id_field[0]=='t' else (Rim if id_field[0]=='r' else Wheel)) # Rim if id_field[0]=='r' else Wheel

    db.session.query(currObject).filter(currObject.baseid == id_field). \
            update({'ad_status': promo_status}, synchronize_session="evaluate")
    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    return jsonify({'id': id_field, 'status':promo_status})

#Сменился бренд, надо вернуть список моделей
@blueprint.route('/changeBrandRequest', methods=['POST'])
@login_required
def changeBrandRequest():
    s = request.get_json(force=True)
    brand=s['brand']
    models=TireGuide.query.with_entities(TireGuide.id, TireGuide.model).filter(TireGuide.brand==brand)\
        .group_by(TireGuide.model).order_by(TireGuide.model).all()
    modelsresult=[]
    for model in models:
        modelsresult.append(model._asdict())
    # print(modelsresult)
    return jsonify(modelsresult)

#Сменился бренд, надо вернуть список моделей
@blueprint.route('/changeCarBrandRequest', methods=['POST'])
@login_required
def changeCarBrandRequest():
    s = request.get_json(force=True)
    brand=s['carBrand']
    models=CarsGuide.query.with_entities(CarsGuide.id, CarsGuide.model).filter((CarsGuide.brand==brand) & (CarsGuide.rimDiametr.isnot(None)))\
        .group_by(CarsGuide.model).order_by(CarsGuide.model).all()
    modelsresult=[]
    for model in models:
        modelsresult.append(model._asdict())
    # print(modelsresult)
    return jsonify(modelsresult)


#Сменился бренд диска, надо вернуть список моделей
@blueprint.route('/changeRimBrandRequest', methods=['POST'])
@login_required
def changeRimBrandRequest():
    s = request.get_json(force=True)
    brand=s['brand']
    models=RimPrices.query.with_entities(RimPrices.id, RimPrices.model).filter(RimPrices.brand==brand)\
        .group_by(RimPrices.model).order_by(RimPrices.model).all()
    modelsresult=[]
    for model in models:
        modelsresult.append(model._asdict())
    # print(modelsresult)
    return jsonify(modelsresult)

#Сменилась модель, надо поменять сезонность
@blueprint.route('/changeModelRequest', methods=['POST'])
@login_required
def changeModelRequest():
    s = request.get_json(force=True)
    brand= s['brand']
    model = s['model']
    season_thorns=TireGuide.query.with_entities(TireGuide.id, TireGuide.season, TireGuide.thorns, TireGuide.purpose,
                                                TireGuide.description, TireGuide.price)\
        .filter((TireGuide.model==model) & (TireGuide.brand==brand))\
        .group_by(TireGuide.season, TireGuide.thorns).order_by(TireGuide.season).first()
    result=season_thorns._asdict()
    season=result['season']
    thorns = result['thorns'] if result['thorns'] else False
    if (season=='Зимние') & (thorns):
        season = season + ' шипованные'
    elif (season == 'Зимние') & (not thorns):
        season = season + ' нешипованные'
    return jsonify({'season': season, 'purpose':result['purpose'], 'price':result['price'], 'description':result['description']})


#Сменилась модель, надо поменять сезонность
@blueprint.route('/changeCarModelRequest', methods=['POST'])
@login_required
def changeCarModelRequest():
    s = request.get_json(force=True)
    brand= s['brand']
    model = s['model']
    # print(s)
    yearList=CarsGuide.query.with_entities(CarsGuide.id, CarsGuide.brand, CarsGuide.model, CarsGuide.ET, CarsGuide.rimDiametr, CarsGuide.rimWidth,
                                           CarsGuide.rimBolts, CarsGuide.rimDia, CarsGuide.year)\
        .filter((CarsGuide.model==model) & (CarsGuide.brand==brand) & (CarsGuide.rimDiametr.isnot(None)))\
        .group_by(CarsGuide.year).order_by(CarsGuide.year).first()
    result=yearList._asdict()
    # print(result)
    return jsonify(result)

#Выбрали неоригинал
@blueprint.route('/change_original_state', methods=['POST'])
@login_required
def change_original_state():
    rimsList=RimPrices.query.with_entities(RimPrices.id, RimPrices.brand).group_by(RimPrices.brand).all()
    # rimsList.insert(0, (-1, 'Выберите бренд'))
    # print(rimsList)
    brandsResult=[]
    for cur_rim in rimsList:
        # print(type(cur_rim))
        brandsResult.append(cur_rim._asdict())
    # print(brandsResult)
    brandsResult.insert(0, dict(id=-1, brand='Выберите бренд'))
    return jsonify(brandsResult)


#Снимаем с или ставим продвижение Авито
@blueprint.route('/stock_tables/change_avtorupromo_state', methods=['POST'])
@login_required
def change_avtorupromo_state():
    sites_dict={'idis-for-priority':'is_for_priority'}
    s = request.get_json(force=True)
    # print('value=',s['value'])
    new_value = s['value']
    promo_status = str(sites_dict.get(s['id'].split('_')[0]))
    id_field = str(s['id'].split('_')[1])
    currObject=(Tire if id_field[0]=='t' else (Rim if id_field[0]=='r' else Wheel)) # Rim if id_field[0]=='r' else Wheel
    #Меняем статус публикации объявления в базе данных
    db.session.query(currObject).filter(currObject.baseid == id_field). \
            update({'is_for_priority': new_value}, synchronize_session="evaluate")
    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    return jsonify({'id': id_field, 'value':new_value})

@blueprint.route('/index.html')
@login_required
def index():
    return render_template('index.html', segment='index') #, graphJSON=createGraph(dfTire, regionsList[0]), regions=regionsList

def createGraph(dfTire, region):
    dfToShow = dfTire.loc[(dfTire['region'] == region) & (dfTire['diametr'] == 15)]
    distData = dfToShow['unitPrice']
    # Обрезаем выбросы, слева и справа по 1%
    distData = pd.Series(mstats.winsorize(distData, limits=[0.01, 0.01]))
    dfToShow = dfToShow.loc[dfToShow['unitPrice'] < distData.max()]
    hist_data = [distData]
    fig = ff.create_distplot(hist_data, [region], bin_size=500, rug_text=region)
    fig.update_layout(title='Распределение цен', template='plotly_white')
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@blueprint.route('/updateWear', methods=['POST'])
@login_required
def updateWear():
    args = request.get_json(force=True)
    # print(args)
    argDict={'protector_height':args['protector_height']}
    query = db.session.query(WearDiscounts.protector_height, WearDiscounts.summer_discount, WearDiscounts.winter_discount).filter_by(**argDict).limit(1)
    dfDiscount = pd.read_sql(query.statement, query.session.bind).set_index('protector_height')
    if 'season' in args:
        discount = dfDiscount.loc[int(args['protector_height']), 'summer_discount'] if 'етние' in args['season'] else dfDiscount.loc[int(args['protector_height']), 'winter_discount']
    else:
        discount = 0.

    # print('discount', discount)

    return str(round(discount*100))

def checkChartArgs(args):
    seasonDict = { 'Зимние шипованные':'zimnie_shipovannye',
                  'Зимние нешипованные':'zimnie_neshipovannye',
                  'Летние':'letnie',
                  'Всесезонные': 'vsesezonnye'}

    if 'region' in args:
        # Забираем зоны Авито
        query = db.session.query(AvitoZones.zone, AvitoZones.engzone).filter(AvitoZones.zone == args['region']).limit(1)
        dfZones = pd.read_sql(query.statement, query.session.bind).set_index('zone')
        region = dfZones.loc[args['region'], 'engzone']
        args['region']=region #Меняем на латиницу
    else:
        region = 'rossiya'

    if 'count' in args:
        recCount = args['count']
        del args['count']
    else:
        recCount = 300  # По умолчанию передаем 300 значений

    if 'pages' in args:
        pages = int(args['pages'])
        del args['pages']
    else:
        pages = 10  # По умолчанию смотрим 10 страниц

    if 'protector_wear' in args:
        del args['protector_wear']

    if 'season' in args:
        season = seasonDict.get(args['season']) #А в авито - латиница
    else:
        season = 'zimnie_neshipovannye'
    # print(args)
    for key in ['width', 'height']:
        if key in args:
            args[key]=int(args[key])

    return args, region, season, pages, recCount

@blueprint.route('/updateChartNow', methods=['POST'])
@login_required
def updateChartNow():
    args = request.get_json(force=True)  # flat=False
    # print('args=', args)
    if args.get('protector_wear') =='':
        protector_wear=10.
    else:
        protector_wear = int(args.get('protector_wear'))
    protector_wear=protector_wear/100.

    # Выполняем все проверки
    argsDict = dict([(k, v) for k, v in args.items() if (v != '' and v !='Выберите бренд')])
    argsDict, region, season, pages, recCount = checkChartArgs(argsDict)
    brand=None
    if 'brand' in  argsDict: #убираем из фильтра - потом сделаем список из датафрейма
        brand = argsDict['brand']
        del argsDict['brand']
    # print('argsDict=', argsDict)
    query = db.session.query(ApiTire.brand, ApiTire.season, ApiTire.wear_num, ApiTire.unitPrice, ApiTire.avito_link).filter_by(
        **argsDict).filter(ApiTire.wear_num != None).limit(recCount)
    df = pd.read_sql(query.statement, query.session.bind)
    df=df.loc[df.wear_num>0]
    df.drop_duplicates(inplace=True)
    df['brandName'] = 'Все бренды'
    # print(df.head())
    if brand: #Второй график делаем с фильтром по бренду
        df2 = df.loc[df.brand.str.contains(brand, case=False)].copy(deep=True)
        df2['brandName'] = brand
        df=pd.concat([df, df2])

    # print(df.head())
    fig = px.scatter(
        df, x='wear_num', y='unitPrice',  trendline='ols', color='brandName',  hover_data=['brand'],
        labels={
            "wear_num": "Износ, %",
            "unitPrice": "Цена за 1 штуку, руб."
        }, title='Распределение цен на шины', template='plotly_white'
    )
    model = px.get_trendline_results(fig)
    # print(model)
    predictPrice=None

    if not model.empty:
        results = model.iloc[0]["px_fit_results"]
        if brand and len(model)>1: #значит есть вторая линия
            results = model.iloc[1]["px_fit_results"]
        # print(results)
        alpha = results.params[0]
        beta = results.params[1]
        predictPrice=round(alpha+beta*protector_wear)
        #Если рекомендуемая цена <0 то 25 руб
        predictPrice = predictPrice if predictPrice>0 else 25.
        fig.add_scatter(x=[protector_wear], y=[predictPrice], mode="markers", marker_symbol='circle-x',
                    marker=dict(size=15, color="orange", ),
                    name="рекомендованная цена")

    fig.update_layout(xaxis=dict(tickformat=',.0%', hoverformat=",.0%"), legend=dict(orientation="h",
        yanchor="bottom", y=1.02,  xanchor="left", x=-0.1, title_text=''))

    return jsonify({'chartData':json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder), 'predictResult':predictPrice})

@blueprint.route('/start_TirePricesScan', methods=['POST'])
def start_TirePricesScan():
    """Запускает сканирование предложений на Авито
    и возвращает ссылку на обработчик результатов и id задачи в Celery"""

    args = request.get_json(force=True)  # flat=False
    # Выполняем все проверки
    argsDict = dict([(k, v) for k, v in args.items() if (v != '')])
    args, region, season, pages, recCount = checkChartArgs(argsDict)
    tirePricesTask = getAvitoTirePrices.delay(args.get('diametr'), args.get('width'), args.get('height'), region, season, pages)

    return jsonify({}), 202, {'Location': url_for('home_blueprint.updateTirePrices', task_id=tirePricesTask.id)}

@blueprint.route('/updateTirePrices', methods=['POST'])
@login_required
def updateTirePrices():

    args = request.get_json(force=True)  # flat=False
    task = getAvitoTirePrices.AsyncResult(args['task_id'])
    del args['task_id']

    # Выполняем все проверки и готовим объект для графика
    argsDict = dict([(k, v) for k, v in args.items() if (v != '')])
    args, region, season, pages, recCount = checkChartArgs(argsDict)
    query = db.session.query(ApiTire.brand, ApiTire.season, ApiTire.wear_num, ApiTire.unitPrice).filter_by(
        **args).limit(recCount)
    df = pd.read_sql(query.statement, query.session.bind)
    if not df.empty:
        df=df.loc[df.wear_num>0]
        df.drop_duplicates(inplace=True)
        # print(df.head())
        fig = px.scatter(
            df, x='wear_num', y='unitPrice',  trendline='ols', trendline_color_override='orange', hover_data=['brand'],
            labels={
                "wear_num": "Износ, %",
                "unitPrice": "Цена за 1 штуку, руб."
            }, title='Распределение цен на шины', template='plotly_white'
        )
        fig.update_layout(xaxis=dict(tickformat=',.0%', hoverformat=",.0%"))
        return jsonify({'state':task.state, 'graphData': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder), 'currPage':task.result})
    else:
        return jsonify({'state': task.state, 'graphData': None, 'currPage': task.result})

@blueprint.route('/settings.html', methods=['GET', 'POST'])
@login_required
def settings():
    # print(request.form)
    form = EditProfileForm(request.form)  #current_user.username
    if 'Get_Avito' in request.form:
        # print('Мы здесь')
        if is_not_blank(form.avito_client_id.data) and is_not_blank(form.avito_client_secret.data):
            avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(
                AvitoZones.zone).order_by(AvitoZones.id).all()
            form.def_display_area1.choices = avito_zones
            form.def_display_area1.default = current_user.def_display_area1
            form.process()
            form.avito_client_id.data = current_user.avito_client_id
            form.avito_client_secret.data = current_user.avito_client_secret
            form.avito_profile_url.data = current_user.avito_profile_url
            form.store.data=current_user.store
            form.avito_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.avito_path).replace('\\', '/')
            form.autoru_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.autoru_path).replace('\\', '/')
            form.drom_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.drom_path).replace('\\', '/')
            avito = get_avito_data(current_user.avito_client_id, current_user.avito_client_secret)
            if avito['id']:
                current_user.avito_profile_idNum = avito['id']
            # current_user.def_manager_name = avito['name']
            # current_user.def_contact_mail = avito['email']
            # if is_not_blank(avito['phone']):
            #     current_user.def_contact_phone = avito['phone']
            # else:
            #     current_user.def_contact_phone = form.def_contact_phone.data
            if avito['profile_url']:
                current_user.avito_profile_url = avito['profile_url']
            if avito['balance_real']:
                current_user.avito_balance_real = avito['balance_real']
            if avito['balance_bonus']:
                current_user.avito_balance_bonus = avito['balance_bonus']
            if avito['id']:
                current_user.avito_profile_idNum = avito['id'] #При этом в форму его не выводим
            current_user.avito_client_id = form.avito_client_id.data
            current_user.avito_client_secret = form.avito_client_secret.data
            db.session.commit()
            form.avito_profile_url.data = current_user.avito_profile_url
            # form.avito_profile_idNum=current_user.avito_profile_idNum
            form.avito_balance_real.data = current_user.avito_balance_real
            form.avito_balance_bonus.data = current_user.avito_balance_bonus
            form.def_allow_email.data = current_user.def_allow_email
            form.def_manager_name.data = current_user.def_manager_name
            form.def_contact_phone.data = current_user.def_contact_phone
            form.def_contact_mail.data = current_user.def_contact_mail
            form.def_adress.data = current_user.def_adress
            form.def_latitude = current_user.def_latitude
            form.def_longitude = current_user.def_longitude

    if 'Save' in request.form:
    # if form.validate_on_submit():
        current_user.def_contact_mail = form.def_contact_mail.data
        # current_user.avito_balance_bonus = form.avito_balance_bonus.data
        current_user.def_contact_phone = form.def_contact_phone.data
        current_user.def_manager_name = form.def_manager_name.data
        #Досюда в условие else
        current_user.def_adress = form.def_adress.data
        # current_user.def_latitude = form.def_latitude.data
        # current_user.def_longitude = form.def_longitude.data
        current_user.def_display_area1 = form.def_display_area1.data
        current_user.store = form.store.data
        current_user.def_latitude = form.def_latitude.data if form.def_latitude.data != '' else None
        current_user.def_longitude = form.def_longitude.data if form.def_latitude.data != '' else None

        db.session.commit()
        # flash('Your changes have been saved.')
        return redirect(url_for('home_blueprint.settings'))

    elif request.method == 'GET':
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.def_display_area1.choices = avito_zones
        form.def_display_area1.default=current_user.def_display_area1
        form.process()
        form.avito_client_id.data = current_user.avito_client_id
        form.avito_client_secret.data = current_user.avito_client_secret
        form.avito_profile_url.data = current_user.avito_profile_url
        form.store.data=current_user.store
        form.avito_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.avito_path).replace('\\', '/')
        form.autoru_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.autoru_path).replace('\\', '/')
        form.drom_path.data=os.path.join(request.host_url, app.config['XML_FOLDER'], current_user.drom_path).replace('\\', '/')
        form.avito_balance_real.data = current_user.avito_balance_real
        form.avito_balance_bonus.data = current_user.avito_balance_bonus
        form.def_allow_email.data = current_user.def_allow_email
        form.def_manager_name.data = current_user.def_manager_name
        form.def_contact_phone.data = current_user.def_contact_phone
        form.def_contact_mail.data = current_user.def_contact_mail
        form.def_adress.data = current_user.def_adress
        form.def_latitude.data = current_user.def_latitude
        form.def_longitude.data = current_user.def_longitude

    return render_template('settings.html', title='Заполнение профиля', user=current_user, form=form, segment='settings')  #title='Заполнение профиля', user=current_user, form=form

#Создаем новое объявление о продаже шин
@blueprint.route('/tire.html', methods=['GET', 'POST'])
@login_required
def tire():
    curr_store=current_user.store
    # form = TirePrepareForm(request.form)  #current_user.username
    brands=TireGuide.query.with_entities(TireGuide.id, TireGuide.brand).group_by(TireGuide.brand).all()
    brands.insert(0, (-1, 'Выберите бренд'))
    form = TirePrepareForm(CombinedMultiDict((request.files, request.form)))
    form.brand.choices=brands
    tirephotos=[url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example1.jpg').replace('\\', '/')),
                url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example2.jpg').replace('\\', '/')),
                url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example3.jpg').replace('\\', '/'))]
    if 'Save' in request.form:
        # print('Мы здесь')
        brands=dict(brands)
        currBrand=brands[form.brand.data] if form.brand.data else None
        if currBrand:
            models=dict(TireGuide.query.with_entities(TireGuide.id, TireGuide.model).filter(TireGuide.brand.__eq__(currBrand)).group_by(TireGuide.model).all())
            # print('form.model.data=',form.model.data)
            # print(tire.recommended_price)
        newtire = Tire(
            brand=currBrand,
            model=models[form.model.data] if (form.model.data and form.model.data!=-1) else None,
            listing_fee=form.listing_fee.data, ad_status=form.ad_status.data, avito_id=form.avito_id.data,
            manager_name=form.manager_name.data, contact_phone=form.contact_phone.data, address=form.address.data,
            display_area1=form.display_area1.data,
            ad_type=form.ad_type.data, qte=form.qte.data,  inSet=form.inSet.data, title=form.title.data, description=form.description.data,
            price=form.price.data, recommended_price=form.recommended_price.data, condition=form.condition.data, shirina_profilya=form.shirina_profilya.data,
            vysota_profilya=form.vysota_profilya.data,
            diametr=form.diametr.data, owner=current_user, sezonnost=form.sezonnost.data,
            protector_height=form.protector_height.data,  protector_wear=form.protector_wear.data,
            store=curr_store,
            avito_show = form.avito_show.data, youla_show = form.youla_show.data, drom_show=form.drom_show.data,
            videourl=form.videourl.data,
            product_year=form.product_year.data,
            youla_status = form.youla_status.data)
        newtire.baseid='t' + str(newtire.id)
    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = TirePhoto(tire=newtire, photo=new_filename)
                db.session.add(newphoto)

        db.session.add(newtire)
        db.session.commit()
        newtire.baseid='t' + str(newtire.id)
        db.session.commit()
        current_user.to_avito_xml()
        current_user.to_avtoru_xml()
        current_user.to_drom_xml()
        current_user.to_youla_xml()

        # flash('Ваше предложение зарегистрировано!')
        return redirect(url_for('home_blueprint.tire'))
    elif request.method == 'GET':
        form.brand.choices = brands
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        form.display_area1.default=current_user.def_display_area1
        form.process()
        form.listing_fee.data='Package',
        # form.ad_status.data='Free',
        form.condition.data='Б/у',

        form.description.data='Комплект резины'
        form.manager_name.data = current_user.def_manager_name
        form.contact_phone.data = current_user.def_contact_phone
        form.address.data = current_user.def_adress
        return render_template('tire.html', title='Предложение по шинам', user=current_user, form=form,
                               segment='tire', tirephotos=tirephotos, graphJSON=[])


@blueprint.route('/rim.html', methods=['GET', 'POST'])
@login_required
def rim():
    curr_store=current_user.store
    carBrands=CarsGuide.query.with_entities(CarsGuide.id, CarsGuide.brand).group_by(CarsGuide.brand).all()
    carBrands.insert(0, (-1, 'Выберите бренд'))

    # carModels=CarsGuide.query.with_entities(CarsGuide.id, CarsGuide.model).filter((CarsGuide.brand==brand) & (CarsGuide.rimDiametr.isnot(None)))\
    #     .group_by(CarsGuide.model).order_by(CarsGuide.model).all()

    brands=RimPrices.query.with_entities(RimPrices.id, RimPrices.brand).group_by(RimPrices.brand).all()
    brands.insert(0, (-1, 'Выберите бренд'))

    form = RimPrepareForm(CombinedMultiDict((request.files, request.form)))
    if request.method =='GET':
        form.carbrand.choices=carBrands
        form.rimbrand.choices=brands
        rimphotos=[url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example1.jpg').replace('\\', '/')),
                    url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example2.jpg').replace('\\', '/')),
                    url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example3.jpg').replace('\\', '/'))]
    if 'Save' in request.form:
        carBrands = dict(carBrands)
        rimModel= request.form['rimmodel'] if 'rimmodel' in request.form else None  #Если не выбирали бренд дисков - то модели дисков нет
        newrim = Rim(
            carbrand=carBrands[int(request.form['carbrand'])] if request.form['carbrand'] else None,
            carmodel=request.form['carmodel'],
            rimbrand=request.form['rimbrand'],
            rimmodel=rimModel, #Они менялись динамически на фронте, поэтому берем из request.for,
            listing_fee=form.listing_fee.data, ad_status=form.ad_status.data, avito_id=form.avito_id.data,
            manager_name=form.manager_name.data, contact_phone=form.contact_phone.data, address=form.address.data,
            display_area1=form.display_area1.data,
            ad_type=form.ad_type.data, qte=form.qte.data, inSet = form.inSet.data,
            title=form.title.data, description=form.description.data,
            price=form.price.data, condition=form.condition.data,
            owner=current_user,
            rimtype=form.rimtype.data,
            rimwidth=form.rimwidth.data,
            rimdiametr=form.rimdiametr.data,
            rimbolts=form.rimbolts.data,
            rimboltsdiametr=form.rimboltsdiametr.data,
            rimoffset=form.rimoffset.data,
            rimoriginal=form.rimoriginal.data,
            store=curr_store,
            rimyear = form.rimyear.data,
            recommended_price=form.recommended_price.data,
            youla_status=form.youla_status.data,
        avito_show=form.avito_show.data, youla_show=form.youla_show.data, drom_show=form.drom_show.data
        )
    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = RimPhoto(rim=newrim, photo=new_filename)
                db.session.add(newrim)

        db.session.add(newrim)
        db.session.commit()
        newrim.baseid='r' + str(newrim.id)
        db.session.commit()

        current_user.to_avito_xml()
        current_user.to_avtoru_xml()
        current_user.to_drom_xml()
        current_user.to_youla_xml()

        # flash('Ваше предложение зарегистрировано!')
        return redirect(url_for('home_blueprint.rim'))
    elif request.method == 'GET':
        form.rimbrand.choices = brands
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        form.display_area1.default=current_user.def_display_area1
        form.process()
        form.listing_fee.data='Package',
        # form.ad_status.data='Free',
        form.condition.data='Б/у',
        form.description.data='Комплект дисков'
        form.manager_name.data = current_user.def_manager_name
        form.contact_phone.data = current_user.def_contact_phone
        form.address.data = current_user.def_adress
        return render_template('rim.html', title='Предложение по дискам', user=current_user, form=form,
                               segment='rim', rimphotos=rimphotos)

#Создаем новое объявление о продаже шин
@blueprint.route('/wheel.html', methods=['GET', 'POST'])
@login_required
def wheel():
    curr_store=current_user.store
    # form = TirePrepareForm(request.form)  #current_user.username
    brands=TireGuide.query.with_entities(TireGuide.id, TireGuide.brand).group_by(TireGuide.brand).all()
    brands.insert(0, (-1, 'Выберите бренд'))
    form = WheelPrepareForm(CombinedMultiDict((request.files, request.form)))
    form.tirebrand.choices=brands

    carBrands=CarsGuide.query.with_entities(CarsGuide.id, CarsGuide.brand).group_by(CarsGuide.brand).all()
    carBrands.insert(0, (-1, 'Выберите бренд'))
    rimBrands=RimPrices.query.with_entities(RimPrices.id, RimPrices.brand).group_by(RimPrices.brand).all()
    rimBrands.insert(0, (-1, 'Выберите бренд'))
    form.carbrand.choices=carBrands
    form.rimbrand.choices=rimBrands
    tirephotos=[url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example1.jpg').replace('\\', '/')),
                url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example2.jpg').replace('\\', '/')),
                url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], 'example3.jpg').replace('\\', '/'))]

    if 'Save' in request.form:
        brands=dict(brands)
        currBrand=brands[form.tirebrand.data] if form.tirebrand.data else None
        if currBrand:
            models=dict(TireGuide.query.with_entities(TireGuide.id, TireGuide.model).filter(TireGuide.brand.__eq__(currBrand)).group_by(TireGuide.model).all())
        carBrands = dict(carBrands)
        newwheel = Wheel(
            carbrand=carBrands[int(request.form['carbrand'])] if request.form['carbrand'] else None,
            carmodel=request.form['carmodel'] if request.form['carmodel'] else None,
            rimbrand=request.form['rimbrand'] if request.form['rimbrand'] else None,
            # rimmodel=request.form['rimmodel'] if request.form['rimmodel'] else None, #Они менялись динамически на фронте, поэтому берем из request.for,
            rimtype = form.rimtype.data,
            rimwidth = form.rimwidth.data,
            rimdiametr = form.rimdiametr.data,
            rimbolts = form.rimbolts.data,
            rimboltsdiametr = form.rimboltsdiametr.data,
            rimoffset = form.rimoffset.data,
            rimoriginal=form.rimoriginal.data,
            rimyear = form.rimyear.data,
            tirebrand = currBrand,
            tiremodel = models[form.tiremodel.data] if (form.tiremodel.data and form.tiremodel.data!=-1) else None,
            listing_fee = form.listing_fee.data, ad_status=form.ad_status.data, avito_id=form.avito_id.data,
            manager_name = form.manager_name.data, contact_phone=form.contact_phone.data, address=form.address.data,
            display_area1 = form.display_area1.data,
            ad_type = form.ad_type.data, qte=form.qte.data, inSet = form.inSet.data,
            title = form.title.data, description = form.description.data,
            price = form.price.data, recommended_price = form.recommended_price.data, condition = form.condition.data, shirina_profilya=form.shirina_profilya.data,
            vysota_profilya = form.vysota_profilya.data,
            owner = current_user, sezonnost = form.sezonnost.data,
            protector_height  = form.protector_height.data,  protector_wear = form.protector_wear.data,
            store = curr_store,
            avito_show = form.avito_show.data, youla_show = form.youla_show.data, drom_show=form.drom_show.data,
            videourl=form.videourl.data,
            tireproduct_year=form.tireproduct_year.data,
            youla_status=form.youla_status.data)
        newwheel.baseid='w' + str(newwheel.id)
    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = WheelPhoto(wheel=newwheel, photo=new_filename)
                db.session.add(newphoto)

        db.session.add(newwheel)
        db.session.commit()
        newwheel.baseid='w' + str(newwheel.id)
        db.session.commit()
#Когда доделаю публикацию вернуться сюда
        # current_user.to_avito_xml()
        # current_user.to_avtoru_xml()
        # current_user.to_drom_xml()
        # current_user.to_youla_xml()

        return redirect(url_for('home_blueprint.wheel'))
    elif request.method == 'GET':
        form.tirebrand.choices = brands
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        form.display_area1.default=current_user.def_display_area1
        form.process()
        form.listing_fee.data='Package',
        # form.ad_status.data='Free',
        form.condition.data='Б/у',

        form.description.data='Комплект резины'
        form.manager_name.data = current_user.def_manager_name
        form.contact_phone.data = current_user.def_contact_phone
        form.address.data = current_user.def_adress
        return render_template('wheel.html', title='Предложение по колесам', user=current_user, form=form,
                               segment='wheel', tirephotos=tirephotos, graphJSON=[])

#Корректировка объявления по шинам
@blueprint.route('/edit_tire/<tire_id>', methods=['GET', 'POST'])
@login_required
def edit_tire(tire_id):
    current_tire=current_user.tires.filter(Tire.id==tire_id).first()
    form = EditTireForm(CombinedMultiDict((request.files, request.form)))
    if 'Delete' in request.form:
        db.session.query(TirePhoto.tire_id).filter(TirePhoto.tire_id == current_tire.id).delete()
        # print(db.session.query(TirePhoto.tire_id).filter(TirePhoto.tire_id==current_tire.id).all())
        db.session.delete(current_tire)
        db.session.commit()
        # current_tire.delete
        return redirect(url_for('home_blueprint.stocks'))
    if 'Save' in request.form:
        current_tire.listing_fee=form.listing_fee.data
        current_tire.ad_status=form.ad_status.data
        current_tire.avito_id=form.avito_id.data
        current_tire.manager_name=form.manager_name.data
        current_tire.contact_phone=form.contact_phone.data
        current_tire.address=form.address.data
        current_tire.display_area1=form.display_area1.data
        current_tire.ad_type=form.ad_type.data
        current_tire.qte = form.qte.data
        current_tire.inSet = form.inSet.data
        current_tire.avito_show = form.avito_show.data
        # current_tire.avtoru_show = form.avtoru_show.data
        current_tire.drom_show = form.drom_show.data
        current_tire.youla_show = form.youla_show.data
        # print('Form qte ', form.qte.data)
        # print('Tire qte ', current_tire.qte)
        current_tire.title=form.title.data
        current_tire.description=form.description.data
        current_tire.price=form.price.data
        current_tire.recommended_price = form.recommended_price.data
        # current_tire.is_for_priority = form.is_for_priority.data
        current_tire.youla_status = form.youla_status.data
        # current_tire.condition=form.condition.data

    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = TirePhoto(tire=current_tire, photo=new_filename)
                db.session.add(newphoto)

        db.session.commit()
        # flash('Ваше предложение зарегистрировано!')
        current_user.to_avito_xml()
        current_user.to_avtoru_xml()
        current_user.to_drom_xml()
        current_user.to_youla_xml()

        return redirect(url_for('home_blueprint.edit_tire', tire_id=tire_id))
    elif request.method == 'GET':
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        form.display_area1.default=current_tire.display_area1
        form.process()
        tire_price, newTire_price = 0, 0
        # tire_price, newTire_price = calc_recommended_tireprice({'brand':current_tire.brand, 'model':current_tire.model, 'diametr':current_tire.diametr,
        #                                                        'width':current_tire.shirina_profilya, 'height':current_tire.vysota_profilya,
        #                                                        'thorns':None,
        #                                                        'is_winter':None,
        #                                                        'protector_height':current_tire.protector_height})
        # print(newTire_price)
        tire_price = int(tire_price * int(current_tire.qte))
        form.recommended_price.data = int(round(tire_price, 0))
        # current_tire_photos = current_user.tires.filter(Tire.id == tire_id).first().photos.all()
        current_tire_photos = current_user.tires.filter(Tire.id == current_tire.id).first().photos.all()
        # print(current_tire_photos)
        photos_list = [url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], str(current_tire_photo)).replace('\\', '/')) \
                       for current_tire_photo in current_tire_photos]
        df_photos=pd.DataFrame({'photos':photos_list, 'photo_buttons': current_tire_photos})
        df_photos['photo_buttons'] = df_photos['photo_buttons'].apply \
            (lambda x: '<a href = "' + url_for('home_blueprint.delete_photo', photo=str(x), tire_id=str(current_tire.id)) + '" class ="btn btn-sm btn-secondary"> Удалить </a>')
        form.listing_fee.data = current_tire.listing_fee
        form.ad_status.data = current_tire.ad_status
        form.avito_id.data = current_tire.avito_id
        form.manager_name.data = current_tire.manager_name
        form.contact_phone.data=current_tire.contact_phone
        form.address.data= current_tire.address
        form.ad_type.data = current_tire.ad_type
        form.avito_show.data = current_tire.avito_show
        form.drom_show.data = current_tire.drom_show
        form.youla_show.data = current_tire.youla_show
        # form.is_for_priority.data =current_tire.is_for_priority
        form.qte.data = current_tire.qte
        form.inSet.data = current_tire.inSet
        form.title.data = current_tire.title
        form.description.data = current_tire.description
        form.price.data = current_tire.price
        form.youla_status.data = current_tire.youla_status
        # form.recommended_price.data = current_tire.recommended_price

        return render_template('edit_tire.html', title='Предложение по шинам', tire_id=tire_id, form=form, segment='edit_tire',
            df_photos=df_photos)

# def update_load():
#     with app.app_context():  #app_context
#         while True:
#             sleep(3)
#             # with app.test_request_context('/avito_scan.html'):
#             turbo.push(turbo.replace(render_template('avitoscan-table.html'), 'offerstable'))

# @blueprint.context_processor
@blueprint.route('/avito_offerstable/<task_id>', methods=['GET'])
@login_required
def avito_offerstable(task_id):
    # print('Задача:', task_id)
    task = getAvitoTirePricesByLocale.AsyncResult(task_id)
    columnWidths = [1, 1, 1, 3, 2, 2, 1, 1]
    columnNames=['Дата проверки', 'Размерность', 'Цена, Руб.', 'Ссылка на объявление',
                 'Регион', 'Сезонность', 'Износ, %', 'Расстояние, Км']
    #До начала работы статус будет PENDING, потом PROGRESS
    # print(task.state, task.result)
    if task.state in ['PROGRESS', 'FINISHED']:
        # print(task.state, task.result)
        #Собираем данные для отображения на странице
        args = dict(request_type=1) #Фильтруем по сканированным по локале и радиусу поиска

        query = db.session.query(ApiTire.brand, ApiTire.season, ApiTire.region, ApiTire.diametr, ApiTire.width,
                                     ApiTire.height,
                                     ApiTire.wear_num, ApiTire.unitPrice, ApiTire.avito_link, ApiTire.avito_lat, ApiTire.avito_lon,
                                     ApiTire.update_date).filter_by(**args).order_by(ApiTire.unitPrice.asc())
        df = pd.read_sql(query.statement, query.session.bind)

        df.drop_duplicates(inplace=True)
        db_table_toshow = pd.DataFrame(
            columns=['Date', 'Size', 'Price', 'Title', 'Region', 'Season', 'Wear', 'Distance'])
        if not df.empty:
            db_table_toshow['Date']=pd.to_datetime(df['update_date'], dayfirst=True).dt.strftime('%Y/%m/%d')
            db_table_toshow['Title']=df.apply(lambda x: createLink(x['avito_link'], x['brand']), axis=1)
            db_table_toshow['Region']=df['avito_link'].apply(lambda x: x.split('/')[3])
            db_table_toshow['Season']=df['season']
            # print(df['season'].head())
            db_table_toshow['Size']=df['width'].astype(str) + '/' + \
                    df['height'].astype(str) + ' R' + df['diametr'].astype(str)
            db_table_toshow['Size']=db_table_toshow['Size'].apply(lambda x: x.replace('.0', ''))
            df['wear_num'].fillna(-1, inplace=True)
            db_table_toshow['Wear']=(df['wear_num']*100).round(0).astype(int).astype(str) + '%'
            db_table_toshow['Wear'].replace('-100%', '---', inplace=True)
            # db_table_toshow['Wear']=db_table_toshow['Wear'].astype(str) + '%'
            db_table_toshow['Price']=df['unitPrice'].astype(str)
            # print(current_user)
            db_table_toshow['Distance']=''
            if current_user.def_latitude and current_user.def_longitude:
                db_table_toshow['Distance'] = df.apply(lambda x: calculateTheDistance(current_user.def_latitude, x['avito_lat'], current_user.def_longitude, x['avito_lon']), axis=1)
                db_table_toshow['Distance'].fillna(-1, inplace=True)
                db_table_toshow['Distance'] = db_table_toshow['Distance'].round(0).astype(int)
                db_table_toshow['Distance'].replace(-1, '--', inplace=True)

        # print(list(df.values.tolist()))
        row_data = list(db_table_toshow.values.tolist())
        # db_table_toshow.to_csv(r'c:\Users\ESPERANCE\Documents\test.csv', encoding='cp1251', sep=';')
        return jsonify({'state':task.state, 'offerstable': row_data, 'columnWidths' :columnWidths, 'columnNames':columnNames, 'currPage':task.result})
    else: #task.state!=Progress && != Finished
        return jsonify({'state':task.state, 'offerstable': None, 'columnWidths' :columnWidths, 'columnNames':columnNames, 'currPage':None})

@blueprint.route('/start_avitoscan', methods=['POST'])
def start_avitoscan():
    seasonDict = {'Зимние шипованные': 'zimnie_shipovannye',
                  'Зимние нешипованные': 'zimnie_neshipovannye',
                  'Летние': 'letnie',
                  'Всесезонные': 'vsesezonnye'}
    s = request.get_json(force=True)
    # print(s)
    if s['region']:
        region = AvitoZones.query.with_entities(AvitoZones.engzone).filter(
            AvitoZones.zone == s['region']).first()
        # print(region)
        region = region[0]
    else:
        region = 'moskva_i_mo'

    if s['season']:
        season = seasonDict.get(s['season'])  # А в авито - латиница
    else:
        season = 'zimnie_neshipovannye'

    lat = s['lat'] if s['lat'] else 55.755814 #Если не указано - Москва
    lon = s['lon'] if s['lon'] else 37.617635 #Если не указано - Москва

    avitoScanTask = getAvitoTirePricesByLocale.delay(s['diametr'], s['width'], s['height'],
                                                               lon, lat,
                                                               region, season,
                                                               int(s['pages']), s['searchRadius'])
    return jsonify({}), 202, {'Location': url_for('home_blueprint.avito_offerstable', task_id=avitoScanTask.id)}

@blueprint.route('/avito_scan.html', methods=['GET', 'POST'])
@login_required
def avito_scan():
    seasonDict = {'Зимние шипованные': 'zimnie_shipovannye',
                  'Зимние нешипованные': 'zimnie_neshipovannye',
                  'Летние': 'letnie',
                  'Всесезонные': 'vsesezonnye'}

    form = AvitoScanForm(CombinedMultiDict((request.files, request.form)))
    # print(request.form)
    # if 'StartSearch' in request.form:
    # if form.validate_on_submit():
    if 'StartSearch' in request.form:
        #Выбираем регион из справочника
        # print(form.searchRegion.data)
        if form.searchRegion.data:
            region = AvitoZones.query.with_entities(AvitoZones.engzone).filter(AvitoZones.id == form.searchRegion.data).first()
            region=region[0]
        else:
            region = 'moskva_i_mo'

        if request.form['sezonnost']:
            season = seasonDict.get(request.form['sezonnost'])  # А в авито - латиница
        else:
            season = 'zimnie_neshipovannye'

        lat = form.searchLat.data if form.searchLat.data else 55.755814 #Если не указано - Москва
        lon = form.searchLon.data if form.searchLon.data else 37.617635 #Если не указано - Москва
        return redirect(url_for('home_blueprint.avito_scan'))
    elif request.method == 'GET':
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.searchRegion.choices = avito_zones
        form.searchRegion.default=current_user.def_display_area1
        form.process()
        form.searchLon.data = current_user.def_longitude
        form.searchLat.data = current_user.def_latitude
        return render_template('avito_scan.html', segment='avito_acan', form=form)


#Корректировка объявления по дискам
@blueprint.route('/edit_rim/<rim_id>', methods=['GET', 'POST'])
@login_required
def edit_rim(rim_id):
    current_rim=current_user.rims.filter(Rim.id==rim_id).first()
    form = EditTireForm(CombinedMultiDict((request.files, request.form)))
    if 'Delete' in request.form:
        db.session.query(RimPhoto.rim_id).filter(RimPhoto.rim_id == current_rim.id).delete()
        # print(db.session.query(TirePhoto.tire_id).filter(TirePhoto.tire_id==current_tire.id).all())
        db.session.delete(current_rim)
        db.session.commit()
        # current_tire.delete
        return redirect(url_for('home_blueprint.stocks'))
    if 'Save' in request.form:
        # print(request.form)
        # current_rim.rimbrand = request.form['rimbrand'], current_rim.rimmodel = request.form['rimmodel'],  # Они менялись динамически на фронте, поэтому берем из request.for,
        current_rim.qte = form.qte.data
        current_rim.inSet = form.inSet.data
        current_rim.listing_fee=form.listing_fee.data
        current_rim.ad_status=form.ad_status.data
        current_rim.avito_id=form.avito_id.data
        current_rim.manager_name=form.manager_name.data
        current_rim.contact_phone=form.contact_phone.data
        current_rim.address=form.address.data
        current_rim.display_area1=form.display_area1.data
        current_rim.ad_type=form.ad_type.data
        current_rim.avito_show = form.avito_show.data
        current_rim.youla_show = form.youla_show.data
        current_rim.drom_show = form.drom_show.data
        current_rim.is_for_priority = form.is_for_priority.data
        # print('Form qte ', form.qte.data)
        # print('Tire qte ', current_tire.qte)
        current_rim.title=form.title.data
        current_rim.description=form.description.data
        current_rim.price=form.price.data
        # current_rim.recommended_price = form.recommended_price.data
        # current_tire.condition=form.condition.data

    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = RimPhoto(rim=current_rim, photo=new_filename)
                db.session.add(newphoto)

        db.session.commit()
        # flash('Ваше предложение зарегистрировано!')
        current_user.to_avito_xml()
        current_user.to_avtoru_xml()
        current_user.to_drom_xml()
        current_user.to_youla_xml()

        return redirect(url_for('home_blueprint.edit_rim', rim_id=rim_id))
    elif request.method == 'GET':
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        form.display_area1.default=current_rim.display_area1
        form.process()
        rim_price, newRim_price = calc_recommended_rimprice(brand=current_rim.rimbrand, model=current_rim.rimmodel, diametr=current_rim.rimdiametr,
                                                            original=current_rim.rimoriginal,
                                                               ET=current_rim.rimoffset,
                                                               width=current_rim.rimwidth,
                                                               bolts=current_rim.rimbolts,
                                                               dia=current_rim.rimboltsdiametr, age=datetime.today().year - int(current_rim.rimyear))
        # print(rim_price, current_rim.qte)
        rim_price = int(rim_price * int(current_rim.qte))
        form.recommended_price.data = int(round(rim_price, 0))
        # current_tire_photos = current_user.tires.filter(Tire.id == tire_id).first().photos.all()
        current_rim_photos = current_user.rims.filter(Rim.id == current_rim.id).first().photos.all()
        # print(current_tire_photos)
        photos_list = [url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], str(current_rim_photo)).replace('\\', '/')) \
                       for current_rim_photo in current_rim_photos]
        df_photos=pd.DataFrame({'photos':photos_list, 'photo_buttons': current_rim_photos})
        df_photos['photo_buttons'] = df_photos['photo_buttons'].apply \
            (lambda x: '<a href = "' +
                       url_for('home_blueprint.delete_rimphoto', photo=str(x), rim_id=str(current_rim.id)) +
                       '" class ="btn btn-sm btn-secondary"> Удалить </a>')
        form.listing_fee.data = current_rim.listing_fee
        form.ad_status.data = current_rim.ad_status
        form.avito_id.data = current_rim.avito_id
        form.manager_name.data = current_rim.manager_name
        form.contact_phone.data=current_rim.contact_phone
        form.address.data= current_rim.address
        form.ad_type.data = current_rim.ad_type
        form.avito_show.data = current_rim.avito_show
        form.youla_show.data = current_rim.youla_show
        form.drom_show.data = current_rim.drom_show
        form.is_for_priority.data = current_rim.is_for_priority

        # print('Qte=', current_tire.qte)
        form.qte.data = current_rim.qte
        form.inSet.data = current_rim.inSet
        form.title.data = current_rim.title
        form.description.data = current_rim.description
        form.price.data = current_rim.price
        # form.recommended_price.data = current_tire.recommended_price

        return render_template('edit_rim.html', title='Предложение по шинам', rim_id=rim_id, form=form, segment='edit_rim', df_photos=df_photos)

#Корректировка объявления по дискам
@blueprint.route('/edit_wheel/<wheel_id>', methods=['GET', 'POST'])
@login_required
def edit_wheel(wheel_id):
    current_wheel=current_user.wheels.filter(Wheel.id==wheel_id).first()
    print(current_wheel)

    form = EditTireForm(CombinedMultiDict((request.files, request.form)))
    if 'Delete' in request.form:
        db.session.query(WheelPhoto.wheel_id).filter(WheelPhoto.wheel_id == current_wheel.id).delete()
        db.session.delete(current_wheel)
        db.session.commit()
        # current_tire.delete
        return redirect(url_for('home_blueprint.stocks'))
    if 'Save' in request.form:
        # print(request.form)
        # current_rim.rimbrand = request.form['rimbrand'], current_rim.rimmodel = request.form['rimmodel'],  # Они менялись динамически на фронте, поэтому берем из request.for,
        current_wheel.qte = form.qte.data
        current_wheel.inSet = form.inSet.data
        current_wheel.listing_fee=form.listing_fee.data
        current_wheel.ad_status=form.ad_status.data
        current_wheel.avito_id=form.avito_id.data
        current_wheel.manager_name=form.manager_name.data
        current_wheel.contact_phone=form.contact_phone.data
        current_wheel.address=form.address.data
        current_wheel.display_area1=form.display_area1.data
        current_wheel.ad_type=form.ad_type.data
        current_wheel.avito_show = form.avito_show.data
        current_wheel.youla_show = form.youla_show.data
        current_wheel.drom_show = form.drom_show.data
        current_wheel.is_for_priority = form.is_for_priority.data
        current_wheel.title=form.title.data
        current_wheel.description=form.description.data
        current_wheel.price=form.price.data
        # current_wheel.recommended_price = form.recommended_price.data
        # current_tire.condition=form.condition.data

    #Займемся фотками
        for file in form.photo1.data:
            photo1 = secure_filename(file.filename)
            if photo1:
                new_filename=current_user.username + "_" + datetime.today().strftime('%Y_%m_%d_%H_%M_%S') + "_" + photo1
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                newphoto = WheelPhoto(wheel=current_wheel, photo=new_filename)
                db.session.add(newphoto)

        db.session.commit()
        # flash('Ваше предложение зарегистрировано!')
        current_user.to_avito_xml()
        current_user.to_avtoru_xml()
        current_user.to_drom_xml()
        current_user.to_youla_xml()

        return redirect(url_for('home_blueprint.edit_wheel', wheel_id=wheel_id))
    elif request.method == 'GET':
        avito_zones = AvitoZones.query.with_entities(AvitoZones.id, AvitoZones.zone).group_by(AvitoZones.zone).order_by(AvitoZones.id).all()
        form.display_area1.choices = avito_zones
        print(current_wheel)
        form.display_area1.default=current_wheel.display_area1
        form.process()
        # current_tire_photos = current_user.tires.filter(Tire.id == tire_id).first().photos.all()
        current_wheel_photos = current_user.wheels.filter(Wheel.id == current_wheel.id).first().photos.all()
        # print(current_wheel_photos)
        photos_list = [url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], str(current_wheel_photo)).replace('\\', '/')) \
                       for current_wheel_photo in current_wheel_photos]
        df_photos=pd.DataFrame({'photos':photos_list, 'photo_buttons': current_wheel_photos})
        df_photos['photo_buttons'] = df_photos['photo_buttons'].apply \
            (lambda x: '<a href = "' +
                       url_for('home_blueprint.delete_wheelphoto', photo=str(x), wheel_id=str(current_wheel.id)) +
                       '" class ="btn btn-sm btn-secondary"> Удалить </a>')
        form.listing_fee.data = current_wheel.listing_fee
        form.ad_status.data = current_wheel.ad_status
        form.avito_id.data = current_wheel.avito_id
        form.manager_name.data = current_wheel.manager_name
        form.contact_phone.data=current_wheel.contact_phone
        form.address.data= current_wheel.address
        form.ad_type.data = current_wheel.ad_type
        form.avito_show.data = current_wheel.avito_show
        form.youla_show.data = current_wheel.youla_show
        form.drom_show.data = current_wheel.drom_show
        form.is_for_priority.data = current_wheel.is_for_priority
        form.qte.data = current_wheel.qte
        form.inSet.data = current_wheel.inSet
        form.title.data = current_wheel.title
        form.description.data = current_wheel.description
        form.price.data = current_wheel.price
        # form.recommended_price.data = current_tire.recommended_price

        return render_template('edit_wheel.html', title='Предложение по шинам', wheel_id=wheel_id, form=form, segment='edit_wheel', df_photos=df_photos)

#Склады
@blueprint.route('/stocks.html', methods=['GET'])
@login_required
def stocks():
    #Готовим структуру для вывода на экран
    stocks_dict = {}
    cut_labels = ['До 10', '11..20', '21..30', '31..40', '41..50', '>50']
    cut_bins = [-1, 10, 20, 30, 40, 50, 1000]

    first_month_day=datetime.today().date().replace(day=1).strftime('%Y-%m-%d') #Первый день текущего месяца

#Формируем данные по шинам
    stocks_dict['ActiveStock'] = db.session.query(func.sum(Tire.price)).filter(Tire.sold.__eq__(False)) \
        .filter(Tire.owner.__eq__(current_user)).scalar()
    stocks_dict['SoldStock'] = db.session.query(func.sum(Tire.price)).filter(Tire.sold.__eq__(True)) \
        .filter((Tire.owner.__eq__(current_user)) & (Tire.sold_date.isnot(None)) & (Tire.sold_date >= first_month_day )).scalar()
    # Формируем данные по дискам
    stocks_dict['ActiveRimStock'] = db.session.query(func.sum(Rim.price)).filter(Rim.sold.__eq__(False)) \
        .filter(Rim.owner.__eq__(current_user)).scalar()
    stocks_dict['SoldRimStock'] = db.session.query(func.sum(Rim.price)).filter(Rim.sold.__eq__(True)) \
        .filter(
        (Rim.owner.__eq__(current_user)) & (Rim.sold_date.isnot(None)) & (Rim.sold_date >= first_month_day)).scalar()
    # Формируем данные по колесам
    stocks_dict['ActiveWheelStock'] = db.session.query(func.sum(Wheel.price)).filter(Wheel.sold.__eq__(False)) \
        .filter(Wheel.owner.__eq__(current_user)).scalar()
    stocks_dict['SoldWheelStock'] = db.session.query(func.sum(Wheel.price)).filter(Wheel.sold.__eq__(True)) \
        .filter(
        (Wheel.owner.__eq__(current_user)) & (Wheel.sold_date.isnot(None)) & (Wheel.sold_date >= first_month_day)).scalar()

    #Таблица данных
    table_data=pd.DataFrame(columns=['Days', 'Qte', 'Percent', 'Cost', 'Cost_perc', 'Avg'])
    db_base_data = pd.read_sql('SELECT id, timestamp, price FROM tire WHERE (Not sold) AND (user_id = ' + str(current_user.id) + ') UNION ' \
                                'SELECT id, timestamp, price FROM rim WHERE (Not sold) AND (user_id = ' + str(current_user.id) + ') UNION ' \
                                'SELECT id, timestamp, price FROM wheel WHERE (Not sold) AND (user_id = ' + str(current_user.id) + ');', db.session.bind)
    # print(db_base_data.head())
    table_data = pd.DataFrame(columns=['Days', 'Qte', 'Percent', 'Cost', 'Cost_perc', 'Avg'])
    table_data.Days = ['До 10', '11..20', '21..30', '31..40', '41..50', '>50']
    table_data['Days']=table_data.apply(lambda row: '<a href="' + url_for('home_blueprint.stock_tables',  page=str(row.name)) + '">' + str(row['Days']) + '</a><br>', axis=1)

    if not db_base_data.empty:
        db_base_data.timestamp = pd.to_datetime(db_base_data.timestamp, dayfirst=True)
        db_base_data['days'] = (pd.to_datetime(datetime.today(), dayfirst=True) - db_base_data.timestamp)
        db_base_data['days'] = db_base_data['days'].apply(lambda x: x.days)
        db_base_data['cut_ex'] = pd.cut(db_base_data['days'], bins=cut_bins, labels=cut_labels)
        # print(db_base_data.head())
        table_data.Qte = db_base_data.groupby('cut_ex', as_index=False)['id'].count()['id']
        table_data['Percent'] = table_data['Qte'] / table_data['Qte'].sum()*100.
        table_data['Percent'] =table_data['Percent'].round(0).astype(str)+" %"
        table_data.Cost = db_base_data.groupby('cut_ex', as_index=False)['price'].sum()['price']
        table_data['Cost_perc'] = table_data['Cost'] / table_data['Cost'].sum()*100.
        table_data['Cost_perc'] =table_data['Cost_perc'].round(0).astype(str)+" %"
        table_data.Avg = db_base_data.groupby('cut_ex', as_index=False)['price'].mean()['price'].round(0)

    if request.method == 'GET':
        #Заполним структуру данными
        #User.query.with_entities(func.avg(Tire.price).label('Total'))
        # db.session.query(func.sum(Tire.price)).filter(Tire.sold.__eq__(False)).filter(Tire.owner.__eq__(u)).scalar()
        #db.session.query(func.sum(Tire.price)).filter(Tire.sold.__eq__(False)).scalar()

        return render_template('stocks.html', title='Склады', user=current_user, stocks_dict=stocks_dict, row_data=list(table_data.values.tolist()),
                                segment='stocks') #form=form,

def create_tools_field(x):
    # Добавляем выключатель В Продаже
    ch='checked' if not x['sold'] else ''
    result = '''<div class="form-switch" > <input class="form-check-input" type="checkbox" 
            name="idSold_''' + str(x['baseid']) + '''" id="idSold_''' + str(x['baseid']) + '" ' + ch + ''' onclick=change_publishedstatus("idSold_''' + str(x['baseid']) + '''")> 
                <label class ="form-check-label" for ="idSold_''' + str(x['baseid']) + '''"> В продаже </label></div>'''
    # Добавляем выключатель на Авито
    ch='checked' if x['avito_show'] else ''
    result = result + '\n' + '''<div class="form-switch" > <input class="form-check-input" type="checkbox" 
            name="idAvito_''' + str(x['baseid']) + '''" id="idAvito_''' + str(x['baseid']) + '"' + ch +  ''' onclick=change_publishedstatus("idAvito_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idAvito_''' + str(x['baseid']) + '''">На Авито</label></div>'''
    # Добавляем выключатель на Drom
    ch='checked' if x['drom_show'] else ''
    result = result + '\n' + '''<div class="form-switch" > <input class="form-check-input" type="checkbox" 
            name="idDrom_''' + str(x['baseid']) + '''" id="idDrom_''' + str(x['baseid']) + '"' + ch +  ''' onclick=change_publishedstatus("idDrom_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idDrom_''' + str(x['baseid']) + '''">На Дром</label></div>'''
    # Добавляем выключатель на Youla
    ch='checked' if x['youla_show'] else ''
    result = result + '\n' + '''<div class="form-switch" > <input class="form-check-input" type="checkbox" 
            name="idYoula_''' + str(x['baseid']) + '''" id="idYoula_''' + str(x['baseid']) + '"' + ch +  ''' onclick=change_publishedstatus("idAYoula_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idYoula_''' + str(x['baseid']) + '''">На Youla</label></div>'''
    return result

def create_avtorupromo_field(x):
    # Добавляем выключатель В Продаже
    ch='checked' if x['is_for_priority'] else ''
    result = '''<div class="form-switch" > <input class="form-check-input" type="checkbox" 
            name="id_is_for_priority_''' + str(x['baseid']) + '''" id="idis-for-priority_''' + str(x['baseid']) + '" ' + ch + ''' onclick=change_avtoru_promo("idis-for-priority_''' + str(x['baseid']) + '''")> 
                <label class ="form-check-label" for ="idis-for-priority_''' + str(x['baseid']) + '''"> Auto.ru Промо</label></div>'''
    return result

def create_youlapromo_field(x):
    # Добавляем выключатель В Продаже
    ch='checked' if x['youla_status']=='Нет' else ''
    result ='''<fieldset> <table> <tr> <td> <div class="form-check" > <input class="form-check-input" type="radio"
            name="youla_status_id_''' + str(x['baseid']) + '''" id="idYoulaNone_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idYoulaNone_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idYoulaNone_''' + str(x['baseid']) + '''">Нет</label></div>'''
    # Turbo
    ch='checked' if x['youla_status']=='Turbo' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="youla_status_id_''' + str(x['baseid']) + '''" id="idYoulaTurbo_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idYoulaTurbo_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idYoulaTurbo_''' + str(x['baseid']) + '''">Turbo</label> </div>'''
    # Premum
    ch='checked' if x['youla_status']=='Premium' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="youla_status_id_''' + str(x['baseid']) + '''" id="idYoulaPremium_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idYoulaPremium_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idYoulaPremium_''' + str(x['baseid']) + '''">Premium</label> </div>'''
    # Boost
    ch='checked' if x['youla_status']=='Boost' else ''
    result = result + '\n' + '''<div class="form-check"> <input class="form-check-input" type="radio"
            name="youla_status_id_''' + str(x['baseid']) + '''" id="idYoulaBoost_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idYoulaBoost_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idYoulaBoost_''' + str(x['baseid']) + '''">Boost</label> </div> </td> </tr> </table> </fieldset>'''
    return result

def create_promo_field(x):
    # Проверяем статус free 'Highlight', 'XL', 'x2_1', 'x2_7', 'x5_1', 'x5_7', 'x10_1', 'x10_7'
    # sites_dict={'idFree':'Free', 'idHighlight':'Highlight', 'idx2-1':'x2_1', 'idx5-1':'x5_1', 'idx10-1':'x10_1', 'idXL':'XL','idx2-7':'x2_7',
    #             'idx5-7':'x5_7','idx10-7':'x10_7'}
    ch='checked' if x['ad_status']=='Free' else ''
    result ='''<fieldset> <table> <tr> <td> <div class="form-check" > <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idFree_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idFree_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idFree_''' + str(x['baseid']) + '''">Free</label></div>'''
    # Highlight
    ch='checked' if x['ad_status']=='Highlight' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idHighlight_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idHighlight_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idHighlight_''' + str(x['baseid']) + '''">Highlight</label> </div>'''
    # x2_1
    ch='checked' if x['ad_status']=='x2_1' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx2-1_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx2-1_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx2-1_''' + str(x['baseid']) + '''">x2_1</label> </div>'''
    # x5_1
    ch='checked' if x['ad_status']=='x5_1' else ''
    result = result + '\n' + '''<div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx5-1_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx5-1_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx5-1_''' + str(x['baseid']) + '''">x5_1</label> </div>'''
    # x10_1
    ch='checked' if x['ad_status']=='x10_1' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx10-1_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx10-1_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx10-1_''' + str(x['baseid']) + '''">x10_1</label> </div>  </td>'''
    # XL
    ch='checked' if x['ad_status']=='XL' else ''
    result = result + '\n' + ''' <td> <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idXL_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idXL_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idXL_''' + str(x['baseid']) + '''">XL</label> </div>'''
    # x2_7
    ch='checked' if x['ad_status']=='x2_7' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx2-7_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx2-7_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx2-7_''' + str(x['baseid']) + '''">x2_7</label> </div>'''
    # x5_7
    ch='checked' if x['ad_status']=='x5_7' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx5-7_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx5-7_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx5-7_''' + str(x['baseid']) + '''">x5_7</label> </div>'''
    # x10_7
    ch='checked' if x['ad_status']=='x10_7' else ''
    result = result + '\n' + ''' <div class="form-check"> <input class="form-check-input" type="radio"
            name="ad_status_id_''' + str(x['baseid']) + '''" id="idx10-7_''' + str(x['baseid']) + '"' + ch + ''' onclick=change_promostatus("idx10-7_''' + str(x['baseid']) + '''")>
                <label class ="form-check-label" for ="idx10-7_''' + str(x['baseid']) + '''">x10_7</label> </div> </td> </tr> </table> </fieldset>'''
    return result

@blueprint.route('/delete_photo/<photo>/<tire_id>', methods=['GET'])
@login_required
def delete_photo(photo, tire_id):
    Tire_photo=current_user.tires.filter(Tire.id == tire_id).first().photos.filter(TirePhoto.photo == photo).first()
    db.session.delete(Tire_photo)
    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    # print('Здесь удаляем фото {} с id {}'.format(Tire_photo.photo, Tire_photo.id))
    return redirect(url_for('home_blueprint.edit_tire', tire_id=tire_id))

@blueprint.route('/delete_rimphoto/<photo>/<rim_id>', methods=['GET'])
@login_required
def delete_rimphoto(photo, rim_id):
    Rim_photo=current_user.rims.filter(Rim.id == rim_id).first().photos.filter(RimPhoto.photo == photo).first()
    db.session.delete(Rim_photo)
    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    # print('Здесь удаляем фото {} с id {}'.format(Tire_photo.photo, Tire_photo.id))
    return redirect(url_for('home_blueprint.edit_rim', rim_id=rim_id))

@blueprint.route('/delete_wheelphoto/<photo>/<wheel_id>', methods=['GET'])
@login_required
def delete_wheelphoto(photo, wheel_id):
    Wheel_photo=current_user.wheel.filter(Wheel.id == wheel_id).first().photos.filter(WheelPhoto.photo == photo).first()
    db.session.delete(Wheel_photo)
    db.session.commit()
    current_user.to_avito_xml()
    current_user.to_avtoru_xml()
    current_user.to_drom_xml()
    current_user.to_youla_xml()

    # print('Здесь удаляем фото {} с id {}'.format(Tire_photo.photo, Tire_photo.id))
    return redirect(url_for('home_blueprint.edit_wheel', rim_id=wheel_id))

#Показываем склад
@blueprint.route('/stock_tables/<page>', methods=['GET', 'POST'])
@login_required
def stock_tables(page):
    cut_bins = [-1, 10, 20, 30, 40, 50, 1000]

    #Таблица данных для отображения
    # db_base_data = pd.read_sql('SELECT * FROM tire WHERE (Not sold) AND (user_id = ' + str(current_user.id) + ');', db.session.bind)
    db_base_data = pd.read_sql('''SELECT  t.id, t.brand, t.baseid, t.price, t.timestamp, t.sold, t.avito_show, t.youla_show, t.drom_show, t.ad_status, t.youla_status,
        t.title, t.sezonnost, t.shirina_profilya AS width, t.diametr, t.vysota_profilya AS height, t.protector_height, t.protector_wear, t.product_year AS year,
        (SELECT tf.Photo FROM tire_photo tf WHERE tf.tire_id = t.id ORDER BY Photo ASC LIMIT 1) AS Photo
        FROM tire t WHERE t.user_id = ''' + str(current_user.id) + ' ' \
       'UNION ' \
       '''SELECT r.id, r.rimbrand, r.baseid, r.price, r.timestamp, r.sold, r.avito_show, r.youla_show, r.drom_show, r.ad_status, r.youla_status,
       r.title, r.rimtype, r.rimwidth AS width, r.rimdiametr AS diametr, r.rimbolts, r.rimboltsdiametr, r.rimoffset, r.rimyear AS year,
       (SELECT rf.Photo FROM rim_photo rf WHERE rf.rim_id = r.id ORDER BY Photo ASC LIMIT 1) AS Photo
       FROM rim r WHERE r.user_id = ''' + str(current_user.id) + ' ' \
        'UNION ' \
        '''SELECT w.id, w.rimbrand, w.baseid, w.price, w.timestamp, w.sold, w.avito_show, w.youla_show, w.drom_show, w.ad_status, w.youla_status,
       w.title, w.rimtype, w.rimwidth AS width, w.rimdiametr AS diametr, w.rimbolts, w.rimboltsdiametr, w.rimoffset, w.rimyear AS year,
       (SELECT wf.Photo FROM wheel_photo wf WHERE wf.wheel_id = w.id ORDER BY Photo ASC LIMIT 1) AS Photo
       FROM wheel w WHERE w.user_id = ''' + str(current_user.id) + ';', db.session.bind)
    #Сортирум по от свежих к старым
    db_base_data.sort_values('timestamp', ascending=False, inplace=True)
    #Отфильтруем теперь по параметрам запроса
    argsDict= request.args.to_dict()
    argsDict = dict([(k, v) for k, v in argsDict.items() if v !=''])

    if not argsDict: #нет параметров - ничего не делаем
        pass
    else: #Фильтруем по параметрам
        db_base_data=db_base_data.loc[db_base_data[list(argsDict.keys())].isin(list(argsDict.values())).all(axis=1), :]


    db_base_data.timestamp = pd.to_datetime(db_base_data.timestamp, dayfirst=True)
    db_base_data['days'] = (pd.to_datetime(datetime.today(), dayfirst=True) - db_base_data.timestamp)
    db_base_data['days'] = db_base_data['days'].apply(lambda x: x.days)
    # print(db_base_data.head())
    # print('page=', page)
    if len(db_base_data) > 0 and page != 'all' and request.method != 'POST':   #Если POST - то показываем все записи по данному фильтру
        db_base_data = db_base_data.loc[(db_base_data['days'] >= cut_bins[int(page)]) & (db_base_data['days'] < cut_bins[int(page)+1])]
    # print(db_base_data.head())
    db_table_toshow = pd.DataFrame(columns=['Photo', 'Description', 'Price', 'Tools', 'Promotion', 'Youla_promo', 'HREF'])
    db_table_toshow['Price'] = 'Цена продажи: ' + db_base_data['price'].astype(str) + ' Руб.'
    db_table_toshow['Tools'] = db_base_data[['baseid', 'sold', 'avito_show', 'youla_show', 'drom_show']].to_dict('records')
    db_table_toshow['Tools']= db_table_toshow['Tools'].apply(lambda x: create_tools_field(x))
    db_table_toshow['Promotion'] = db_base_data[['baseid', 'ad_status']].to_dict('records')
    db_table_toshow['Promotion'] = db_table_toshow['Promotion'].apply(lambda x: create_promo_field(x))
    db_table_toshow['Youla_promo'] = db_base_data[['baseid', 'youla_status']].to_dict('records')
    db_table_toshow['Youla_promo']= db_table_toshow['Youla_promo'].apply(lambda x: create_youlapromo_field(x))
    db_table_toshow['Photo']=db_base_data.Photo
    db_table_toshow['Photo'] = db_table_toshow['Photo'].apply( lambda x: url_for('static', filename=os.path.join(app.config['PHOTOS_FOLDER'], x).replace('\\','/')) if x else None)
    db_table_toshow['HREF']=db_base_data.baseid.astype(str)
    #А здесь ссылку вставляем либо на edit_tire либо на edit_rim
    db_table_toshow['Description'] =  db_table_toshow['HREF'].apply(lambda x: '<a href="' +
                                                                              (url_for('home_blueprint.edit_tire', tire_id=x[1:]) if x[0]=='t' else (url_for('home_blueprint.edit_rim', rim_id=x[1:]) if x[0]=='r' else url_for('home_blueprint.edit_wheel', wheel_id=x[1:]))) +
                                                                              '"> # в системе: ' + x + '</a><br>')
    db_table_toshow['Description']= db_table_toshow['Description'] +  ' <br> ' + db_base_data['title'] + '<br> ' + db_base_data['year'].astype(str) + '<br> '
    db_table_toshow['HREF']=db_table_toshow['HREF'].apply(lambda x: '<a class ="btn btn-secondary text-dark me-4" href="' +
                                                                    (url_for('home_blueprint.edit_tire', tire_id=x[1:]) if x[0]=='t' else (url_for('home_blueprint.edit_rim', rim_id=x[1:]) if x[0]=='r' else url_for('home_blueprint.edit_wheel', wheel_id=x[1:]))) +
                                                                    '"> Изменить #' + x + '</a><br>')
    default_photo = os.path.join(app.config['PHOTOS_FOLDER'], 'NoPhoto.png')
    print(db_table_toshow.columns)
    pages_list = {'0':'До 10', '1':'11..20', '2':'21..30', '3':'31..40', '4':'41..50', '5':'>50', 'all':'>0'}
    #Подготовим список брендов для фильтра
    brandsList = db.session.query(Tire.id, Tire.brand).filter(Tire.user_id==current_user.id).group_by(Tire.brand).all()
    brandsList.insert(0, (0, ""))
    #Подготовим список диаметров для фильтра
    diametrList = db.session.query(Tire.id, Tire.diametr).filter(Tire.user_id==current_user.id).group_by(Tire.diametr).all()
    diametrList.insert(0, (0, ""))
    #Подготовим список ширин для фильтра
    widthList = db.session.query(Tire.id, Tire.shirina_profilya).filter(Tire.user_id==current_user.id).group_by(Tire.shirina_profilya).all()
    widthList.insert(0, (0, ""))
    #Подготовим список высот для фильтра
    heightList = db.session.query(Tire.id, Tire.vysota_profilya).filter(Tire.user_id==current_user.id).group_by(Tire.vysota_profilya).all()
    heightList.insert(0, (0, ""))

    if request.method=='POST':
        argsDict=request.get_json(force=True)
        # print(argsDict)
        return jsonify({'brand':argsDict['brand'] if 'brand' in argsDict else None,
                       'link':  url_for('home_blueprint.stock_tables', page='all',
                                        brand=argsDict['brand'] if 'brand' in argsDict else None,
                                        diametr=argsDict['diametr'] if 'diametr' in argsDict else None,
                                        width=argsDict['width'] if 'width' in argsDict else None,
                                        height=argsDict['height'] if 'height' in argsDict else None)})
        # return redirect(url_for('home_blueprint.stock_tables', page='all', brand=argsDict['brand'] if 'brand' in argsDict else None))

    return render_template('stock-tables.html', title='Управление складом', user=current_user, row_data=list(db_table_toshow.values.tolist()),
                           segment='stock-tables', default_photo=default_photo, brandsList=brandsList, diametrList=diametrList,
                           widthList=widthList, heightList=heightList, curr_page=pages_list[page]) #form=form,

def createLink(link, text):
    return '<a class ="text-dark me-4" href="' + link + '" target="_blank"> ' + text + '</a><br>'

#Показываем склад
@blueprint.route('/avito_tires/<page>', methods=['GET'])
@login_required
def avito_tires(page):

    args = request.args.to_dict() #в аргументах должны быть характеристики шин
    # Выполняем все проверки
    [abort_if_param_doesnt_exist(param) for param in list(args.keys())]  # Проверяем что параметры валидные

    argsDict = dict([(k, v) for k, v in args.items() if v])
    args=argsDict

    if not page:
        page = 1
    else:
        page = int(page)
    pureRegion=None

    #Регион преобразуем в латиницу
    if 'region' in args:
        # Забираем зоны Авито
        pureRegion=args['region']
        query = db.session.query(AvitoZones.zone, AvitoZones.engzone).filter(AvitoZones.zone == args['region']).limit(1)
        dfZones = pd.read_sql(query.statement, query.session.bind).set_index('zone')
        region = dfZones.loc[args['region'], 'engzone']
        args['region']=region #Меняем на латиницу
    else:
        args['region'] = 'rossiya'
    args['request_type'] = 0 #Смотрим сканированные без привязки к локации

    # print(args)
    #Для пажинации выясним количество страниц
    pageSize = int(100)

    pagesNum = int(db.session.query(func.count(ApiTire.id)).filter_by(**args).scalar()/pageSize)+1
    pages_list = range(1, pagesNum)  #{1:1, 2:2, ...}
    linksList = [url_for('home_blueprint.avito_tires', page=i+1, region=pureRegion if pureRegion else None,
                         diametr=args['diametr'] if 'diametr' in args else None, width=args['width'] if 'width' in args else None,
                         height=args['height'] if 'height' in args else None) for i in range(0, pagesNum-1)]
    linksDict=dict(zip(pages_list, linksList))
    offset = pageSize * (page - 1)
    # print()
    query = db.session.query(ApiTire.brand, ApiTire.season, ApiTire.region, ApiTire.diametr, ApiTire.width,
                                 ApiTire.height,
                                 ApiTire.wear_num, ApiTire.unitPrice, ApiTire.avito_link, ApiTire.avito_lat, ApiTire.avito_lon,
                                 ApiTire.update_date).filter_by(**args).order_by(ApiTire.unitPrice.asc())
    df = pd.read_sql(query.statement, query.session.bind)
    df=df[offset:offset + pageSize]
    # print(df.head())
    columnWidths = [1, 1, 1, 3, 2, 2, 1, 1]
    db_table_toshow = pd.DataFrame(
        columns=['Date', 'Size', 'Price', 'Title', 'Region', 'Season', 'Wear', 'Distance'])
    if not df.empty:
        db_table_toshow['Date']=pd.to_datetime(df['update_date'], dayfirst=True).dt.strftime('%Y/%m/%d')
        db_table_toshow['Title']=df.apply(lambda x: createLink(x['avito_link'], x['brand']), axis=1)
        db_table_toshow['Region']=df['avito_link'].apply(lambda x: x.split('/')[3])
        db_table_toshow['Season']=df['season']
        db_table_toshow['Size']=df['width'].astype(str) + '/' + \
                df['height'].astype(str) + ' R' + df['diametr'].astype(str)
        db_table_toshow['Size']=db_table_toshow['Size'].apply(lambda x: x.replace('.0', ''))
        df['wear_num'].fillna(-1, inplace=True)
        db_table_toshow['Wear']=(df['wear_num']*100).round(0).astype(int).astype(str) + '%'
        db_table_toshow['Wear'].replace('-100%', '---', inplace=True)
        # db_table_toshow['Wear']=db_table_toshow['Wear'].astype(str) + '%'
        db_table_toshow['Price']=df['unitPrice'].astype(str)
        if current_user.def_latitude and current_user.def_longitude:
            db_table_toshow['Distance'] = df.apply(lambda x: calculateTheDistance(current_user.def_latitude, x['avito_lat'], current_user.def_longitude, x['avito_lon']), axis=1)
            db_table_toshow['Distance'].fillna(-1, inplace=True)
            db_table_toshow['Distance'] = db_table_toshow['Distance'].round(0).astype(int)
            db_table_toshow['Distance'].replace(-1, '--', inplace=True)

    if request.method == 'GET':
        return render_template('avito_tires.html', title='Предложения на Avito', user=current_user, row_data=list(db_table_toshow.values.tolist()),
                            segment='avito_tires', linksDict=linksDict, curr_page=page, columnWidths=columnWidths)

def forms_prepare(segment, method):
    print('Страница {} метод {}'.format(segment, method))
    # return settings_form(segment, method)

@blueprint.route('/save_personnal_photo', methods=['POST'])
@login_required
def save_personnal_photo():
    # print(request.files.get('persoPhoto'))
    myFile=request.files.get('persoPhoto')
    # print(myFile)
    photo1 = secure_filename(myFile.filename)
    if photo1:
        new_filename = current_user.username + "_" + photo1
        myFile.save(os.path.join(app.config['PERSO_PHOTO_FOLDER'], new_filename))
        current_user.avatar_photo=os.path.join(app.config['PERSO_PHOTO'], new_filename).replace('\\', '/')
        db.session.commit()
    return jsonify({'result':  url_for('static', filename=current_user.avatar_photo)})


@blueprint.route('/<template>', methods=['GET', 'POST'])
@login_required
def route_template(template):

    try:
        if not template.endswith( '.html' ):
            template += '.html'
        # Detect the current page
        segment = get_segment( request )
        return render_template( template, segment=segment )
    except TemplateNotFound:
        return render_template('page-404.html'), 404
    except:
        return render_template('page-500.html'), 500

# Helper - Extract current page name from request 
def get_segment( request ):
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            segment = 'index'
        return segment
    except:
        return None  

