# -*- coding: utf-8 -*-
import os
import sys
import winreg
from datetime import datetime
import pandas as pd
from PySide6.QtCore import QObject, Slot, Signal

# ================= 数据映射 (业务核心，原样保留) =================
SMART_STD_MAPPING = {
    "上衣": "GB/T 22849-2024",
    "裤子": "FZ/T 81007-2022",
    "卫衣": "FZ/T 73020-2019",
    "外套": "FZ/T 81008-2021",
    "裙子": "FZ/T 81007-2022"
}

STD_MAPPING = {
    "卫衣": "FZ/T 73020-2019", "裤子": "FZ/T 81007-2022",
    "棉服": "GB/T 2662-2017", "T恤": "GB/T 22849-2024",
    "夹克": "FZ/T 81008-2021", "防晒衣": "GB/T 18830-2009",
    "牛仔裤": "FZ/T 81006-2017", "毛衣": "FZ/T 73005-2021"
}

SIZE_MAPPING = {
    "M-3XL": ["M", "L", "XL", "2XL", "3XL"],
    "M-4XL": ["M", "L", "XL", "2XL", "3XL", "4XL"],
    "29-36": ["29", "30", "31", "32", "33", "34", "36"],
    "29-35-36": ["29", "30", "31", "32", "33", "34", "35", "36"],
    "29-38": ["29", "30", "31", "32", "33", "34", "36", "38"]
}

COLOR_PRESETS = ["白色", "黑色", "卡其色", "杏色", "红色", "蓝色", "绿色", "灰色"]


class ProductMatrixBackend(QObject):
    logMessage = Signal(str)
    queueChanged = Signal()
    generateFinished = Signal(str)
    generateError = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_queue = []

    @Slot(result=list)
    def getSizeOptions(self):
        return list(SIZE_MAPPING.keys())

    @Slot(result=list)
    def getAbbrOptions(self):
        return ["上衣", "裤子", "卫衣", "外套", "裙子"]

    @Slot(result=list)
    def getStdQuickOptions(self):
        return list(STD_MAPPING.keys())

    @Slot(result=list)
    def getColorPresets(self):
        return COLOR_PRESETS

    @Slot(str, result=str)
    def getSmartStd(self, abbr):
        return SMART_STD_MAPPING.get(abbr, "")

    @Slot(str, result=str)
    def getStdByQuick(self, quick):
        return STD_MAPPING.get(quick, "")

    @Slot(result=str)
    def getDefaultExportPath(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            path, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            return os.path.expandvars(path)
        except Exception:
            return os.path.expanduser("~/Desktop")

    @Slot(str, list, str, str, str, str, str, str, str)
    def addToQueue(self, main_code, colors, size_option, abbr,
                   unit, origin, comp, std, supplier):
        if not main_code:
            self.logMessage.emit("[警告] 主商家编码不能为空！")
            return
        if not colors:
            self.logMessage.emit("[警告] 请至少添加一个颜色！")
            return

        snapshot = {
            "main_code": main_code,
            "colors": list(colors),
            "size_option": size_option,
            "abbr": abbr,
            "unit": unit,
            "origin": origin,
            "comp": comp,
            "std": std,
            "supplier": supplier
        }
        self.task_queue.append(snapshot)
        self.queueChanged.emit()
        time_str = datetime.now().strftime("%H:%M:%S")
        self.logMessage.emit(f"[{time_str}] 已生成快照并入队: {main_code}")

    @Slot(int)
    def deleteFromQueue(self, index):
        if 0 <= index < len(self.task_queue):
            self.task_queue.pop(index)
            self.queueChanged.emit()
            self.logMessage.emit("已移除选中项。")

    @Slot(result=list)
    def getQueue(self):
        result = []
        for task in self.task_queue:
            result.append({
                "mainCode": task["main_code"],
                "colors": "、".join(task["colors"]),
                "sizeOption": task["size_option"],
                "std": task["std"]
            })
        return result

    @Slot(str)
    def generateExcel(self, out_path):
        if not self.task_queue:
            self.generateError.emit("队列为空，请先录入商品！")
            return
        if not os.path.isdir(out_path):
            self.generateError.emit("输出目录无效！")
            return

        data_rows = []
        for task in self.task_queue:
            sizes = SIZE_MAPPING.get(task["size_option"], [task["size_option"]])
            colors = task["colors"]
            for color in colors:
                for size in sizes:
                    row = {
                        "主商家编码": task["main_code"],
                        "商品名称": task["main_code"],
                        "是否含SKU": "是",
                        "规格商家编码": f"{task['main_code']}-{color}-{size}",
                        "颜色属性": color,
                        "第二属性": size,
                        "商品简称": task["abbr"],
                        "商品基本单位": task["unit"],
                        "产地": task["origin"],
                        "成份": task["comp"],
                        "执行标准": task["std"],
                        "商品安全类别": "G18401-2010（B类）",
                        "供应商名称": task["supplier"]
                    }
                    data_rows.append(row)

        try:
            df = pd.DataFrame(data_rows)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"zzz导入模板_{timestamp}.xlsx"
            full_path = os.path.join(out_path, filename)
            df.to_excel(full_path, index=False, engine='openpyxl')
            time_str = datetime.now().strftime("%H:%M:%S")
            self.logMessage.emit(
                f"[{time_str}] 成功导出: {filename} (共{len(data_rows)}行)")
            self.generateFinished.emit(
                f"已成功生成数据表！\n路径：{full_path}")
        except Exception as e:
            self.generateError.emit(f"生成Excel时遇到错误：\n{str(e)}")
