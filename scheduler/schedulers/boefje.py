import copy
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List, Optional

import mmh3
import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import OOI, Boefje, BoefjeTask, Organisation, Plugin, PrioritizedItem, TaskStatus

from .scheduler import Scheduler


class BoefjeScheduler(Scheduler):
    """A KAT specific implementation of a Boefje scheduler. It extends
    the `Scheduler` class by adding a `organisation` attribute.

    Attributes:
        organisation: The organisation that this scheduler is for.
    """

    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        ranker: rankers.Ranker,
        organisation: Organisation,
        populate_queue_enabled: bool = True,
    ):
        super().__init__(
            ctx=ctx,
            scheduler_id=scheduler_id,
            queue=queue,
            ranker=ranker,
            populate_queue_enabled=populate_queue_enabled,
        )

        self.organisation: Organisation = organisation

    def populate_queue(self) -> None:
        """Populate the PriorityQueue."""

        # scan levels changes of ooi's
        self.create_tasks_scan_level_change()

        # new boefjes
        self.create_tasks_new_boefje()

        # rescheduling of oois
        self.create_tasks_reschedule_ooi()

    def create_tasks_scan_level_change(self):
        """Create tasks for oois that have a scan level change.

        We loop until we don't have any messages on the queue anymore.
        """
        while not self.queue.full():
            latest_ooi = None
            try:
                latest_ooi = self.ctx.services.scan_profile.get_latest_object(
                    queue=f"{self.organisation.id}__scan_profile_increments",
                )
            except (
                pika.exceptions.ConnectionClosed,
                pika.exceptions.ChannelClosed,
                pika.exceptions.ChannelClosedByBroker,
                pika.exceptions.AMQPConnectionError,
            ) as e:
                self.logger.warning(
                    "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__scan_profile_increments",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

            if latest_ooi is None:
                return

            if latest_ooi is not None:
                self.logger.debug(
                    "Received scan profile increment for ooi: %s [org_id=%s, scheduler_id=%s]",
                    latest_ooi,
                    self.organisation.id,
                    self.scheduler_id,
                )

                # From ooi's create prioritized items (tasks) to push onto queue
                # continue with the next object (when there are more objects)
                # to see if there are more tasks to add.
                p_items = self.create_tasks_for_oois([latest_ooi])
                if not p_items:
                    continue

                # NOTE: maxsize 0 means unlimited
                while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
                    self.logger.debug(
                        "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                        self.queue.maxsize,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    time.sleep(1)

                self.push_items_to_queue(p_items)

                # Create or update in OOI store with checked_at
                self.ctx.ooi_store.create_or_update_ooi(latest_ooi)
            else:
                # Stop the loop when we've processed everything from the
                # messaging queue, so we can continue to the next step.
                self.logger.debug(
                    "No latest oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                break
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def create_tasks_new_boefje(self) -> None:
        """Create tasks for the ooi's that are associated with a new added boefjes."""
        if self.queue.full():
            self.logger.info(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

        latest_boefje = None
        try:
            new_boefjes = self.ctx.services.katalogus.get_new_boefjes_by_org_id(self.organisation.id)
        except (
            pika.exceptions.ConnectionClosed,
            pika.exceptions.ChannelClosed,
            pika.exceptions.ChannelClosedByBroker,
            pika.exceptions.AMQPConnectionError,
        ) as e:
            self.logger.warning(
                "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                f"{self.organisation.id}__scan_profile_increments",
                self.organisation.id,
                self.scheduler_id,
            )
            if self.stop_event.is_set():
                raise e

        if new_boefjes is None:
            return

        oois = set()
        for new_boefje in new_boefjes:
            for type_ in new_boefje.consumes:
                oois.update(self.ctx.ooi_store.get_oois_by_type(organisation_id=self.organisation.id, type=type_))

        p_items = self.create_tasks_for_oois(list(oois))
        if not p_items:
            return

        # NOTE: maxsize 0 means unlimited
        while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
            self.logger.debug(
                "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.maxsize,
                self.organisation.id,
                self.scheduler_id,
            )
            time.sleep(1)

        self.push_items_to_queue(p_items)

        # Create or update in OOI store with checked_at
        for ooi in oois:
            self.ctx.ooi_store.create_or_update_ooi(ooi)

    def create_tasks_reschedule_ooi(self) -> None:
        """Create tasks for ooi's that need to be rescheduled."""
        if self.queue.full():
            self.logger.info(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

        oois = self.reschedule_oois()
        if not oois:
            self.logger.debug(
                "No oois for organisation to be rescheduled: %s [org_id=%s, scheduler_id=%s]",
                self.organisation.name,
                self.organisation.id,
                self.scheduler_id,
            )
            return

        # From ooi's create prioritized items (tasks) to push onto queue
        p_items = self.create_tasks_for_oois(oois)
        if not p_items:
            return

        # NOTE: maxsize 0 means unlimited
        while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
            self.logger.debug(
                "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.maxsize,
                self.organisation.id,
                self.scheduler_id,
            )
            time.sleep(1)

        self.push_items_to_queue(p_items)

        # Create or update in OOI store with checked_at
        for ooi in oois:
            self.ctx.ooi_store.create_or_update_ooi(ooi)

    def create_tasks_for_oois(self, oois: List[OOI]) -> List[PrioritizedItem]:
        """For every provided ooi we will create available and enabled boefje
        tasks.

        Args:
            oois: A list of OOIs.

        Returns:
            A list of BoefjeTask of type PrioritizedItem.
        """
        tasks: List[PrioritizedItem] = []
        for ooi in oois:
            tasks_for_ooi = self.create_tasks_for_ooi(ooi)
            tasks.extend(tasks_for_ooi)

        return tasks

    def create_tasks_for_ooi(self, ooi: OOI) -> List[PrioritizedItem]:
        """For an ooi we will create available and enabled boefje tasks.

        Args:
            ooi: The ooi to create tasks for.

        Returns:
            A list of BoefjeTask of type PrioritizedItem.
        """
        boefjes: List[Plugin] = self.get_boefjes_for_ooi(ooi)
        if boefjes is None or len(boefjes) == 0:
            self.logger.debug(
                "No boefjes for ooi: %s [org_id=%s, scheduler_id=%s]",
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        p_items = self.create_p_items_for_boefjes(boefjes, ooi)

        return p_items

    def get_boefjes_for_ooi(self, ooi) -> List[Plugin]:
        """Get available all boefjes (enabled and disabled) for an ooi.

        Args:
            ooi: The models.OOI to get boefjes for.

        Returns:
            A list of Plugin of type Boefje that can be run on the ooi.
        """
        try:
            boefjes = self.ctx.services.katalogus.get_boefjes_by_type_and_org_id(
                ooi.object_type,
                self.organisation.id,
            )
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning(
                "Could not get boefjes for object_type: %s [object_type=%s, org_id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi.object_type,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        if boefjes is None:
            self.logger.debug(
                "No boefjes found for type: %s [ooi=%s, org_id=%s, scheduler_id=%s]",
                ooi.object_type,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return []

        self.logger.debug(
            "Found %s boefjes for ooi: %s [ooi=%s, boefjes=%s, org_id=%s, scheduler_id=%s]",
            len(boefjes),
            ooi,
            ooi,
            [boefje.id for boefje in boefjes],
            self.organisation.id,
            self.scheduler_id,
        )

        return boefjes

    def create_p_items_for_boefjes(self, boefjes: List[Plugin], ooi: OOI) -> List[PrioritizedItem]:
        """For an ooi and its associated boefjes we will create tasks that
        can be pushed onto the queue.

        Args:
            boefjes: A list of Boefje objects.
            ooi: The OOI for which the tasks need to be created.

        Returns:
            A list of Boefje tasks of type PrioritizedItem.
        """
        p_items: List[PrioritizedItem] = []
        for boefje in boefjes:
            p_item = self.create_p_item_for_boefje(boefje, ooi)
            if p_item is None:
                continue

            p_items.append(p_item)

        return p_items

    def create_p_item_for_boefje(self, boefje: Plugin, ooi: OOI) -> Optional[PrioritizedItem]:
        """For an ooi and its associated boefjes we will create tasks that
        can be pushed onto the queue. It will check:

            * If the boefje is enabled
            * Is allowed to run on the ooi (scan level / profile)
            * If the boefje is already running on the ooi
            * If the boefje has already run within the grace period

        Args:
            boefjes: A list of Boefje objects.
            ooi: The OOI for which the tasks need to be created.

        Returns:
            A Boefje tasks of type PrioritizedItem.
        """
        if boefje.enabled is False:
            self.logger.debug(
                "Boefje: %s is disabled [org_id=%s, boefje_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.name,
                self.organisation.id,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        task = BoefjeTask(
            boefje=Boefje.parse_obj(boefje),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        if ooi.scan_profile is None:
            self.logger.debug(
                "No scan_profile found for ooi: %s [ooi_id=%s, scan_profile=%s, org_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                ooi.scan_profile,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        ooi_scan_level = ooi.scan_profile.level
        if ooi_scan_level is None:
            self.logger.warning(
                "No scan level found for ooi: %s [ooi_id=%s, org_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s [boefje_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

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
            return None

        # We don't want the populator to add/update tasks to the
        # queue, when they are already on there. However, we do
        # want to allow the api to update the priority. So we
        # created the queue with allow_priority_updates=True
        # regardless. When the ranker is updated to correctly rank
        # tasks, we can allow the populator to also update the
        # priority. Then remove the following:
        if self.queue.is_item_on_queue(PrioritizedItem(scheduler_id=self.scheduler_id, data=task)):
            self.logger.debug(
                "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        try:
            task_db = self.ctx.task_store.get_task_by_hash(
                mmh3.hash_bytes(f"{ooi.primary_key}-{boefje.id}-{self.organisation.id}").hex()
            )

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
            return None

        # Task has been finished (failed, or succeeded), and we have no results
        # of it in bytes.
        if (
            task_db is not None
            and last_run_boefje is None
            and (task_db.status != TaskStatus.COMPLETED or task_db.status == TaskStatus.FAILED)
        ):
            self.logger.warning(
                "Boefje: %s is not in the last run boefjes, but is in the tasks table [task_id=%s, boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                task_db.id,
                boefje.name,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        # Is boefje still running according to the database?
        if task_db is not None and (task_db.status != TaskStatus.COMPLETED or task_db.status == TaskStatus.FAILED):
            self.logger.debug(
                "Boefje: %s is still being processed [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        # Is boefje still running according to bytes?
        if last_run_boefje is not None and last_run_boefje.ended_at is None and last_run_boefje.started_at is not None:
            self.logger.debug(
                "Boefje %s is still running according to bytes [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        # Did the grace period end, according to bytes?
        if (
            last_run_boefje is not None
            and last_run_boefje.ended_at is not None
            and datetime.now(timezone.utc) - last_run_boefje.ended_at
            < timedelta(seconds=self.ctx.config.pq_populate_grace_period)
        ):
            self.logger.debug(
                "Grace period for boefje: %s and input_ooi: %s has not yet passed, skipping ... [last_run_boefje=%s, boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                ooi.primary_key,
                last_run_boefje,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        # We can calculate the priority of the task, the task is ready
        # for rescheduling, e.g. it's a new task or the task has been
        # completed, and the grace period has ended.
        score = self.ranker.rank(SimpleNamespace(last_run_boefje=last_run_boefje, task=task))
        if score < 0:
            self.logger.warning(
                "Score too low for boefje: %s and input ooi: %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                ooi.primary_key,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            return None

        p_item = PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler_id,
            priority=score,
            data=task,
        )

        p_item.hash = mmh3.hash_bytes(f"{boefje.id}-{ooi.primary_key}-{self.organisation.id}").hex()

        return p_item

    def reschedule_oois(self) -> List[OOI]:
        """Get oois that need to be rescheduled. We only consider oois
        that have been processed by the scheduler after the set grace period.

        Returns:
            List[OOI]: List of oois that need to be rescheduled
        """
        datastore_oois = self.ctx.ooi_store.get_oois_last_checked_since(
            datetime.now(timezone.utc) - timedelta(seconds=self.ctx.config.pq_populate_grace_period)
        )

        # Remove oois from the database that are no longer present in the
        # datastore, we check octopoes if they are still present.
        oois = {ooi.primary_key: ooi for ooi in datastore_oois}
        removed_oois = [
            ooi.primary_key
            for ooi in datastore_oois
            if self.ctx.services.octopoes.get_object(self.organisation.id, ooi.primary_key) is None
        ]

        for removal in removed_oois:
            self.ctx.ooi_store.delete_ooi(removal)
            oois.pop(removal)
            self.logger.debug("Removed ooi: %s from datastore", removal)

        return list(oois.values())
