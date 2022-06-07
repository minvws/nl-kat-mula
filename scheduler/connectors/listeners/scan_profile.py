import inspect
import json
from typing import List, Optional

import pika
from scheduler.models import OOI
from scheduler.models import ScanProfile as ScanProfileModel

from .listeners import RabbitMQ


class ScanProfile(RabbitMQ):
    name = "scan_profile"

    def get_latest_object(self, queue: str) -> Optional[OOI]:
        response = self.get(queue)
        if response is None:
            return None

        scan_profile = ScanProfileModel(**response)
        ooi = OOI(
            primary_key=scan_profile.reference,
            ooi_type=scan_profile.ooi_type,
            scan_profile=scan_profile,
        )

        return ooi

    def get_latest_objects(self, queue: str, n: int) -> Optional[List[OOI]]:
        oois: List[OOI] = []

        for i in range(n):
            ooi = self.get_latest_object(queue=queue)
            if ooi is None:
                break

            oois.append(ooi)

        return oois
