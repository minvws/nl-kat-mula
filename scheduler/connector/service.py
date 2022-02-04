import logging
from typing import Dict

import requests


class Service:
    logger: logging.Logger
    name: str
    host: str
    timeout: int

    def __init__(self, host: str, timeout: int = 5):
        self.host = host
        self.timeout = timeout
        self.check_host()

    def make_request(self, url: str) -> requests.Response:
        response = requests.get(url, timeout=self.timeout)
        self._verify_response(response)
        return response

    def check_host(self) -> bool:
        try:
            response = requests.get(self.host, timeout=self.timeout)
            self._verify_response(response)
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
    pass


class Octopoes(Service):
    pass


class Rocky(Service):
    pass
