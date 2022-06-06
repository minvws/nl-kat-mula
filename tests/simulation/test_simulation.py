import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from scheduler import (config, connectors, dispatchers, models, queues,
                       rankers, schedulers)
from tests.factories import (BoefjeMetaFactory, OOIFactory,
                             OrganisationFactory, PluginFactory,
                             RawDataFactory, ScanProfileFactory)


class SimulationTestCase(unittest.TestCase):
    def setUp(self):
        self.cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = self.cfg

        self.organisation = OrganisationFactory()

    def create_normalizer_scheduler_for_organisation(self, organisation):
        normalizer_queue = queues.NormalizerPriorityQueue(
            pq_id=f"normalizer-{organisation.id}",
            maxsize=self.cfg.pq_maxsize,
            item_type=models.NormalizerTask,
            allow_priority_updates=True,
        )

        normalizer_dispatcher = dispatchers.NormalizerDispatcher(
            ctx=self.mock_ctx,
            pq=normalizer_queue,
            item_type=models.NormalizerTask,
            celery_queue="normalizers",
            task_name="tasks.handle_ooi",
        )

        normalizer_ranker = rankers.NormalizerRanker(
            ctx=self.mock_ctx,
        )

        return schedulers.NormalizerScheduler(
            ctx=self.mock_ctx,
            scheduler_id=organisation.id,
            queue=normalizer_queue,
            dispatcher=normalizer_dispatcher,
            ranker=normalizer_ranker,
            organisation=organisation,
        )

    def create_boefje_scheduler_for_organisation(self, organisation):
        boefje_queue = queues.BoefjePriorityQueue(
            pq_id=f"boefje-{organisation.id}",
            maxsize=self.cfg.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
        )

        boefje_dispatcher = dispatchers.BoefjeDispatcher(
            ctx=self.mock_ctx,
            pq=boefje_queue,
            item_type=models.BoefjeTask,
            celery_queue="boefje",
            task_name="tasks.handle_boefje",
        )

        boefje_ranker = rankers.BoefjeRanker(
            ctx=self.mock_ctx,
        )

        return schedulers.BoefjeScheduler(
            ctx=self.mock_ctx,
            scheduler_id=organisation.id,
            queue=boefje_queue,
            dispatcher=boefje_dispatcher,
            ranker=boefje_ranker,
            organisation=organisation,
        )

    @mock.patch("scheduler.context.AppContext.services.scan_profile.get_latest_object")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_simulation(self, mock_get_random_objects, mock_get_latest_object):

        mock_get_latest_object.return_value = OOIFactory(scan_profile=ScanProfileFactory(level=0))

        mock_get_random_objects.return_value = [OOIFactory(scan_profile=ScanProfileFactory(level=0))]

        # n_scheduler = self.create_normalizer_scheduler_for_organisation(self.organisation)
        b_scheduler = self.create_boefje_scheduler_for_organisation(self.organisation)

        # n_scheduler.populate_queue()
        b_scheduler.populate_queue()
