from functools import lru_cache
from typing import Dict, List

import requests


class Katalogus:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @lru_cache(maxsize=1)
    def get_boefjes(self):
        response = requests.get(f"{self.endpoint}/boefjes")
        self._verify_response(response)

        return response.json()

    @staticmethod
    def _verify_response(response: requests.Response) -> None:
        response.raise_for_status()

    def get_normalizer_modules_by_boefje_module(self) -> Dict[str, List[str]]:
        boefjes = self.get_boefjes()

        return {boefje["module"]: boefje["dispatches"]["normalizers"] for boefje in boefjes}
