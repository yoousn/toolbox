# -*- coding: utf-8 -*-
import re
import random
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Signal, QThread


class AttendanceSyncWorker(QThread):
    logSignal = Signal(str)
    finishedSignal = Signal(str)
    errorSignal = Signal(str)

    def __init__(self, file_path, settings=None):
        super().__init__()
        self.file_path = file_path
        self.settings = settings or {}

    def run(self):
        try:
            import xlwings as xw

            file_path = self.file_path
            password = "AAAABBAABBBO"

            self.logSignal.emit("正在启动考勤 5.0 终极同步流程...")

            wb = xw.Book(file_path)
            sheet1 = wb.sheets["考勤记录"]
            sheet1.api.Unprotect(password)

            sync_data = {}
            s = self.settings
            same_time_limit = s.get('same_time_limit', 2)
            late_mode = s.get('late_mode', 0)  # 0=随机上限, 1=指定次数
            late_limit = s.get('late_limit', 5)
            late_count = s.get('late_count', 5)
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

            noon_out_range = s.get('noon_out_range', 5)
            morning_out_range = s.get('morning_out_range', 5)
            night_out_range = s.get('night_out_range', 5)

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

            def generate_new_times(shift):
                while True:
                    is_late_over_20 = False
                    if shift == 'morning':
                        if random.randint(1, 100) <= morning_probs[0]:
                            h, m = 7, random.randint(39, 51)
                        else:
                            m = random.randint(51, 60)
                            h = 8 if m == 60 else 7
                            m = 0 if m == 60 else m
                        if h == 8 or (h == 7 and m > 50):
                            is_late_over_20 = True
                    elif shift == 'noon':
                        r = random.randint(1, 100)
                        if r <= noon_probs[0]:
                            if raw_p[0] == 0:
                                # 该区间概率为0但舍入修正可能落入
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
                    if is_late_over_20 and shift != 'night':
                        if late_mode == 0:
                            if state['late_over_20'] >= late_limit:
                                continue
                        # 指定模式下不在这里限制，后面统一处理

                    state['used_times'][time_str] = \
                        state['used_times'].get(time_str, 0) + 1
                    if is_late_over_20 and shift != 'night':
                        state['late_over_20'] += 1

                    if shift == 'morning':
                        out_time = f"16:3{random.randint(1, morning_out_range)}"
                    elif shift == 'noon':
                        out_time = f"21:{random.randint(1, noon_out_range):02d}"
                    elif shift == 'night':
                        out_time = f"00:{random.randint(1, night_out_range):02d}"

                    return time_str, out_time

            skipped_days = []
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

                    if ((9*60 <= t_in <= 11*60+30) and
                            (17*60 <= t_out <= 20*60)):
                        self.logSignal.emit(
                            f"⚠️ 特殊班次: 第【{col}】号 "
                            f"[{in_time} - {out_time}]，已跳过")
                        continue

                    shift = None
                    if (((t_in >= 14*60) or
                         (12*60 <= t_in <= 13*60+59)) and
                            (20*60 <= t_out <= 21*60+20)):
                        shift = 'noon'
                    elif ((t_in >= 14*60) and
                          (23*60+55 <= t_out <= 24*60+30)):
                        shift = 'night'
                    elif (in_time.startswith("07") or
                          in_time.startswith("08")):
                        shift = 'morning'

                    if shift:
                        new_in, new_out = generate_new_times(shift)
                        cell.number_format = '@'
                        cell.value = f"{new_in}\n{new_out}"
                        cell.api.WrapText = True
                        sync_data[col] = (new_in, new_out)
                    else:
                        skipped_days.append(
                            f"第{col}号[{in_time}-{out_time}]")

            sheet1.api.Protect(password)
            self.logSignal.emit(
                f"1.【考勤记录】修改完成，已抓取 {len(sync_data)} 组数据。"
                f"迟到20分: {state['late_over_20']}/5")
            if skipped_days:
                self.logSignal.emit(
                    f"⚠️ 未识别班次，跳过 {len(skipped_days)} 天: "
                    f"{', '.join(skipped_days)}")

            # --- 步骤2: 同步异常统计 (按日期+姓名匹配行) ---
            if "异常统计" in [s.name for s in wb.sheets]:
                sheet2 = wb.sheets["异常统计"]
                sheet2.api.Unprotect(password)
                # 建立日期→行号映射 (只匹配梁汝华的行)
                updated_count = 0
                for row in range(5, 200):
                    b_val = sheet2.range(f"B{row}").value
                    if not b_val:
                        break  # 空行 = 数据结束
                    if "梁汝华" not in str(b_val):
                        continue
                    d_val = str(sheet2.range(f"D{row}").value or "")
                    # 从日期中提取日号，如 "2026-04-06" → 6
                    m = re.search(r"-(\d{1,2})$", d_val.strip())
                    if not m:
                        continue
                    day = int(m.group(1))
                    if day in sync_data:
                        new_in, new_out = sync_data[day]
                        for col_name, val in [('E', new_in),
                                              ('F', new_out)]:
                            cell = sheet2.range(f"{col_name}{row}")
                            cell.number_format = '@'
                            cell.value = val
                        updated_count += 1
                sheet2.api.Protect(password)
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
                sheet3.api.Unprotect(password)
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
                    for day_idx in range(1, 32):
                        if day_idx not in sync_data:
                            continue
                        row = 11 + day_idx
                        new_in, new_out = sync_data[day_idx]
                        for c_idx, val in [(in_col_idx, new_in),
                                           (out_col_idx, new_out)]:
                            target = sheet3.range((row, c_idx))
                            target.number_format = '@'
                            target.value = val
                            target.api.HorizontalAlignment = -4108
                    sheet3.api.Protect(password)
                    self.logSignal.emit(
                        f"3.【{card_sheet_name}】梁汝华考勤卡已同步。")
                else:
                    sheet3.api.Protect(password)
                    self.logSignal.emit(
                        f"⚠️【{card_sheet_name}】未找到梁汝华，跳过。")
            else:
                self.logSignal.emit("⚠️ 未找到考勤卡表，已跳过。")

            # --- 步骤4: 更新制表时间 ---
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 4a. 考勤记录 L3 → 制表时间
            sheet1.api.Unprotect(password)
            sheet1.range("L3").number_format = '@'
            sheet1.range("L3").value = today_str
            sheet1.api.Protect(password)
            self.logSignal.emit(
                f"4a.【考勤记录】L3 制表时间已更新为: {today_str}")

            # 4b. 考勤卡表 Q2 → 制表时间 (动态查找表名)
            if card_sheet_name:
                sheet_card = wb.sheets[card_sheet_name]
                sheet_card.api.Unprotect(password)
                sheet_card.range("Q2").number_format = '@'
                sheet_card.range("Q2").value = today_str
                sheet_card.api.Protect(password)
                self.logSignal.emit(
                    f"4b.【{card_sheet_name}】Q2 制表时间已更新为:"
                    f" {today_str}")
            else:
                self.logSignal.emit(
                    "⚠️ 未找到考勤卡表，已跳过制表时间更新。")



            wb.save()
            self.finishedSignal.emit("全部执行完毕！")

        except Exception as e:
            self.errorSignal.emit(f"执行过程中遇到错误: {e}")


class AttendanceSyncBackend(QObject):
    logMessage = Signal(str)
    syncFinished = Signal(str)
    syncError = Signal(str)
    busyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._busy = False

    @Slot(result=str)
    def getDefaultFilePath(self):
        return r"D:\Desktop\1_标准报表.xls"

    @Slot(str, str)
    def runSync(self, file_path, settings_json='{}'):
        if self._busy:
            return
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
        self._worker.start()

    def _on_finished(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.syncFinished.emit(msg)

    def _on_error(self, msg):
        self._busy = False
        self.busyChanged.emit()
        self.syncError.emit(msg)
