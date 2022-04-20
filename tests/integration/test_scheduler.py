import datetime
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import config, connectors, context, dispatcher, models
from tests.factories import (BoefjeFactory, BoefjeMetaFactory, OOIFactory,
                             OrganisationFactory)


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):

        # Octopoes
        ooi = OOIFactory()

        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )

        self.mock_octopoes.get_objects.return_value = [
            ooi
        ]

        # Katalogus
        boefje = BoefjeFactory()

        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )

        self.mock_katalogus.get_organisations.return_value = [
            OrganisationFactory(),
        ]
        self.mock_katalogus.get_boefjes_by_ooi_type.return_value = [
            boefje,
        ]

        # Bytes
        self.mock_bytes = mock.create_autospec(
            spec=connectors.services.Bytes,
            spec_set=True,
        )

        self.mock_bytes.get_last_run_boefje.return_value = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.id,
        )

        # Config
        cfg = config.settings.Settings()

        # AppContext
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()

        self.mock_ctx.services.octopoes = self.mock_octopoes
        self.mock_ctx.services.katalogus = self.mock_katalogus
        self.mock_ctx.services.bytes = self.mock_bytes
        self.mock_ctx.config = cfg

        self.scheduler = scheduler.Scheduler(self.mock_ctx)

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
