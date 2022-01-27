from typing import Dict


def get_job_meta() -> Dict:
    return dict(
        id="test-job",
        input_ooi="Hostname|internet|example.com.",
        module="tests.modules.dummy_boefje",
        arguments={},
        organization="test",
    )
