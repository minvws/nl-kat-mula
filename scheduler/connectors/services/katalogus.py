from typing import List

from scheduler.models import Boefje, Organisation, Plugin
from scheduler.utils import dict_utils

from .services import HTTPService


class Katalogus(HTTPService):
    name = "katalogus"

    def __init__(self, host: str, source: str, timeout: int = 5):
        super().__init__(host, source, timeout)

        self.organisations_plugin_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict()
        self.organisations_boefje_type_cache: dict_utils.ExpiringDict = dict_utils.ExpiringDict()

        self._flush_organisations_plugin_cache()
        self._flush_organisations_boefje_type_cache()

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

    def _flush_organisations_boefje_type_cache(self) -> None:
        orgs = self.get_organisations()

        for org in orgs:
            self.organisations_boefje_type_cache[org.id] = {}

            for plugin in self.get_plugins_by_organisation(org.id):
                if  plugin.type != "boefje":
                    continue

                # NOTE: when it is a boefje the consumes field is a string field
                self.organisations_boefje_type_cache[org.id].setdefault(plugin.consumes, []).append(plugin)


    def get_boefjes(self) -> List[Boefje]:
        url = f"{self.host}/boefjes"
        response = self.get(url)
        return [Boefje(**boefje) for boefje in response.json()]

    def get_boefje(self, boefje_id: str) -> Boefje:
        url = f"{self.host}/boefjes/{boefje_id}"
        response = self.get(url)
        return Boefje(**response.json())

    def get_organisation(self, organisation_id) -> Organisation:
        url = f"{self.host}/v1/organisations/{organisation_id}"
        response = self.get(url)
        return Organisation(**response.json())

    def get_organisations(self) -> List[Organisation]:
        url = f"{self.host}/v1/organisations"
        response = self.get(url)
        return [Organisation(**organisation) for organisation in response.json().values()]

    def get_plugins_by_organisation(self, organisation_id: str) -> List[Plugin]:
        url = f"{self.host}/v1/organisations/{organisation_id}/plugins"
        response = self.get(url)
        return [Plugin(**plugin) for plugin in response.json()]

    def get_plugin_by_id_and_org_id(self, plugin_id: str, org_id: str) -> Plugin:
        try:
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])
        except dict_utils.ExpiredError:
            self._flush_organisations_plugin_cache()
            return dict_utils.deep_get(self.organisations_plugin_cache, [organisation_id, plugin_id])

    def get_boefjes_by_type_and_org_id(self, boefje_type: str, organisation_id: str) -> List[Plugin]:
        try:
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])
        except dict_utils.ExpiredError:
            self._flush_organisations_boefje_type_cache()
            return dict_utils.deep_get(self.organisations_boefje_type_cache, [organisation_id, boefje_type])
