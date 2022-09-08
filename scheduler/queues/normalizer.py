from scheduler import models

from .pq import DataStorePriorityQueue, PriorityQueue


class NormalizerPriorityQueue(DataStorePriorityQueue):
    def get_item_identifier(self, item: models.NormalizerTask) -> str:
        return f"{item.normalizer.id}_{item.boefje_meta.id}_{item.boefje_meta.organization}"
