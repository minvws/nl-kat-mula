import unittest
from unittest import mock

from scheduler import (config, connectors, dispatchers, models, queues,
                       rankers, schedulers)
from tests.factories import (BoefjeMetaFactory, OOIFactory,
                             OrganisationFactory, PluginFactory,
                             RawDataFactory, ScanProfileFactory)


class NormalizerSchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.NormalizerPriorityQueue(
            pq_id=f"normalizer-{self.organisation.id}",
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

    @mock.patch("scheduler.context.AppContext.services.bytes.get_raw")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_create_tasks_for_raw(self, mock_get_normalizers, mock_get_raw):
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data = RawDataFactory(
            boefje_meta=boefje_meta,
        )

        mock_get_raw.return_value = raw_data

        tasks = self.scheduler.create_tasks_for_raw_data(raw_data)
        print(len(tasks))
        self.assertGreaterEqual(len(tasks), 1)
