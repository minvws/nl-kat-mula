import pytest

from scheduler.katalogus import Katalogus
from scheduler import settings


@pytest.fixture
def katalogus():
    return Katalogus(settings.katalogus_api)


def test_get_boefjes(katalogus):
    boefjes = katalogus.get_boefjes()

    assert isinstance(boefjes, list)


def test_match_normalizer(katalogus: Katalogus):
    boefje_to_normalizer = katalogus.get_normalizer_modules_by_boefje_module()

    assert boefje_to_normalizer["kat_dns.resolve"] == ["kat_dns_normalize"]
    assert boefje_to_normalizer["kat_nmap.scan"] == ["kat_nmap_normalize"]
    assert boefje_to_normalizer["kat_ssl_scan.scan"] == ["kat_ssl_scan_normalize"]
