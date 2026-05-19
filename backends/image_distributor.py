# -*- coding: utf-8 -*-
import os
import shutil
from PySide6.QtCore import QObject, Slot, Signal


class ImageDistributorBackend(QObject):
    logMessage = Signal(str)
    distributionFinished = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_image = ""
        self._target_folders = []
        self._default_image_dir = "D:/1上款/尺码"
        self._last_target_dir = "D:/1上款"

    @Slot(result=str)
    def getDefaultImageDir(self):
        if not os.path.exists(self._default_image_dir):
            os.makedirs(self._default_image_dir, exist_ok=True)
        return self._default_image_dir

    @Slot(result=str)
    def getLastTargetDir(self):
        if not os.path.exists(self._last_target_dir):
            os.makedirs(self._last_target_dir, exist_ok=True)
        return self._last_target_dir

    @Slot(str)
    def setSourceImage(self, path):
        if path.startswith("file:///"):
            path = path[8:]
        self._source_image = path
        self.logMessage.emit(f"已选择图片: {path}")

    @Slot(result=str)
    def getSourceImage(self):
        return self._source_image

    @Slot(str, result=bool)
    def addTargetFolder(self, path):
        if path.startswith("file:///"):
            path = path[8:]
        if path and path not in self._target_folders:
            self._target_folders.append(path)
            self._last_target_dir = path
            self.logMessage.emit(f"已添加主文件夹: {path}")
            return True
        return False

    @Slot(result=list)
    def getTargetFolders(self):
        return list(self._target_folders)

    @Slot()
    def clearFolders(self):
        self._target_folders.clear()
        self.logMessage.emit("目标文件夹列表已清空。")

    @Slot(int)
    def removeFolder(self, index):
        if 0 <= index < len(self._target_folders):
            removed = self._target_folders.pop(index)
            self.logMessage.emit(f"已移除: {removed}")

    @Slot()
    def startDistribution(self):
        if not self._source_image:
            self.logMessage.emit("[警告] 请先选择一张需要分发的图片！")
            self.distributionFinished.emit(0)
            return
        if not self._target_folders:
            self.logMessage.emit("[警告] 请至少添加一个目标主文件夹！")
            self.distributionFinished.emit(0)
            return

        self.logMessage.emit("-" * 40)
        self.logMessage.emit("开始批量分发...")
        success_count = 0

        for main_folder in self._target_folders:
            self.logMessage.emit(f"\n正在处理主文件夹: {main_folder}")
            try:
                items = os.listdir(main_folder)
            except Exception as e:
                self.logMessage.emit(f"[错误] 无法读取文件夹 {main_folder}: {e}")
                continue

            for item in items:
                sub_folder_path = os.path.join(main_folder, item)
                if os.path.isdir(sub_folder_path):
                    target_file_path = os.path.join(
                        sub_folder_path, os.path.basename(self._source_image))
                    try:
                        shutil.copy2(self._source_image, target_file_path)
                        self.logMessage.emit(f"成功 -> {sub_folder_path}")
                        success_count += 1
                    except Exception as e:
                        self.logMessage.emit(f"[失败] -> {sub_folder_path} (原因: {e})")

        self.logMessage.emit("-" * 40)
        self.logMessage.emit(f"分发完成！成功复制: {success_count} 个文件夹。")
        self.distributionFinished.emit(success_count)
