import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import config, connectors, context, dispatcher, models
from tests.factories import BoefjeFactory, OOIFactory, OrganisationFactory


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):

        # Octopoes
        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )
        self.mock_octopoes.get_objects.return_value = [
            OOIFactory(),
        ]

        # Katalogus
        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )
        self.mock_katalogus.get_organisations.return_value = [
            OrganisationFactory(),
        ]
        self.mock_katalogus.get_boefjes_by_ooi_type.return_value = [
            BoefjeFactory(),
        ]

        # Config
        cfg = config.settings.Settings()

        # AppContext
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()

        self.mock_ctx.services.octopoes = self.mock_octopoes
        self.mock_ctx.services.katalogus = self.mock_katalogus
        self.mock_ctx.return_value.config = cfg

        self.scheduler = scheduler.Scheduler()
        self.scheduler.ctx = self.mock_ctx

    def test_populate_boefjes_queue(self):
        """Should populate the boefjes queue with the correct boefje objects"""
        self.scheduler._populate_boefjes_queue()
        self.assertEqual((len(self.scheduler.queues.get("boefjes"))), 1)

    def test_populate_boefjes_queue_grace_period(self):
        pass

    def test_celery_dispatcher(self):
        # TODO: Add item to queue, instead of populate self.scheduler._populate_boefjes_queue()
        self.scheduler._populate_boefjes_queue()
        self.assertEqual((len(self.scheduler.queues.get("boefjes"))), 1)

        d = dispatcher.CeleryDispatcher(
            ctx=self.mock_ctx,
            pq=self.scheduler.queues.get("boefjes"),
            item_type=models.BoefjeTask,
            celery_queue="boefjes",
            task_name="tasks.handle_boefje",
        )

        d.app.send_task = mock.Mock()
        mock.patch("uuid.UUID.hex", return_value=uuid.uuid4().hex).start()

        # Get item and dispatch it
        p_item = d.pq.pop()
        d.dispatch(p_item)

        d.app.send_task.assert_called_once_with(
            name="tasks.handle_boefje",
            args=(p_item.item.dict(),),
            queue="boefjes",
            task_id=uuid.uuid4().hex,
        )
