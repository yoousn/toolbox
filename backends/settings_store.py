# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path


class SettingsStore:
    def __init__(self, filename: str = "settings.json"):
        base_dir = Path(os.environ.get("APPDATA", Path.home())) / "Toolbox"
        self._path = base_dir / filename
        self._data = self._load()

    def get(self, key: str, default=""):
        return self._data.get(key, default)

    def set(self, key: str, value):
        if value is None:
            return
        self._data[key] = value
        self._save()

    def _load(self):
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


settings = SettingsStore()
