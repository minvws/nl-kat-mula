from scheduler import models

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def get_item_identifier(self, item: models.NormalizerTask) -> str:
        return f"{item.normalizer.id}_{item.raw_data.boefje_meta.id}_{item.raw_data.boefje_meta.organization}"
