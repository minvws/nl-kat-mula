from factory import (Factory, Faker, LazyFunction, PostGenerationMethodCall,
                     Sequence, fuzzy)
from scheduler.models import OOI


class OOIFactory(Factory):
    class Meta:
        model = OOI

    name: str = Faker("name")

    ooi_type: str = Faker(
        "random_element",
        elements=(
            "Hostname",
            "Network",
        ),
    )

    reference = Faker("name")
