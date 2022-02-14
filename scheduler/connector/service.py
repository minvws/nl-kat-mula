import datetime
import logging
import socket
import time
import urllib.parse
from typing import Any, Dict, List

import requests
import scheduler


class HTTPService:
    """HTTPService exposes methods to make http requests to services that
    typically expose rest api endpoints
    """

    logger: logging.Logger
    name: str
    source: str
    host: str
    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    health_endpoint: str = "/health"
    timeout: int

    def __init__(self, host: str, source: str, timeout: int = 5):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.host = host
        self.source = source
        self.timeout = timeout

        if self.source:
            self.headers["User-Agent"] = self.source

        self._do_checks()

    def get(self, url: str, params: Dict = None) -> requests.Response:
        response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
        self.logger.debug(f"Made GET request to {url}. [name={self.name} url={url}]")

        self._verify_response(response)

        return response

    def post(self, url: str, payload: str, params: Dict = None) -> requests.Response:
        response = requests.post(url, headers=self.headers, data=payload, timeout=self.timeout)
        self.logger.debug(f"Made POST request to {url}. [name={self.name} url={url} data={payload}]")

        self._verify_response(response)

        return response

    def _do_checks(self) -> None:
        if self.host is not None and self._retry(self._check_host) is False:
            raise RuntimeError(f"Host {self.host} is not reachable.")

        if self.health_endpoint is not None and self._retry(self._check_health) is False:
            raise RuntimeError(f"Service {self.name} is not running.")

    def _check_host(self) -> bool:
        """Check if the host is reachable."""
        try:
            uri = urllib.parse.urlparse(self.host)
            if uri.netloc.find("@") != -1:
                host, port = uri.netloc.split("@")[1].split(":")
            else:
                host, port = uri.netloc.split(":")

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(port)))
            return True
        except socket.error:
            return False

    def _check_health(self) -> bool:
        """Check if host is reachable and if the service is running."""
        try:
            self.get(f"{self.host}{self.health_endpoint}")
            return True
        except requests.exceptions.RequestException:
            return False

    def _retry(self, func: callable) -> bool:
        """Retry a function until it returns True."""
        i = 0
        while i < 10:
            if func() is True:
                self.logger.info(f"Connected to {self.host}. [name={self.name} host={self.host} func={func.__name__}]")
                return True
            else:
                self.logger.warning(
                    f"Not able to reach host, retrying in {self.timeout} seconds. [name={self.name} host={self.host} func={func.__name__}]"
                )

                i += 1
                time.sleep(self.timeout)

        return False

    def _verify_response(self, response: requests.Response) -> None:
        # FIXME: handle the exception, we don't want to stop threads because
        # of a bad response
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTPError: {e} [name={self.name} url={response.url} response={response.content}]")
            raise (e)


class Katalogus(HTTPService):
    name = "katalogus"

    def get_boefjes(self) -> Dict:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return response.json()

    def get_boefje(self, boefje_id: str) -> Dict:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return response.json()


class Bytes(HTTPService):
    name = "bytes"


class Octopoes(HTTPService):
    name = "octopoes"
    health_endpoint = "/_dev/health"  # FIXME: _dev

    def get_objects(self) -> List:
        url = f"{self.host}/_dev/objects"  # FIXME: _dev
        response = self.get(url)
        return response.json()

    def get_random_objects(self, n: int):
        url = f"{self.host}/_dev/objects/random"  # FIXME: _dev
        response = self.get(url, params={"n": str(n)})
        return response.json()

    def get_object(self, reference: str) -> Dict:
        url = f"{self.host}/_dev"  # FIXME: _dev
        response = self.get(url, params={"reference": reference})
        return response.json()


class Rocky(HTTPService):
    name = "rocky"


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

        # FIXME: do we want to create a querybuilder?
        payload = f"{{:query {{:find [(rand {n} id)], :where [[?e :crux.db/id id] [?e :ooi_type]]}}}}"

        response = self.post(url=url, payload=payload)

        return response.json()
