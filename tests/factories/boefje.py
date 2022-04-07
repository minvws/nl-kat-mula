from typing import List

from factory import Factory, Faker, LazyFunction, PostGenerationMethodCall, Sequence, fuzzy
from scheduler.models import Boefje


class BoefjeFactory(Factory):
    class Meta:
        model = Boefje

    id: str = Sequence(lambda n: n)
    name: str = Faker("name")
    description: str = Faker("text")
    scan_level: int = fuzzy.FuzzyInteger(0, 10)
    consumes: List[str] = LazyFunction(lambda: [])
    produces: List[str] = LazyFunction(lambda: [])
