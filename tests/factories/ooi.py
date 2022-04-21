import uuid

import factory
from factory import Factory, Faker, LazyFunction, PostGenerationMethodCall, Sequence, fuzzy
from scheduler.models import OOI, ScanProfile


class ScanProfileFactory(Factory):
    class Meta:
        model = ScanProfile

    reference: str = Faker("uuid4")
    level: int = fuzzy.FuzzyInteger(0, 4)
    scan_profile_type: str = Faker(
        "random_element",
        elements=["declared", "empty", "inherited"],
    )


# NOTE: we're not extending the Factory class here, since the OOI model
# has an alternative field name for `id`. Using that will not work with
# pydantic and factory boy.
class OOIFactory(OOI):
    id = (lambda: uuid.uuid4().hex)()

    name: str = Faker("name")

    ooi_type: str = Faker(
        "random_element",
        elements=["Hostname", "Network"],
    )

    scan_profile: ScanProfile
