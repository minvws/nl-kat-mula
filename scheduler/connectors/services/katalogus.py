from typing import Dict, List

from scheduler.models import Boefje

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    # NOTE: for now we leverage an in-memory cache for getting
    # boefjes by ooi_type. When necessary we can use the
    # _get_boefjes_by_ooi_type which implements a timed lru cache.
    boefjes_by_ooi_type_cache: Dict[str, List[Boefje]] = {}

    def __init__(self, host: str, source: str, timeout: int = 5):
        super().__init__(host, source, timeout)

        self.boefjes_by_ooi_type_cache = {}
        self._flush_boefjes_by_ooi_type_cache()

    def _flush_boefjes_by_ooi_type_cache(self) -> None:
        boefjes = self.get_boefjes()

        for boefje in boefjes:
            for ooi_type in boefje.consumes:
                if ooi_type not in self.boefjes_by_ooi_type_cache:
                    self.boefjes_by_ooi_type_cache[ooi_type] = [boefje]
                else:
                    self.boefjes_by_ooi_type_cache[ooi_type].append(boefje)

    def get_boefjes_by_ooi_type(self, ooi_type: str) -> List[Boefje]:
        return self.boefjes_by_ooi_type_cache.get(ooi_type, [])

    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())
