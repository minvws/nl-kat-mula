import unittest
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import config, connectors, context, dispatcher
from tests.factories import BoefjeFactory, OOIFactory


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
        self.mock_katalogus.cache_ooi_type.get.return_value = [
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

    def test_pop_boefjes_queue(self):
        pass

    def test_push_boefjes_queue(self):
        pass

    def test_dispatcher(self):
        self.scheduler._populate_boefjes_queue()

        d = dispatcher.BoefjeDispatcher(
            ctx=self.mock_ctx,
            pq=self.scheduler.queues.get("boefjes"),
            queue="boefjes",
            task_name="tasks.handle_boefje",
        )

        d.app.send_task = mock.Mock()

        # Get item from queue, and dispatch it
        item = self.scheduler.queues.get("boefjes").pop()
        d.dispatch(item)

        d.app.send_task.assert_called_once_with(
            name="tasks.handle_boefje",
            args=(item.item.dict(),),
            queue="boefjes",
            task_id=item.item.id,
        )
