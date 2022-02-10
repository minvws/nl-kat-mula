import logging

import pika


# TODO: you can do an implementation of a specific Listener that users
# the context and do dispatches on that. Figure out what form works best.
class Listener:
    func: callable

    def __init__(self, func: callable):
        self.func = func

    def dispatch(self):
        self.func()  # TODO: will this work with arguments? and context?


class RabbitMQ(Listener):
    logger: logging.Logger
    dsn: str
    queue: str

    def __init__(self, func: callable, dsn: str, queue: str):
        super().__init__(func)
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

        self.dispatch()

        channel.basic_ack(delivery_tag=method_frame.delivery_tag)


class Kafka(Listener):
    pass
