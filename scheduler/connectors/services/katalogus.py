from typing import List

from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    def __init__(self, host: str, source: str, timeout: int = 5):
        super().__init__(host, source, timeout)

        self.boefjes_by_ooi_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict()
        self.organisations_plugin_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict()
        self.organisations_normalizer_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict()

        self._flush_boefjes_by_ooi_type_cache()
        self._flush_organisations_plugin_cache()
        self._flush_organisations_normalizer_type_cache()

    def _flush_boefjes_by_ooi_type_cache(self) -> None:
        boefjes = self.get_boefjes()

        for boefje in boefjes:
            if boefje.consumes is None:
                continue

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

    def _flush_organisations_normalizer_type_cache(self) -> None:
        orgs = self.get_organisations()

        for org in orgs:
            for plugin in self.get_plugins_by_organisation(org.id):
                if plugin.type != "normalizer":
                    continue

                for consume in plugin.consumes:
                    if consume not in self.organisations_normalizer_type_cache[org.id]:
                        self.organisations_normalizer_type_cache[org.id][consume] = plugin
                    else:
                        self.organisations_normalizer_type_cache[org.id][consume].append(plugin)

    # TODO: perhaps rename to get_boefjes_by_consumes
    def get_boefjes_by_ooi_type(self, ooi_type: str) -> List[Boefje]:
        try:
            return self.boefjes_by_ooi_type_cache.get(ooi_type, [])
        except dict_utils.ExpiredError:
            self._flush_boefjes_by_ooi_type_cache()
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

    def get_plugin_by_id_and_org_id(self, plugin_id: str, organisation_id: str) -> Plugin:
        try:
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])
        except dict_utils.ExpiredError:
            self._flush_organisations_plugin_cache()
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])

    # TODO: should return normalizer
    def get_normalizers_by_org_id_and_type(self, organisation_id: str, normalizer_type: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])
        except dict_utils.ExpiredError:
            self._flush_organisations_normalizer_cache()
            return dict_utils.deep_get(self.organisations_normalizer_type_cache, [organisation_id, normalizer_type])

