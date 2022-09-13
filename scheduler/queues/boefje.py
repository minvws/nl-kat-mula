from scheduler import models
from scheduler.utils import dict_utils

from .pq import PriorityQueue


class BoefjePriorityQueue(PriorityQueue):
    def get_item_identifier(self, p_item: models.PrioritizedItem) -> str:
        boefje_id = dict_utils.deep_get(p_item, ["data", "boefje", "id"])
        input_ooi = dict_utils.deep_get(p_item, ["data", "input_ooi"])
        organization = dict_utils.deep_get(p_item, ["data", "organization"])

        return f"{boefje_id}_{input_ooi}_{organization}"
