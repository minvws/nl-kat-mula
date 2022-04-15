from datetime import datetime
from typing import Any, Dict, List

from factory import (Factory, Faker, LazyFunction, PostGenerationMethodCall,
                     Sequence, fuzzy)
from scheduler.models import Boefje, BoefjeMeta


class BoefjeFactory(Factory):
    class Meta:
        model = Boefje

    id: str = Sequence(lambda n: n)
    name: str = Faker("name")
    description: str = Faker("text")
    scan_level: int = fuzzy.FuzzyInteger(0, 10)
    consumes: List[str] = LazyFunction(lambda: [])
    produces: List[str] = LazyFunction(lambda: [])


class BoefjeMetaFactory(Factory):
    class Meta:
        model = BoefjeMeta

    id: str = Sequence(lambda n: n)
    arguments: Dict[str, Any] = {}
    organization: str = Faker("company")
    started_at: datetime = Faker("date_time")
    ended_at: datetime = Faker("date_time")
