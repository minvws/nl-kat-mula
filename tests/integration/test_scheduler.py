import datetime
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import (config, connectors, context, dispatchers, models,
                       queues, rankers, schedulers)
from tests.factories import (BoefjeFactory, BoefjeMetaFactory, OOIFactory,
                             OrganisationFactory, ScanProfileFactory)


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Mock connectors: octopoes
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )

        self.mock_octopoes.get_random_objects.return_value = [ooi, None]
        self.mock_ctx.services.octopoes = self.mock_octopoes

        # Mock connectors: Scan profiles
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        self.mock_scan_profiles = mock.create_autospec(
            spec=connectors.listeners.ScanProfile,
            spec_set=True,
        )

        self.mock_scan_profiles.get_latest_object.side_effect = [ooi, None]

        self.mock_ctx.services.scan_profile = self.mock_scan_profiles

        # Mock connectors: Katalogus
        boefje = BoefjeFactory(scan_level=0)
        organisation = OrganisationFactory()

        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )

        self.mock_katalogus.get_organisations.return_value = [
            organisation,
        ]
        self.mock_katalogus.get_boefjes_by_ooi_type.return_value = [
            boefje,
        ]

        self.mock_ctx.services.katalogus = self.mock_katalogus

        # Mock connectors: Bytes
        self.mock_bytes = mock.create_autospec(
            spec=connectors.services.Bytes,
            spec_set=True,
        )

        self.mock_bytes.get_last_run_boefje.return_value = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        self.mock_ctx.services.bytes = self.mock_bytes

        # Scheduler
        queue = queues.BoefjePriorityQueue(
            pq_id=organisation.id,
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
            scheduler_id=organisation.id,
            queue=queue,
            dispatcher=dispatcher,
            ranker=ranker,
            organisation=organisation,
        )

        mock_create_tasks_for_oois = mock.patch.object(self.scheduler, "create_tasks_for_oois").start()
        mock_create_tasks_for_oois.side_effect = [
            [queues.PrioritizedItem(
                priority=0,
                item=models.BoefjeTask(
                    id=uuid.uuid4().hex,
                    boefje=BoefjeFactory(),
                    input_ooi=ooi.primary_key,
                    organization=organisation.id,
                ),
            )],
            [],
            [],
            [],
            [],
        ]

        # App
        # self.app = scheduler.App(self.mock_ctx)

    def test_populate_boefjes_queue(self):
        """Should populate the boefjes queue with the correct boefje objects"""
        self.scheduler.populate_queue()
        self.assertEqual(len(self.scheduler.queue), 1)

    @unittest.skip
    def test_populate_boefjes_queue_correct_priority(self):
        """Created objects should have the correct priority"""
        pass

    @unittest.skip
    def test_populate_boefjes_queue_grace_period(self):
        pass

    @unittest.skip
    def test_populate_boefjes_queue_qsize(self):
        pass

    @unittest.skip
    def test_celery_dispatcher(self):
        self.app.schedulers[self.organisation.id].populate_queue()
        self.assertEqual(len(self.app.schedulers[self.organisation.id].queue), 1)

        d = self.app.schedulers[self.organisation.id].dispatcher
        d.app.send_task = mock.Mock()

        # Get item and dispatch it
        p_item = d.pq.pop()
        d.dispatch(p_item)

        item_dict = p_item.item.dict()
        d.app.send_task.assert_called_once_with(
            name="tasks.handle_boefje",
            args=(item_dict,),
            queue="boefjes",
            task_id=item_dict.get("id"),
        )
