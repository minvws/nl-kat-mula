from scheduler import models

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def get_item_identifier(self, item: models.NormalizerTask) -> str:
        return f"{item.id}_{item.organization}"  # TODO
