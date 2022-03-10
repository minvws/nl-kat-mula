from typing import List

from scheduler.models import OOI

from .services import HTTPService


class Octopoes(HTTPService):
    name = "octopoes"
    health_endpoint = "/_dev/health"  # FIXME: _dev

    def get_objects(self) -> List[OOI]:
        url = f"{self.host}/_dev/objects"  # FIXME: _dev
        response = self.get(url)
        return [OOI(**ooi) for ooi in response.json()]

    def get_random_objects(self, n: int) -> List[OOI]:
        """Get `n` random oois from octopoes"""
        url = f"{self.host}/_dev/objects/random"  # FIXME: _dev
        response = self.get(url, params={"n": str(n)})
        return [OOI(**ooi) for ooi in response.json()]

    def get_object(self, reference: str) -> OOI:
        url = f"{self.host}/_dev"  # FIXME: _dev
        response = self.get(url, params={"reference": reference})
        return OOI(**response.json())
