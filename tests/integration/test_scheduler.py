import datetime
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import config, connectors, context, dispatchers, models
from tests.factories import BoefjeFactory, BoefjeMetaFactory, OOIFactory, OrganisationFactory, ScanProfileFactory


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):

        # Octopoes
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )

        self.mock_octopoes.get_objects.return_value = [ooi]

        # Scan profiles
        self.mock_scan_profiles = mock.create_autospec(
            spec=connectors.listeners.ScanProfile,
            spec_set=True,
        )

        self.mock_scan_profiles.get_latest_objects.return_value = [ooi]

        # Katalogus
        boefje = BoefjeFactory(scan_level=0)
        self.organisation = OrganisationFactory()

        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )

        self.mock_katalogus.get_organisations.return_value = [
            self.organisation,
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
            input_ooi=ooi.primary_key,
        )

        # Config
        cfg = config.settings.Settings()

        # AppContext
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()

        self.mock_ctx.services.octopoes = self.mock_octopoes
        self.mock_ctx.services.katalogus = self.mock_katalogus
        self.mock_ctx.services.bytes = self.mock_bytes
        self.mock_ctx.services.scan_profile = self.mock_scan_profiles
        self.mock_ctx.config = cfg

        self.app = scheduler.App(self.mock_ctx)

    def test_populate_boefjes_queue(self):
        """Should populate the boefjes queue with the correct boefje objects"""
        self.app.schedulers[self.organisation.id].populate_queue()
        self.assertEqual(len(self.app.schedulers[self.organisation.id].queue), 1)

    def test_populate_boefjes_queue_correct_priority(self):
        """Created objects should have the correct priority"""
        pass

    def test_populate_boefjes_queue_grace_period(self):
        pass

    def test_populate_boefjes_queue_qsize(self):
        pass

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
