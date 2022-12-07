import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List, Optional

import mmh3
import pika
import requests

from scheduler import context, queues, rankers
from scheduler.models import (OOI, Boefje, BoefjeTask, MutationOperationType,
                              Organisation, Plugin, PrioritizedItem,
                              TaskStatus)

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
        """Populate the PriorityQueue

        This method will populate the queue with tasks. It will first
        create tasks for oois that have a scan level change. Then it
        will create tasks for newly added/enabled boefjes. Finally it
        will create tasks for oois that have not been checked in a
        while.
        """
        self.push_tasks_for_scan_profile_mutations()

        self.push_tasks_for_new_boefjes()

        self.reschedule_tasks()

    def push_tasks_for_scan_profile_mutations(self):
        """Create tasks for oois that have a scan level change.

        We loop until we don't have any messages on the queue anymore.
        """
        while not self.queue.full():
            time.sleep(1)

            mutation = None
            try:
                mutation = self.ctx.services.scan_profile_mutation.get_scan_profile_mutation(
                    queue=f"{self.organisation.id}__scan_profile_mutations",
                )
            except (
                pika.exceptions.ConnectionClosed,
                pika.exceptions.ChannelClosed,
                pika.exceptions.ChannelClosedByBroker,
                pika.exceptions.AMQPConnectionError,
            ) as e:
                self.logger.warning(
                    "Could not connect to rabbitmq queue: %s [org_id=%s, scheduler_id=%s]",
                    f"{self.organisation.id}__scan_profile_mutations",
                    self.organisation.id,
                    self.scheduler_id,
                )
                if self.stop_event.is_set():
                    raise e

            # Stop the loop when we've processed everything from the
            # messaging queue, so we can continue to the next step.
            if mutation is None:
                self.logger.debug(
                    "No latest oois for organisation: %s [org_id=%s, scheduler_id=%s]",
                    self.organisation.name,
                    self.organisation.id,
                    self.scheduler_id,
                )
                return

            self.logger.debug(
                "Received scan level mutation: %s [org_id=%s, scheduler_id=%s]",
                mutation,
                self.organisation.id,
                self.scheduler_id,
            )

            # What available boefjes do we have for this ooi?
            boefjes = self.get_boefjes_for_ooi(ooi)
            if boefjes is None:
                self.logger.debug(
                    "No boefjes for ooi: %s [org_id=%s, scheduler_id=%s]",
                    ooi.id,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            for boefje in boefjes:

                # TODO: when input_ooip is None
                task = BoefjeTask(
                    boefje=Boefje.parse_obj(boefje),
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if not self.is_task_allowed_to_run(boefje, ooi):
                    self.logger.debug(
                        "Task is not allowed to run: %s [org_id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                if self.is_task_running(task):
                    self.logger.debug(
                        "Task is already running: %s [org_id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                score = self.ranker.rank(SimpleNamespace(last_run_boefje=last_run_boefje, task=task)

                # We need to create a PrioritizedItem for this task, to push
                # it to the priority queue.
                p_item = PrioritizedItem(
                    id=task.id,
                    scheduler_id=self.scheduler_id,
                    priority=score,
                    data=task,
                    hash=task.hash,
                )

                # We don't want the populator to add/update tasks to the
                # queue, when they are already on there. However, we do
                # want to allow the api to update the priority. So we
                # created the queue with allow_priority_updates=True
                # regardless. When the ranker is updated to correctly rank
                # tasks, we can allow the populator to also update the
                # priority. Then remove the following:
                if self.queue.is_item_on_queue(p_item):
                    self.logger.debug(
                        "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    return None

            # NOTE: maxsize 0 means unlimited
            while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
                self.logger.debug(
                    "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                    len(p_items),
                    self.queue.qsize(),
                    self.queue.maxsize,
                    self.organisation.id,
                    self.scheduler_id,
                )
                time.sleep(1)

            self.push_item_to_queue(p_item)
        else:
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

    def reschedule_tasks(self):
        # TODO: Get all scheduled jobs that need to be rescheduled. We only consider
        # jobs that have been processed by the scheduler after the set grace
        # period.
        #
        # scheduler_id (should enforce the type of task on the queue, so
        # we don't have to filter on it)
        #
        # status = not scheduled
        # enabled = true
        scheduled_jobs = self.ctx.job_store.get_scheduled_jobs()

        # Do we execute the task again?
        for job in scheduled_jobs:

            # Create a new task, and a new p_item
            task = BoefjeTask(**job.p_item.data)
            if task is None:
                self.logger.debug(
                    "Not able to parse task from job: %s [org_id=%s, scheduler_id=%s]",
                    job,
                    self.organisation.id,
                    self.scheduler_id,
                )


            # Allowed:
            # * If the boefje is enabled
            # * Is allowed to run on the ooi (scan level / profile)
            if not self.is_task_allowed_to_run(task.boefje, task.ooi):
                self.logger.debug(
                    "Boefje is not allowed to run on ooi: %s [org_id=%s, scheduler_id=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                )
                # TODO: remove job from scheduled jobs
                # TODO: what constitutes the removal of a scheduled job?
                # * boefje is disabled, delete
                # * ooi is deleted
                # * scan level is changed
                continue

            # Already running: (better term)
            # * If the boefje is already running on the ooi
            # * If the boefje has already run within the grace period
            if self.is_task_running(task):
                self.logger.debug(
                    "Boefje is already running on ooi: %s [org_id=%s, scheduler_id=%s]",
                    task,
                    self.organisation.id,
                    self.scheduler_id,
                )
                continue

            score = self.ranker.rank(SimpleNamespace(last_run_boefje=last_run_boefje, task=task))

            # TODO: create_p_item becasue we need to ranke
            # We need to create a PrioritizedItem for this task, to push
            # it to the priority queue.
            p_item = PrioritizedItem(
                id=task.id,
                scheduler_id=self.scheduler_id,
                priority=score,
                data=task,
                hash=task.hash,
            )

            if self.queue.is_item_on_queue(p_item):
                self.logger.debug(
                    "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                    boefje.id,
                    boefje.id,
                    ooi.primary_key,
                    self.organisation.id,
                    self.scheduler_id,
                )


            self.push_item_to_queue(p_item)

    def is_task_allowed_to_run(self, boefje: Plugin, ooi: OOI) -> bool:
        """Checks whether a boefje is allowed to run on an ooi.

        Args:
            boefje: The boefje to check.
            ooi: The ooi to check.

        Returns:
            True if the boefje is allowed to run on the ooi, False otherwise.
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
            return False

        if ooi.scan_profile is None:
            self.logger.debug(
                "No scan_profile found for ooi: %s [ooi_id=%s, scan_profile=%s, org_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                ooi.scan_profile,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        ooi_scan_level = ooi.scan_profile.level
        if ooi_scan_level is None:
            self.logger.warning(
                "No scan level found for ooi: %s [ooi_id=%s, org_id=%s, scheduler_id=%s]",
                ooi.primary_key,
                ooi,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

        boefje_scan_level = boefje.scan_level
        if boefje_scan_level is None:
            self.logger.warning(
                "No scan level found for boefje: %s [boefje_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                self.organisation.id,
                self.scheduler_id,
            )
            return False

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
            return False

        return True

    def is_task_running(task: BoefjeTask) -> bool:
        task_db = self.ctx.task_store.get_task_by_hash(task.hash)

        # Is task still running according to the datastore?
        if task_db is not None and (task_db.status != TaskStatus.COMPLETED or task_db.status == TaskStatus.FAILED):
            self.logger.debug(
                "According to the datastore, boefje: %s is still being processed [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            continue

        # Has grace period passed according to datastore?
        if (
            task_db is not None
            and (task_db.status == TaskStatus.COMPLETED or task_db.status == TaskStatus.FAILED)
            and datetime.utcnow() - task_db.modified_at < timedelta(seconds=self.ctx.config.pq_populate_grace_period)
        ):
            self.logger.debug(
                "According to the datastore, grace period has not passed for boefje: %s [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            continue

        # TODO: exception
        task_bytes = self.ctx.services.bytes.get_last_run_boefje(
            boefje_id=task.boefje.id,
            input_ooi=task.input_ooi,
            organization_id=task.organization,
        )

        # Task has been finished (failed, or succeeded) according to
        # the database, and we have no results of it in bytes, meaning
        # we have a problem
        if (
            task_db is not None
            and (task_db.status != TaskStatus.COMPLETED or task_db.status == TaskStatus.FAILED)
            and task_bytes is None
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
            continue

        # Is boefje still running according to bytes?
        if (
            task_bytes is not None
            and task_bytes.ended_at is None
            and last_run_boefje.started_at is not None
        ):
            self.logger.debug(
                "According to Bytes, boefje %s is still being processed [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                boefje.id,
                boefje.id,
                ooi.primary_key,
                self.organisation.id,
                self.scheduler_id,
            )
            continue

        # Did the grace period pass, according to bytes?
        if (
            task_bytes is not None
            and task_bytes.ended_at is not None
            and datetime.now(timezone.utc) - task_bytes.ended_at
            < timedelta(seconds=self.ctx.config.pq_populate_grace_period)
        ):
            self.logger.debug(
                "According to Bytes grace, period for boefje: %s and input_ooi: %s has not yet passed, skipping ... [task_bytes=%s, boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
            )
            continue

    def push_tasks_new_boefje(self) -> None:
        """Create tasks for the ooi's that are associated with a new added boefjes."""
        if self.queue.full():
            self.logger.info(
                "Boefjes queue is full, not populating with new tasks [qsize=%d, org_id=%s, scheduler_id=%s]",
                self.queue.qsize(),
                self.organisation.id,
                self.scheduler_id,
            )
            return

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

        self.logger.debug(
            "Received new boefjes: %s [org_id=%s, scheduler_id=%s]",
            new_boefjes,
            self.organisation.id,
            self.scheduler_id,
        )

        for boefje in new_boefjes:
            # TODO: get all ooi's for this organisation that this boefje could
            # be run on. This needs to come from octopoes
            oois = self.ctx.services.octopoes.get_oois_by_boefje(boefje_id=new_boefjes[0].id)

            for ooi in oois:
                task = BoefjeTask(
                    boefje=boefje,
                    input_ooi=ooi.primary_key,
                    organization=self.organisation.id,
                )

                if not self.is_task_allowed_to_run(boefje, ooi):
                    self.logger.debug(
                        "Task is not allowed to run: %s [org_id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                if self.is_task_running(task):
                    self.logger.debug(
                        "Task is already running: %s [org_id=%s, scheduler_id=%s]",
                        task,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    continue

                # TODO: create_p_item becasue we need to ranke
                # We need to create a PrioritizedItem for this task, to push
                # it to the priority queue.
                p_item = PrioritizedItem(
                    id=task.id,
                    scheduler_id=self.scheduler_id,
                    priority=score,
                    data=task,
                    hash=task.hash,
                )

                if self.queue.is_item_on_queue(p_item):
                    self.logger.debug(
                        "Boefje: %s is already on queue [boefje_id=%s, ooi_id=%s, org_id=%s, scheduler_id=%s]",
                        boefje.id,
                        boefje.id,
                        ooi.primary_key,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    return None

                # TODO: p_items -> p_item
                # NOTE: maxsize 0 means unlimited
                while len(p_items) > (self.queue.maxsize - self.queue.qsize()) and self.queue.maxsize != 0:
                    self.logger.debug(
                        "Waiting for queue to have enough space, not adding %d tasks to queue [qsize=%d, maxsize=%d, org_id=%s, scheduler_id=%s]",
                        len(p_items),
                        self.queue.qsize(),
                        self.queue.maxsize,
                        self.organisation.id,
                        self.scheduler_id,
                    )
                    time.sleep(1)

                self.push_item_to_queue(p_item)

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
