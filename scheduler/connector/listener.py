import logging

import pika


class Listener:
    pass


class RabbitMQ(Listener):
    logger: logging.Logger
    dsn: str
    queue: str

    def __init__(self, dsn, queue):
        self.logger = logging.getLogger(__name__)
        self.dsn = dsn
        self.queue = queue

    def listen(self):
        connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        channel = connection.channel()
        channel.basic_consume(queue=self.queue, on_message_callback=self.callback)
        channel.start_consuming()

    def callback(self, channel, method_frame, header_frame, body):
        self.logger.info(" [x] Received %r" % body)

        # TODO: do something, pass in function

        channel.basic_ack(delivery_tag=method_frame.delivery_tag)


class Kafka(Listener):
    pass
