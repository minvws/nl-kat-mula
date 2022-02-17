import unittest
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import connector, context
from tests.factories import BoefjeFactory, OOIFactory


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):

        # Octopoes
        self.mock_octopoes = mock.create_autospec(
            spec=connector.Octopoes,
            spec_set=True,
        )
        self.mock_octopoes.get_objects.return_value = [
            OOIFactory(),
        ]

        # Katalogus
        self.mock_katalogus = mock.create_autospec(
            spec=connector.Katalogus,
            spec_set=True,
        )
        self.mock_katalogus.cache_ooi_type.get.return_value = [
            BoefjeFactory(),
        ]

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.services.octopoes = self.mock_octopoes
        self.mock_ctx.services.katalogus = self.mock_katalogus

        self.scheduler = scheduler.Scheduler()
        self.scheduler.ctx = self.mock_ctx

    def test_populate_boefjes_queue(self):
        """Should populate the boefjes queue with the correct boefje objects"""
        self.scheduler._populate_boefjes_queue()
        self.assertEqual((len(self.scheduler.boefjes_queue)), 1)

    def test_pop_boefjes_queue(self):
        pass

    def test_push_boefjes_queue(self):
        pass
