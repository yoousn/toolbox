# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Signal


class ImageFileCheckerBackend(QObject):
    logMessage = Signal(str)
    operationFinished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_recycle_bin = os.path.join(
            os.path.expanduser("~"), "ImageFileTool_RecycleBin")
        os.makedirs(self.app_recycle_bin, exist_ok=True)
        self.deleted_files_map = {}

    @Slot(str, list)
    def checkFiles(self, folder_path, filenames):
        import urllib.parse
        if folder_path.startswith("file:///"):
            folder_path = folder_path[8:]
        folder_path = os.path.normpath(urllib.parse.unquote(folder_path))

        if not folder_path or not os.path.isdir(folder_path):
            self.logMessage.emit("[错误] 请先选择一个有效的目标文件夹！")
            return
        target_files = [n.strip() if n.strip().lower().endswith(('.jpg', '.jpeg', '.png')) else f"{n.strip()}.jpg"
                        for n in filenames if n and n.strip()]
        if not target_files:
            self.logMessage.emit("[错误] 请输入至少一个文件名！")
            return
        self._walk_and_operate(folder_path, target_files, 'check')

    @Slot(str, list)
    def deleteFiles(self, folder_path, filenames):
        import urllib.parse
        if folder_path.startswith("file:///"):
            folder_path = folder_path[8:]
        folder_path = os.path.normpath(urllib.parse.unquote(folder_path))

        if not folder_path or not os.path.isdir(folder_path):
            self.logMessage.emit("[错误] 请先选择一个有效的目标文件夹！")
            return
        target_files = [n.strip() if n.strip().lower().endswith(('.jpg', '.jpeg', '.png')) else f"{n.strip()}.jpg"
                        for n in filenames if n and n.strip()]
        if not target_files:
            self.logMessage.emit("[错误] 请输入至少一个文件名！")
            return
        self._walk_and_operate(folder_path, target_files, 'delete')

    def _walk_and_operate(self, folder_path, target_files, operation):
        found_map = {}
        self.logMessage.emit(f"开始在文件夹【{folder_path}】中搜索...")

        for dirpath, _, filenames_in_dir in os.walk(folder_path):
            for filename in filenames_in_dir:
                if filename in target_files:
                    full_path = os.path.join(dirpath, filename)
                    if filename not in found_map:
                        found_map[filename] = []
                    found_map[filename].append(full_path)

        files_actually_found = set(found_map.keys())
        if not files_actually_found:
            self.logMessage.emit("\n在所有子文件夹中均未找到指定文件。")
        else:
            self.logMessage.emit("\n--- 结果报告 ---")
            for filename in sorted(files_actually_found):
                paths = found_map[filename]
                self.logMessage.emit(f"\n找到文件: {filename}")
                for path in paths:
                    if operation == 'check':
                        self.logMessage.emit(f"  -> 路径: {path}")
                    elif operation == 'delete':
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                            recycle_filename = f"{timestamp}_{os.path.basename(path)}"
                            destination_path = os.path.join(
                                self.app_recycle_bin, recycle_filename)
                            shutil.move(path, destination_path)
                            self.deleted_files_map[recycle_filename] = path
                            self.logMessage.emit(f"  -> 已移至回收站: {path}")
                        except Exception as e:
                            self.logMessage.emit(
                                f"  -> 移动失败: {path} (错误: {e})")

        not_found_files = set(target_files) - files_actually_found
        if not_found_files:
            self.logMessage.emit("\n--- 未找到的文件 ---")
            for filename in sorted(list(not_found_files)):
                self.logMessage.emit(f"- {filename}")
        self.logMessage.emit("\n操作完成。")

    @Slot(result=list)
    def getDeletedFiles(self):
        result = []
        for recycle_name, original_path in self.deleted_files_map.items():
            result.append({
                "recycleName": recycle_name,
                "originalPath": original_path
            })
        return result

    @Slot(list, bool, str)
    def restoreFiles(self, recycle_names, to_original, restore_path):
        import urllib.parse
        if restore_path.startswith("file:///"):
            restore_path = restore_path[8:]
        restore_path = os.path.normpath(urllib.parse.unquote(restore_path))

        restored_count = 0
        for recycle_name in recycle_names:
            if recycle_name not in self.deleted_files_map:
                continue
            src_path = os.path.join(self.app_recycle_bin, recycle_name)
            if to_original:
                dest_path = self.deleted_files_map[recycle_name]
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            else:
                original_filename = os.path.basename(
                    self.deleted_files_map[recycle_name])
                dest_path = os.path.join(restore_path, original_filename)
            try:
                shutil.move(src_path, dest_path)
                self.logMessage.emit(
                    f"[恢复成功] {recycle_name} -> {dest_path}")
                del self.deleted_files_map[recycle_name]
                restored_count += 1
            except Exception as e:
                self.logMessage.emit(
                    f"[恢复失败] 无法移动 {recycle_name}: {e}")

        self.operationFinished.emit(f"成功恢复 {restored_count} 个文件。")
