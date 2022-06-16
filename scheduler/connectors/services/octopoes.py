from datetime import timedelta
from typing import List

from scheduler.models import OOI

from .services import HTTPService


class Octopoes(HTTPService):
    name = "octopoes"

    def get_objects(self, organisation_id: str) -> List[OOI]:
        """Get all oois from octopoes"""
        url = f"{self.host}/{organisation_id}/objects"
        response = self.get(url)
        return [OOI(**ooi) for ooi in response.json()]

    def get_random_objects(self, organisation_id: str, n: int) -> List[OOI]:
        """Get `n` random oois from octopoes"""
        url = f"{self.host}/{organisation_id}/objects/random"
        response = self.get(url, params={"amount": str(n)})
        return [OOI(**ooi) for ooi in response.json()]

    def get_object(self, organisation_id: str, reference: str) -> OOI:
        """Get an ooi from octopoes"""
        url = f"{self.host}/{organisation_id}"
        response = self.get(url, params={"reference": reference})
        return OOI(**response.json())
