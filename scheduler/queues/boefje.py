from scheduler import models

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def get_item_identifier(self, item: models.BoefjeTask) -> str:
        return item.hash
