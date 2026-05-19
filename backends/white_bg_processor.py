# -*- coding: utf-8 -*-
import os
from PySide6.QtCore import QObject, Slot, Signal, QThread


class WhiteBgWorker(QThread):
    logSignal = Signal(str)
    progressSignal = Signal(int, int)
    finishedSignal = Signal(int)
    errorSignal = Signal(str)

    def __init__(self, image_paths, save_format, session):
        super().__init__()
        self.image_paths = image_paths
        self.save_format = save_format
        self.session = session

    def run(self):
        try:
            total = len(self.image_paths)
            self.progressSignal.emit(0, total)

            for i, img_path in enumerate(self.image_paths):
                self.logSignal.emit(f"处理中: {i+1}/{total}")
                self._process_single(img_path)
                self.progressSignal.emit(i + 1, total)

            self.finishedSignal.emit(total)
        except Exception as e:
            import traceback
            self.errorSignal.emit(
                f"{str(e)}\n{traceback.format_exc()}")

    def _process_single(self, img_path):
        from PIL import Image
        from rembg import remove

        save_format_str = self.save_format.lower()
        save_format = "jpg" if "jpg" in save_format_str else "png"
        clean_path = img_path.replace('\\', '/')

        with open(clean_path, 'rb') as f:
            img = Image.open(f)
            output = remove(img, session=self.session)

        save_dir = os.path.dirname(clean_path)
        base_save_path = os.path.join(save_dir, f"白底图.{save_format}")
        save_path = base_save_path
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(save_dir, f"白底图_{counter}.{save_format}")
            counter += 1

        if save_format == "jpg":
            white_bg = Image.new("RGB", output.size, "WHITE")
            white_bg.paste(
                output,
                mask=output.split()[3] if output.mode == 'RGBA' else None)
            white_bg.save(save_path, "JPEG", quality=95)
        else:
            output.save(save_path, "PNG")


class WhiteBgProcessorBackend(QObject):
    logMessage = Signal(str)
    progressUpdated = Signal(int, int)
    processingFinished = Signal(int)
    errorOccurred = Signal(str)
    resultItemAdded = Signal(str, bool)
    busyChanged = Signal()

    def __init__(self, u2net_available=False, app_dir="", parent=None):
        super().__init__(parent)
        self._u2net_available = u2net_available
        self._app_dir = app_dir
        self._image_paths = []
        self._missing_folders = []
        self._worker = None
        self._busy = False
        self._session = None
        self._session_initialized = False
        self._default_path = "D:\\1上款"

    def _ensure_session(self):
        """懒加载 rembg session，避免启动时崩溃"""
        if self._session_initialized:
            return self._session is not None
        self._session_initialized = True

        if not self._u2net_available:
            return False
        try:
            # 设置 U2NET_HOME 让 rembg 能找到本地模型
            u2net_home = os.path.join(self._app_dir, ".u2net")
            os.environ["U2NET_HOME"] = u2net_home
            from rembg import new_session
            self._session = new_session("u2net")
            return True
        except Exception as e:
            self._u2net_available = False
            print(f"u2net session init failed: {e}")
            return False

    @Slot(result=bool)
    def isU2netAvailable(self):
        return self._u2net_available

    @Slot(result=str)
    def getDefaultPath(self):
        return self._default_path

    @Slot(str, str)
    def detectImages(self, base_dir, filename):
        if not os.path.exists(base_dir):
            self.logMessage.emit("[错误] 指定目录不存在！")
            return
        if not filename:
            self.logMessage.emit("[错误] 请输入要搜索的文件名！")
            return

        self._image_paths = []
        self._missing_folders = []

        all_subdirs = []
        for root, dirs, files in os.walk(base_dir):
            if root != base_dir:
                all_subdirs.append(root)

        for subdir in all_subdirs:
            found = False
            try:
                for file in os.listdir(subdir):
                    file_base, file_ext = os.path.splitext(file)
                    if (file_base.startswith(filename) and
                            file_ext.lower()[1:] in ['jpg', 'jpeg', 'png']):
                        full_path = os.path.join(subdir, file)
                        self._image_paths.append(full_path)
                        self.resultItemAdded.emit(full_path, False)
                        found = True
                        break
            except Exception:
                pass

            if not found:
                self._missing_folders.append(subdir)
                self.resultItemAdded.emit(f"【缺失】{subdir}", True)

        if not self._image_paths and not self._missing_folders:
            self.logMessage.emit("未找到匹配的图片文件和文件夹")
        else:
            self.logMessage.emit(
                f"找到 {len(self._image_paths)} 个匹配文件，"
                f"{len(self._missing_folders)} 个缺失文件夹")

    @Slot(list, str)
    def processSpecificFiles(self, file_paths, save_format):
        self._image_paths = [str(p) for p in file_paths]
        self.processImages(save_format)

    @Slot(str)
    def processImages(self, save_format):
        if not self._image_paths:
            self.logMessage.emit("[错误] 没有可处理的图片！")
            return
        if not self._ensure_session():
            self.logMessage.emit("[错误] u2net模型未加载！请检查 .u2net 文件夹")
            return
        if self._busy:
            return

        self._busy = True
        self.busyChanged.emit()

        self._worker = WhiteBgWorker(
            self._image_paths, save_format, self._session)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.progressSignal.connect(self.progressUpdated.emit)
        self._worker.finishedSignal.connect(self._on_finished)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, count):
        self._busy = False
        self.busyChanged.emit()
        self.processingFinished.emit(count)
        self.logMessage.emit(f"处理完成! 共处理 {count} 张图片")

    def _on_error(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.errorOccurred.emit(msg)

    @Slot()
    def clearResults(self):
        self._image_paths = []
        self._missing_folders = []
