FROM python:3.9-slim-bullseye

# Environment variables, setting app home path and copy of the python app in the container
ENV PYTHONUNBUFFERED True

ENV APP_HOME /home/rezinos  
WORKDIR $APP_HOME
RUN useradd rezinos
RUN chown -R rezinos:rezinos ./
# ./

COPY . ./

# Update/upgrade the system
RUN apt -y update
RUN apt -y upgrade

# Install App dependencies and chrome webdriver
RUN apt install -yqq unzip curl wget python3-pip
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# WORKDIR /home/rezinos

copy requirements.txt requirements.txt
# RUN python -m venv venv комментарий
# RUN venv/bin/pip install -r requirements.txt

RUN pip install -r requirements.txt
RUN pip uninstall -y jwt
RUN pip uninstall -y Pyjwt
RUN pip install Pyjwt==1.7.1

RUN pip install gunicorn pymysql

COPY app app
COPY media media
# COPY migrations migrations
COPY run.py config.py boot.sh thorns.csv wear_discounts.csv TirePricesBase.csv RimPricesBase.csv RimsCatalogue.csv TireGide.csv Areas.csv RossiyaAllTires_Result.csv ./
RUN chmod +x boot.sh

ENV FLASK_APP run.py
ENV FLASK_ENV config.ProductionConfig

RUN chown -R rezinos:rezinos ./
USER rezinos

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]

