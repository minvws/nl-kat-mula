import logging

import pika


# TODO: you can do an implementation of a specific Listener that users
# the context and do dispatches on that. Figure out what form works best.
class Listener:
    logger: logging.Logger

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def dispatch(self, *args, **kwargs):
        raise NotImplementedError


class RabbitMQ(Listener):
    dsn: str
    queue: str

    def __init__(self, dsn: str, queue: str):
        super().__init__()
        self.dsn = dsn
        self.queue = queue

    def listen(self):
        connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        channel = connection.channel()
        channel.basic_consume(queue=self.queue, on_message_callback=self.callback)
        channel.start_consuming()

    def callback(self, *args, **kwargs):
        channel, method_frame, header_frame, body = args
        self.logger.info(" [x] Received %r" % body)

        self.dispatch(args, kwargs)

        channel.basic_ack(delivery_tag=method_frame.delivery_tag)


class Kafka(Listener):
    pass
