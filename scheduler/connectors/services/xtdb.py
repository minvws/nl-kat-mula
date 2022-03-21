import datetime
from typing import List

from scheduler.models import OOI

from .services import HTTPService


class XTDB(HTTPService):
    name = "xtdb"
    health_endpoint = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.headers["Content-Type"] = "application/edn"

    def get_random_objects(self, n: int) -> List[OOI]:
        """Get `n` random oois from xtdb."""
        now = datetime.datetime.utcnow().isoformat(timespec="minutes")
        url = f"{self.host}/_crux/query?valid-time={now}"
        payload = f"{{:query {{:find [(rand {n} id)], :where [[?e :crux.db/id id] [?e :ooi_type]]}}}}"

        response = self.post(url=url, payload=payload)
        self.logger.info(response.json())

        return [OOI(**ooi) for ooi in response.json()]
