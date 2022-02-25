from .listeners import RabbitMQ


class Octopoes(RabbitMQ):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        self.logger.info("hello, world")
