# -*- coding: utf-8 -*-
"""
启动时后台检查 GitHub Releases 是否有新版本。
"""
import json
import urllib.request
from PySide6.QtCore import QObject, Signal, Slot, QThread


class _CheckWorker(QThread):
    found = Signal(str, str, str)   # latest_version, download_url, release_notes
    no_update = Signal()
    failed = Signal(str)

    def __init__(self, repo: str, current_version: str, token: str = ""):
        super().__init__()
        self.repo = repo
        self.current_version = current_version
        self.token = token

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Toolbox-UpdateChecker/1.0")
            req.add_header("Accept", "application/vnd.github+json")
            if self.token:
                req.add_header("Authorization", f"Bearer {self.token}")

            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.load(resp)

            latest = (data.get("tag_name") or "").lstrip("vV").strip()
            if not latest:
                self.no_update.emit()
                return

            if _normalize(latest) == _normalize(self.current_version):
                self.no_update.emit()
                return

            download_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".zip") or name.endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url:
                # 没找到 asset 就给 release 页面链接
                download_url = data.get("html_url", "")

            notes = data.get("body", "") or ""
            self.found.emit(latest, download_url, notes)
        except Exception as e:
            self.failed.emit(str(e))


def _normalize(v: str) -> str:
    return v.lstrip("vV").strip()


class UpdateCheckerBackend(QObject):
    updateAvailable = Signal(str, str, str)   # latest_version, url, notes
    upToDate = Signal()
    checkFailed = Signal(str)

    def __init__(self, repo: str, current_version: str, token: str = ""):
        super().__init__()
        self._repo = repo
        self._current = current_version
        self._token = token
        self._worker: _CheckWorker | None = None

    @Slot(result=str)
    def currentVersion(self) -> str:
        return self._current

    @Slot()
    def check(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = _CheckWorker(self._repo, self._current, self._token)
        self._worker.found.connect(self.updateAvailable)
        self._worker.no_update.connect(self.upToDate)
        self._worker.failed.connect(self.checkFailed)
        self._worker.start()
