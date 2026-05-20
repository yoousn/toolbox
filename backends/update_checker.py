# -*- coding: utf-8 -*-
"""
启动时后台检查 GitHub Releases 是否有新版本。
支持程序内下载更新包并自动替换重启。
"""
import json
import os
import sys
import time
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QThread, QCoreApplication


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
                if name.endswith(".zip"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url:
                download_url = data.get("html_url", "")

            notes = data.get("body", "") or ""
            self.found.emit(latest, download_url, notes)
        except Exception as e:
            self.failed.emit(str(e))


class _DownloadUpdateWorker(QThread):
    """下载更新包并解压替换。"""
    progress = Signal(int, str)     # 百分比, 状态文字
    finished_ok = Signal(str)       # 解压目录
    failed = Signal(str)

    def __init__(self, url: str, app_dir: str):
        super().__init__()
        self.url = url
        self.app_dir = Path(app_dir)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        tmp_dir = Path(tempfile.gettempdir()) / "toolbox_update"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = tmp_dir / "update.zip"

        try:
            # 下载
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Toolbox-Updater/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 256
                last_ts = time.time()
                last_bytes = 0
                speed = 0.0

                with open(zip_path, "wb") as f:
                    while True:
                        if self._cancel:
                            zip_path.unlink(missing_ok=True)
                            self.failed.emit("已取消")
                            return
                        buf = resp.read(chunk_size)
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)

                        now = time.time()
                        if now - last_ts >= 0.3:
                            dt = now - last_ts
                            db = downloaded - last_bytes
                            inst = db / dt if dt > 0 else 0
                            speed = inst if speed == 0 else 0.3 * inst + 0.7 * speed
                            last_ts = now
                            last_bytes = downloaded

                            mb_done = downloaded / 1024 / 1024
                            if total:
                                pct = int(downloaded * 100 / total)
                                mb_total = total / 1024 / 1024
                                spd = _fmt_speed(speed)
                                self.progress.emit(pct, f"{mb_done:.1f}/{mb_total:.1f} MB · {spd}")
                            else:
                                self.progress.emit(0, f"已下载 {mb_done:.1f} MB")

            # 解压(带路径穿越防护)
            self.progress.emit(100, "解压中...")
            extract_dir = tmp_dir / "extracted"
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir, ignore_errors=True)
            extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    # 防 ZIP Slip:禁止绝对路径和 "../" 穿越
                    member_path = os.path.normpath(member.filename)
                    if os.path.isabs(member_path) or member_path.startswith(".."):
                        self.progress.emit(100, f"跳过可疑路径: {member.filename}")
                        continue
                    target = extract_dir / member_path
                    # 二次确认不越界
                    try:
                        target.resolve().relative_to(extract_dir.resolve())
                    except ValueError:
                        self.progress.emit(100, f"跳过越界路径: {member.filename}")
                        continue
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            dst.write(src.read())

            zip_path.unlink(missing_ok=True)
            self.finished_ok.emit(str(extract_dir))
        except Exception as e:
            zip_path.unlink(missing_ok=True)
            if self._cancel:
                self.failed.emit("已取消")
            else:
                self.failed.emit(f"下载失败: {e}")


def _normalize(v: str) -> str:
    return v.lstrip("vV").strip()


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "-- KB/s"
    if bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / 1024 / 1024:.2f} MB/s"


class UpdateCheckerBackend(QObject):
    updateAvailable = Signal(str, str, str)   # latest_version, url, notes
    upToDate = Signal()
    checkFailed = Signal(str)
    downloadProgress = Signal(int, str)       # 百分比, 状态
    downloadFinished = Signal()
    downloadFailed = Signal(str)
    busyChanged = Signal()

    def __init__(self, repo: str, current_version: str, token: str = "", app_dir: str = ""):
        super().__init__()
        self._repo = repo
        self._current = current_version
        self._token = token
        self._app_dir = app_dir or str(Path(sys.executable).parent)
        self._worker: _CheckWorker | None = None
        self._dl_worker: _DownloadUpdateWorker | None = None
        self._extract_dir = ""

    @Slot(result=str)
    def currentVersion(self) -> str:
        return self._current

    @Slot(result=bool)
    def isDownloading(self) -> bool:
        return self._dl_worker is not None and self._dl_worker.isRunning()

    @Slot()
    def check(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = _CheckWorker(self._repo, self._current, self._token)
        self._worker.found.connect(self.updateAvailable)
        self._worker.no_update.connect(self.upToDate)
        self._worker.failed.connect(self.checkFailed)
        self._worker.start()

    @Slot(str)
    def downloadUpdate(self, url: str):
        """下载更新包"""
        if self._dl_worker and self._dl_worker.isRunning():
            return
        self._dl_worker = _DownloadUpdateWorker(url, self._app_dir)
        self._dl_worker.progress.connect(self.downloadProgress)
        self._dl_worker.finished_ok.connect(self._on_download_ok)
        self._dl_worker.failed.connect(self.downloadFailed)
        self._dl_worker.finished.connect(self.busyChanged.emit)
        self._dl_worker.start()
        self.busyChanged.emit()

    @Slot()
    def cancelDownload(self):
        if self._dl_worker and self._dl_worker.isRunning():
            self._dl_worker.cancel()

    @Slot()
    def applyUpdate(self):
        """生成更新脚本并重启程序"""
        if not self._extract_dir:
            return

        extract_path = Path(self._extract_dir)
        # 找到解压后的实际目录(zip 里通常有一层文件夹)
        contents = list(extract_path.iterdir())
        source_dir = contents[0] if len(contents) == 1 and contents[0].is_dir() else extract_path

        # 对于 PyInstaller 打包的 exe, sys.executable 就是 exe 本身
        # 使用 _MEIPASS 环境变量判断是否是 PyInstaller 环境
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller 打包模式: exe 在 app_dir 下
            app_dir = Path(sys.executable).parent.resolve()
            exe_name = Path(sys.executable).name
        else:
            # 开发模式
            app_dir = Path(self._app_dir).resolve()
            exe_name = Path(sys.executable).name

        # 生成 updater.bat
        # 策略: 先 xcopy /C 复制所有文件(跳过被占用的exe),再循环重试exe直到替换成功
        bat_path = Path(tempfile.gettempdir()) / "toolbox_updater.bat"

        # 使用短路径名避免中文/空格问题
        source_dir_str = str(source_dir)
        app_dir_str = str(app_dir)
        exe_path = app_dir / exe_name

        bat_content = f'''@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 正在更新工具箱,请稍候...
echo 源目录: {source_dir_str}
echo 目标目录: {app_dir_str}
echo 目标exe: {exe_path}
echo ========================================
timeout /t 3 /nobreak >nul
echo [1/3] 复制更新文件...
xcopy /E /Y /Q /C "{source_dir_str}\\*" "{app_dir_str}\\"
if errorlevel 1 (
    echo xcopy 出错,错误码: %errorlevel%
)
echo [2/3] 替换主程序...
:retry_exe
copy /Y "{source_dir_str}\\{exe_name}" "{app_dir_str}\\{exe_name}" >nul 2>&1
if errorlevel 1 (
    echo 等待旧进程释放exe...
    timeout /t 1 /nobreak >nul
    goto retry_exe
)
echo [3/3] 清理临时文件...
rmdir /S /Q "{extract_path}"
echo 更新完成,正在重启...
start "" "{exe_path}"
del "%~f0"
'''
        bat_path.write_text(bat_content, encoding="utf-8")

        # 启动 bat 并退出当前程序
        os.startfile(str(bat_path))
        QCoreApplication.quit()

    def _on_download_ok(self, extract_dir: str):
        self._extract_dir = extract_dir
        self.downloadFinished.emit()
