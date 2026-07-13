"""Offline unit tests for PubChem-backed drug synonym resolution (F24b).
No network calls: PubChem lookups are stubbed and the disk cache is
redirected to a tmp_path so tests never touch the real persistent cache."""

import asyncio

import pytest

from app.services import drug_synonym_service as dss
from app.services.drug_synonym_service import DrugSynonymService, _is_usable_synonym


def test_is_usable_synonym_filters_noise():
    assert _is_usable_synonym("Belinostat", "Belinostat") is False  # same as query
    assert _is_usable_synonym("50-18-0", "Belinostat") is False  # CAS number
    assert _is_usable_synonym("x" * 41, "Belinostat") is False  # too long
    assert _is_usable_synonym("PXD101", "Belinostat") is True
    assert _is_usable_synonym("Beleodaq", "Belinostat") is True


def test_get_synonyms_caches_and_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(dss, "_CACHE_PATH", tmp_path / "syn.json")
    svc = DrugSynonymService()

    calls = {"n": 0}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "InformationList": {
                    "Information": [
                        {"Synonym": ["Belinostat", "PXD101", "Beleodaq", "50-18-0", "x" * 50]}
                    ]
                }
            }

    async def fake_get(url):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(svc.client, "get", fake_get)

    result = asyncio.run(svc.get_synonyms("Belinostat"))
    assert result == ["PXD101", "Beleodaq"]

    # Second call for the same drug is served from cache — no extra HTTP call.
    result2 = asyncio.run(svc.get_synonyms("belinostat"))
    assert result2 == ["PXD101", "Beleodaq"]
    assert calls["n"] == 1


def test_get_synonyms_returns_empty_on_lookup_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(dss, "_CACHE_PATH", tmp_path / "syn.json")
    svc = DrugSynonymService()

    async def fake_get(url):
        raise dss.httpx.ConnectError("no network")

    monkeypatch.setattr(svc.client, "get", fake_get)

    result = asyncio.run(svc.get_synonyms("SomeInvestigationalDrug"))
    assert result == []
