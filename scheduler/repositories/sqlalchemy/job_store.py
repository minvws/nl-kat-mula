from typing import List, Optional, Tuple, Union

from scheduler import models

from ..stores import JobStorer
from .datastore import SQLAlchemy


class JobStore(JobStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    # TODO: filters
    def get_scheduled_jobs(self) -> Tuple[List[models.ScheduledJob], int]:
        """Get all scheduled jobs.

        Returns:
            A list of ScheduledJob instances.
        """
        with self.datastore.session() as session:
            query = session.query(models.ScheduledJob)
            return query.all(), query.count()

    def get_scheduled_job(self, job_id: str) -> Optional[models.ScheduledJob]:
        """Get a scheduled job.

        Args:
            job_id: The ID of the job to get.

        Returns:
            The ScheduledJob instance if found, None otherwise.
        """
        with self.datastore.session() as session:
            job_orm = session.query(models.ScheduledJobORM).get(job_id)

            if job_orm is None:
                return None

            return models.ScheduledJob.from_orm(job_orm)

    def create_scheduled_job(self, job: models.ScheduledJob) -> None:
        """Create a scheduled job.

        Args:
            scheduled_job: The scheduled job to create.
        """
        with self.datastore.session() as session:
            job_orm = models.ScheduledJobORM(**job.dict())
            session.add(scheduled_job)

            created_job = models.ScheduledJob.from_orm(job_orm)

            return created_job

    # TODO; test this out
    def update_scheduled_job(self, job: models.ScheduledJob) -> None:
        """Update a scheduled job.

        Args:
            scheduled_job: The scheduled job to update.
        """
        with self.datastore.session() as session:
            job_orm = session.query(models.ScheduledJobORM).get(job.id)

            if job_orm is None:
                return None

            job_orm.update_from_model(job)

            return models.ScheduledJob.from_orm(job_orm)
