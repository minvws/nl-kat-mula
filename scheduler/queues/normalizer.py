from typing import Any, Dict

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class NormalizerPriorityQueue(PriorityQueue):
    def get_item_identifier(self, data: Dict) -> str:
        normalizer_id = dict_utils.deep_get(data, ["normalizer", "id"])
        input_ooi = dict_utils.deep_get(data, ["input_ooi"])
        organization = dict_utils.deep_get(data, ["organization"])

        return f"{normalizer_id}_{input_ooi}_{organization}"
