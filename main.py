# -*- coding: utf-8 -*-
"""
工具箱主入口。

版本号策略:本文件 __version__ 与 git tag(去掉前缀 v)保持一致。
打 tag 前先改这里,例如 __version__ = "1.0.1" 对应 tag v1.0.1。
"""
import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtGui import QFont

from backends.image_distributor import ImageDistributorBackend
from backends.video_processor import VideoProcessorBackend
from backends.image_file_checker import ImageFileCheckerBackend
from backends.product_matrix import ProductMatrixBackend
from backends.attendance_sync import AttendanceSyncBackend
from backends.cert_generator import CertGeneratorBackend
from backends.white_bg_processor import WhiteBgProcessorBackend
from backends.size_matcher import SizeMatcherBackend
from backends.model_downloader import ModelDownloaderBackend
from backends.update_checker import UpdateCheckerBackend


__version__ = "1.1.2"
GITHUB_REPO = "yoousn/toolbox"


def main():
    # 使用 Basic 样式以支持自定义 background/contentItem
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    app = QApplication(sys.argv)
    app.setApplicationName("工具箱")
    app.setApplicationVersion(__version__)

    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    # 两个关键目录:
    #   app_dir      → exe 所在目录(更新替换、模型下载等)
    #   resource_dir  → QML 等资源目录(PyInstaller 打包后是 _MEIPASS 临时目录)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        app_dir = Path(sys.executable).parent
        resource_dir = Path(sys._MEIPASS)
    else:
        app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        resource_dir = app_dir

    engine = QQmlApplicationEngine()

    # ---- 创建后端实例 ----
    image_distributor = ImageDistributorBackend()
    video_processor = VideoProcessorBackend()
    image_file_checker = ImageFileCheckerBackend()
    product_matrix = ProductMatrixBackend()
    attendance_sync = AttendanceSyncBackend()
    cert_generator = CertGeneratorBackend()

    model_downloader = ModelDownloaderBackend(str(app_dir))
    u2net_available = model_downloader.isDownloaded("u2net")
    white_bg = WhiteBgProcessorBackend(u2net_available, str(app_dir))
    size_matcher = SizeMatcherBackend()

    # 模型下载完成后通知白底图后端激活功能
    def _on_model_downloaded(model_id: str, _path: str):
        if model_id == "u2net":
            white_bg.markU2netAvailable()
    model_downloader.succeeded.connect(_on_model_downloaded)

    # 更新检查(公开仓库不需要 token)
    update_checker = UpdateCheckerBackend(
        repo=GITHUB_REPO,
        current_version=__version__,
        token=os.environ.get("TOOLBOX_GH_TOKEN", ""),
        app_dir=str(app_dir),
    )

    # ---- 注册到 QML 引擎 ----
    ctx = engine.rootContext()
    ctx.setContextProperty("imageDistributor", image_distributor)
    ctx.setContextProperty("videoProcessor", video_processor)
    ctx.setContextProperty("imageFileChecker", image_file_checker)
    ctx.setContextProperty("productMatrix", product_matrix)
    ctx.setContextProperty("attendanceSync", attendance_sync)
    ctx.setContextProperty("certGenerator", cert_generator)
    ctx.setContextProperty("whiteBgProcessor", white_bg)
    ctx.setContextProperty("sizeMatcher", size_matcher)
    ctx.setContextProperty("modelDownloader", model_downloader)
    ctx.setContextProperty("updateChecker", update_checker)
    ctx.setContextProperty("appVersion", __version__)
    ctx.setContextProperty("u2netAvailable", u2net_available)

    # 加载 QML(从资源目录,不是 app_dir)
    qml_file = str(resource_dir / "qml" / "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    # 启动后异步检查更新(不阻塞 UI)
    update_checker.check()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
