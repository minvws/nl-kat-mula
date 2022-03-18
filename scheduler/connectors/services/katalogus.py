from typing import Dict, List

from scheduler.models import Boefje

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    cache_ooi_type: Dict[str, Boefje] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._warm_cache_ooi_type()

    # FIXME: can we optimize the double for loop?
    def _warm_cache_ooi_type(self) -> None:
        boefjes = self.get_boefjes()
        for boefje in boefjes:
            for ooi_type in boefje.consumes:
                if ooi_type not in self.cache_ooi_type:
                    self.cache_ooi_type[ooi_type] = [boefje]
                else:
                    self.cache_ooi_type[ooi_type].append(boefje)

    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())
