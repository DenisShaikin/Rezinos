# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import TextField, PasswordField
from wtforms.validators import InputRequired, Email, DataRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField, MultipleFileField, RadioField
from wtforms import FloatField, DecimalField, DateField, DateTimeField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import ValidationError, DataRequired,  Email, EqualTo, Required
from flask_wtf.file import  FileRequired, FileAllowed

from app.base.models import  User
from wtforms import TextAreaField
from wtforms.validators import Length
from flask_login import current_user

## login and registration

class LoginForm(FlaskForm):
    username = TextField    ('Username', id='username_login'   , validators=[DataRequired()])
    password = PasswordField('Password', id='pwd_login'        , validators=[DataRequired()])

class CreateAccountForm(FlaskForm):
    username = TextField('Username'     , id='username_create' , validators=[DataRequired()])
    email    = TextField('Email'        , id='email_create'    , validators=[DataRequired(), Email()])
    password = PasswordField('Password' , id='pwd_create'      , validators=[DataRequired()])

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторно Пароль', validators=[DataRequired(), EqualTo('password',
                                                                                     message='Пароль должен совпадать')])  #, EqualTo('password')

class EditProfileForm(FlaskForm):
    # username = StringField('Логин', validators=[DataRequired()])
    # email = StringField('email', validators=[Length(min=0, max=140)])
    avito_client_id = StringField('Client ID')
    avito_client_secret = StringField('Client Secret')
    avito_profile_url = StringField('URL профиля на Авито')
    avito_profile_idNum = StringField('ID профиля Авито')
    avito_balance_real = FloatField('Баланс Авито', default=0)
    avito_balance_bonus = FloatField('Бонус Авито', default=0)
    def_allow_email = BooleanField('Возможность написать сообщение по объявлению через сайт', id='allow_email', default="checked")
    def_manager_name = TextField('Контактное лицо', id='manager_name', validators=[DataRequired(), Length(min=1, max=140)])
    def_contact_phone = TextField('Телефон менеджера', id='contact_phone', validators=[DataRequired(), Length(min=1, max=20)])
    def_contact_mail = TextField('Email менеджера', id='contact_email', validators=[DataRequired(), Length(min=1, max=100)])
    def_adress = TextField('Полный адрес объекта', id='adress', validators=[Required(), Length(min=1, max=256)])
    def_latitude = TextField('Широта', id='lat')
    def_longitude = TextField('Долгота', id='lon')

    store = StringField('ID магазина Auto.ru')
    avito_path = StringField('Путь к фидам Avito')
    autoru_path = StringField('Путь к фидам Auto.ru')

    # def_latitude = FloatField('Широта', default=0)
    # def_longitude = FloatField('Долгота', default=0)
    def_display_area1 = SelectField('Первая зона показа', id='display_area', validate_choice=False, coerce=int)
    # def_display_area2=StringField('Вторая зона показа')
    # def_display_area3=StringField('Третья зона показа')
    # def_display_area4=StringField('Четвертая зона показа')
    # def_display_area5=StringField('Пятая зона показа')

    # submit = SubmitField('Submit')

    # def __init__(self, original_username, *args, **kwargs):
    #     super(EditProfileForm, self).__init__(*args, **kwargs)
    #     self.original_username = original_username
    #
    # def validate_username(self, username):
    #     if username.data != self.original_username:
    #         user = User.query.filter_by(username=self.username.data).first()
    #         if user is not None:
    #             raise ValidationError('Please use a different username.')

class TirePrepareForm(FlaskForm):
    brand=SelectField('Производитель', validate_choice=False, coerce=int)
    model=SelectField('Модель', validate_choice=False, coerce=int)
    listing_fee=SelectField('Пакет размещения', choices=['PackageSingle', 'Package', 'Single'], default='Package')
    # ad_status=SelectField('Платная услуга', choices=['Free', 'Highlight', 'XL', 'x2_1', 'x2_7', 'x5_1', 'x5_7', 'x10_1', 'x10_7'])
    ad_status=RadioField('Платная услуга', choices=[('Free', 'Free'), ('Highlight', 'Highlight'), ('XL', 'XL'),
                                                     ('x2_1', 'x2_1'), ('x5_1', 'x5_1'), ('x10_1', 'x10_1'), ('x2_7', 'x2_7'), ('x5_7', 'x5_7'), ('x10_7', 'x10_7')],
                         validators=[Required()], default='Free')
    avito_id=StringField('Номер объявления на Авито, если разместили его вручную')
    avito_show=BooleanField('Выставить на Авито',default=True)
    avtoru_show=BooleanField('Выставить на Auto.ru', default=False)
    drom_show=BooleanField('Выставить на Drom', default=False)
    allow_email=BooleanField('Возможность написать сообщение по объявлению через сайт', default="checked")
    manager_name=StringField('Контактное лицо', validators=[Required(), Length(min=1, max=140)])
    contact_phone=StringField('Телефон менеджера', validators=[Required()])
    address=TextAreaField('Полный адрес объекта', validators=[Required(), Length(min=1, max=256)])
    latitude = FloatField('Широта', default=0)
    longitude = FloatField('Долгота', default=0)
    display_area1 = SelectField('Первая зона показа', validate_choice=False, coerce=int)
    display_area2 = StringField('Вторая зона показа')
    display_area3 = StringField('Третья зона показа')
    display_area4 = StringField('Четвертая зона показа')
    display_area5 = StringField('Пятая зона показа')
    # type_id = SelectField(u'Выберите категорию', choices=['Шины', 'Колёса', 'Диски', 'Колпаки'])
    ad_type = SelectField(u'Вид объявления', choices=['Товар приобретен на продажу', 'Товар от производителя'])
    is_for_priority =BooleanField(u'Продвижение на Auto.ru', default=False) #auto.ru кнопка продвижения
    qte=IntegerField(u'Количество', validators=[DataRequired()], default=4)
    title = StringField(u'Название объявления')
    description = TextAreaField(u'Текстовое описание объявления', validators=[DataRequired()])
    price = IntegerField(u'Цена', validators=[DataRequired()])
    condition = SelectField(u'Состояние', choices=['Б/у', 'Новое'])
    oem = StringField(u'Номенклатурный номер')
    recommended_price = IntegerField (u'Рекомендуемая Стоимость')
    product_year = IntegerField(u'Год производства')
    # rim_type = SelectField(u'Тип диска', choices=['Кованые', 'Литые', 'Штампованные', 'Спицованные', 'Сборные'])
    # rimwidth = DecimalField(places=1)
    # rimbolts = IntegerField(u'Количество болтов')
    # rimboltsdiameter = DecimalField(places=1)
    # rimoffset = DecimalField(places=1)
    shirina_profilya = SelectField(u'Ширина профиля', choices=['', '115', '125', '130', '135', '145', '155', '165', '175', '185', '195', '205', '215',
                                                               '225', '230', '235', '245', '255', '265', '275', '285', '295', '305', '315', '325', '335', '345',
                                                               '355', '360','365','375', '380','385','395','400','405','415', '420','425','435','445','455','530','600','605', 'Другое'])
    vysota_profilya=SelectField('Высота профиля', choices=['', '25', '30', '35', '40', '45', '50', '55', '60', '65', '70', '75', '80', '85', '90', '95',
                                                           '100', '105', '110', 'Другое'])
    sezonnost=SelectField('Сезонность', choices=['Зимние нешипованные', 'Зимние шипованные', 'Летние', 'Всесезонные']) #сезонность
    diametr=SelectField('Внутренний Диаметр', choices=['', '4', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                                                       '16.5', '17', '17.5', '18', '19', '19.5', '20', '21', '22', '22.5',
                                                       '23','24','25','26', '26.5', '27', '28', '29', '30', '32', '34', '35', '36', '38',
                                                       '40', '42', '45', '50', '55'])
    protector_height=IntegerField('Глубина протектора', validators=[DataRequired()])
    protector_wear = IntegerField('Износ протектора, %', validators=[DataRequired()])
    photo1=MultipleFileField('Выберите файлы с фото', validators=[FileRequired(), FileAllowed(['png', 'jpg', 'bmp'], "Некорректный формат!")
    ]) #'image', validators=[FileAllowed(images, 'Images only!')]
    videourl=StringField(u'Ссылка на видео Youtube')
    submit = SubmitField('Отправить')

class EditTireForm(FlaskForm):
    listing_fee=SelectField('Пакет размещения', choices=['PackageSingle', 'Package', 'Single'], default='Package')
    ad_status=RadioField('Платная услуга', choices=[('Free', 'Free'), ('Highlight', 'Highlight'), ('XL', 'XL'),
                                                     ('x2_1', 'x2_1'), ('x5_1', 'x5_1'), ('x10_1', 'x10_1'), ('x2_7', 'x2_7'), ('x5_7', 'x5_7'), ('x10_7', 'x10_7')],
                         validators=[Required()], default='Free')
    avito_id=StringField('Номер объявления на Авито, если разместили его вручную')
    avito_show=BooleanField('Выставить на Авито',default=True)
    avtoru_show=BooleanField('Выставить на Auto.ru', default=False)
    drom_show=BooleanField('Выставить на Drom', default=False)
    manager_name=StringField('Контактное лицо', validators=[Length(min=0, max=40)])
    contact_phone=StringField('Телефон менеджера')
    address=TextAreaField('Полный адрес объекта', validators=[DataRequired(), Length(min=1, max=256)])
    display_area1 = SelectField('Первая зона показа', validate_choice=False, coerce=int)
    # type_id = SelectField(u'Выберите категорию', choices=['Шины', 'Колёса', 'Диски', 'Колпаки'])
    ad_type = SelectField(u'Вид объявления', choices=['Товар приобретен на продажу', 'Товар от производителя'])
    is_for_priority =BooleanField(u'Продвижение на Auto.ru', default=False) #auto.ru кнопка продвижения
    qte=IntegerField(u'Количество', validators=[DataRequired()], default=4)
    title = StringField(u'Название объявления', validators=[DataRequired(), Length(min=1, max=256)])
    description = TextAreaField(u'Текстовое описание объявления', validators=[DataRequired()])
    price = IntegerField(u'Цена', validators=[DataRequired()])
    condition = SelectField(u'Состояние', choices=['Б/у', 'Новое'])
    oem = StringField(u'Номенклатурный номер')
    recommended_price = IntegerField (u'Рекомендуемая Стоимость')
    photo1=MultipleFileField('Выберите файлы с фото') #'image', validators=[FileAllowed(images, 'Images only!')]
    videourl=StringField(u'Ссылка на видео Youtube')
    submit = SubmitField('Отправить')


class RimPrepareForm(FlaskForm):
    carBrand = SelectField('Брэнд АМ', validate_choice=False, coerce=int)
    carModel = SelectField('Модель АМ', validate_choice=False, coerce=int)
    carYear = SelectField('Год произво-ва АМ', validate_choice=False, coerce=int)

    rimbrand=SelectField('Производитель', validate_choice=False, coerce=int)
    rimmodel=SelectField('Модель', validate_choice=False, coerce=int)
    listing_fee=SelectField('Пакет размещения', choices=['PackageSingle', 'Package', 'Single'], default='Package')
    ad_status=RadioField('Платная услуга', choices=[('Free', 'Free'), ('Highlight', 'Highlight'), ('XL', 'XL'),
                                                     ('x2_1', 'x2_1'), ('x2_7', 'x2_7'), ('x5_1', 'x5_1'), ('x5_7', 'x5_7'), ('x10_1', 'x10_1'), ('x10_7', 'x10_7')],
                         validators=[Required()], default='Free')
    avito_id=StringField('Номер объявления на Авито, если разместили его вручную')
    avito_show=BooleanField('Выставить на Авито',default=True)
    avtoru_show=BooleanField('Выставить на Auto.ru', default=False)
    drom_show=BooleanField('Выставить на Drom', default=False)
    allow_email=BooleanField('Возможность написать сообщение по объявлению через сайт', default="checked")
    manager_name=StringField('Контактное лицо', validators=[Length(min=0, max=40)])
    contact_phone=StringField('Телефон менеджера')
    address=TextAreaField('Полный адрес объекта', validators=[Length(min=0, max=256)])
    latitude = FloatField('Широта', default=0)
    longitude = FloatField('Долгота', default=0)
    display_area1 = SelectField('Первая зона показа', validate_choice=False, coerce=int)
    display_area2 = StringField('Вторая зона показа')
    display_area3 = StringField('Третья зона показа')
    display_area4 = StringField('Четвертая зона показа')
    display_area5 = StringField('Пятая зона показа')
    ad_type = SelectField(u'Вид объявления', choices=['Товар приобретен на продажу', 'Товар от производителя'])
    is_for_priority =BooleanField(u'Продвижение на Auto.ru', default='unchecked') #auto.ru кнопка продвижения
    rimqte=IntegerField(u'Количество', validators=[DataRequired()], default=4)
    title = StringField(u'Название объявления')
    description = TextAreaField(u'Текстовое описание объявления', validators=[DataRequired()])
    price = IntegerField(u'Цена', validators=[DataRequired()])
    condition = SelectField(u'Состояние', choices=['Б/у', 'Новое'])
    oem = StringField(u'Номенклатурный номер')
    recommended_price = IntegerField (u'Рекомендуемая Стоимость')
    rimtype = SelectField(u'Тип диска', choices=['Кованые', 'Литые', 'Штампованные', 'Спицованные', 'Сборные'], default='Литые')
    rimwidth = SelectField('Ширина обода', choices=['', '3.5', '4', '4.5','5','5.5','6','6.5','6.75', '7','7.5', '8', '8.25', '8.5','9', '9.5',
                                                    '10', '10.5', '11', '11.5', '12', '12.5', '13', '14', '15'] )
    rimdiametr=SelectField('Диаметр', choices=['', '4', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                                                       '16.5', '17', '17.5', '18', '19', '19.5', '20', '21', '22', '22.5',
                                                       '23','24','25','26', '26.5', '27', '28', '29', '30', '32', '34', '35', '36', '38',
                                                       '40', '42', '45', '50', '55'])
    rimoriginal = BooleanField('Оригинал', id='rim_original', default=False)
    rimbolts = SelectField(u'Количество отверстий', choices=['', '3', '4', '5', '6', '8', '9', '10'])
    rimboltsdiametr = SelectField(u'PCD диаметр расп-я отверстий', choices=['', '98', '100', '105', '107.95', '108', '110', '112', '114.3', '115', '118', '120', '127',
                                                            '130', '135', '139.7', '150', '160', '165', '170', '180', '205', '225', '245', '256', '275', '335'])
    rimoffset = SelectField(u'Вылет', choices=['', "-2", "-5","-6","-7","-8","-10","-12","-13","-14","-15","-16","-20","-22","-24","-25",
                                            "-28","-30","-32","-35","-36","-38","-40","-44","-45","-46","-50","-65","-88","-98",
                                            "0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18",
                                            "19","20","21","22","23","23.5","24","25","26","27","28","29","30","31","31.5","32","33",
                                            "34","34.5","35","36","36.5","37","37.5","38","39","39.5","40","40.5","41","41.3","41.5",
                                            "42","43","43.5","43.8","44","45","45.5","46","47","47.5","48","49","49.5","50","50.5",
                                            "50.8","51","52","52.2","52.5","53","54","55","56","57","58","59","60","61","62","63",
                                            "64","65","66","67","68","69","70","75","83","100","102","105","105.5","106","107","108",
                                            "110","111","115","116","118","120","123","124","125","126","127","128","129","130","132",
                                            "133","134","135","136","138","140","142","143","144","145","147","148","152","156","157",
                                            "161","163","165","167","168","172","175","185","185+"])
    rimyear = IntegerField(default=2021, validators=[DataRequired()], id='rimyear')
    photo1=MultipleFileField('Выберите файлы с фото') #'image', validators=[FileAllowed(images, 'Images only!')]
    videourl=StringField(u'Ссылка на видео Youtube')
    submit = SubmitField('Отправить')