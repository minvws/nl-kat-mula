import unittest
from types import SimpleNamespace
from unittest import mock

import scheduler
from scheduler import context
from scheduler.connector import service


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):

        # Mocking connectors of external services
        self.mock_octopoes = mock.create_autospec(
            spec=service.Octopoes,
            spec_set=True,
        )
        self.mock_octopoes.get_objects.return_value = [
            {"ooi_type": "test"},
        ]

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.services.octopoes = self.mock_octopoes

        self.scheduler = scheduler.Scheduler()
        self.scheduler.ctx = self.mock_ctx

    def test_populate_boefjes_queue(self):
        self.scheduler._populate_boefjes_queue()
