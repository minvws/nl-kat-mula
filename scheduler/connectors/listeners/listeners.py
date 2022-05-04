import json
import logging
from typing import Dict, Optional

import pika


class Listener:
    """The Listener base class interface

    Attributes:
        name:
            Identifier of the Listener
        logger:
            The logger for the class.
    """

    name: Optional[str] = None

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

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

    def __init__(self, dsn: str):
        super().__init__()
        self.dsn = dsn

    def dispatch(self, body: bytes) -> None:
        """Dispatch a message without a return value"""
        raise NotImplementedError

    def basic_consume(self, queue: str) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        channel = connection.channel()
        channel.basic_consume(queue, on_message_callback=self.callback)
        channel.start_consuming()

    def get(self, queue: str) -> Optional[Dict[str, object]]:
        connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        channel = connection.channel()
        method, properties, body = channel.basic_get(queue)

        if body is None:
            return None

        response = json.loads(body)
        channel.basic_ack(method.delivery_tag)

        return response

    def callback(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        self.logger.debug(" [x] Received %r", body)

        self.dispatch(body)

        channel.basic_ack(method.delivery_tag)
