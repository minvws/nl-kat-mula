from .listeners import RabbitMQ


# NOTE: this is an example and not implement or doing anything substantial>
class CreateEventListener(RabbitMQ):
    """The CreateEventListener listens on the the RabbitMQ queue channel
    `create_event` for newly created objects in Octopoes.

    Attributes:
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        normalizer_queue:
            A string describing the normalizer priority queue on which
            incoming objects can be posted to.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.ctx = kwargs.pop("ctx")
        self.normalizer_queue = kwargs.pop("normalizer_queue")

        super().__init__(*args, **kwargs)

    def dispatch(self, *args, **kwargs) -> None:
        self.logger.info("hello, world")

        # TODO: put it on the normalizer queue
