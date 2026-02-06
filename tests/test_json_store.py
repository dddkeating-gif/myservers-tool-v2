"""Tests for myservers.storage.json_store.JsonStore (v2)."""
import tempfile
from pathlib import Path

import pytest

from myservers.storage.json_store import JsonStore


def test_json_store_crud(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonStore(path)
    assert store.get("sect", "k") is None
    store.set("sect", "k", {"a": 1})
    assert store.get("sect", "k") == {"a": 1}
    store.set("sect", "k2", {"b": 2})
    assert store.get("sect", "k2") == {"b": 2}
    store.delete("sect", "k")
    assert store.get("sect", "k") is None
    assert store.get("sect", "k2") == {"b": 2}


def test_json_store_all_sections(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonStore(path)
    store.set("s1", "a", {"x": 1})
    store.set("s2", "b", {"y": 2})
    all_data = store.get("", "", all_sections=True)
    assert isinstance(all_data, dict)
    assert "s1" in all_data and "s2" in all_data
    assert all_data["s1"]["a"] == {"x": 1}
    assert all_data["s2"]["b"] == {"y": 2}


def test_json_store_persists(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    store = JsonStore(path)
    store.set("sect", "key", {"v": 1})
    store2 = JsonStore(path)
    assert store2.get("sect", "key") == {"v": 1}
