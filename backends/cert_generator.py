# -*- coding: utf-8 -*-
import os
import re
from PySide6.QtCore import QObject, Slot, Signal, QThread
from PIL import Image, ImageDraw, ImageFont

from .settings_store import settings


def replace_text_and_save(image_path, text, output_folder):
    """核心图片处理函数 - 从原始脚本原样保留"""
    try:
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        # 使用系统字体绝对路径，避免 PyInstaller 打包后找不到
        win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        font_path = os.path.join(win_fonts, "simsun.ttc")
        if not os.path.exists(font_path):
            font_path = os.path.join(win_fonts, "msyh.ttc")
        font_size = 20
        font = ImageFont.truetype(font_path, font_size)

        text_color = (0, 0, 0)
        outline_color = (255, 255, 255)
        outline_width = 1
        text_position = (182, 198)

        def draw_text_with_outline(draw, text, position, font,
                                   text_color, outline_color, outline_width):
            x, y = position
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text,
                                  font=font, fill=outline_color)
            draw.text((x, y), text, font=font, fill=text_color)

        draw_text_with_outline(draw, text, text_position, font,
                               text_color, outline_color, outline_width)

        base_name = f"{text}.png"
        output_path = os.path.join(output_folder, base_name)
        counter = 1
        while os.path.exists(output_path):
            name, ext = os.path.splitext(base_name)
            output_path = os.path.join(
                output_folder, f"{name}_{counter}{ext}")
            counter += 1

        image.save(output_path)
        return True, output_path
    except Exception as e:
        return False, str(e)


class CertGenerateWorker(QThread):
    logSignal = Signal(str)
    finishedSignal = Signal(int, int)

    def __init__(self, image_path, selected_folder, subdirectories, texts):
        super().__init__()
        self.image_path = image_path
        self.selected_folder = selected_folder
        self.subdirectories = list(subdirectories)
        self.texts = list(texts)

    def run(self):
        success_count = 0
        fail_count = 0

        for i, text in enumerate(self.texts):
            text = str(text).strip()
            if not text:
                continue

            if self.subdirectories and i < len(self.subdirectories):
                output_dir = os.path.join(
                    self.selected_folder, self.subdirectories[i])
            else:
                output_dir = self.selected_folder

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            success, result = replace_text_and_save(
                self.image_path, text, output_dir)
            if success:
                self.logSignal.emit(f"文件已生成：{result}")
                success_count += 1
            else:
                self.logSignal.emit(f"[失败] 生成文件失败：{result}")
                fail_count += 1

        self.finishedSignal.emit(success_count, fail_count)


class CertGeneratorBackend(QObject):
    logMessage = Signal(str)
    generateFinished = Signal(int, int)
    subdirsDetected = Signal(list)
    busyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self._image_path = settings.get(
            "cert_generator.image_path",
            os.path.normpath(os.path.join(desktop, "cs", "合格证.png")))
        self._output_folder = os.path.normpath(os.path.join(desktop, "cs", "x"))
        self._browse_folder = settings.get("cert_generator.browse_folder", r"D:\1上款")
        self._selected_folder = settings.get("cert_generator.selected_folder", "")
        self._subdirectories = []
        self._default_image_folder = settings.get(
            "cert_generator.default_image_folder",
            os.path.normpath(os.path.join(desktop, "上款")))
        self._worker = None
        self._busy = False

    @Slot(result=bool)
    def isBusy(self):
        return self._busy

    @Slot(result=str)
    def getDefaultBrowseFolder(self):
        return self._browse_folder

    @Slot(result=str)
    def getDefaultImageFolder(self):
        return self._default_image_folder

    @Slot(result=str)
    def getImagePath(self):
        return self._image_path

    @Slot(str)
    def setImagePath(self, path):
        path = _clean_path(path)
        self._image_path = path
        settings.set("cert_generator.image_path", path)
        parent = os.path.dirname(path)
        if parent:
            self._default_image_folder = parent
            settings.set("cert_generator.default_image_folder", parent)
        self.logMessage.emit(f"已选择图片: {path}")

    @Slot(str)
    def setSelectedFolder(self, path):
        path = _clean_path(path)
        self._selected_folder = path
        self._browse_folder = path or self._browse_folder
        settings.set("cert_generator.selected_folder", path)
        if path:
            settings.set("cert_generator.browse_folder", path)
        self.logMessage.emit(f"当前主目录: {path}")

    @Slot(str)
    def setOutputFolder(self, path):
        path = _clean_path(path)
        self._output_folder = path
        self.logMessage.emit(f"统一存放目录: {path}")

    @Slot(result=str)
    def getSelectedFolder(self):
        return self._selected_folder

    @Slot(result=list)
    def checkSubdirectories(self):
        if not self._selected_folder:
            self.logMessage.emit("[警告] 请先选择一个目录！")
            return []
        if not os.path.exists(self._selected_folder):
            self.logMessage.emit("[警告] 选择的目录不存在！")
            return []

        try:
            subdirs = []
            for item in os.listdir(self._selected_folder):
                item_path = os.path.join(self._selected_folder, item)
                if os.path.isdir(item_path):
                    subdirs.append(item)

            if not subdirs:
                self.logMessage.emit("该目录下没有子目录！")
                return []

            extracted_texts = []
            for subdir in subdirs:
                match = re.search(r'([A-Za-z0-9]+)', subdir)
                if match:
                    extracted_texts.append(match.group(1))

            if not extracted_texts:
                self.logMessage.emit("没有找到包含英文数字的子目录！")
                return []

            self._subdirectories = subdirs
            self.logMessage.emit(
                f"已检查到 {len(extracted_texts)} 个子目录并自动填写！")
            self.subdirsDetected.emit(extracted_texts)
            return extracted_texts
        except Exception as e:
            self.logMessage.emit(f"检查子目录时出错: {str(e)}")
            return []

    @Slot(list)
    def batchGenerate(self, texts):
        if self._busy:
            return
        if not self._selected_folder:
            self.logMessage.emit("[警告] 请先选择一个目录！")
            self.generateFinished.emit(0, 0)
            return

        self._busy = True
        self.busyChanged.emit()
        self._worker = CertGenerateWorker(
            self._image_path, self._selected_folder, self._subdirectories, texts)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.finishedSignal.connect(self._on_generate_finished)
        self._worker.start()

    def _on_generate_finished(self, success_count, fail_count):
        self._busy = False
        self._worker = None
        self.busyChanged.emit()
        self.generateFinished.emit(success_count, fail_count)


def _clean_path(path: str) -> str:
    import urllib.parse
    path = str(path or "")
    if path.startswith("file:///"):
        path = path[8:]
    return os.path.normpath(urllib.parse.unquote(path)) if path else ""
