import uuid

import pydantic
from scheduler import models


class TestModel(pydantic.BaseModel):
    id: str
    name: str


def create_p_item(scheduler_id: str, priority: int) -> models.PrioritizedItem:
    return models.PrioritizedItem(
        scheduler_id=scheduler_id,
        priority=priority,
        data=TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        ),
    )
