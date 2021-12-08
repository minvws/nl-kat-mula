import logging

from celery import Celery

app = Celery()

app.config_from_object("celery_config")

logging.getLogger("amqp.connection.Connection.heartbeat_tick").setLevel(logging.INFO)
