# -*- coding: utf-8 -*-
"""
按需下载大模型/资源文件。
支持多镜像源选择、延迟测试、自动选最优源。
"""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QThread, Property


# ============================================================
# 镜像源列表
# ============================================================
MIRROR_SOURCES = [
    {
        "id": "github",
        "name": "GitHub 官方",
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
    },
    {
        "id": "ghproxy",
        "name": "GHProxy 加速",
        "url": "https://mirror.ghproxy.com/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
    },
    {
        "id": "huggingface",
        "name": "HuggingFace",
        "url": "https://huggingface.co/BritishWerewolf/U-2-Net/resolve/main/u2net.onnx",
    },
    {
        "id": "sourceforge",
        "name": "SourceForge",
        "url": "https://sourceforge.net/projects/bgremover-app/files/u2net/u2net.onnx/download",
    },
]


# ============================================================
# 模型清单
# ============================================================
MODEL_REGISTRY = {
    "u2net": {
        "path": ".u2net/u2net.onnx",
        "size_mb": 168,
        # Official rembg checksum for the u2net v0.0.0 model.
        "checksum": "md5:60024c5c889badc19c04ad937298a77b",
    },
}


# ============================================================
# 延迟测试线程
# ============================================================
class _LatencyWorker(QThread):
    """测试所有镜像源的响应延迟。"""
    result = Signal(str)  # JSON: [{"id": "...", "latency": 123}, ...]

    def run(self):
        results = []
        for src in MIRROR_SOURCES:
            latency = self._ping(src["url"])
            results.append({
                "id": src["id"],
                "name": src["name"],
                "url": src["url"],
                "latency": latency,  # -1 表示超时/不可用
            })
        self.result.emit(json.dumps(results, ensure_ascii=False))

    @staticmethod
    def _ping(url: str) -> int:
        """发 HEAD 请求测延迟(ms),超时返回 -1"""
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Toolbox-LatencyTest/1.0")
            start = time.time()
            with urllib.request.urlopen(req, timeout=8):
                pass
            return int((time.time() - start) * 1000)
        except Exception:
            return -1


# ============================================================
# 下载线程
# ============================================================
class _DownloadWorker(QThread):
    progress = Signal(int, str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, target: Path, checksum: str = ""):
        super().__init__()
        self.url = url
        self.target = target
        self.checksum = checksum
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.target.with_suffix(self.target.suffix + ".part")

        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Toolbox-ModelDownloader/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 256

                last_emit_ts = time.time()
                last_emit_bytes = 0
                speed_bps = 0.0

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
                        if now - last_emit_ts >= 0.3:
                            delta_t = now - last_emit_ts
                            delta_b = downloaded - last_emit_bytes
                            inst_speed = delta_b / delta_t if delta_t > 0 else 0
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
            if self.checksum:
                expected_algo, expected_hash = _parse_checksum(self.checksum)
                actual = self._hash_file(tmp, expected_algo)
                if actual.lower() != expected_hash.lower():
                    tmp.unlink(missing_ok=True)
                    self.failed.emit(f"校验失败,文件可能损坏")
                    return

            tmp.replace(self.target)
            self.finished_ok.emit(str(self.target))
        except Exception as e:
            tmp.unlink(missing_ok=True)
            if self._cancel:
                self.failed.emit("已取消")
            else:
                self.failed.emit(f"下载失败: {e}")

    @staticmethod
    def _hash_file(path: Path, algorithm: str) -> str:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


# ============================================================
# 暴露给 QML 的后端
# ============================================================
class ModelDownloaderBackend(QObject):
    progressChanged = Signal(int, str)
    succeeded = Signal(str, str)        # model_id, path
    failedSig = Signal(str, str)        # model_id, error
    busyChanged = Signal()
    latencyResult = Signal(str)         # JSON 数组

    def __init__(self, app_dir: str):
        super().__init__()
        self._app_dir = Path(app_dir)
        self._worker: _DownloadWorker | None = None
        self._latency_worker: _LatencyWorker | None = None
        self._current_model = ""

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    @Slot(str, result=bool)
    def isDownloaded(self, model_id: str) -> bool:
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            return False
        return self.modelStatus(model_id) in ("ok", "unchecked", "mismatch")

    @Slot(str, result=str)
    def modelStatus(self, model_id: str) -> str:
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            return "unknown"
        target = self._app_dir / info["path"]
        if not target.exists():
            return "missing"
        checksum = info.get("checksum", "")
        if not checksum:
            return "unchecked"
        try:
            expected_algo, expected_hash = _parse_checksum(checksum)
            actual = _hash_file(target, expected_algo)
        except Exception:
            return "unchecked"
        return "ok" if actual.lower() == expected_hash.lower() else "mismatch"

    @Slot(str, result=str)
    def modelStatusText(self, model_id: str) -> str:
        status = self.modelStatus(model_id)
        if status == "ok":
            return "模型已就绪,校验正常"
        if status == "unchecked":
            return "模型已存在,未配置校验,可尝试使用"
        if status == "mismatch":
            return "模型已存在,但校验不匹配,建议重新下载"
        if status == "missing":
            return "模型未下载"
        return "未知模型"

    @Slot(str, result=int)
    def expectedSizeMb(self, model_id: str) -> int:
        info = MODEL_REGISTRY.get(model_id)
        return int(info["size_mb"]) if info else 0

    @Slot(result=str)
    def getMirrors(self) -> str:
        """返回镜像源列表 JSON"""
        return json.dumps(MIRROR_SOURCES, ensure_ascii=False)

    @Slot()
    def testLatency(self):
        """测试所有镜像源延迟"""
        if self._latency_worker and self._latency_worker.isRunning():
            return
        self._latency_worker = _LatencyWorker()
        self._latency_worker.result.connect(self.latencyResult)
        self._latency_worker.start()

    @Slot(str, str)
    def downloadFromMirror(self, model_id: str, mirror_url: str):
        """从指定镜像下载模型"""
        if self._worker and self._worker.isRunning():
            return
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            self.failedSig.emit(model_id, f"未知模型: {model_id}")
            return

        self._current_model = model_id
        target = self._app_dir / info["path"]
        checksum = info.get("checksum", "")

        self._worker = _DownloadWorker(mirror_url, target, checksum)
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

    @Slot(str)
    def download(self, model_id: str):
        """兼容旧接口:用默认源下载"""
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            self.failedSig.emit(model_id, f"未知模型: {model_id}")
            return
        self.downloadFromMirror(model_id, MIRROR_SOURCES[0]["url"])

    @Slot()
    def cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    @Slot(str, result=str)
    def getModelDir(self, model_id: str) -> str:
        """返回模型应放置的目录路径(供用户手动放置参考)"""
        info = MODEL_REGISTRY.get(model_id)
        if not info:
            return ""
        target = self._app_dir / info["path"]
        return str(target.parent)


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return "-- KB/s"
    if bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / 1024 / 1024:.2f} MB/s"


def _fmt_eta(seconds: float) -> str:
    if seconds < 0 or seconds > 3600 * 24:
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        return f"{seconds // 60}分{seconds % 60:02d}秒"
    return f"{seconds // 3600}时{(seconds % 3600) // 60:02d}分"


def _parse_checksum(checksum: str) -> tuple[str, str]:
    if ":" in checksum:
        algorithm, expected_hash = checksum.split(":", 1)
    else:
        algorithm, expected_hash = "sha256", checksum
    return algorithm.lower(), expected_hash


def _hash_file(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
