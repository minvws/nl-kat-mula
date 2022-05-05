import datetime
import time
import uuid
from types import SimpleNamespace
from typing import List

import pika
import requests

from scheduler import context, dispatchers, queues, rankers, utils
from scheduler.models import OOI, BoefjeTask, Organisation

from .scheduler import Scheduler


class BoefjeScheduler(Scheduler):
    """A KAT specific implementation of a Boefje Scheduler

    Attributes:
        organisation: The organisation that this scheduler is for.
    """

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
                latest_oois = self.ctx.services.scan_profile.get_latest_objects(
                    queue=f"{self.organisation.id}__scan_profile_increments",
                    n=10,
                )
            except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed, pika.exceptions.ChannelClosedByBroker):
                self.logger.warning(
                    "Could not get latest oois for organisation: %s [scheduler_id=%s]",
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            # From ooi's create prioritized items to push onto queue
            p_items = self.create_tasks_for_oois(latest_oois)

            if len(latest_oois) == 0 or len(p_items) == 0:
                self.logger.debug(
                    "No latest oois for organisation: %s [org_id=%s ,scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            self.add_p_items_to_queue(p_items)
            time.sleep(1)
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.scheduler_id,
            )
            return

        while not self.queue.full():
            try:
                random_oois = self.ctx.services.octopoes.get_random_objects(
                    organisation_id=self.organisation.id, n=10,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get random oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            # From ooi's create prioritized items to push onto queue
            p_items = self.create_tasks_for_oois(random_oois)

            if len(random_oois) == 0 or len(p_items) == 0:
                self.logger.debug(
                    "No random oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break

            self.add_p_items_to_queue(p_items)

            time.sleep(1)
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, scheduler_id=%s]",
                self.queue.pq.qsize(),
                self.scheduler_id,
            )
            return

    def create_tasks_for_oois(self, oois: List[OOI]) -> List[queues.PrioritizedItem]:
        """For every provided ooi we will create available and enabled boefje
        tasks.

        Args:
            oois: A list of OOIs.

        Returns:
            A list of BoefjeTasks.
        """
        p_items: List[queues.PrioritizedItem] = []
        for ooi in oois:
            try:
                boefjes = self.ctx.services.katalogus.get_boefjes_by_ooi_type(
                    ooi.ooi_type,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get boefjes for ooi_type: %s [ooi_type=%s, scheduler_id=%s]",
                    ooi.ooi_type,
                    ooi.ooi_type,
                    self.scheduler_id,
                )
                continue

            if boefjes is None:
                self.logger.debug(
                    "No boefjes found for type: %s [ooi=%s, scheduler_id=%s]",
                    ooi.ooi_type,
                    ooi,
                    self.scheduler_id,
                )
                continue

            self.logger.debug(
                "Found %s boefjes for ooi: %s [ooi=%s, boefjes=%s, scheduler_id=%s]",
                len(boefjes),
                ooi,
                ooi,
                [boefje.id for boefje in boefjes],
                self.scheduler_id,
            )

            for boefje in boefjes:
                try:
                    plugin = self.ctx.services.katalogus.get_plugin_by_org_and_boefje_id(
                        organisation_id=self.organisation.id,
                        boefje_id=boefje.id,
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

                if plugin is None:
                    self.logger.debug(
                        "No plugin found for boefje: %s [org_id=%s, boefje_id=%s, scheduler_id=%s]",
                        boefje.id,
                        self.organisation.id,
                        boefje.id,
                        self.scheduler_id,
                    )
                    continue

                if plugin.enabled is False:
                    self.logger.debug(
                        "Boefje: %s is disabled [org_id=%s, boefje_id=%s, scheduler_id=%s]",
                        boefje.id,
                        self.organisation.id,
                        boefje.id,
                        self.scheduler_id,
                    )
                    continue

                task = BoefjeTask(
                    id=uuid.uuid4().hex,
                    boefje=boefje,
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if ooi.scan_profile is None:
                    self.logger.debug(
                        "No scan_profile found for ooi: %s [ooi_id=%s, scan_profile=%s, scheduler_id=%s]",
                        ooi.primary_key,
                        ooi,
                        ooi.scan_profile,
                        self.scheduler_id,
                    )
                    continue

                ooi_scan_level = ooi.scan_profile.level
                if ooi_scan_level is None:
                    self.logger.warning(
                        "No scan level found for ooi: %s [ooi_id=%s, scheduler_id=%s]",
                        ooi.primary_key,
                        ooi,
                        self.scheduler_id,
                    )
                    continue

                boefje_scan_level = boefje.scan_level
                if boefje_scan_level is None:
                    self.logger.warning(
                        "No scan level found for boefje: %s [boefje_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje,
                        self.scheduler_id,
                    )
                    continue

                # Boefje intensity score ooi clearance level, range
                # from 0 to 4. 4 being the highest intensity, and 0 being
                # the lowest. OOI clearance level defines what boefje
                # intesity is allowed to run on.
                if boefje_scan_level > ooi_scan_level:
                    self.logger.debug(
                        "Boefje: %s scan level %s is too intense for ooi: %s scan level %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje_scan_level,
                        ooi.primary_key,
                        ooi_scan_level,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                # We don't want the populator to add/update tasks to the
                # queue, when they are already on there. However, we do
                # want to allow the api to update the priority. So we
                # created the queue with allow_priority_updates=True
                # regardless. When the ranker is updated to correctly rank
                # tasks, we can allow the populator to also update the
                # priority. Then remove the following:
                if self.queue.is_item_on_queue(task):
                    self.logger.debug(
                        "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.scheduler_id,
                    )
                    continue

                # Boefjes should not run before the grace period ends
                try:
                    last_run_boefje = self.ctx.services.bytes.get_last_run_boefje(
                        boefje_id=boefje.id,
                        input_ooi=ooi.primary_key,
                        organization_id=self.organisation.id,
                    )
                except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                    self.logger.warning(
                        "Could not get last run boefje for boefje: %s with ooi: %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.name,
                        ooi.primary_key,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                if (
                    last_run_boefje is not None
                    and last_run_boefje.ended_at is None  # TODO: will this be none?
                    and last_run_boefje.start_time is not None
                ):
                    self.logger.debug(
                        "Boefje %s is already running [boefje_id=%s, ooi_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.scheduler_id,
                    )
                    continue

                if (
                    last_run_boefje is not None
                    and last_run_boefje.ended_at is not None
                    and datetime.datetime.now().astimezone() - last_run_boefje.ended_at
                    < datetime.timedelta(seconds=self.ctx.config.pq_populate_grace_period)
                ):
                    self.logger.debug(
                        "Boefje: %s already run for input ooi %s [last_run_boefje=%s, scheduler_id=%s]",
                        boefje.id,
                        ooi.primary_key,
                        last_run_boefje,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(last_run_boefje=last_run_boefje, task=task))
                if score < 0:
                    self.logger.warning(
                        "Score too low for boefje: %s and input ooi: %s [boefje_id=%s, ooi_id=%s, scheduler_id=%s]",
                        boefje.id,
                        ooi.primary_key,
                        boefje.id,
                        ooi.primary_key,
                        self.scheduler_id,
                    )
                    continue

                p_items.append(queues.PrioritizedItem(priority=score, item=task))

        return p_items
