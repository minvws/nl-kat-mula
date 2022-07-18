import abc
import logging

from scheduler import models


class Datastore(abc.ABC):
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

    def get_task_by_id(self, task_id: str) -> models.Task:
        raise NotImplementedError

    def add_task(self, task: models.Task) -> models.Task:
        raise NotImplementedError

    def update_task(self, task: models.Task) -> models.Task:
        raise NotImplementedError
