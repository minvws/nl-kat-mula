from scheduler import models, queue


class BoefjePriorityQueue(queue.PriorityQueue):
    def get_item_identifier(self, item: models.BoefjeTask) -> str:
        return f"{item.boefje.id}-{item.input_ooi}-{item.organization}"
