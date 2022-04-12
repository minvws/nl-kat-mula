import abc
import logging

import pika


# TODO: you can do an implementation of a specific Listener that users
# the context and do dispatches on that. Figure out what form works best.
class Listener(abc.ABC):
    """The Listener base class interface

    Attributes:
        logger:
            The logger for the class.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def listen(self) -> None:
        raise NotImplementedError


class RabbitMQ(Listener):
    """A RabbitMQ Listener implementation that allows subclassing of specific
    RabbitMQ channel listeners. You can subclass this class and set the
    channel and procedure that needs to be dispatched when receiving messages
    from a RabbitMQ queue.

    Attibutes:
        dsn:
            A string defining the data source name of the RabbitMQ host to
            connect to.
        queue:
            A string defining the RabbitMQ queue to listen to.
    """

    def __init__(self, dsn: str, queue: str):
        super().__init__()
        self.dsn = dsn
        self.queue = queue

    def dispatch(self) -> None:
        raise NotImplementedError

    def listen(self) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        channel = connection.channel()
        channel.basic_consume(queue=self.queue, on_message_callback=self.callback)
        channel.start_consuming()

    def callback(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        self.logger.debug(" [x] Received %r" % body)

        self.dispatch()

        channel.basic_ack(delivery_tag=method.delivery_tag)
