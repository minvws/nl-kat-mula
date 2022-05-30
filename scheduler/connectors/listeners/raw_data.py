from typing import Optional

from scheduler.models import RawData

from .listeners import RabbitMQ


class RawData(RabbitMQ):
    name = "raw_data"

    def get_latest_raw_data(self, queue: str) -> Optional[RawData]:
        response = self.get(queue)
        if response is None:
            return None

        event= RawDataReceivedEvent(**response)

        return event.raw_data
