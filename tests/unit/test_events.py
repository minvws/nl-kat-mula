from scheduler.events import BoefjeFinishedEvent
from tests.load import get_job_meta


def test_create_event() -> None:
    boefje_finished_event = BoefjeFinishedEvent(job_meta=get_job_meta())

    assert boefje_finished_event.type.value == "boefjes.boefje-finished"
