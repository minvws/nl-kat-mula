import json
from typing import List

import pika
from scheduler.models import OOI

from .listeners import RabbitMQ


class ScanProfile(RabbitMQ):
    name = "scan_profile"

    def get_latest_objects(self, queue: str, n: int) -> List[OOI]:
        oois: List[OOI] = []

        for i in range(n):
            response = self.get(queue=queue)
            if response is None:
                break

            oois.append(OOI(**response))

        return oois
