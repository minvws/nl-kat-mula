import abc

from scheduler import models


class Datastore(abc.ABC):

    def add_task(self, task: models.TaskORM):
        raise NotImplementedError
