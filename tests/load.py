from bytes import JobMeta


def get_job_meta() -> JobMeta:
    return JobMeta(
        id="test-job",
        module="tests.modules.dummy_boefje",
        arguments={},
        organization="test",
    )
