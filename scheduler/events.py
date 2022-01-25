from abc import ABC
from enum import Enum
from typing import Dict

from pydantic import BaseModel

from scheduler.app import app

BOEFJES_APP_PREFIX = "boefjes."


class EventType(Enum):
    # Boefjes events
    BOEFJE_FINISHED = BOEFJES_APP_PREFIX + "boefje-finished"


class Event(BaseModel, ABC):
    type: EventType

    class Config:
        use_enum_values = True


# FIXME: is the event structure going to be the same, or like https://github.com/minvws/nl-rt-tim-abang-boefjes/blob/develop/tasks.py#L17? which is a BoefjeMeta https://github.com/minvws/nl-rt-tim-abang-boefjes/blob/51a0ed399261fd2d8dad63dcd1583e7e3702dcf9/job.py#L42
class BoefjeFinishedEvent(Event):
    type = EventType.BOEFJE_FINISHED
    job_meta: Dict


def dispatch(event: Event) -> None:
    with app.connection() as connection:
        event_dispatcher = app.events.Dispatcher(connection)
        event_dispatcher.send(type=event.type, event=event.dict())
