# -*- coding: utf-8 -*-
import os
import re
import shutil
from PySide6.QtCore import QObject, Slot, Signal, QThread

from .settings_store import settings


class SizeMatchWorker(QThread):
    logSignal = Signal(str)
    finishedSignal = Signal(int, int)  # 成功数, 未匹配数

    def __init__(self, size_chart_dir, target_root_dir):
        super().__init__()
        self.size_chart_dir = size_chart_dir
        self.target_root_dir = target_root_dir

    def _extract_code(self, name):
        """从文件名或文件夹名中提取货号。\n        支持: A180黑 -> A180, A201.jpg -> A201, 29-36.png -> 29-36\n        规则: 匹配开头的一段字母数字或纯数字/连字符组合。"""
        name = os.path.splitext(name)[0]  # 去掉扩展名
        # 先尝试匹配开头的大写字母+数字组合 (如 A180, A8806, 飞8603)
        m = re.match(r"([A-Za-z]?\d+[A-Za-z]?\d*)", name)
        if m:
            return m.group(1).upper()
        # 再尝试匹配纯数字/连字符组合 (如 29-36)
        m = re.match(r"([\d\-]+)", name)
        if m:
            return m.group(1)
        return ""

    def run(self):
        self.logSignal.emit("-" * 40)
        self.logSignal.emit("开始尺码表自动匹配...")
        self.logSignal.emit(f"尺码表目录: {self.size_chart_dir}")
        self.logSignal.emit(f"目标主目录: {self.target_root_dir}")

        if not os.path.isdir(self.size_chart_dir):
            self.logSignal.emit("[错误] 尺码表目录不存在！")
            self.finishedSignal.emit(0, 0)
            return
        if not os.path.isdir(self.target_root_dir):
            self.logSignal.emit("[错误] 目标目录不存在！")
            self.finishedSignal.emit(0, 0)
            return

        # 扫描尺码表目录,建立 货号 -> 图片文件路径 映射
        size_chart_map = {}
        for fname in os.listdir(self.size_chart_dir):
            fpath = os.path.join(self.size_chart_dir, fname)
            if not os.path.isfile(fpath):
                continue
            code = self._extract_code(fname)
            if not code:
                continue
            # 如果同一货号有多张,优先保留 jpg/png,跳过后续同名冲突
            if code not in size_chart_map:
                size_chart_map[code] = fpath
                self.logSignal.emit(f"[尺码表] {code} -> {fname}")

        self.logSignal.emit(f"共扫描到 {len(size_chart_map)} 张可识别尺码表")

        # 扫描目标目录下所有子文件夹
        success_count = 0
        unmatched_folders = []

        for folder_name in sorted(os.listdir(self.target_root_dir)):
            folder_path = os.path.join(self.target_root_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            code = self._extract_code(folder_name)
            if not code:
                self.logSignal.emit(f"[跳过] 无法识别货号: {folder_name}")
                continue

            if code in size_chart_map:
                src_path = size_chart_map[code]
                ext = os.path.splitext(src_path)[1]
                # 复制到子文件夹内,保留原文件名
                dest_path = os.path.join(folder_path, os.path.basename(src_path))
                try:
                    shutil.copy2(src_path, dest_path)
                    self.logSignal.emit(f"[成功] {folder_name} <- {os.path.basename(src_path)}")
                    success_count += 1
                except Exception as e:
                    self.logSignal.emit(f"[失败] {folder_name}: {e}")
                    unmatched_folders.append(folder_name)
            else:
                self.logSignal.emit(f"[未匹配] {folder_name} (货号: {code})")
                unmatched_folders.append(folder_name)

        self.logSignal.emit("-" * 40)
        if unmatched_folders:
            self.logSignal.emit(f"未匹配文件夹共 {len(unmatched_folders)} 个:")
            for name in unmatched_folders:
                self.logSignal.emit(f"  - {name}")
        else:
            self.logSignal.emit("所有文件夹均已匹配成功！")
        self.logSignal.emit(f"匹配完成：成功 {success_count} 个，未匹配 {len(unmatched_folders)} 个")

        self.finishedSignal.emit(success_count, len(unmatched_folders))


class SizeMatcherBackend(QObject):
    logMessage = Signal(str)
    matchFinished = Signal(int, int)  # 成功数, 未匹配数
    busyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._size_chart_dir = settings.get(
            "size_matcher.size_chart_dir", "D:/1上款/尺码")
        self._target_root_dir = settings.get(
            "size_matcher.target_root_dir", "D:/1上款")
        self._worker = None
        self._busy = False

    @Slot(result=bool)
    def isBusy(self):
        return self._busy

    @Slot(result=str)
    def getSizeChartDir(self):
        if not os.path.exists(self._size_chart_dir):
            os.makedirs(self._size_chart_dir, exist_ok=True)
        return self._size_chart_dir

    @Slot(result=str)
    def getTargetRootDir(self):
        if not os.path.exists(self._target_root_dir):
            os.makedirs(self._target_root_dir, exist_ok=True)
        return self._target_root_dir

    @Slot(str)
    def setSizeChartDir(self, path):
        import urllib.parse
        if path.startswith("file:///"):
            path = path[8:]
        path = os.path.normpath(urllib.parse.unquote(path))
        if path:
            self._size_chart_dir = path
            settings.set("size_matcher.size_chart_dir", path)
            self.logMessage.emit(f"已设置尺码表目录: {path}")

    @Slot(str)
    def setTargetRootDir(self, path):
        import urllib.parse
        if path.startswith("file:///"):
            path = path[8:]
        path = os.path.normpath(urllib.parse.unquote(path))
        if path:
            self._target_root_dir = path
            settings.set("size_matcher.target_root_dir", path)
            self.logMessage.emit(f"已设置目标目录: {path}")

    @Slot()
    def startMatch(self):
        if self._busy:
            return
        if not os.path.isdir(self._size_chart_dir):
            self.logMessage.emit("[警告] 请先选择尺码表目录！")
            self.matchFinished.emit(0, 0)
            return
        if not os.path.isdir(self._target_root_dir):
            self.logMessage.emit("[警告] 请先选择目标文件夹主目录！")
            self.matchFinished.emit(0, 0)
            return

        self._busy = True
        self.busyChanged.emit()
        self._worker = SizeMatchWorker(self._size_chart_dir, self._target_root_dir)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.finishedSignal.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success, unmatched):
        self._busy = False
        self._worker = None
        self.busyChanged.emit()
        self.matchFinished.emit(success, unmatched)
