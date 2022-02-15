import unittest
from unittest.mock import MagicMock, patch

import scheduler


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_ctx = patch("scheduler.context.AppContext").start()

        self.scheduler = scheduler.Scheduler()
        print(self.scheduler.ctx)

    def test_schedule(self):
        pass

    def test_populate_boefjes_queue(self):
        pass
