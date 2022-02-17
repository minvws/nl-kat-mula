from typing import List

from .service import HTTPService


class XTDB(HTTPService):
    name = "xtdb"
    health_endpoint = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers["Content-Type"] = "application/edn"

    # FIXME: what about org access?
    def get_random_objects(self, n: int) -> List:
        """Get `n` random oois from xtdb."""
        now = datetime.datetime.utcnow().isoformat(timespec="minutes")
        url = f"{self.host}/_crux/query?valid-time={now}"
        payload = f"{{:query {{:find [(rand {n} id)], :where [[?e :crux.db/id id] [?e :ooi_type]]}}}}"

        response = self.post(url=url, payload=payload)

        return response.json()
