import uuid

import factory
from factory import (Factory, Faker, LazyFunction, PostGenerationMethodCall,
                     Sequence, fuzzy)
from scheduler.models import OOI


# NOTE: we're not extending the Factory class here, since the OOI model
# has an alternative field name for `id`. Using that will not work with
# pydantic and factory boy.
class OOIFactory(OOI):
    id = (lambda: uuid.uuid4().hex)()

    name: str = Faker("name")

    ooi_type: str = Faker(
        "random_element",
        elements=(
            "Hostname",
            "Network",
        ),
    )
