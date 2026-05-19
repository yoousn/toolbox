# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QThread


class VideoProcessWorker(QThread):
    logSignal = Signal(str)
    progressSignal = Signal(int, int)
    finishedSignal = Signal(str)
    errorSignal = Signal(str)

    def __init__(self, root_dir, file_format, mode):
        super().__init__()
        self.root_dir = root_dir
        self.file_format = file_format
        self.mode = mode

    def run(self):
        try:
            root_path = Path(self.root_dir)
            if not root_path.is_dir():
                raise ValueError("无效的目录路径！")

            self.logSignal.emit(f"🚀 开始 [{self.mode}] 操作...")
            self.logSignal.emit(f"📁 目标目录: {self.root_dir}")

            ext_upper = self.file_format.upper()
            ext_lower = self.file_format.lower()
            all_video_dir = root_path / f"所有{ext_upper}"

            if self.mode == 'copy':
                all_video_dir.mkdir(exist_ok=True)
                self.logSignal.emit(f"📁 确认总文件夹: {all_video_dir.name}")

            folders = [f for f in root_path.iterdir()
                       if f.is_dir() and f.name != all_video_dir.name]
            total = len(folders)

            if total == 0:
                self.finishedSignal.emit("未找到任何子文件夹。")
                return

            self.logSignal.emit(f"🔍 检测到 {total} 个子文件夹，开始处理...")
            count = 0

            for i, folder_path in enumerate(folders):
                self.progressSignal.emit(i + 1, total)

                video_files = (list(folder_path.glob(f"*.{ext_lower}")) +
                               list(folder_path.glob(f"*.{ext_upper}")))
                video_files = sorted(list(set(video_files)))
                file_count = len(video_files)

                if not video_files:
                    if self.mode == 'analyze':
                        self.logSignal.emit(
                            f"  [空] 文件夹 '{folder_path.name}' 无目标文件")
                    continue

                for file_index, video_file in enumerate(video_files):
                    if file_count > 1:
                        new_name = f"{folder_path.name}_{file_index + 1}.{ext_upper}"
                    else:
                        new_name = f"{folder_path.name}.{ext_upper}"

                    if self.mode == 'analyze':
                        self.logSignal.emit(
                            f"  [发现] {video_file.name} ➡️ {new_name}")
                        count += 1
                    elif self.mode == 'rename':
                        new_filepath = folder_path / new_name
                        if video_file.name != new_name:
                            try:
                                if new_filepath.exists():
                                    self.logSignal.emit(
                                        f"  ⚠️ 跳过: {new_name} 已存在")
                                else:
                                    video_file.rename(new_filepath)
                                    self.logSignal.emit(
                                        f"  📝 重命名: {video_file.name} ➡️ {new_name}")
                                    count += 1
                            except Exception as e:
                                self.logSignal.emit(
                                    f"  ❌ 重命名失败 '{video_file.name}': {e}")
                    elif self.mode == 'copy':
                        target_filepath = all_video_dir / new_name
                        counter = 1
                        stem = target_filepath.stem
                        while target_filepath.exists():
                            target_filepath = all_video_dir / \
                                f"{stem}({counter}).{ext_upper}"
                            counter += 1
                        try:
                            shutil.copy2(video_file, target_filepath)
                            self.logSignal.emit(
                                f"  📋 复制: {video_file.name} ➡️ {target_filepath.name}")
                            count += 1
                        except Exception as e:
                            self.logSignal.emit(
                                f"  ❌ 复制失败 '{video_file.name}': {e}")

            self.finishedSignal.emit(
                f"✨ 操作完成！共成功处理 {count} 个视频文件。")
            self.progressSignal.emit(total, total)

        except Exception as e:
            self.errorSignal.emit(str(e))


class VideoProcessorBackend(QObject):
    logMessage = Signal(str)
    progressUpdated = Signal(int, int)
    taskFinished = Signal(str)
    taskError = Signal(str)
    busyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._busy = False

    @Slot(result=bool)
    def isBusy(self):
        return self._busy

    @Slot(str, str, str)
    def startTask(self, root_dir, file_format, mode):
        if self._busy:
            return
        if root_dir.startswith("file:///"):
            root_dir = root_dir[8:]
        if not root_dir or not os.path.isdir(root_dir):
            self.logMessage.emit("请选择有效的文件夹路径！")
            return

        self._busy = True
        self.busyChanged.emit()

        self._worker = VideoProcessWorker(root_dir, file_format, mode)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.progressSignal.connect(self.progressUpdated.emit)
        self._worker.finishedSignal.connect(self._on_finished)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.taskFinished.emit(msg)

    def _on_error(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.taskError.emit(msg)
