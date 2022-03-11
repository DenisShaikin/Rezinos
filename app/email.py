from flask_mail import Message
from flask import render_template
from flask import current_app as app
import smtplib


toHex = lambda x:"".join([hex(ord(c))[2:].zfill(2) for c in x])

def send_email(subject, sender, recipients, text_body, html_body):
    from email.message import EmailMessage
    # mail=init_mail(app)
    print('server={}, port={}'.format(app.config['MAIL_SERVER'], app.config['MAIL_PORT']))
    print('login=', ascii(app.config['MAIL_USERNAME']))
    print('pass=', ascii(app.config['MAIL_PASSWORD']))
    server = smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['To'] = recipients
    msg['From'] = sender
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype='html')
    server.send_message(msg)
    server.quit()

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Rezinos] Сбросить пароль',
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('accounts/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('accounts/reset_password.html',
                                         user=user, token=token))