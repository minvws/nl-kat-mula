import logging
import socket
import time
import urllib.parse
from typing import Dict

import requests


class Service:
    logger: logging.Logger
    name: str
    source: Dict[str, str]
    host: str
    timeout: int

    def __init__(self, source: str, host: str, timeout: int = 5):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.source = {"User-Agent": f"{source}"}
        self.host = host
        self.timeout = timeout

        if self._retry(self._check_host) is False:
            raise RuntimeError(f"Host {self.host} is not reachable.")

        if self._retry(self._check_health) is False:
            raise RuntimeError(f"Service {self.name} is not running.")

    def make_request(self, url: str) -> requests.Response:
        response = requests.get(url, headers=self.source, timeout=self.timeout)
        self.logger.debug(f"Made request to {url}. [name={self.name} url={url}]")

        self._verify_response(response)

        return response

    # FIXME: use request urllib3 retry
    def _retry(self, func: callable) -> bool:
        """Retry a function until it returns True."""
        i = 0
        while i < 10:
            if func() is True:
                self.logger.debug(f"Connected to {self.host}. [name={self.name} host={self.host}]")
                return True
            else:
                self.logger.warning(
                    f"Not able to reach host, retrying in {self.timeout} seconds. [name={self.name} host={self.host}]"
                )

                i += 1
                time.sleep(self.timeout)

        return False

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
            self.make_request(f"{self.host}/health")
            return True
        except requests.exceptions.RequestException:
            return False

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()


class Katalogus(Service):
    name = "katalogus"

    def get_boefjes(self) -> Dict:
        url = f"{self.host}/boefjes"
        response = self.make_request(url)
        return response.json()


class Bytes(Service):
    name = "bytes"


class Octopoes(Service):
    name = "octopoes"


class Rocky(Service):
    name = "rocky"
