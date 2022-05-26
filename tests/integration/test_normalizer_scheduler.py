import unittest
from unittest import mock

from scheduler import config, connectors, dispatchers, models, queues, rankers, schedulers
from tests.factories import OrganisationFactory


class NormalizerSchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.NormalizerPriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.NormalizerTask,
            allow_priority_updates=True,  # TODO: check if this is correct
        )

        dispatcher = dispatchers.NormalizerDispatcher(
            ctx=self.mock_ctx,
            pq=queue,
            item_type=models.NormalizerTask,
            celery_queue="normalizers",
            task_name="tasks.handle_ooi",  # TODO: check if this is correct
        )

        ranker = rankers.NormalizerRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = schedulers.NormalizerScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            dispatcher=dispatcher,
            ranker=ranker,
            organisation=self.organisation,
        )

    def test_populate_normalizer_queue(self):
        pass
