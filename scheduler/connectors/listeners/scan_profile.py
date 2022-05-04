import inspect
import json
from typing import List

import pika
from scheduler.models import OOI
from scheduler.models import ScanProfile as ScanProfileModel

from .listeners import RabbitMQ


class ScanProfile(RabbitMQ):
    name = "scan_profile"

    def get_latest_objects(self, queue: str, n: int) -> List[OOI]:
        oois: List[OOI] = []

        for i in range(n):
            response = self.get(queue=queue)

            # When no messages are available, stop
            if response is None:
                break

            scan_profile = ScanProfileModel(**response)

            oois.append(
                OOI(
                    primary_key=scan_profile.reference,
                    ooi_type=scan_profile.ooi_type,
                    scan_profile=scan_profile,
                )
            )

        return oois
