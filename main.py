# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtGui import QFont

from backends.image_distributor import ImageDistributorBackend
from backends.video_processor import VideoProcessorBackend
from backends.image_file_checker import ImageFileCheckerBackend
from backends.product_matrix import ProductMatrixBackend
from backends.attendance_sync import AttendanceSyncBackend
from backends.cert_generator import CertGeneratorBackend
from backends.white_bg_processor import WhiteBgProcessorBackend


def main():
    # 使用 Basic 样式以支持自定义 background/contentItem
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

    app = QApplication(sys.argv)

    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    # 确定程序所在目录
    app_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # 检测 u2net 模型文件
    u2net_model = app_dir / ".u2net" / "u2net.onnx"
    u2net_available = u2net_model.exists()

    if not u2net_available:
        QMessageBox.warning(
            None, "模型缺失",
            "请检查本目录有没有u2net模型文件\n\n"
            "未在 .u2net 文件夹中找到 u2net.onnx 模型文件。\n"
            "白底图功能将不可用。"
        )

    engine = QQmlApplicationEngine()

    # 创建后端实例
    image_distributor = ImageDistributorBackend()
    video_processor = VideoProcessorBackend()
    image_file_checker = ImageFileCheckerBackend()
    product_matrix = ProductMatrixBackend()
    attendance_sync = AttendanceSyncBackend()
    cert_generator = CertGeneratorBackend()
    white_bg = WhiteBgProcessorBackend(u2net_available, str(app_dir))

    # 注册到 QML 引擎
    ctx = engine.rootContext()
    ctx.setContextProperty("imageDistributor", image_distributor)
    ctx.setContextProperty("videoProcessor", video_processor)
    ctx.setContextProperty("imageFileChecker", image_file_checker)
    ctx.setContextProperty("productMatrix", product_matrix)
    ctx.setContextProperty("attendanceSync", attendance_sync)
    ctx.setContextProperty("certGenerator", cert_generator)
    ctx.setContextProperty("whiteBgProcessor", white_bg)
    ctx.setContextProperty("u2netAvailable", u2net_available)

    # 加载 QML
    qml_file = str(app_dir / "qml" / "Main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
