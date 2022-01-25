from functools import wraps, partial
from logging import getLogger
from typing import Dict, Callable
from uuid import uuid4

import click

from scheduler import settings
from scheduler.app import app
from scheduler.events import EventType
from scheduler.katalogus import Katalogus

logger = getLogger(__name__)


@click.command()
def start() -> None:
    logger.info("Starting scheduler...")
    katalogus = Katalogus(settings.katalogus_api)

    with app.connection() as connection:
        event_receiver = app.events.Receiver(
            connection,
            handlers=make_handlers_first_log_event(
                {
                    EventType.BOEFJE_FINISHED.value: partial(
                        handle_boefje_finished, katalogus=katalogus
                    ),
                    "task-succeeded": on_event,
                }
            ),
        )
        event_receiver.capture()


# FIXME: Remove. For testing only.
def on_event(event):
    logger.info(f"event happened {event}")


def make_handlers_first_log_event(
    handler_mapping: Dict[str, Callable[[Dict], None]]
) -> Dict[str, Callable]:
    return {
        key: first_log_event(handler)
        for key, handler in handler_mapping.items()
    }


def first_log_event(handler: Callable) -> Callable[[Dict], Callable]:
    @wraps(handler)
    def new(event: Dict, *args, **kwargs):
        logger.info("Received event: %s", event)
        return handler(event, *args, **kwargs)

    return new


def handle_boefje_finished(event: Dict, katalogus: Katalogus) -> None:
    # FIXME: are we certain of the keys in the event?
    schedule_normalizers(event["fields"]["job_meta"], katalogus)


def schedule_normalizers(job_meta: Dict, katalogus: Katalogus) -> None:
    logger.info("Scheduling normalizers")

    normalizers_by_boefje = katalogus.get_normalizer_modules_by_boefje_module()
    normalizer_modules = normalizers_by_boefje.get(job_meta["module"], [])

    # NOTE: will be in the form as:
    # [{"id":"binaryedge","name":"BinaryEdge","description":"Use BinaryEdge to find open ports with vulnerabilities that are found on that port","consumes":["IPAddressV6","IPAddressV4"],"produces":["IPPort","KATFindingType","Finding","SoftwareInstance","IPService","Software","CVEFindingType","Service"],"scan_level":1,"image":null}]

    for normalizer_module in normalizer_modules:
        # FIXME: is this still correct? See: https://github.com/minvws/nl-rt-tim-abang-boefjes/blob/develop/tasks.py#L24-L28
        #
        # like:
        #
        # normalizer_job_meta = dict(
        #     id=job_meta["id"],
        #     normalizer=normalizer_module,
        #     boefje_meta=job_meta,
        # )

        normalizer_job_meta = dict(
            id=str(uuid4()),
            module=normalizer_module,
            arguments=job_meta["arguments"],
            organization=job_meta["organization"],
        )

        logger.info("Scheduling job: %s", normalizer_job_meta)

        app.send_task(
            "tasks.handle_normalizer",
            (normalizer_job_meta,),
            queue="normalizers",
        )


if __name__ == "__main__":
    start()
