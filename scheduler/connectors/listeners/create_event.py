from .listeners import RabbitMQ


class CreateEventListener(RabbitMQ):
    def __init__(self, *args, **kwargs):

        self.ctx = kwargs.pop("ctx")
        self.normalizer_queue = kwargs.pop("normalizer_queue")

        super().__init__(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        self.logger.info("hello, world")

        # TODO: put it on the normalizer queue
