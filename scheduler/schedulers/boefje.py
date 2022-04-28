from typing import List

import requests

from scheduler import queues
from scheduler.models import OOI

from .scheduler import Scheduler


class BoefjeScheduler(Scheduler):
    def populate_queue(self):
        if self.queue.full():
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d]",
                self.queue.pq.qsize(),
            )
            return

        try:
            latest_oois = self.ctx.services.scan_profile.get(queue=f"{self.scheduler_id}__scan_profile_increments")
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning("Could not get objects for organisation %s [org_id=%s]", org.name, org.id)
            return

        p_items = self.get_p_items_for_oois(latest_oois)
        self.add_p_items_to_queue(boefjes_queue, p_items)

        if boefjes_queue.full():
            self.logger.warning(
                "Boefjes queue is full, not populating with new tasks [qsize=%d]",
                boefjes_queue.pq.qsize(),
            )
            return

        try:
            random_oois = self.ctx.services.octopoes.get_random_objects(organisation_id=org.id, n=10)
        except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
            self.logger.warning("Could not get objects for organisation %s [org_id=%s]", org.name, org.id)
            return

        p_items = self.get_p_items_for_oois(random_oois)
        self.add_p_items_to_queue(boefjes_queue, p_items)

    def get_p_items_for_oois(self, oois: List[OOI]) -> List[queues.PrioritizedItem]:
        """Get a list of prioritized items for a list of OOIs.

        Args:
            oois: A list of OOIs.

        Returns:
            A list of BoefjeTasks.
        """
        p_items: List[queue.PrioritizedItem] = []
        for ooi in oois:
            try:
                boefjes = self.ctx.services.katalogus.get_boefjes_by_ooi_type(
                    ooi.ooi_type,
                )
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning(
                    "Could not get boefjes for ooi_type %s [ooi_type=%s]", ooi.ooi_type, ooi.ooi_type
                )
                continue

            if boefjes is None:
                self.logger.debug(
                    "No boefjes found for type %s [ooi=%s]",
                    ooi.ooi_type,
                    ooi,
                )
                continue

            self.logger.debug(
                "Found %s boefjes for ooi %s [ooi=%s, boefjes=%s}",
                len(boefjes),
                ooi,
                ooi,
                [boefje.id for boefje in boefjes],
            )

            for boefje in boefjes:
                try:
                    plugin = self.ctx.services.katalogus.get_plugin_by_org_and_boefje_id(
                        organisation_id=org.id,
                        boefje_id=boefje.id,
                    )
                except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                    self.logger.warning(
                        "Could not get plugin for org %s and boefje %s [org_id=%s, boefje_id=%s]",
                        org.name,
                        boefje.name,
                        org.id,
                        boefje.name,
                    )
                    continue

                if plugin is None:
                    self.logger.debug(
                        "No plugin found for boefje %s [org=%s, boefje=%s]",
                        boefje.id,
                        org.id,
                        boefje.id,
                    )
                    continue

                if plugin.enabled is False:
                    self.logger.debug("Boefje %s is disabled", boefje.id)
                    continue

                task = BoefjeTask(
                    id=uuid.uuid4().hex,
                    boefje=boefje,
                    input_ooi=ooi.id,
                    organization=org.id,
                )

                ooi_scan_level = ooi.scan_profile.level
                if ooi_scan_level is None:
                    self.logger.warning(
                        "No scan level found for ooi %s [ooi=%s]",
                        ooi.id,
                        ooi,
                    )
                    continue

                boefje_scan_level = boefje.scan_level
                if boefje_scan_level is None:
                    self.logger.warning(
                        "No scan level found for boefje %s [boefje=%s]",
                        boefje.id,
                        boefje,
                    )
                    continue

                # Boefje intensity score ooi clearance level, range
                # from 0 to 4. 4 being the highest intensity, and 0 being
                # the lowest. OOI clearance level defines what boefje
                # intesity is allowed to run on.
                if boefje_scan_level > ooi_scan_level:
                    self.logger.debug(
                        "Boefje %s scan level %s is too intense for ooi %s scan level %s [boefje_id=%s, ooi_id=%s]",
                        boefje.id,
                        boefje_scan_level,
                        ooi.id,
                        ooi_scan_level,
                        boefje.id,
                        ooi.id,
                    )
                    continue

                # We don't want the populator to add/update tasks to the
                # queue, when they are already on there. However, we do
                # want to allow the api to update the priority. So we
                # created the queue with allow_priority_updates=True
                # regardless. When the ranker is updated to correctly rank
                # tasks, we can allow the populator to also update the
                # priority. Then remove the following:
                if boefjes_queue.is_item_on_queue(task):
                    self.logger.debug(
                        boefje.id,
                        ooi.id,
                        org.id,
                    )
                    continue

                # Boefjes should not run before the grace period ends
                try:
                    last_run_boefje = self.ctx.services.bytes.get_last_run_boefje(
                        boefje_id=boefje.id,
                        input_ooi=ooi.id,
                        organization_id=org.id,
                    )
                except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                    self.logger.warning(
                        "Could not get last run boefje for boefje: '%s' with ooi: '%s' [boefje_id=%s, ooi_id=%s, org_id=%s]",
                        boefje.name,
                        ooi.id,
                        boefje.id,
                        ooi.id,
                        org.id,
                    )
                    continue

                if (
                    last_run_boefje is not None
                    and datetime.datetime.now().astimezone() - last_run_boefje.ended_at
                    < datetime.timedelta(seconds=self.ctx.config.pq_populate_grace_period)
                ):
                    self.logger.debug(
                        "Boefje %s already run for input ooi %s [last_run_boefje=%s]",
                        boefje.id,
                        ooi.id,
                        last_run_boefje,
                    )
                    continue

                score = boefjes_ranker.rank(task)
                p_items.append(queue.PrioritizedItem(priority=score, item=task))
