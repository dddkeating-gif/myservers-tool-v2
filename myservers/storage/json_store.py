"""Minimal JSON file store: section/key CRUD. No secrets—use keyring for credentials.
Legacy-compatible API."""
import json
from pathlib import Path


class JsonStore:
    """CRUD over a single JSON file (dict of sections -> key -> value)."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, section: str, key: str | None = None, *, all_sections: bool = False) -> dict | list | None:
        data = self._load()
        if all_sections:
            return data
        bucket = data.get(section, {})
        if key is None:
            return dict(bucket) if isinstance(bucket, dict) else bucket
        return bucket.get(key) if isinstance(bucket, dict) else None

    def set(self, section: str, key: str, value: dict) -> None:
        data = self._load()
        data.setdefault(section, {})[key] = value
        self._save(data)

    def delete(self, section: str, key: str) -> None:
        data = self._load()
        if section not in data or not isinstance(data[section], dict) or key not in data[section]:
            return
        del data[section][key]
        self._save(data)
