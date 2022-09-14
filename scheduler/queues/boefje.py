from typing import Any, Dict

from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def get_item_identifier(self, data: Any) -> str:
        boefje_id = dict_utils.deep_get(data, ["data", "boefje", "id"])
        input_ooi = dict_utils.deep_get(data, ["data", "input_ooi"])
        organization = dict_utils.deep_get(data, ["data", "organization"])

        return f"{boefje_id}_{input_ooi}_{organization}"
