import uuid

import factory
from factory import Factory, Faker, LazyFunction, PostGenerationMethodCall, Sequence, fuzzy
from scheduler.models import OOI


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

    # organization: str = Faker("company")


# class OOIFactory(Factory):
#     # __id__ = (lambda: uuid.uuid4().hex)()
#     # __id__ = "test"
#     # __id__ = factory.Sequence()
#     __id__ = Sequence(lambda n: '{}-{}'.format(uuid.uuid4().hex, n))
#
#     name: str = Faker("name")
#
#     ooi_type: str = Faker(
#         "random_element",
#         elements=(
#             "Hostname",
#             "Network",
#         ),
#     )
#
#     organization: str = Faker("company")
#
#     reference = Faker("name")
#
#     class Meta:
#         model = OOI
