from typing import List

from scheduler.models import OOI

from .services import HTTPService


class Octopoes(HTTPService):
    name = "octopoes"
    health_endpoint = "/_dev/health"  # FIXME: _dev

    def get_objects(self, org: str) -> List[OOI]:
        # url = f"{self.host}/{org}/objects"
        url = f"{self.host}/_dev/objects"
        response = self.get(url)
        return [OOI(**ooi) for ooi in response.json()]

    def get_random_objects(self, org: str, n: int) -> List[OOI]:
        """Get `n` random oois from octopoes"""
        url = f"{self.host}/{org}/objects/random"
        response = self.get(url, params={"amount": str(n)})
        return [OOI(**ooi) for ooi in response.json()]

    def get_object(self, org: str, reference: str) -> OOI:
        url = f"{self.host}/{org}"
        response = self.get(url, params={"reference": reference})
        return OOI(**response.json())
