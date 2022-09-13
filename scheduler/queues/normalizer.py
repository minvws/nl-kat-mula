from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def get_item_identifier(self, item: models.PrioritizedItem) -> str:
        normalizer_id = dict_utils.deep_get(item, ["data", "normalizer", "id"])
        input_ooi = dict_utils.deep_get(item, ["data", "input_ooi"])
        organization = dict_utils.deep_get(item, ["data", "organization"])

        return f"{normalizer_id}_{input_ooi}_{organization}"
