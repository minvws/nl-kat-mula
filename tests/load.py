from bytes import JobMeta


def get_job_meta() -> JobMeta:
    return JobMeta(
        id="test-job",
        input_ooi="Hostname|internet|example.com.",
        module="tests.modules.dummy_boefje",
        arguments={},
        organization="test",
    )
