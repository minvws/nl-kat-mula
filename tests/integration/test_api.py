import unittest
import uuid
from unittest import mock

import requests
from fastapi.testclient import TestClient
from scheduler import (config, connectors, dispatchers, models, queues,
                       rankers, schedulers, server)
from tests.factories import (BoefjeFactory, OOIFactory, OrganisationFactory,
                             ScanProfileFactory)


def create_p_item(organisation_id: str, priority: int) -> models.QueuePrioritizedItem:
    scan_profile = ScanProfileFactory(level=0)
    ooi = OOIFactory(scan_profile=scan_profile)
    item_id = uuid.uuid4().hex
    item = models.QueuePrioritizedItem(
        priority=priority,
        item=models.BoefjeTask(
            id=item_id,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=organisation_id,
        )
    )
    return item


class APITestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.BoefjePriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
        )

        dispatcher = dispatchers.BoefjeDispatcher(
            ctx=self.mock_ctx,
            pq=queue,
            item_type=models.BoefjeTask,
            celery_queue="boefjes",
            task_name="tasks.handle_boefje",
        )

        ranker = rankers.BoefjeRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = schedulers.BoefjeScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            dispatcher=dispatcher,
            ranker=ranker,
            organisation=self.organisation,
        )

        self.server = server.Server(self.mock_ctx, {self.scheduler.scheduler_id: self.scheduler})

        self.client = TestClient(self.server.api)

    def test_get_schedulers(self):
        response = self.client.get("/schedulers")
        self.assertEqual(response.status_code, 200)

    def test_get_scheduler(self):
        response = self.client.get(f"/schedulers/{self.scheduler.scheduler_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("id"), self.scheduler.scheduler_id)

    def test_patch_scheduler(self):
        self.assertEqual(True, self.scheduler.populate_queue_enabled)
        response = self.client.patch(f"/schedulers/{self.scheduler.scheduler_id}", json={"populate_queue_enabled": False})
        self.assertEqual(200, response.status_code)
        self.assertEqual(False, response.json().get("populate_queue_enabled"))

    def test_get_queues(self):
        response = self.client.get("/queues")
        self.assertEqual(response.status_code, 200)

    def test_get_queue(self):
        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("id"), self.scheduler.scheduler_id)

    def test_push_queue(self):
        self.assertEqual(0, self.scheduler.queue.qsize())

        item = create_p_item(self.organisation.id, 0)

        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=item.dict())
        self.assertEqual(response.status_code, 204)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_incorrect_item_type(self):
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json={"priority": 0, "item": "not a task"})
        self.assertEqual(response.status_code, 400)

    def test_push_queue_full(self):
        # Set maxsize of the queue to 1
        self.scheduler.queue.maxsize = 1

        # Add one task to the queue
        first_item = create_p_item(self.organisation.id, 0)
        self.scheduler.queue.push(first_item)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Try to add another task to the queue through the api
        second_item = create_p_item(self.organisation.id, 1)
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=second_item.dict())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_replace_not_allowed(self):
        """When pushing an item that is already in the queue the item
        shouldn't be pushed.
        """
        # Set queue to not allow duplicates
        self.scheduler.queue.allow_replace = False

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        self.scheduler.queue.push(initial_item)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())

        # The queue should still have one item
        self.assertEqual(response.status_code, 400)
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_replace_allowed(self):
        # Set queue to not allow duplicates
        self.scheduler.queue.allow_replace = True

        # Add one task to the queue
        initial_item = create_p_item(self.organisation.id, 0)
        self.scheduler.queue.push(initial_item)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Add the same item again through the api
        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=initial_item.dict())

        # The queue should have two items, entry_finder one
        self.assertEqual(response.status_code, 204)
        self.assertEqual(2, self.scheduler.queue.qsize())
        self.assertEqual(1, len(self.scheduler.queue.entry_finder))

        # Check if the item on the queue is the replaced item
        self.assertEqual(initial_item.item.id, self.scheduler.queue.peek(0).p_item.item.id)

    def test_push_updates_not_allowed(self):
        pass

    def test_push_updates_allowed(self):
        pass

    def test_push_priority_updates_not_allowed(self):
        pass

    def test_push_priority_updates_allowed(self):
        pass

    def test_update_priority_higher(self):
        pass

    def test_update_priority_lower(self):
        pass

    def test_pop_queue(self):
        # Add one task to the queue
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        item_id = uuid.uuid4().hex
        item = models.QueuePrioritizedItem(
            priority=0,
            item=models.BoefjeTask(
                id=item_id,
                boefje=BoefjeFactory(),
                input_ooi=ooi.primary_key,
                organization=self.organisation.id,
            )
        )
        self.scheduler.queue.push(item)
        self.assertEqual(1, self.scheduler.queue.qsize())

        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}/pop")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("item").get("id"), item_id)
        self.assertEqual(0, self.scheduler.queue.qsize())
