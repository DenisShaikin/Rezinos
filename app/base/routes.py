# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import random
import string
from flask import render_template, redirect, request, url_for
from flask_login import (
    current_user,
    login_user,
    logout_user
)

from app import db, login_manager
from app.base import blueprint
from app.base.forms import LoginForm, CreateAccountForm
from app.base.models import User

from app.base.util import verify_pass

from app.base.forms import ResetPasswordRequestForm
from app.base.forms import ResetPasswordForm
from app.email import send_password_reset_email
import os
from flask import current_app as app

## Login & Registration


@blueprint.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('home_blueprint.index'))
    form = ResetPasswordRequestForm()

    if 'reset_password' in request.form:
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        return redirect(url_for('base_blueprint.login'))
    return render_template('accounts/emailpass.html',
                           msg='Введите Ваш email', form=form)

@blueprint.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home_blueprint.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('home_blueprint.index'))
    ResetPassForm = ResetPasswordForm()
    if 'reset_password' in request.form:
        if ResetPassForm.password.data==ResetPassForm.password2.data:
            user.set_password(ResetPassForm.password.data)
            db.session.commit()
            # flash('Your password has been reset.')
            return redirect(url_for('base_blueprint.login'))
        else :
            print('Пароль не совпадает')
            render_template( 'accounts/reset_passwordform.html',
                             msg='Пароль не совпадает',
                             success=False,
                             form=ResetPassForm)

    return render_template( 'accounts/reset_passwordform.html',
                            msg='Введите новый пароль 2 раза',
                            success=False,
                            form=ResetPassForm)

@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))  #'base_blueprint.login' home_blueprint.stocks

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:
        
        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        user = User.query.filter_by(username=username).first()
        
        # Check the password
        if user and verify_pass( password, user.password):

            login_user(user)
            return redirect(url_for('base_blueprint.route_default'))

        # Something (user or pass) is not ok
        return render_template( 'accounts/login.html', msg='Неверный логин или пароль', form=login_form)

    if not current_user.is_authenticated:
        return render_template( 'accounts/login.html',
                                form=login_form)
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    login_form = LoginForm(request.form)
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username  = request.form['username']
        email     = request.form['email'   ]

        # Check usename exists
        user = User.query.filter_by(username=username).first()
        if user:
            return render_template( 'accounts/register.html', 
                                    msg='Логин уже существует',
                                    success=False,
                                    form=create_account_form)

        # Check email exists
        user = User.query.filter_by(email=email).first()
        if user:
            return render_template( 'accounts/register.html',
                                    msg='email уже существует',
                                    success=False,
                                    form=create_account_form)

        # else we can create the user
        user = User(**request.form)
        randomstring=''.join(random.choice(string.ascii_letters + username) for i in range(20))
        user.avito_path=os.path.join(randomstring + '_' + 'avito.xml')
        user.autoru_path=os.path.join(randomstring + '_' + 'auto.xml')
        user.drom_path=os.path.join(randomstring + '_' + 'drom.xml')
        user.youla_path=os.path.join(randomstring + '_' + 'youla.xml')
        user.avatar_photo='assets/img/team/test_profile-picture-4.jpg'

        # print(request.form)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('base_blueprint.login'))
        # return render_template( 'accounts/login.html',
        #                         msg='Пользователь создан <a href="/login">Войти</a>',
        #                         success=True,
        #                         form=login_form)

    else:
        return render_template( 'accounts/register.html', form=create_account_form)

@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('base_blueprint.login'))

## Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('page-403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('page-403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('page-404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('page-500.html'), 500
