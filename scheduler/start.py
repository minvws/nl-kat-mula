from functools import wraps, partial
from logging import getLogger
from typing import Dict, List, Callable
from uuid import uuid4

import click
from bytes import JobMeta
from pydantic import parse_obj_as

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
                    EventType.BOEFJE_FINISHED.value: partial(handle_boefje_finished, katalogus=katalogus),
                }
            ),
        )
        event_receiver.capture()


def make_handlers_first_log_event(handler_mapping: Dict[str, Callable[[Dict], None]]) -> Dict[str, Callable]:
    return {key: first_log_event(handler) for key, handler in handler_mapping.items()}


def first_log_event(handler: Callable) -> Callable[[Dict], Callable]:
    @wraps(handler)
    def new(event: Dict, *args, **kwargs):
        logger.info("Received event: %s", event)
        return handler(event, *args, **kwargs)

    return new


def handle_boefje_finished(event: Dict, katalogus: Katalogus) -> None:
    job_meta: JobMeta = parse_obj_as(JobMeta, event["fields"]["job_meta"])

    schedule_normalizers(job_meta, katalogus)


def schedule_normalizers(job_meta: JobMeta, katalogus: Katalogus) -> None:
    logger.info("Scheduling normalizers")
    normalizers_by_boefje = katalogus.get_normalizer_modules_by_boefje_module()
    normalizer_modules = normalizers_by_boefje.get(job_meta.module, [])

    for normalizer_module in normalizer_modules:
        normalizer_job_meta = JobMeta(
            id=str(uuid4()),
            module=normalizer_module,
            arguments=job_meta.arguments,
            organization=job_meta.organization,
        )
        logger.info("Scheduling job: %s", normalizer_job_meta)

        app.send_task("tasks.handle_normalizer", (normalizer_job_meta,), queue="normalizers")


if __name__ == "__main__":
    start()
