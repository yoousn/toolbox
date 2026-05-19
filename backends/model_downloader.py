# -*- coding: utf-8 -*-
"""
按需下载大模型/资源文件。
所有大文件不入 git,首次使用时由本模块下载到本地。

新增模型:在 MODEL_REGISTRY 加一项即可。
"""
import hashlib
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QThread, Property


# ============================================================
# 模型清单(单一数据源)
# ============================================================
# url     : 直链下载地址(必须是无需鉴权的公开链接)
# path    : 相对程序根目录的保存路径
# size_mb : 用于 UI 提示
# sha256  : 可选,做完整性校验。不填则跳过校验
# ============================================================
MODEL_REGISTRY = {
    "u2net": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
        "path": ".u2net/u2net.onnx",
        "size_mb": 168,
        "sha256": "",  # 留空 = 不校验。如需严格校验,本地算好填进来
    },
    # 以后加新模型:
    # "yolov8n": {
    #     "url": "...",
    #     "path": "models/yolov8n.onnx",
    #     "size_mb": 12,
    #     "sha256": "",
    # },
}


class _DownloadWorker(QThread):
    progress = Signal(int, str)   # 百分比 0-100, 状态文字
    finished_ok = Signal(str)     # 文件保存路径
    failed = Signal(str)          # 错误信息

    def __init__(self, model_id: str, app_dir: Path):
        super().__init__()
        self.model_id = model_id
        self.app_dir = app_dir
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        info = MODEL_REGISTRY.get(self.model_id)
        if not info:
            self.failed.emit(f"未知模型: {self.model_id}")
            return

        target = self.app_dir / info["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".part")

        try:
            import time

            req = urllib.request.Request(
                info["url"],
                headers={"User-Agent": "Toolbox-ModelDownloader/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 256  # 256 KB

                start_ts = time.time()
                last_emit_ts = start_ts
                last_emit_bytes = 0
                speed_bps = 0.0  # bytes per second(滑动窗口)

                with open(tmp, "wb") as f:
                    while True:
                        if self._cancel:
                            tmp.unlink(missing_ok=True)
                            self.failed.emit("已取消")
                            return
                        buf = resp.read(chunk_size)
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)

                        now = time.time()
                        # 至少 0.3s 推送一次状态,避免刷爆主线程
                        if now - last_emit_ts >= 0.3:
                            delta_t = now - last_emit_ts
                            delta_b = downloaded - last_emit_bytes
                            inst_speed = delta_b / delta_t if delta_t > 0 else 0
                            # 平滑一下,避免数字跳得太厉害
                            speed_bps = (
                                inst_speed if speed_bps == 0
                                else 0.3 * inst_speed + 0.7 * speed_bps
                            )
                            last_emit_ts = now
                            last_emit_bytes = downloaded

                            mb_done = downloaded / 1024 / 1024
                            speed_str = _fmt_speed(speed_bps)
                            if total:
                                pct = int(downloaded * 100 / total)
                                mb_total = total / 1024 / 1024
                                remain = total - downloaded
                                eta = _fmt_eta(remain / speed_bps) if speed_bps > 0 else "--"
                                self.progress.emit(
                                    pct,
                                    f"{mb_done:.1f} / {mb_total:.1f} MB  ·  {speed_str}  ·  剩余 {eta}",
                                )
                            else:
                                self.progress.emit(
                                    0, f"已下载 {mb_done:.1f} MB  ·  {speed_str}"
                                )

            # 校验
            expected = info.get("sha256")
            if expected:
                actual = self._sha256(tmp)
                if actual.lower() != expected.lower():
                    tmp.unlink(missing_ok=True)
                    self.failed.emit(
                        f"校验失败,文件可能损坏。\n期望 {expected}\n实际 {actual}"
                    )
                    return

            tmp.replace(target)  # 原子替换,中途断网不会留半截文件
            self.finished_ok.emit(str(target))
        except Exception as e:
            tmp.unlink(missing_ok=True)
            if self._cancel:
                self.failed.emit("已取消")
            else:
                self.failed.emit(f"下载失败: {e}")

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


class ModelDownloaderBackend(QObject):
    """暴露给 QML 用的下载器。"""
    progressChanged = Signal(int, str)
    succeeded = Signal(str, str)        # model_id, path
    failedSig = Signal(str, str)        # model_id, error
    busyChanged = Signal()

    def __init__(self, app_dir: str):
        super().__init__()
        self._app_dir = Path(app_dir)
        self._worker: _DownloadWorker | None = None
        self._current_model = ""

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    @Slot(str, result=bool)
    def isDownloaded(self, model_id: str) -> bool:
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            return False
        return (self._app_dir / info["path"]).exists()

    @Slot(str, result=int)
    def expectedSizeMb(self, model_id: str) -> int:
        info = MODEL_REGISTRY.get(model_id)
        return int(info["size_mb"]) if info else 0

    @Slot(str)
    def download(self, model_id: str):
        if self._worker and self._worker.isRunning():
            return
        if model_id not in MODEL_REGISTRY:
            self.failedSig.emit(model_id, f"未知模型: {model_id}")
            return

        self._current_model = model_id
        self._worker = _DownloadWorker(model_id, self._app_dir)
        self._worker.progress.connect(self.progressChanged)
        self._worker.finished_ok.connect(
            lambda p, m=model_id: self.succeeded.emit(m, p)
        )
        self._worker.failed.connect(
            lambda e, m=model_id: self.failedSig.emit(m, e)
        )
        self._worker.finished.connect(self.busyChanged.emit)
        self._worker.start()
        self.busyChanged.emit()

    @Slot()
    def cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()


def _fmt_speed(bps: float) -> str:
    """字节/秒 → 人类可读"""
    if bps <= 0:
        return "-- KB/s"
    if bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / 1024 / 1024:.2f} MB/s"


def _fmt_eta(seconds: float) -> str:
    """秒数 → 'mm:ss' 或 'h:mm:ss'"""
    if seconds < 0 or seconds > 3600 * 24:
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分{seconds % 60:02d}秒"
    return f"{seconds // 3600}时{(seconds % 3600) // 60:02d}分"
