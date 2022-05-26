import time
import uuid
from types import SimpleNamespace
from typing import List

import requests

from scheduler import context, dispatchers, queues, rankers, utils
from scheduler.models import BoefjeMeta, NormalizerTask, Organisation, RawData

from .scheduler import Scheduler


class NormalizerScheduler(Scheduler):
    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        ranker: rankers.Ranker,
        dispatcher: dispatchers.Dispatcher,
        organisation: Organisation,
    ):
        super().__init__(
            ctx=ctx,
            scheduler_id=scheduler_id,
            queue=queue,
            ranker=ranker,
            dispatcher=dispatcher,
        )

        self.organisation: Organisation = organisation

    def populate_queue(self) -> None:
        while not self.queue.full():
            try:
                # TODO: would be better to have a queue for this
                last_raw_data = self.ctx.services.bytes.get_raw(
                    organisation_id=self.organisation.id,
                    normalized=False,
                    limit=1,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get last run boefjes [org_id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            if not last_raw_data:
                self.logger.info(
                    "No last run boefjes found [org_id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            p_items = self.create_tasks_for_raw_data(last_raw_data)
            if len(p_items) == 0:
                time.sleep(5)
                continue

            # NOTE: maxsize 0 means unlimited
            while len(p_items) > self.queue.maxsize - self.queue.pq.qsize() and self.queue.maxsize != 0:
                self.logger.debug(
                    "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d maxsize=%d, scheduler_id=%s]",
                    len(p_items),
                    self.queue.pq.qsize(),
                    self.queue.maxsize,
                    self.scheduler_id,
                )
                time.sleep(5)

            self.add_p_items_to_queue(p_items)
            time.sleep(5)
        else:
            self.logger.warning(
                "Normalizer queue is full, not populating with new tasks [qsize=%d, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.scheduler_id,
            )
            return

    def create_tasks_for_raw_data(self, raw_data: RawData) -> List[queues.PrioritizedItem]:
        """Create normalizer tasks for every boefje that has been processed,
        and created raw data in Bytes.
        """
        p_items: List[queues.PrioritizedItem] = []

        for mime_type in raw_data.mime_types:
            try:
                normalizers = self.ctx.services.katalogus.get_normalizers_by_org_id_and_type(
                    self.organisation.id, mime_type,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get normalizers for org: %s and mime_type: %s [boefje_meta_id=%s, org_id=%s, scheduler_id=%s]",
                    self.organisation.name, mime_type, raw_data.boefje_meta.id, self.organisation.id, self.scheduler_id,
                )
                continue

            if normalizers is None:
                self.logger.debug(
                    "No normalizers found for boefje_id %s [boefje_id=%s, org_id=%s, scheduler_id=%s]",
                    raw_data.boefje_meta.boefje.id, self.organisation.id, self.scheduler_id,
                )
                continue

            self.logger.debug(
                "Found %d normalizers for boefje: %s [boefje_id=%s, normalizers=%s, org_id=%s, scheduler_id=%s]",
                len(normalizers),
                raw_data.boefje_meta.boefje.id,
                raw_data.boefje_meta.boefje.id,
                [normalizer.name for normalizer in normalizers],
                self.organisation.id,
                self.scheduler_id,
            )

            for normalizer in normalizers:
                if normalizer.enabled is False:
                    self.logger.debug(
                        "Normalizer: %s is disabled for org: %s [plugin_id=%s, org_id=%s, scheduler_id=%s]",
                        normalizer.name, self.organisation.name, normalizer.id, self.organisation.id, self.scheduler_id,
                    )
                    continue

                task = NormalizerTask(
                    id=uuid.uuid4().hex,
                    normalizer=normalizer,
                    boefje_meta=raw_data.boefje_meta,
                )

                if self.queue.is_item_on_queue(task):
                    self.logger.debug(
                        "Normalizer task: %s is already on queue [normalizer_id=%s, boefje_meta_id=%s, org_id=%s, scheduler_id=%s]",
                        normalizer.name,
                        normalizer.id,
                        raw_data.boefje_meta.id,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(task=task))
                p_items.append(queues.PrioritizedItem(priority=score, item=task))

        return p_items
