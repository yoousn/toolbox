# -*- coding: utf-8 -*-
import os
import ctypes
import shutil
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QThread

from .settings_store import settings


class VideoProcessWorker(QThread):
    logSignal = Signal(str)
    progressSignal = Signal(int, int)
    finishedSignal = Signal(str)
    errorSignal = Signal(str)

    def __init__(self, root_dir, file_format, mode, first_only=False):
        super().__init__()
        self.root_dir = root_dir
        self.file_format = file_format
        self.mode = mode
        self.first_only = first_only

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

                # 只选第一个视频
                if self.first_only and len(video_files) > 1:
                    video_files = [video_files[0]]

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


# ============================================================
# 视频清理 Worker — 扫描/回收站删除
# ============================================================
class VideoCleanupWorker(QThread):
    """扫描目录下所有视频文件，或将它们移至 Windows 回收站。"""

    VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}

    logSignal = Signal(str)
    progressSignal = Signal(int, int)
    finishedSignal = Signal(str)
    errorSignal = Signal(str)
    scanSummary = Signal(int, str)  # file_count, total_size_str

    def __init__(self, root_dir, mode='scan'):
        super().__init__()
        self.root_dir = root_dir
        self.mode = mode  # 'scan' or 'delete'

    def run(self):
        try:
            root_path = Path(self.root_dir)
            if not root_path.is_dir():
                raise ValueError("无效的目录路径！")

            self.logSignal.emit("🔍 正在扫描「所有XXX」类文件夹中的视频文件 ...")
            self.logSignal.emit(f"📁 目录: {self.root_dir}")
            self.logSignal.emit("📎 仅扫描由「提取副本」功能生成的文件夹 (所有MOV, 所有MP4 ...)")

            found: list[tuple[str, int]] = []
            total_size = 0

            # 递归扫描所有子目录，寻找名称以"所有"开头的文件夹
            for dirpath, dirnames, fnames in os.walk(self.root_dir):
                dirname = os.path.basename(dirpath)
                # 根目录本身如果叫"所有XXX"也会被处理
                if dirpath != self.root_dir and not dirname.startswith("所有"):
                    # 但是如果连同根目录一起传进来，根目录不是"所有"开头，那就看其下的子目录
                    # wait, os.path.basename of root_dir might not start with "所有"
                    # We only care about the current directory being processed.
                    if not dirname.startswith("所有"):
                        continue
                elif dirpath == self.root_dir and not os.path.basename(os.path.normpath(self.root_dir)).startswith("所有"):
                    # 根目录不满足条件，跳过处理根目录的文件，但继续遍历子目录
                    pass

                # If the current dirpath represents a "所有" folder
                # If the current dirpath represents a "所有" folder
                if os.path.basename(os.path.normpath(dirpath)).startswith("所有"):
                    folder_video_count = 0
                    folder_video_size = 0
                    non_videos = []

                    for fname in fnames:
                        fpath = os.path.join(dirpath, fname)
                        if os.path.splitext(fname)[1].lower() in self.VIDEO_EXTS:
                            try:
                                sz = os.path.getsize(fpath)
                            except OSError:
                                sz = 0
                            found.append((fpath, sz))
                            total_size += sz
                            folder_video_count += 1
                            folder_video_size += sz
                        else:
                            # 忽略一些常见的系统隐藏文件
                            if fname.lower() not in ['desktop.ini', '.ds_store', 'thumbs.db']:
                                non_videos.append(fname)

                    if folder_video_count > 0 or non_videos:
                        rel_folder = os.path.relpath(dirpath, self.root_dir)
                        if rel_folder == ".": 
                            rel_folder = os.path.basename(os.path.normpath(dirpath))
                        
                        folder_info = f"\n📂 {rel_folder}/"
                        if folder_video_count > 0:
                            folder_info += f"  (含 {folder_video_count} 个视频, {_fmt_size(folder_video_size)})"
                        self.logSignal.emit(folder_info)

                        for nv in non_videos:
                            self.logSignal.emit(f"  ⚠️ 非视频文件: {nv}")

            count = len(found)
            size_str = _fmt_size(total_size)

            if count == 0:
                self.finishedSignal.emit("✅ 未找到「所有XXX」文件夹中的视频文件。")
                return

            self.logSignal.emit(f"\n📊 共发现 {count} 个视频文件，总占用 {size_str}")
            self.scanSummary.emit(count, size_str)

            if self.mode == 'scan':
                self.finishedSignal.emit(
                    f"扫描完成: {count} 个文件, 总计 {size_str}")
                return

            # ---- 删除模式 ----
            self.logSignal.emit("\n🗑️ 正在移至 Windows 回收站 ...")
            ok = 0
            fail = 0
            freed = 0

            for i, (fp, sz) in enumerate(found):
                self.progressSignal.emit(i + 1, count)
                try:
                    if _send_to_recycle_bin(fp):
                        ok += 1
                        freed += sz
                    else:
                        self.logSignal.emit(f"  ❌ {os.path.basename(fp)}")
                        fail += 1
                except Exception as e:
                    self.logSignal.emit(
                        f"  ❌ {os.path.basename(fp)}: {e}")
                    fail += 1

            self.progressSignal.emit(count, count)
            self.finishedSignal.emit(
                f"✨ 清理完成: 成功 {ok} 个, 失败 {fail} 个, "
                f"释放 {_fmt_size(freed)}")

        except Exception as e:
            self.errorSignal.emit(str(e))


# ============================================================
# Windows 回收站工具函数
# ============================================================
class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("wFunc", ctypes.c_uint),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", ctypes.c_bool),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]


def _send_to_recycle_bin(path: str) -> bool:
    """通过 Windows Shell API 将文件移至回收站(可撤销)。"""
    abs_path = os.path.abspath(path)
    file_from = abs_path + '\0'   # 双 null 终止
    op = _SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = 3          # FO_DELETE
    op.pFrom = file_from
    op.pTo = None
    # FOF_ALLOWUNDO(0x40) | FOF_NOCONFIRMATION(0x10) | FOF_SILENT(0x04)
    op.fFlags = 0x0054
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return result == 0


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


# ============================================================
# 暴露给 QML 的后端
# ============================================================
class VideoProcessorBackend(QObject):
    logMessage = Signal(str)
    progressUpdated = Signal(int, int)
    taskFinished = Signal(str)
    taskError = Signal(str)
    busyChanged = Signal()
    # 清理专用信号
    scanSummary = Signal(int, str)   # count, size_str

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._cleanup_worker = None
        self._busy = False
        self._default_dir = settings.get("video_processor.default_dir", "D:\\1上款")

    @Slot(result=bool)
    def isBusy(self):
        return self._busy

    @Slot(result=str)
    def getDefaultDir(self):
        return self._default_dir

    @Slot(str)
    def rememberDefaultDir(self, root_dir):
        root_dir = _clean_path(root_dir)
        if root_dir:
            self._default_dir = root_dir
            settings.set("video_processor.default_dir", root_dir)

    @Slot(str, str, str, bool)
    def startTask(self, root_dir, file_format, mode, first_only=False):
        if self._busy:
            return
        root_dir = _clean_path(root_dir)

        if not root_dir or not os.path.isdir(root_dir):
            self.logMessage.emit("请选择有效的文件夹路径！")
            return
        self.rememberDefaultDir(root_dir)

        self._busy = True
        self.busyChanged.emit()

        self._worker = VideoProcessWorker(root_dir, file_format, mode, first_only)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.progressSignal.connect(self.progressUpdated.emit)
        self._worker.finishedSignal.connect(self._on_finished)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.start()

    # ---- 视频清理 ----
    @Slot(str)
    def scanVideos(self, root_dir):
        """扫描目录下所有视频文件(不删除)。"""
        self._start_cleanup(root_dir, 'scan')

    @Slot(str)
    def cleanupVideos(self, root_dir):
        """扫描并移至回收站。"""
        self._start_cleanup(root_dir, 'delete')

    def _start_cleanup(self, root_dir, mode):
        if self._busy:
            return
        root_dir = _clean_path(root_dir)
        if not root_dir or not os.path.isdir(root_dir):
            self.logMessage.emit("请选择有效的文件夹路径！")
            return
        self.rememberDefaultDir(root_dir)

        self._busy = True
        self.busyChanged.emit()

        self._cleanup_worker = VideoCleanupWorker(root_dir, mode)
        self._cleanup_worker.logSignal.connect(self.logMessage.emit)
        self._cleanup_worker.progressSignal.connect(
            self.progressUpdated.emit)
        self._cleanup_worker.finishedSignal.connect(self._on_finished)
        self._cleanup_worker.errorSignal.connect(self._on_error)
        self._cleanup_worker.scanSummary.connect(self.scanSummary.emit)
        self._cleanup_worker.start()

    def _on_finished(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.taskFinished.emit(msg)

    def _on_error(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.taskError.emit(msg)


def _clean_path(path: str) -> str:
    import urllib.parse
    path = str(path or "")
    if path.startswith("file:///"):
        path = path[8:]
    return os.path.normpath(urllib.parse.unquote(path)) if path else ""
