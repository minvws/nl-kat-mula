import pytest
from scheduler import settings
from scheduler.katalogus import Katalogus


@pytest.fixture
def katalogus():
    return Katalogus(settings.katalogus_api)


def test_get_boefjes(katalogus):
    boefjes = katalogus.get_boefjes()

    assert isinstance(boefjes, list)


def test_match_normalizer(katalogus: Katalogus):
    boefje_to_normalizer = katalogus.get_normalizer_modules_by_boefje_module()

    assert boefje_to_normalizer["dns-records"] == ["kat_dns_normalize"]
    assert boefje_to_normalizer["nmap-tcp-full"] == ["kat_nmap_normalize"]
    assert boefje_to_normalizer["ssl-version"] == ["kat_ssl_scan_normalize"]
