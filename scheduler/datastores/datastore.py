import abc
import logging
from typing import List, Union

from scheduler import models


class Datastore(abc.ABC):
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def get_tasks(self, scheduler_id: Union[str, None], status: Union[str, None], offset: int = 0, limit: int = 100) -> (List[models.Task], int):
        raise NotImplementedError

    @abc.abstractmethod
    def get_task_by_id(self, id: str) -> models.Task:
        raise NotImplementedError

    @abc.abstractmethod
    def get_task_by_hash(self, task_id: hash) -> models.Task:
        raise NotImplementedError

    @abc.abstractmethod
    def add_task(self, task: models.Task) -> models.Task:
        raise NotImplementedError

    @abc.abstractmethod
    def update_task(self, task: models.Task) -> models.Task:
        raise NotImplementedError
