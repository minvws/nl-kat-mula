from typing import Dict, List

from scheduler.models import Boefje
from scheduler.utils import cache

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @cache.ttl_lru_cache(ttl=60*10)
    def _get_boefjes_by_ooi_type(self, ooi_type: str) -> List[Boefje]:
        boefjes = self.get_boefjes()

        cache_ooi_type = {}
        for boefje in boefjes:
            for ooi_type in boefje.consumes:
                if ooi_type not in cache_ooi_type:
                    cache_ooi_type[ooi_type] = [boefje]
                else:
                    cache_ooi_type[ooi_type].append(boefje)

        return cache_ooi_type.get(ooi_type, [])

    def get_boefjes_by_ooi_type(self, ooi_type: str) -> List[Boefje]:
        return self._get_boefjes_by_ooi_type(ooi_type)

    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())
