import unittest
import uuid
from unittest import mock

import requests
from fastapi.testclient import TestClient
from scheduler import (config, connectors, dispatchers, models, queues,
                       rankers, schedulers, server)
from tests.factories import (BoefjeFactory, OOIFactory, OrganisationFactory,
                             ScanProfileFactory)


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

    def test_patch_incorrect_item_type(self):
        pass

    def test_get_queues(self):
        response = self.client.get("/queues")
        self.assertEqual(response.status_code, 200)

    def test_get_queue(self):
        response = self.client.get(f"/queues/{self.scheduler.scheduler_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("id"), self.scheduler.scheduler_id)

    def test_push_queue(self):
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

        # TODO: Check if there are items on the queue

        response = self.client.post(f"/queues/{self.scheduler.scheduler_id}/push", json=item.dict())
        self.assertEqual(response.status_code, 204)

        # TODO: Check if there are items on the queue

    def test_push_incorrect_item_type(self):
        pass

    def test_push_queue_full(self):
        pass

    def test_pop_queue(self):
        pass
