from typing import List

import requests

from scheduler import context, dispatchers, queues, rankers, utils
from scheduler.models import Organisation

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
        while not self.queue.is_full():
            try:
                last_run_boefjes = self.ctx.services.bytes.get_last_run_boefje_by_organisation_id(self.organisation.id)
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get last run boefjes [org_id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            if not last_run_boefjes:
                self.logger.info(
                    "No last run boefjes found [org_id=%s, scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            p_items = self.create_tasks_for_boefjes(last_run_boefjes)
            if len(p_items) == 0:
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
                time.sleep(1)

            self.add_p_items_to_queue(p_items)
            time.sleep(1)
        else:
            self.logger.warning(
                "Normalizer queue is full, not populating with new tasks [qsize=%d, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.scheduler_id,
            )
            return

    def create_tasks_for_boefje(self, boefje: BoefjeMeta) -> List[PrioritizedItem]:
        """Create normalizer tasks for every boefje that has been processed.
        """
        p_items: List[queues.PrioritizedItem] = []

        for produces in boefje.produces:
            try:
                plugin = self.ctx.services.plugins.get_normalizers_by_org_id_and_type(
                    self.organisation.id, produces,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get plugin for org: %s and boefje: %s [org_id=%s, boefje_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    boefje.name,
                    self.organisation.id,
                    boefje.name,
                    self.scheduler_id,
                )
                continue

            if not plugin:
                self.logger.warning(
                    "No plugin found for org: %s and boefje: %s [org_id=%s, boefje_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    boefje.name,
                    self.organisation.id,
                    boefje.name,
                    self.scheduler_id,
                )
                continue

            if plugin.enabled is False:
                self.logger.debug(
                    "Plugin: %s is disabled [org_id=%s, plugin_id=%s, scheduler_id=%s]",
                    plugin.id,
                    self.organisation.id,
                    plugin.id,
                    self.scheduler_id,
                )
                continue

            task = NormalizerTask() # TODO

            if self.queue.is_item_on_queue(task)
                self.logger.debug(
                    "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, scheduler_id=%s]",
                    boefje.id,
                    boefje.id,
                    ooi.primary_key,
                    self.scheduler_id,
                )
                continue

            score = self.ranker.rank(SimpleNamespace(task=task))
            p_items.append(queues.PrioritizedItem(priority=score, item=task))

        return p_items
