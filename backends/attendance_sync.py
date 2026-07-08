# -*- coding: utf-8 -*-
import os
import re
import random
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Signal, QThread, Property

from .settings_store import settings


class AttendanceSyncWorker(QThread):
    logSignal = Signal(str)
    finishedSignal = Signal(str)
    errorSignal = Signal(str)
    syncDataReady = Signal(str)  # JSON: {day: {"in": "..", "out": "..", "modified": true/false}, ...}

    def __init__(self, file_path, settings=None):
        super().__init__()
        self.file_path = file_path
        self.settings = settings or {}

    def run(self):
        app = None
        wb = None
        try:
            import xlwings as xw
            import urllib.parse
            import pythoncom
            import gc
            pythoncom.CoInitialize()

            # URL 解码并格式化路径，解决中文与空格导致打不开 Excel 的致命 Bug
            file_path = os.path.normpath(urllib.parse.unquote(self.file_path))
            
            # 工作表保护密码
            password = "AAAABBAABBBO"

            self.logSignal.emit("正在启动考勤 5.0 终极同步流程...")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.errorSignal.emit(f"错误: 文件不存在 - {file_path}")
                return

            # 检查文件是否被占用（用 r+ 模式更可靠地检测 Excel 锁定）
            try:
                with open(file_path, 'r+b'):
                    pass
            except PermissionError:
                self.errorSignal.emit(f"OCCUPIED|{file_path}")
                return

            # 使用专用 Excel 实例，避免与已有 Excel 冲突
            self.logSignal.emit("正在启动 Excel 实例...")
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False    # 禁用警告弹窗，防止卡死
            app.calculation = 'manual'    # 手动计算，提升性能

            self.logSignal.emit(f"正在打开文件: {file_path}")
            wb = app.books.open(file_path)

            self.logSignal.emit("正在访问【考勤记录】工作表...")
            sheet1 = wb.sheets["考勤记录"]
            if sheet1.api.ProtectContents:
                try:
                    sheet1.api.Unprotect(password)
                except Exception as e:
                    self.errorSignal.emit(f"错误: 无法解除【考勤记录】工作表保护，请检查密码是否正确 - {e}")
                    return

            sync_data = {}
            s = self.settings
            # 防御性下限保护：避免 0 值导致死循环
            same_time_limit = max(1, s.get('same_time_limit', 2))
            late_mode = s.get('late_mode', 0)  # 0=随机上限, 1=指定次数
            late_limit = max(0, s.get('late_limit', 5))
            late_count = max(0, s.get('late_count', 5))
            state = {'used_times': {}, 'late_over_20': 0}

            # 概率参数 + 自动按比例分配
            raw_p = [s.get('noon_p1', 40),
                     s.get('noon_p2', 40),
                     s.get('noon_p3', 20)]
            # 过滤掉为0的区间，剩余按比例扩展到100
            total = sum(raw_p)
            if total > 0:
                noon_probs = [round(p / total * 100) for p in raw_p]
            else:
                noon_probs = [34, 33, 33]
            # 修正舍入误差
            noon_probs[0] += 100 - sum(noon_probs)

            # 防御性参数处理：若 out_range 被用户设为 0，用 max(1, out_range) 规避崩溃
            # 同时加上限保护，避免生成非法时间字符串（如 21:60）
            noon_out_range = min(59, max(1, s.get('noon_out_range', 5)))
            morning_out_range = min(29, max(1, s.get('morning_out_range', 5)))
            night_out_range = min(59, max(1, s.get('night_out_range', 5)))

            raw_mp = [s.get('morning_p1', 80),
                      s.get('morning_p2', 20)]
            total_mp = sum(raw_mp)
            if total_mp > 0:
                morning_probs = [round(p / total_mp * 100) for p in raw_mp]
            else:
                morning_probs = [50, 50]
            morning_probs[0] += 100 - sum(morning_probs)

            self.logSignal.emit(
                f"参数: 中班 {noon_probs[0]}/{noon_probs[1]}/"
                f"{noon_probs[2]}%  "
                f"早班 {morning_probs[0]}/{morning_probs[1]}%  "
                f"迟到{'指定'+str(late_count)+'次' if late_mode==1 else '上限'+str(late_limit)+'次'}")

            def time_to_mins(t_str):
                h, m = map(int, t_str.split(':'))
                return h * 60 + m

            def generate_new_times(shift, force_late=None):
                max_attempts = 2000  # 最大尝试次数，防止死循环
                attempts = 0
                while True:
                    attempts += 1
                    if attempts > max_attempts:
                        # 兜底：返回一个简单时间，避免卡死
                        if shift == 'morning':
                            return "07:45", f"16:{30 + random.randint(1, min(morning_out_range, 29)):02d}"
                        elif shift == 'noon':
                            return "12:05", f"21:{random.randint(1, noon_out_range):02d}"
                        else:
                            return "15:20", f"00:{random.randint(1, night_out_range):02d}"
                    is_late_over_20 = False
                    if shift == 'morning':
                        if force_late is True:
                            # 强制迟到：51~60 分
                            m = random.randint(51, 60)
                            h = 8 if m == 60 else 7
                            m = 0 if m == 60 else m
                        elif force_late is False:
                            # 强制不迟到：39~50 分
                            h, m = 7, random.randint(39, 50)
                        else:
                            # 随机模式
                            if random.randint(1, 100) <= morning_probs[0]:
                                h, m = 7, random.randint(39, 50)
                            else:
                                m = random.randint(51, 60)
                                h = 8 if m == 60 else 7
                                m = 0 if m == 60 else m
                        
                        if h == 8 or (h == 7 and m > 50):
                            is_late_over_20 = True

                    elif shift == 'noon':
                        if force_late is True:
                            # 强制迟到：21~30 分
                            h, m = 12, random.randint(21, 30)
                        elif force_late is False:
                            # 强制不迟到：2~20 分
                            p0 = noon_probs[0]
                            p1 = noon_probs[1]
                            total_p = p0 + p1
                            if total_p > 0 and random.randint(1, total_p) <= p0:
                                if raw_p[0] == 0:
                                    h, m = 12, random.randint(10, 20)
                                else:
                                    h, m = 12, random.randint(2, 9)
                            else:
                                h, m = 12, random.randint(10, 20)
                        else:
                            # 随机模式
                            r = random.randint(1, 100)
                            if r <= noon_probs[0]:
                                if raw_p[0] == 0:
                                    h, m = 12, random.randint(10, 19)
                                else:
                                    h, m = 12, random.randint(2, 9)
                            elif r <= noon_probs[0] + noon_probs[1]:
                                h, m = 12, random.randint(10, 19)
                            else:
                                h, m = 12, random.randint(20, 30)
                        
                        if m > 20:
                            is_late_over_20 = True

                    elif shift == 'night':
                        if random.random() < 0.8:
                            h, m = 15, random.randint(15, 40)
                        else:
                            h, m = 15, random.randint(5, 50)

                    time_str = f"{h:02d}:{m:02d}"
                    if state['used_times'].get(time_str, 0) \
                            >= same_time_limit:
                        continue
                    
                    if shift != 'night':
                        if force_late is None and late_mode == 0:
                            if is_late_over_20 and state['late_over_20'] >= late_limit:
                                continue

                    state['used_times'][time_str] = \
                        state['used_times'].get(time_str, 0) + 1
                    if is_late_over_20 and shift != 'night':
                        state['late_over_20'] += 1

                    if shift == 'morning':
                        out_time = f"16:{30 + random.randint(1, min(morning_out_range, 29)):02d}"
                    elif shift == 'noon':
                        out_time = f"21:{random.randint(1, noon_out_range):02d}"
                    elif shift == 'night':
                        out_time = f"00:{random.randint(1, night_out_range):02d}"

                    return time_str, out_time

            # --- 步骤1: 两阶段精准分配 ---
            # 阶段 A：扫描所有日期，识别班次及过滤特殊班次
            day_shifts = {}
            skipped_days = []
            special_days = set()

            for col in range(1, 32):
                cell = sheet1.range((6, col))
                val = cell.value
                if not val:
                    continue
                times = re.findall(r"(\d{1,2}:\d{2})", str(val))
                if len(times) >= 2:
                    in_time = times[0]
                    out_time = times[-1]
                    t_in = time_to_mins(in_time)
                    t_out = time_to_mins(out_time)
                    if t_out < t_in:
                        t_out += 24 * 60

                    # 识别特殊班次并跳过
                    if ((9*60 <= t_in <= 11*60+30) and
                            (17*60 <= t_out <= 20*60)):
                        special_days.add(col)
                        continue

                    shift = None
                    if (((t_in >= 14*60) or
                         (12*60 <= t_in <= 13*60+59)) and
                            (20*60 <= t_out <= 21*60+20)):
                        shift = 'noon'
                    elif ((t_in >= 14*60) and
                          (t_out >= 23*60+55)):
                        shift = 'night'
                    elif (in_time.startswith("07") or
                          in_time.startswith("08")):
                        shift = 'morning'

                    if shift:
                        day_shifts[col] = shift
                    else:
                        skipped_days.append(
                            f"第{col}号[{in_time}-{out_time}]")

            # 阶段 B：如果为“指定次数”模式，确定需要强制迟到的天数
            late_days = set()
            if late_mode == 1:
                eligible_days = [c for c, sh in day_shifts.items() if sh in ('morning', 'noon')]
                late_days = set(random.sample(eligible_days, min(late_count, len(eligible_days))))

            # 阶段 C：依次生成打卡时间并写入单元格
            for col in sorted(day_shifts.keys()):
                shift = day_shifts[col]
                force_late = None
                if late_mode == 1:
                    force_late = (col in late_days)

                new_in, new_out = generate_new_times(shift, force_late)
                cell = sheet1.range((6, col))
                cell.number_format = '@'
                cell.value = f"{new_in}\n{new_out}"
                cell.api.WrapText = True
                sync_data[col] = (new_in, new_out)

            # 打印特殊班次跳过日志
            for col in sorted(special_days):
                cell = sheet1.range((6, col))
                val = cell.value
                times = re.findall(r"(\d{1,2}:\d{2})", str(val))
                in_time = times[0]
                out_time = times[-1]
                self.logSignal.emit(
                    f"⚠️ 特殊班次: 第【{col}】号 "
                    f"[{in_time} - {out_time}]，已跳过")

            if sheet1.api.ProtectContents == False:
                try:
                    sheet1.api.Protect(password)
                except Exception as e:
                    self.logSignal.emit(f"⚠️ 重新保护【考勤记录】失败: {e}")
            self.logSignal.emit(
                f"1.【考勤记录】修改完成，已抓取 {len(sync_data)} 组数据。"
                f"迟到20分: {state['late_over_20']}/{late_limit}")
            if skipped_days:
                self.logSignal.emit(
                    f"⚠️ 未识别班次，跳过 {len(skipped_days)} 天: "
                    f"{', '.join(skipped_days)}")

            # --- 步骤2: 同步异常统计 (按日期+姓名匹配行) ---
            if "异常统计" in [s.name for s in wb.sheets]:
                sheet2 = wb.sheets["异常统计"]
                if sheet2.api.ProtectContents:
                    try:
                        sheet2.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【异常统计】保护: {e}")
                # 建立日期→行号映射 (只匹配梁汝华的行)
                updated_count = 0
                for row in range(5, 200):
                    b_val = sheet2.range(f"B{row}").value
                    if not b_val:
                        self.logSignal.emit(f"   异常统计扫描到第 {row} 行遇到空行，停止扫描（休息日无数据属正常）")
                        break  # 空行 = 数据结束
                    if "梁汝华" not in str(b_val):
                        continue
                    d_raw = sheet2.range(f"D{row}").value
                    # 从日期中提取日号：支持 datetime 对象、字符串 "2026-04-06"、"2026-04-06 00:00:00"
                    day = None
                    if hasattr(d_raw, 'day') and hasattr(d_raw, 'month'):
                        # datetime/date 对象
                        day = d_raw.day
                    elif d_raw:
                        d_val = str(d_raw).strip()
                        # 匹配末尾的 "-日号" 或 "/日号"（兼容各种日期格式）
                        m = re.search(r"[-/](\d{1,2})(?:\s|$)", d_val)
                        if m:
                            day = int(m.group(1))
                    if day is None or day not in sync_data:
                        continue
                    new_in, new_out = sync_data[day]
                    for col_name, val in [('E', new_in),
                                          ('F', new_out)]:
                        cell = sheet2.range(f"{col_name}{row}")
                        cell.number_format = '@'
                        cell.value = val
                    updated_count += 1
                if sheet2.api.ProtectContents == False:
                    try:
                        sheet2.api.Protect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 重新保护【异常统计】失败: {e}")
                self.logSignal.emit(
                    f"2.【异常统计】已同步更新 {updated_count} 条。")

            # --- 步骤3: 同步考勤卡表 (动态查找表名和梁汝华位置) ---
            sheet_names = [s.name for s in wb.sheets]
            # 查找 X.Y.Z 格式的考勤卡表名
            card_sheet_name = None
            for sn in sheet_names:
                if re.match(r"\d+\.\d+\.\d+", sn):
                    card_sheet_name = sn
                    break
            if card_sheet_name:
                sheet3 = wb.sheets[card_sheet_name]
                if sheet3.api.ProtectContents:
                    try:
                        sheet3.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【{card_sheet_name}】保护: {e}")
                # 在 Row 3 搜索梁汝华的位置，确定列偏移
                in_col_idx = None
                out_col_idx = None
                for col_idx in range(1, 60):
                    val = sheet3.range((3, col_idx)).value
                    if val and "梁汝华" in str(val):
                        # 找到姓名所在列，往回找"上班"/"下班"标签
                        # 根据分析: 姓名在 J(10)/Y(25) 列
                        # 上班列在 B(2)/Q(17) 列, 下班列在 D(4)/S(19)
                        # 规律: 上班列 = 姓名列 - 8, 下班列 = 姓名列 - 6
                        # 验证: J=10, B=2(10-8=2 ok), D=4(10-6=4 ok)
                        #        Y=25, Q=17(25-8=17 ok), S=19(25-6=19 ok)
                        in_col_idx = col_idx - 8
                        out_col_idx = col_idx - 6
                        self.logSignal.emit(
                            f"   在【{card_sheet_name}】找到梁汝华"
                            f" (Col {col_idx})")
                        break
                if in_col_idx and out_col_idx:
                    # 加班时段列（星期六日数据应写入此区域）
                    # 姓名=col_idx, 签到=col_idx+1 (K), 签退=col_idx+3 (M)
                    overtime_in_col = col_idx + 1
                    overtime_out_col = col_idx + 3
                    weekend_count = 0
                    weekday_count = 0
                    weekend_cleared = 0
                    for day_idx in range(1, 32):
                        row = 11 + day_idx
                        # 读取星期信息（第1列格式如 "13 六"、"07 日"）
                        day_label = sheet3.range((row, 1)).value
                        is_weekend = bool(day_label and ("六" in str(day_label) or "日" in str(day_label)))
                        if is_weekend:
                            # 周末：清空第一时段列（避免旧数据残留），数据写入加班时段
                            for c_idx in (in_col_idx, out_col_idx):
                                clear_cell = sheet3.range((row, c_idx))
                                if clear_cell.value:
                                    clear_cell.value = None
                                    weekend_cleared += 1
                            if day_idx in sync_data:
                                new_in, new_out = sync_data[day_idx]
                                for c_idx, val in [(overtime_in_col, new_in),
                                                   (overtime_out_col, new_out)]:
                                    target = sheet3.range((row, c_idx))
                                    target.number_format = '@'
                                    target.value = val
                                    target.api.HorizontalAlignment = -4108
                                weekend_count += 1
                        else:
                            if day_idx in sync_data:
                                new_in, new_out = sync_data[day_idx]
                                for c_idx, val in [(in_col_idx, new_in),
                                                   (out_col_idx, new_out)]:
                                    target = sheet3.range((row, c_idx))
                                    target.number_format = '@'
                                    target.value = val
                                    target.api.HorizontalAlignment = -4108
                                weekday_count += 1
                    if sheet3.api.ProtectContents == False:
                        try:
                            sheet3.api.Protect(password)
                        except Exception as e:
                            self.logSignal.emit(f"⚠️ 重新保护【{card_sheet_name}】失败: {e}")
                    self.logSignal.emit(
                        f"3.【{card_sheet_name}】梁汝华考勤卡已同步"
                        f"（工作日{weekday_count}天→第一时段，"
                        f"周末{weekend_count}天→加班时段，"
                        f"清理周末第一时段旧数据{weekend_cleared}格）。")
                else:
                    if sheet3.api.ProtectContents == False:
                        try:
                            sheet3.api.Protect(password)
                        except Exception as e:
                            self.logSignal.emit(f"⚠️ 重新保护【{card_sheet_name}】失败: {e}")
                    self.logSignal.emit(
                        f"⚠️【{card_sheet_name}】未找到梁汝华，跳过。")
            else:
                self.logSignal.emit("⚠️ 未找到考勤卡表，已跳过。")

            # --- 步骤4: 更新制表时间 ---
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 4a. 考勤记录 L3 → 制表时间
            if sheet1.api.ProtectContents:
                try:
                    sheet1.api.Unprotect(password)
                except Exception as e:
                    self.logSignal.emit(f"⚠️ 无法解除【考勤记录】保护来更新制表时间: {e}")
            sheet1.range("L3").number_format = '@'
            sheet1.range("L3").value = today_str
            if sheet1.api.ProtectContents == False:
                try:
                    sheet1.api.Protect(password)
                except Exception as e:
                    self.logSignal.emit(f"⚠️ 重新保护【考勤记录】失败: {e}")
            self.logSignal.emit(
                f"4a.【考勤记录】L3 制表时间已更新为: {today_str}")

            # 4b. 考勤卡表 Q2 → 制表时间 (动态查找表名)
            if card_sheet_name:
                sheet_card = wb.sheets[card_sheet_name]
                if sheet_card.api.ProtectContents:
                    try:
                        sheet_card.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【{card_sheet_name}】保护来更新制表时间: {e}")
                sheet_card.range("Q2").number_format = '@'
                sheet_card.range("Q2").value = today_str
                if sheet_card.api.ProtectContents == False:
                    try:
                        sheet_card.api.Protect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 重新保护【{card_sheet_name}】失败: {e}")
                self.logSignal.emit(
                    f"4b.【{card_sheet_name}】Q2 制表时间已更新为:"
                    f" {today_str}")
            else:
                self.logSignal.emit(
                    "⚠️ 未找到考勤卡表，已跳过制表时间更新。")



            wb.save()

            # 构建面板数据：1-31 号，modified 表示是否成功生成新时间
            panel_data = {}
            for day in range(1, 32):
                if day in sync_data:
                    new_in, new_out = sync_data[day]
                    panel_data[str(day)] = {"in": new_in, "out": new_out, "modified": True}
                else:
                    # 保留原始时间（如果单元格有内容）
                    cell_val = sheet1.range((6, day)).value
                    times = re.findall(r"(\d{1,2}:\d{2})", str(cell_val)) if cell_val else []
                    if len(times) >= 2:
                        panel_data[str(day)] = {"in": times[0], "out": times[-1], "modified": False}
                    else:
                        panel_data[str(day)] = {"in": "", "out": "", "modified": False}
            import json
            self.syncDataReady.emit(json.dumps(panel_data, ensure_ascii=False))

            self.finishedSignal.emit("全部执行完毕！")

        except FileNotFoundError as e:
            self.errorSignal.emit(f"错误: 文件未找到 - {e}")
        except Exception as e:
            import traceback
            self.errorSignal.emit(f"执行过程中遇到错误: {e}\n详细信息:\n{traceback.format_exc()}")
        finally:
            try:
                if wb:
                    self.logSignal.emit("正在关闭工作簿...")
                    wb.close()
            except Exception as e:
                self.logSignal.emit(f"关闭工作簿时出错: {e}")
            try:
                if app:
                    self.logSignal.emit("正在退出 Excel 实例...")
                    app.quit()
            except Exception as e:
                self.logSignal.emit(f"退出 Excel 实例时出错: {e}")
            # 强制释放 COM 对象，避免文件锁残留
            try:
                del wb
            except Exception:
                pass
            try:
                del app
            except Exception:
                pass
            gc.collect()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


class LoadExcelWorker(QThread):
    logSignal = Signal(str)
    errorSignal = Signal(str)
    syncDataReady = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        import urllib.parse
        import xlwings as xw
        import json
        import pythoncom
        import gc
        pythoncom.CoInitialize()

        file_path = os.path.normpath(urllib.parse.unquote(self.file_path))
        app = None
        wb = None

        try:
            if not os.path.exists(file_path):
                self.errorSignal.emit(f"错误: 文件不存在 - {file_path}")
                return

            # 检查文件是否被占用（read_only 模式有时也能打开被锁文件，但 COM 残留锁可能导致失败）
            try:
                with open(file_path, 'r+b'):
                    pass
            except PermissionError:
                self.errorSignal.emit(f"OCCUPIED|{file_path}")
                return

            self.logSignal.emit("正在加载 Excel 当前数据（只读）...")
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False
            app.calculation = 'manual'
            wb = app.books.open(file_path, read_only=True)

            panel_data = {}

            # 1. 考勤记录：第6行，1-31列
            if "考勤记录" in [s.name for s in wb.sheets]:
                sheet1 = wb.sheets["考勤记录"]
                for day in range(1, 32):
                    cell_val = sheet1.range((6, day)).value
                    times = re.findall(r"(\d{1,2}:\d{2})", str(cell_val)) if cell_val else []
                    all_times = " ".join(times) if times else ""
                    # 计算工时（第一个到最后一个的时间差，小时）
                    duration = 0
                    if len(times) >= 2:
                        try:
                            h1, m1 = map(int, times[0].split(":"))
                            h2, m2 = map(int, times[-1].split(":"))
                            diff = (h2 * 60 + m2) - (h1 * 60 + m1)
                            if diff < 0:
                                diff += 24 * 60  # 跨天
                            duration = round(diff / 60, 1)
                        except Exception:
                            pass
                    panel_data[str(day)] = {
                        "in": times[0] if len(times) >= 1 else "",
                        "out": times[-1] if len(times) >= 2 else "",
                        "allTimes": all_times,
                        "timeCount": len(times),
                        "duration": duration,
                        "modified": False,
                        "sheet1": len(times) >= 1
                    }
            else:
                for day in range(1, 32):
                    panel_data[str(day)] = {"in": "", "out": "", "allTimes": "", "timeCount": 0, "duration": 0, "modified": False, "sheet1": False}

            # 2. 异常统计：按姓名+日期匹配
            if "异常统计" in [s.name for s in wb.sheets]:
                sheet2 = wb.sheets["异常统计"]
                for row in range(5, 200):
                    b_val = sheet2.range(f"B{row}").value
                    if not b_val:
                        break
                    if "梁汝华" not in str(b_val):
                        continue
                    d_raw = sheet2.range(f"D{row}").value
                    # 兼容 datetime 对象和字符串
                    day = None
                    if hasattr(d_raw, 'day') and hasattr(d_raw, 'month'):
                        day = d_raw.day
                    elif d_raw:
                        d_val = str(d_raw).strip()
                        m = re.search(r"[-/](\d{1,2})(?:\s|$)", d_val)
                        if m:
                            day = int(m.group(1))
                    if day is None or not (1 <= day <= 31):
                        continue
                    in_val = sheet2.range(f"E{row}").value
                    out_val = sheet2.range(f"F{row}").value
                    key = str(day)
                    panel_data[key]["sheet2"] = bool(in_val and out_val)
                    if not panel_data[key]["in"] and in_val:
                        panel_data[key]["in"] = str(in_val)
                    if not panel_data[key]["out"] and out_val:
                        panel_data[key]["out"] = str(out_val)

            # 3. 考勤卡表：按姓名列偏移
            card_sheet_name = None
            for sn in [s.name for s in wb.sheets]:
                if re.match(r"\d+\.\d+\.\d+", sn):
                    card_sheet_name = sn
                    break
            if card_sheet_name:
                sheet3 = wb.sheets[card_sheet_name]
                in_col_idx = None
                out_col_idx = None
                for col_idx in range(1, 60):
                    val = sheet3.range((3, col_idx)).value
                    if val and "梁汝华" in str(val):
                        in_col_idx = col_idx - 8
                        out_col_idx = col_idx - 6
                        break
                if in_col_idx and out_col_idx:
                    # 加班时段列（周末数据所在区域）
                    overtime_in_col = col_idx + 1
                    overtime_out_col = col_idx + 3
                    for day in range(1, 32):
                        row = 11 + day
                        # 读取星期信息（第1列格式如 "13 六"、"07 日"）
                        day_label = sheet3.range((row, 1)).value
                        is_weekend = bool(day_label and ("六" in str(day_label) or "日" in str(day_label)))
                        # 周末读加班时段列，工作日读第一时段列
                        if is_weekend:
                            actual_in_col = overtime_in_col
                            actual_out_col = overtime_out_col
                        else:
                            actual_in_col = in_col_idx
                            actual_out_col = out_col_idx
                        in_val = sheet3.range((row, actual_in_col)).value
                        out_val = sheet3.range((row, actual_out_col)).value
                        key = str(day)
                        panel_data[key]["sheet3"] = bool(in_val and out_val)
                        if not panel_data[key]["in"] and in_val:
                            panel_data[key]["in"] = str(in_val)
                        if not panel_data[key]["out"] and out_val:
                            panel_data[key]["out"] = str(out_val)

            self.syncDataReady.emit(json.dumps(panel_data, ensure_ascii=False))
            self.logSignal.emit("当前数据加载完成")

        except Exception as e:
            import traceback
            self.errorSignal.emit(f"加载失败: {e}\n{traceback.format_exc()}")
        finally:
            try:
                if wb:
                    wb.close()
            except Exception:
                pass
            try:
                if app:
                    app.quit()
            except Exception:
                pass
            try:
                del wb
            except Exception:
                pass
            try:
                del app
            except Exception:
                pass
            gc.collect()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


class ManualUpdateWorker(QThread):
    logSignal = Signal(str)
    errorSignal = Signal(str)
    syncDataReady = Signal(str)
    finishedSignal = Signal(str)

    def __init__(self, file_path, day, all_times_list, last_panel_data):
        super().__init__()
        self.file_path = file_path
        self.day = day
        self.all_times_list = all_times_list  # list of time strings
        self.last_panel_data = last_panel_data

    def run(self):
        import urllib.parse
        import xlwings as xw
        import json
        import pythoncom
        import gc
        pythoncom.CoInitialize()

        file_path = os.path.normpath(urllib.parse.unquote(self.file_path))
        password = "AAAABBAABBBO"
        app = None
        wb = None

        try:
            try:
                with open(file_path, 'r+b'):
                    pass
            except PermissionError:
                self.errorSignal.emit(f"OCCUPIED|{file_path}")
                return

            self.logSignal.emit(f"正在同步 {self.day} 号手动修改...")
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False
            app.calculation = 'manual'
            wb = app.books.open(file_path)

            updated_sheets = []
            skipped_sheets = []

            # 1. 考勤记录
            if "考勤记录" in [s.name for s in wb.sheets]:
                sheet1 = wb.sheets["考勤记录"]
                if sheet1.api.ProtectContents:
                    try:
                        sheet1.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【考勤记录】保护: {e}")
                try:
                    cell = sheet1.range((6, self.day))
                    if cell.value or len(self.all_times_list) > 0:
                        cell.number_format = '@'
                        cell.value = "\n".join(self.all_times_list)
                        cell.api.WrapText = True
                        updated_sheets.append("考勤记录")
                    else:
                        skipped_sheets.append("考勤记录: 该日无数据")
                except Exception as e:
                    skipped_sheets.append(f"考勤记录: {e}")
                if sheet1.api.ProtectContents == False:
                    try:
                        sheet1.api.Protect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 重新保护【考勤记录】失败: {e}")

            # 2. 异常统计
            if "异常统计" in [s.name for s in wb.sheets]:
                sheet2 = wb.sheets["异常统计"]
                if sheet2.api.ProtectContents:
                    try:
                        sheet2.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【异常统计】保护: {e}")
                try:
                    found = False
                    for row in range(5, 200):
                        b_val = sheet2.range(f"B{row}").value
                        if not b_val:
                            break
                        if "梁汝华" not in str(b_val):
                            continue
                        d_raw = sheet2.range(f"D{row}").value
                        # 兼容 datetime 对象和字符串
                        day_val = None
                        if hasattr(d_raw, 'day') and hasattr(d_raw, 'month'):
                            day_val = d_raw.day
                        elif d_raw:
                            d_val = str(d_raw).strip()
                            m = re.search(r"[-/](\d{1,2})(?:\s|$)", d_val)
                            if m:
                                day_val = int(m.group(1))
                        if day_val != self.day:
                            continue
                        first_t = self.all_times_list[0] if self.all_times_list else ""
                        last_t = self.all_times_list[-1] if len(self.all_times_list) >= 2 else ""
                        if first_t:
                            cell = sheet2.range(f"E{row}")
                            cell.number_format = '@'
                            cell.value = first_t
                        if last_t:
                            cell = sheet2.range(f"F{row}")
                            cell.number_format = '@'
                            cell.value = last_t
                        found = True
                        break
                    if found:
                        updated_sheets.append("异常统计")
                    else:
                        skipped_sheets.append("异常统计: 该日无数据")
                except Exception as e:
                    skipped_sheets.append(f"异常统计: {e}")
                if sheet2.api.ProtectContents == False:
                    try:
                        sheet2.api.Protect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 重新保护【异常统计】失败: {e}")

            # 3. 考勤卡表
            card_sheet_name = None
            for sn in [s.name for s in wb.sheets]:
                if re.match(r"\d+\.\d+\.\d+", sn):
                    card_sheet_name = sn
                    break
            if card_sheet_name:
                sheet3 = wb.sheets[card_sheet_name]
                if sheet3.api.ProtectContents:
                    try:
                        sheet3.api.Unprotect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 无法解除【{card_sheet_name}】保护: {e}")
                try:
                    in_col_idx = None
                    out_col_idx = None
                    for col_idx in range(1, 60):
                        val = sheet3.range((3, col_idx)).value
                        if val and "梁汝华" in str(val):
                            in_col_idx = col_idx - 8
                            out_col_idx = col_idx - 6
                            break
                    if in_col_idx and out_col_idx:
                        row = 11 + self.day
                        # 读取星期信息，判断是否为周末
                        day_label = sheet3.range((row, 1)).value
                        is_weekend = bool(day_label and ("六" in str(day_label) or "日" in str(day_label)))
                        # 周末写入加班时段列，工作日写入第一时段列
                        if is_weekend:
                            actual_in_col = col_idx + 1   # 签到列
                            actual_out_col = col_idx + 3   # 签退列
                        else:
                            actual_in_col = in_col_idx
                            actual_out_col = out_col_idx
                        target_in = sheet3.range((row, actual_in_col))
                        target_out = sheet3.range((row, actual_out_col))
                        if target_in.value or target_out.value or len(self.all_times_list) > 0:
                            first_t = self.all_times_list[0] if self.all_times_list else ""
                            last_t = self.all_times_list[-1] if len(self.all_times_list) >= 2 else ""
                            if first_t:
                                target_in.number_format = '@'
                                target_in.value = first_t
                                target_in.api.HorizontalAlignment = -4108
                            if last_t:
                                target_out.number_format = '@'
                                target_out.value = last_t
                                target_out.api.HorizontalAlignment = -4108
                            updated_sheets.append(card_sheet_name)
                        else:
                            skipped_sheets.append(f"{card_sheet_name}: 该日无数据")
                    else:
                        skipped_sheets.append(f"{card_sheet_name}: 未找到梁汝华")
                except Exception as e:
                    skipped_sheets.append(f"{card_sheet_name}: {e}")
                if sheet3.api.ProtectContents == False:
                    try:
                        sheet3.api.Protect(password)
                    except Exception as e:
                        self.logSignal.emit(f"⚠️ 重新保护【{card_sheet_name}】失败: {e}")

            wb.save()

            key = str(self.day)
            if key in self.last_panel_data:
                self.last_panel_data[key]["allTimes"] = " ".join(self.all_times_list)
                self.last_panel_data[key]["timeCount"] = len(self.all_times_list)
                self.last_panel_data[key]["modified"] = True
                # 重新计算工时
                if len(self.all_times_list) >= 2:
                    try:
                        h1, m1 = map(int, self.all_times_list[0].split(":"))
                        h2, m2 = map(int, self.all_times_list[-1].split(":"))
                        diff = (h2 * 60 + m2) - (h1 * 60 + m1)
                        if diff < 0:
                            diff += 24 * 60
                        self.last_panel_data[key]["duration"] = round(diff / 60, 1)
                    except Exception:
                        pass
            self.syncDataReady.emit(json.dumps(self.last_panel_data, ensure_ascii=False))

            msg = f"已更新: {', '.join(updated_sheets)}"
            if skipped_sheets:
                msg += f" | 跳过: {', '.join(skipped_sheets)}"
            self.logSignal.emit(msg)
            self.finishedSignal.emit(msg)

        except Exception as e:
            import traceback
            self.logSignal.emit(f"手动修改失败: {e}\n{traceback.format_exc()}")
            self.finishedSignal.emit(f"失败: {e}")
        finally:
            try:
                if wb:
                    wb.close()
            except Exception:
                pass
            try:
                if app:
                    app.quit()
            except Exception:
                pass
            try:
                del wb
            except Exception:
                pass
            try:
                del app
            except Exception:
                pass
            gc.collect()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


class AttendanceSyncBackend(QObject):
    logMessage = Signal(str)
    syncFinished = Signal(str)
    syncError = Signal(str)
    busyChanged = Signal()
    fileClosed = Signal(bool)
    syncDataReady = Signal(str)  # JSON
    manualUpdateFinished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._busy = False
        self._last_file_path = ""
        self._last_panel_data = {}

    @Property(bool, notify=busyChanged)
    def isBusy(self):
        """供 QML 查询当前是否忙，绑定到 enabled 属性时能自动刷新"""
        return self._busy

    @Slot(str)
    def closeExcelFile(self, file_path):
        import urllib.parse
        import gc

        file_path = os.path.normpath(urllib.parse.unquote(file_path))
        file_name = os.path.basename(file_path).lower()
        closed = False

        # 第1步：通过 xlwings 查找并关闭 Excel 实例中的工作簿
        try:
            import xlwings as xw
            apps = list(xw.apps)
            if apps:
                for app in apps:
                    try:
                        for wb in app.books:
                            try:
                                if wb.name and wb.name.lower() == file_name:
                                    self.logMessage.emit(f"找到目标文件: {wb.name}，正在关闭...")
                                    wb.close()
                                    closed = True
                                    self.logMessage.emit(f"已成功关闭: {wb.name}")
                                    break
                            except Exception:
                                continue
                        if closed:
                            try:
                                app.quit()
                            except Exception:
                                pass
                            break
                    except Exception:
                        continue
            else:
                self.logMessage.emit("未找到运行中的 Excel 实例，尝试清理 COM 对象...")
        except Exception as e:
            self.logMessage.emit(f"通过 xlwings 关闭时出错: {e}")

        # 第2步：强制垃圾回收，释放残留的 COM 对象（解决 Excel 进程已退出但文件锁未释放的问题）
        try:
            gc.collect()
            try:
                import pythoncom
                pythoncom.CoUninitialize()
                pythoncom.CoInitialize()
            except Exception:
                pass
        except Exception:
            pass

        # 第3步：检查文件是否已释放
        import time
        for _ in range(3):
            try:
                with open(file_path, 'r+b'):
                    pass
                closed = True
                self.logMessage.emit("文件已释放，可以继续操作")
                break
            except PermissionError:
                time.sleep(0.5)

        if not closed:
            self.logMessage.emit(
                f"未能释放文件占用，可能是程序内部残留锁。"
                f"建议：重启程序后再试，或手动结束 Python 进程。")

        self.fileClosed.emit(closed)

    @Slot(result=str)
    def getDefaultFilePath(self):
        return settings.get("attendance_sync.file_path", r"D:\Desktop\1_标准报表.xls")

    @Slot(str)
    def rememberFilePath(self, file_path):
        import urllib.parse
        file_path = str(file_path or "")
        if file_path.startswith("file:///"):
            file_path = file_path[8:]
        file_path = os.path.normpath(urllib.parse.unquote(file_path)) if file_path else ""
        if file_path:
            settings.set("attendance_sync.file_path", file_path)

    @Slot(str, str)
    def runSync(self, file_path, settings_json='{}'):
        if self._busy:
            return
        self.rememberFilePath(file_path)
        self._last_file_path = file_path
        self._busy = True
        self.busyChanged.emit()

        import json
        try:
            settings = json.loads(settings_json)
        except Exception:
            settings = {}

        self._worker = AttendanceSyncWorker(file_path, settings)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.finishedSignal.connect(self._on_finished)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.syncDataReady.connect(self._on_sync_data_ready)
        self._worker.finished.connect(self._on_worker_finished)  # 安全网：QThread 内置信号，确保 _busy 必定复位
        self._worker.start()

    def _on_finished(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.syncFinished.emit(msg)

    def _on_error(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.syncError.emit(msg)

    def _on_sync_data_ready(self, data_json):
        import json
        try:
            self._last_panel_data = json.loads(data_json)
        except Exception:
            self._last_panel_data = {}
        self.syncDataReady.emit(data_json)

    @Slot(result=str)
    def getLastPanelData(self):
        import json
        return json.dumps(self._last_panel_data, ensure_ascii=False)

    @Slot(str)
    def loadExcelData(self, file_path):
        if self._busy:
            return
        self._last_file_path = file_path
        self._busy = True
        self.busyChanged.emit()

        self._worker = LoadExcelWorker(file_path)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.syncDataReady.connect(self._on_sync_data_ready)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    @Slot(str, int, str)
    def manualUpdateDay(self, file_path, day, times_json):
        if self._busy:
            return
        self._busy = True
        self.busyChanged.emit()

        import json
        try:
            times_list = json.loads(times_json)
        except Exception:
            times_list = []
        self._worker = ManualUpdateWorker(file_path, day, times_list, self._last_panel_data)
        self._worker.logSignal.connect(self.logMessage.emit)
        self._worker.errorSignal.connect(self._on_error)
        self._worker.syncDataReady.connect(self._on_sync_data_ready)
        self._worker.finishedSignal.connect(self._on_manual_update_finished)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        self._busy = False
        self.busyChanged.emit()

    def _on_manual_update_finished(self, msg):
        self.manualUpdateFinished.emit(msg)
