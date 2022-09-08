from scheduler import models

from .pq import DataStorePriorityQueue, PriorityQueue


class BoefjePriorityQueue(DataStorePriorityQueue):
    def get_item_identifier(self, item: models.BoefjeTask) -> str:
        return f"{item.boefje.id}_{item.input_ooi}_{item.organization}"
