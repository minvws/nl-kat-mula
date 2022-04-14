from scheduler import models, queue


class BoefjePriorityQueue(queue.PriorityQueue):
    def get_item_identifier(self, item: models.BoefjeTask) -> str:
        return f"{item.boefje.id}_{item.input_ooi}_{item.organization}"
