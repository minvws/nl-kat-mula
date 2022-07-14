import abc
import logging

from scheduler import models


class Datastore(abc.ABC):
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

    def add_task(self, task: models.Task) -> models.Task:
        raise NotImplementedError
