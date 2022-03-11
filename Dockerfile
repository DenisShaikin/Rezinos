FROM python:3.9-slim-bullseye

RUN useradd rezinos
WORKDIR /home/rezinos

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

RUN chown -R rezinos:rezinos ./
USER rezinos

EXPOSE 5000

ENTRYPOINT ["./boot.sh"]

