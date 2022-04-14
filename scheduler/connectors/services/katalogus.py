from typing import Dict, List

from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    # NOTE: for now we leverage an in-memory cache for getting
    # boefjes by ooi_type. When necessary we can use the
    # _get_boefjes_by_ooi_type which implements a timed lru cache.
    boefjes_by_ooi_type_cache: Dict[str, List[Boefje]] = {}
    organisations_plugin_cache: Dict[str, Dict[str, Plugin]] = {}

    def __init__(self, host: str, source: str, timeout: int = 5):
        super().__init__(host, source, timeout)

        self.boefjes_by_ooi_type_cache = {}
        self._flush_boefjes_by_ooi_type_cache()

        self.organisations_plugin_cache = {}
        self._flush_organisations_plugin_cache()

    def _flush_boefjes_by_ooi_type_cache(self) -> None:
        boefjes = self.get_boefjes()

        for boefje in boefjes:
            for ooi_type in boefje.consumes:
                if ooi_type not in self.boefjes_by_ooi_type_cache:
                    self.boefjes_by_ooi_type_cache[ooi_type] = [boefje]
                else:
                    self.boefjes_by_ooi_type_cache[ooi_type].append(boefje)

    def _flush_organisations_plugin_cache(self) -> None:
        orgs = self.get_organisations()

        for org in orgs:
            self.organisations_plugin_cache[org.id] = {
                plugin.id: plugin for plugin in self.get_plugins_by_organisation(org.id)
            }

    def get_boefjes_by_ooi_type(self, ooi_type: str) -> List[Boefje]:
        return self.boefjes_by_ooi_type_cache.get(ooi_type, [])

    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())

    def get_organisations(self) -> List[Organisation]:
        url = f"{self.host}/v1/organisations"
        response = self.get(url)
        return [Organisation(**organisation) for organisation in response.json().values()]

    def get_plugins_by_organisation(self, organisation_id: str) -> List[Plugin]:
        url = f"{self.host}/v1/organisations/{organisation_id}/plugins"
        response = self.get(url)
        return [Plugin(**plugin) for plugin in response.json().values()]

    def get_plugin_by_org_and_boefje_id(self, organisation_id: str, boefje_id: str) -> Plugin:
        plugin = dict_utils.deep_get(
            self.organisations_plugin_cache,
            [organisation_id, boefje_id]
        )
        return Plugin(**plugin)
