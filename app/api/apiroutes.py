# -*- encoding: utf-8 -*-
"""
Copyright (c) 2022 - DC
"""
from app import db
from flask_restful import Resource, abort
from flask import jsonify, g, request
from flask_httpauth import HTTPBasicAuth
from app.api.apimodels import ApiUser, ApiTire
import threading
from app.api.avitoutils import getAvitoTirePrices
from flask import current_app

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = ApiUser.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = ApiUser.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True

class NewUser(Resource):
    def post(self):
        # print(request.json)
        username = request.json.get('username')
        password = request.json.get('password')
        if username is None or password is None:
            abort(400) # missing arguments
        if ApiUser.query.filter_by(username = username).first() is not None:
            abort(400) # existing user
        user = ApiUser(username = username)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        # print(url_for('getuser', id = user.id, _external = True))
        return jsonify({'username': user.username})

class GetUser(Resource):
    def get(self, id):
        user = ApiUser.query.get(id)
        if not user:
            abort(400)
        return jsonify({'username': user.username})


def abort_if_param_doesnt_exist(t_id):
    if t_id not in ['diametr', 'width', 'height', 'count', 'season', 'pages', 'region']:
        abort(404, message="Parameter {} do not exist.".format(t_id))

class TirePrices(Resource):
    @auth.login_required
    def get(self, region='rossiya'):
        seasonDict={'zimnie_shipovannye':'Зимние шипованные',
                    'zimnie_neshipovannye':'Зимние нешипованные',
                    'letnie':'Летние',
                    'vsesezonnye':'Всесезонные'}

        # parser = reqparse.RequestParser()
        # parser.add_argument('diametr', type=float, help='diameter of the tire')
        # parser.add_argument('width', type=int, help='width of the tire')
        # parser.add_argument('height', type=int, help='width of the tire')
        # parser.add_argument('count', type=int, help='count of records')
        # #Проверка на корректность ключей
        # args = parser.parse_args()
        # print(args)
        # запускаем обновление и возвращаем результат из базы
        args = request.args.to_dict()  # flat=False
        print(args)
        if 'count' in args:
            recCount=request.args['count']
            del args['count']
        else:
            recCount=300 #По умолчанию передаем 300 значений

        if 'pages' in args:
            pages=int(request.args['pages'])
            del args['pages']
        else:
            pages=10 #По умолчанию смотрим 10 страниц

        if 'season' in args:
            season=args['season']
            args['season']=seasonDict.get(args['season'])
            print(args)
        else:
            season='zimnie_neshipovannye'
        [abort_if_param_doesnt_exist(param) for param in list(args.keys())] #Проверяем что параметры валидные

        dfUpdateBase = getAvitoTirePrices(args.get('diametr'), args.get('width'), args.get('height'), region, season, pages)
        # threading.Thread(target=updateTires, kwargs={'app':current_app._get_current_object(), 'region': region,  'season':season, 'width': args.get('width'), 'height':args.get('height'), 'diametr': args.get('diametr'), 'pages':pages}).start()

        query=db.session.query(ApiTire.brand, ApiTire.season, ApiTire.wear_num, ApiTire.unitPrice).filter_by(**args).limit(recCount)
        tires = query.all()
        # print(tires)
        tireList= []
        for tire in tires:
            tireList.append(tire._asdict())
        return jsonify(tireList)
