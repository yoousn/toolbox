import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"

    // 防止联动递归
    property bool _updating: false

    // 日期面板数据模型（顶层，弹窗和主页面共享）
    ListModel { id: panelModel }

    // 时间输入框模型
    ListModel { id: timeInputModel }

    // 中班概率联动：修改一个，按比例分配剩余到另外两个
    function redistributeNoon(changedId) {
        if (_updating) return
        _updating = true
        var v1 = parseInt(noonP1.text) || 0
        var v2 = parseInt(noonP2.text) || 0
        var v3 = parseInt(noonP3.text) || 0
        var remain, other1, other2
        if (changedId === 1) {
            v1 = Math.min(v1, 100)
            remain = 100 - v1
            if (v2 + v3 > 0) {
                var r = v2 / (v2 + v3)
                v2 = Math.round(remain * r)
                v3 = remain - v2
            } else {
                v2 = Math.round(remain / 2)
                v3 = remain - v2
            }
            noonP2.text = String(v2)
            noonP3.text = String(v3)
        } else if (changedId === 2) {
            v2 = Math.min(v2, 100)
            remain = 100 - v2
            if (v1 + v3 > 0) {
                var r2 = v1 / (v1 + v3)
                v1 = Math.round(remain * r2)
                v3 = remain - v1
            } else {
                v1 = Math.round(remain / 2)
                v3 = remain - v1
            }
            noonP1.text = String(v1)
            noonP3.text = String(v3)
        } else {
            v3 = Math.min(v3, 100)
            remain = 100 - v3
            if (v1 + v2 > 0) {
                var r3 = v1 / (v1 + v2)
                v1 = Math.round(remain * r3)
                v2 = remain - v1
            } else {
                v1 = Math.round(remain / 2)
                v2 = remain - v1
            }
            noonP1.text = String(v1)
            noonP2.text = String(v2)
        }
        _updating = false
    }

    // 早班概率联动
    function redistributeMorning(changedId) {
        if (_updating) return
        _updating = true
        var v1 = parseInt(morningP1.text) || 0
        var v2 = parseInt(morningP2.text) || 0
        if (changedId === 1) {
            v1 = Math.min(v1, 100)
            morningP2.text = String(100 - v1)
        } else {
            v2 = Math.min(v2, 100)
            morningP1.text = String(100 - v2)
        }
        _updating = false
    }

    function resetDefaults() {
        _updating = true
        noonP1.text = "40"; noonP2.text = "40"; noonP3.text = "20"
        noonOutRange.text = "5"
        morningP1.text = "80"; morningP2.text = "20"
        morningOutRange.text = "5"
        nightOutRange.text = "5"
        lateModeCombo.currentIndex = 0
        lateCount.text = "5"; lateLimit.text = "5"
        sameTimeLimit.text = "2"
        _updating = false
    }

    function buildSettings() {
        var obj = {
            "noon_p1": parseInt(noonP1.text),
            "noon_p2": parseInt(noonP2.text),
            "noon_p3": parseInt(noonP3.text),
            "noon_out_range": parseInt(noonOutRange.text),
            "morning_p1": parseInt(morningP1.text),
            "morning_p2": parseInt(morningP2.text),
            "morning_out_range": parseInt(morningOutRange.text),
            "night_out_range": parseInt(nightOutRange.text),
            "late_mode": lateModeCombo.currentIndex,
            "late_count": parseInt(lateCount.text),
            "late_limit": parseInt(lateLimit.text),
            "same_time_limit": parseInt(sameTimeLimit.text)
        }
        for (var k in obj) { if (isNaN(obj[k])) obj[k] = 0 }
        return JSON.stringify(obj)
    }

    function formatTimeInput(text) {
        var t = text.replace(/[^0-9]/g, "")
        if (t.length === 4) {
            return t.substring(0, 2) + ":" + t.substring(2, 4)
        }
        return text
    }

    FileDialog {
        id: excelFileDlg
        title: "选择考勤报表文件"
        currentFolder: "file:///" + attendanceSync.getDefaultFilePath().replace(/\\/g, "/").split("/").slice(0, -1).join("/")
        nameFilters: ["Excel 文件 (*.xls *.xlsx)"]
        onAccepted: {
            pathInput.text = selectedFile.toString().replace("file:///", "")
            attendanceSync.rememberFilePath(pathInput.text)
        }
    }

    Connections {
        target: attendanceSync
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onSyncFinished(msg) { statusLabel.text = msg; statusLabel.color = "#0078D4"; closeExcelBtn.visible = false }
        function onSyncError(msg) {
            if (msg.startsWith("OCCUPIED|")) {
                statusLabel.text = "文件被占用，请点击“关闭已打开的Excel”按钮"
                closeExcelBtn.visible = true
            } else {
                statusLabel.text = "错误: " + msg
                closeExcelBtn.visible = false
            }
            // 如果日期校对弹窗正在加载（panelModel 为空）时出错，关闭弹窗避免永久卡在加载界面
            if (dayPanelWindow.visible && panelModel.count === 0) {
                dayPanelWindow.hide()
            }
        }
        function onFileClosed(closed) {
            closeExcelBtn.visible = false   // 关闭后隐藏按钮
            if (closed) {
                statusLabel.text = "文件已关闭，可以重新同步"
                statusLabel.color = "#0078D4"
            } else {
                statusLabel.text = "未能关闭文件，请手动关闭 Excel"
                statusLabel.color = "#D32F2F"
            }
        }
        function onSyncDataReady(dataJson) {
            var oldSelectedDay = dayPanelWindow.selectedDay
            updatePanelModel(dataJson)
            // 如果弹窗已打开且没有选中日期，默认选中第一天
            if (dayPanelWindow.visible && oldSelectedDay === 0) {
                dayPanelWindow.selectFirstDay()
            }
        }
        function onManualUpdateFinished(msg) {
            statusLabel.text = msg
            statusLabel.color = "#0078D4"
        }
    }

    function updatePanelModel(dataJson) {
        panelModel.clear()
        // 先添加一个包含所有 role 的占位条目，确保 ListModel 识别所有 role
        panelModel.append({
            day: 0, inTime: "", outTime: "", allTimes: "",
            timeCount: 0, duration: 0,
            modified: false, sheet1: false, sheet2: false, sheet3: false
        })
        panelModel.remove(0)

        try {
            var data = JSON.parse(dataJson)
            for (var day = 1; day <= 31; day++) {
                var key = String(day)
                var item = data[key] || {}
                panelModel.append({
                    day: day,
                    inTime: item.in || "",
                    outTime: item.out || "",
                    allTimes: item.allTimes || "",
                    timeCount: item.timeCount || 0,
                    duration: item.duration || 0,
                    modified: !!item.modified,
                    sheet1: !!item.sheet1,
                    sheet2: !!item.sheet2,
                    sheet3: !!item.sheet3
                })
            }
        } catch (e) {
            console.log("解析面板数据失败:", e)
        }
    }

    Flickable {
        anchors.fill: parent; anchors.margins: 16
        contentHeight: mainCol.height + 20; clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: mainCol; width: parent.width; spacing: 12

            // ---- 文件 ----
            Rectangle {
                Layout.fillWidth: true; height: fileRow.height + 30
                radius: 8; color: "#FFF"; border.color: "#E0E0E0"
                RowLayout {
                    id: fileRow
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 15 }
                    spacing: 8
                    Label { text: "📂"; font.pixelSize: 16 }
                    Rectangle {
                        Layout.fillWidth: true; implicitHeight: 32; radius: 4
                        border.color: "#CCC"; color: "#FFF"
                        TextInput {
                            id: pathInput; text: attendanceSync.getDefaultFilePath()
                            anchors.fill: parent; anchors.leftMargin: 8
                            verticalAlignment: TextInput.AlignVCenter
                            color: "#333"; font.pixelSize: 13; clip: true; selectByMouse: true
                        }
                    }
                    ModernButton { text: "浏览"; implicitHeight: 32; onClicked: excelFileDlg.open() }
                    ModernButton {
                        id: closeExcelBtn
                        visible: false
                        text: "关闭已打开的Excel"
                        implicitHeight: 32
                        onClicked: attendanceSync.closeExcelFile(pathInput.text)
                    }
                }
            }

            // ---- 参数卡片 ----
            Rectangle {
                Layout.fillWidth: true; height: paramCol.height + 30
                radius: 8; color: "#FFF"; border.color: "#E0E0E0"

                ColumnLayout {
                    id: paramCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 15 }
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "⚙️ 打卡参数"; font.pixelSize: 14; font.bold: true; color: "#333"; Layout.fillWidth: true }
                        ModernButton {
                            text: "还原默认"; implicitHeight: 26; font.pixelSize: 11
                            onClicked: resetDefaults()
                        }
                    }

                    // ===== 中班 =====
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#EEE" }
                    Label { text: "中班 (12:XX ~ 21:0X)"; font.pixelSize: 13; font.bold: true; color: "#0078D4" }

                    GridLayout {
                        columns: 8; columnSpacing: 6; rowSpacing: 6; Layout.fillWidth: true

                        Label { text: "0~10分%"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: noonP1.activeFocus ? "#0078D4" : "#CCC"
                            color: noonP1.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: noonP1; text: "40"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 100 }
                                onEditingFinished: redistributeNoon(1)
                            }
                        }

                        Label { text: "10~20分%"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: noonP2.activeFocus ? "#0078D4" : "#CCC"
                            color: noonP2.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: noonP2; text: "40"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 100 }
                                onEditingFinished: redistributeNoon(2)
                            }
                        }

                        Label { text: "20~30分%"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: noonP3.activeFocus ? "#0078D4" : "#CCC"
                            color: noonP3.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: noonP3; text: "20"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 100 }
                                onEditingFinished: redistributeNoon(3)
                            }
                        }

                        Label { text: "下班N分"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: noonOutRange.activeFocus ? "#0078D4" : "#CCC"
                            color: noonOutRange.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: noonOutRange; text: "5"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 1; top: 30 }
                            }
                        }
                    }
                    Label {
                        text: "修改任一概率后按回车/Tab，其余自动按比例分配至100%"
                        font.pixelSize: 10; color: "#AAA"; font.italic: true
                    }

                    // ===== 早班 =====
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#EEE" }
                    Label { text: "早班 (07:XX ~ 16:3X)"; font.pixelSize: 13; font.bold: true; color: "#0078D4" }

                    GridLayout {
                        columns: 6; columnSpacing: 6; rowSpacing: 6; Layout.fillWidth: true

                        Label { text: "39~50分%"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: morningP1.activeFocus ? "#0078D4" : "#CCC"
                            color: morningP1.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: morningP1; text: "80"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 100 }
                                onEditingFinished: redistributeMorning(1)
                            }
                        }

                        Label { text: "51~60分%"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: morningP2.activeFocus ? "#0078D4" : "#CCC"
                            color: morningP2.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: morningP2; text: "20"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 100 }
                                onEditingFinished: redistributeMorning(2)
                            }
                        }

                        Label { text: "下班N分"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: morningOutRange.activeFocus ? "#0078D4" : "#CCC"
                            color: morningOutRange.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: morningOutRange; text: "5"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 1; top: 29 }
                            }
                        }
                    }

                    // ===== 晚班 =====
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#EEE" }
                    Label { text: "晚班 (15:XX ~ 00:0X)"; font.pixelSize: 13; font.bold: true; color: "#0078D4" }

                    GridLayout {
                        columns: 2; columnSpacing: 6; rowSpacing: 6

                        Label { text: "下班N分"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: nightOutRange.activeFocus ? "#0078D4" : "#CCC"
                            color: nightOutRange.activeFocus ? "#F0F6FF" : "#FFF"
                            TextInput {
                                id: nightOutRange; text: "5"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 1; top: 30 }
                            }
                        }
                    }

                    // ===== 通用 =====
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#EEE" }
                    Label { text: "通用设置"; font.pixelSize: 13; font.bold: true; color: "#0078D4" }

                    GridLayout {
                        columns: 6; columnSpacing: 6; rowSpacing: 6; Layout.fillWidth: true

                        Label { text: "迟到20分"; font.pixelSize: 12; color: "#555" }
                        ComboBox {
                            id: lateModeCombo
                            model: ["随机(上限)", "指定次数"]
                            implicitWidth: 110; implicitHeight: 28; font.pixelSize: 12
                        }

                        Label {
                            text: lateModeCombo.currentIndex === 0 ? "上限次数" : "固定次数"
                            font.pixelSize: 12; color: "#555"
                        }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: "#CCC"
                            TextInput {
                                id: lateLimit; text: "5"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 25 }
                                visible: lateModeCombo.currentIndex === 0
                            }
                            TextInput {
                                id: lateCount; text: "5"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 0; top: 25 }
                                visible: lateModeCombo.currentIndex === 1
                            }
                        }

                        Label { text: "同时间上限"; font.pixelSize: 12; color: "#555" }
                        Rectangle {
                            implicitWidth: 45; implicitHeight: 28; radius: 4
                            border.color: "#CCC"
                            TextInput {
                                id: sameTimeLimit; text: "2"; anchors.fill: parent; anchors.leftMargin: 6
                                verticalAlignment: TextInput.AlignVCenter; font.pixelSize: 13; color: "#333"
                                selectByMouse: true; validator: IntValidator { bottom: 1; top: 10 }
                            }
                        }
                    }
                }
            }

            // ---- 启动同步 + 日期校对 ----
            ModernButton {
                Layout.fillWidth: true; implicitHeight: 44
                text: "🚀 启动同步"
                enabled: !attendanceSync.isBusy
                opacity: enabled ? 1.0 : 0.5
                onClicked: {
                    logModel.clear(); statusLabel.text = "正在同步..."
                    statusLabel.color = "#666"
                    attendanceSync.runSync(pathInput.text, buildSettings())
                }
            }

            ModernButton {
                Layout.fillWidth: true; implicitHeight: 36
                text: "📅 打开日期校对窗口"
                bgColor: "#50C878"
                hoverColor: "#45B569"
                pressedColor: "#3A9A58"
                enabled: !attendanceSync.isBusy
                opacity: enabled ? 1.0 : 0.5
                onClicked: {
                    // 防御性检查：忙时不打开弹窗，避免永久卡在加载界面
                    if (attendanceSync.isBusy) {
                        statusLabel.text = "正在处理其他操作，请稍后再试"
                        statusLabel.color = "#FF9800"
                        return
                    }
                    if (!panelModel.count) {
                        logModel.clear(); statusLabel.text = "正在加载..."
                        statusLabel.color = "#666"
                        attendanceSync.loadExcelData(pathInput.text)
                    } else {
                        // 如果已有数据，默认选中第一天有数据的日期
                        dayPanelWindow.selectFirstDay()
                    }
                    dayPanelWindow.show()
                    dayPanelWindow.raise()
                    dayPanelWindow.requestActivate()
                }
            }

            Label { id: statusLabel; text: ""; color: "#666"; font.pixelSize: 13; Layout.alignment: Qt.AlignHCenter }

            // ---- 日志 ----
            Rectangle {
                Layout.fillWidth: true; height: 180
                radius: 6; color: "#F8F8F8"; border.color: "#DDD"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 2
                    Label { text: "📋 执行日志"; font.pixelSize: 11; font.bold: true; color: "#999" }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2
                        model: ListModel { id: logModel }
                        delegate: Label {
                            text: model.text; color: "#333"; font.pixelSize: 12
                            font.family: "Consolas"; width: ListView.view.width; wrapMode: Text.Wrap
                        }
                        onCountChanged: positionViewAtEnd()
                    }
                }
            }
        }
    }

    // ---- 日期校对弹窗 ----
    Window {
        id: dayPanelWindow
        title: "日期校对面板"
        width: 676; height: 676  // 520 * 1.3
        flags: Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint
        visible: false

        Rectangle {
            anchors.fill: parent; color: "#F5F6F8"

            // 加载中遮罩
            Rectangle {
                anchors.fill: parent
                color: "#F5F6F8"
                visible: panelModel.count === 0
                z: 10
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 16
                    BusyIndicator { running: true; width: 62; height: 62; Layout.alignment: Qt.AlignHCenter }
                    Label {
                        text: "正在读取 Excel 数据，请稍候..."
                        font.pixelSize: 17; color: "#666"
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Label {
                        text: "（首次加载需要几秒，数据会缓存）"
                        font.pixelSize: 14; color: "#999"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            ColumnLayout {
                anchors { fill: parent; margins: 20 }
                spacing: 16
                visible: panelModel.count > 0

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "📅 日期校对面板"
                        font.pixelSize: 20; font.bold: true; color: "#333"; Layout.fillWidth: true
                    }
                    RowLayout {
                        spacing: 14
                        Label { text: "● 工时≤8.5h"; font.pixelSize: 13; color: "#F44336" }
                        Label { text: "● 3条记录"; font.pixelSize: 13; color: "#FFC107" }
                        Label { text: "● 正常"; font.pixelSize: 13; color: "#333" }
                    }
                }
                Label {
                    text: "绿色=已修改 灰色=未修改 | 点击日期可编辑时间"
                    font.pixelSize: 13; color: "#999"
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 7
                    rowSpacing: 8; columnSpacing: 8

                    Repeater {
                        model: panelModel
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 65
                            radius: 5
                            color: {
                                if (dayPanelWindow.selectedDay === day) return "#E3F2FD"
                                return modified ? "#E8F5E9" : "#F5F5F5"
                            }
                            border.color: dayPanelWindow.selectedDay === day ? "#1976D2" : "#DDD"

                            property int day: model.day
                            property bool modified: model.modified

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    dayPanelWindow.selectedDay = day
                                    dayPanelWindow.loadTimesForDay(model.allTimes)
                                }
                            }

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 1
                                Label {
                                    text: day
                                    font.pixelSize: 17; font.bold: true
                                    color: modified ? "#2E7D32" : "#666"
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Label {
                                    text: model.allTimes ? model.allTimes : "--"
                                    font.pixelSize: 13
                                    color: modified ? "#2E7D32" : "#999"
                                    Layout.alignment: Qt.AlignHCenter
                                    wrapMode: Text.Wrap
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                Label {
                                    text: "●"
                                    font.pixelSize: 13
                                    Layout.alignment: Qt.AlignHCenter
                                    color: {
                                        if (model.timeCount === 3) return "#FFC107"
                                        if (model.duration > 0 && model.duration <= 8.5) return "#F44336"
                                        return "#333"
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 1; color: "#DDD"
                    visible: dayPanelWindow.selectedDay > 0
                }

                // 多时间编辑器
                ColumnLayout {
                    visible: dayPanelWindow.selectedDay > 0
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: dayPanelWindow.selectedDay + "号 - 所有打卡时间"
                        font.pixelSize: 15; color: "#333"; font.bold: true
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: timeInputModel
                            RowLayout {
                                spacing: 8
                                Label {
                                    text: "第" + (index + 1) + "个:"
                                    font.pixelSize: 14; color: "#555"
                                }
                                Rectangle {
                                    implicitWidth: 110; implicitHeight: 36; radius: 4
                                    border.color: "#CCC"; color: "#FFF"
                                    TextInput {
                                        id: timeEditField
                                        text: model.timeValue
                                        anchors.fill: parent; anchors.leftMargin: 8
                                        verticalAlignment: TextInput.AlignVCenter
                                        font.pixelSize: 15; color: "#333"
                                        selectByMouse: true
                                        onEditingFinished: {
                                            var newText = formatTimeInput(text)
                                            timeInputModel.setProperty(index, "timeValue", newText)
                                        }
                                    }
                                }
                                Rectangle {
                                    implicitWidth: 36; implicitHeight: 36; radius: 4
                                    color: "#FFEBEE"
                                    visible: timeInputModel.count > 1
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: {
                                            timeInputModel.remove(index)
                                        }
                                    }
                                    Label {
                                        anchors.centerIn: parent
                                        text: "✕"
                                        font.pixelSize: 16; color: "#F44336"
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        spacing: 8
                        ModernButton {
                            text: "+ 添加时间"; implicitHeight: 36; font.pixelSize: 14
                            onClicked: {
                                timeInputModel.append({"timeValue": ""})
                            }
                        }
                        ModernButton {
                            text: "同步修改"; implicitHeight: 36; font.pixelSize: 14
                            onClicked: {
                                var validTimes = []
                                for (var i = 0; i < timeInputModel.count; i++) {
                                    var t = formatTimeInput(timeInputModel.get(i).timeValue.trim())
                                    if (t) validTimes.push(t)
                                }
                                if (validTimes.length === 0) {
                                    statusLabel.text = "请至少输入一个有效时间"
                                    statusLabel.color = "#D32F2F"
                                    return
                                }
                                statusLabel.text = "正在同步 " + dayPanelWindow.selectedDay + " 号..."
                                attendanceSync.manualUpdateDay(pathInput.text, dayPanelWindow.selectedDay, JSON.stringify(validTimes))
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Label {
                    text: "提示：关闭弹窗不会丢失数据，点击“打开日期校对窗口”可恢复"
                    font.pixelSize: 10; color: "#999"; Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        property int selectedDay: 0

        function loadTimesForDay(allTimes) {
            // 清空并重新填充时间输入框
            timeInputModel.clear()
            var times = allTimes.trim().split(/\s+/)
            for (var i = 0; i < times.length; i++) {
                if (times[i]) {
                    timeInputModel.append({"timeValue": times[i]})
                }
            }
            // 如果没有时间，至少添加一个空输入框
            if (timeInputModel.count === 0) {
                timeInputModel.append({"timeValue": ""})
            }
        }

        function selectFirstDay() {
            // 默认选中有数据的第一天
            for (var i = 0; i < panelModel.count; i++) {
                if (panelModel.get(i).allTimes) {
                    selectedDay = panelModel.get(i).day
                    loadTimesForDay(panelModel.get(i).allTimes)
                    return
                }
            }
            // 如果没有数据，选中1号
            if (panelModel.count > 0) {
                selectedDay = panelModel.get(0).day
                loadTimesForDay("")
            }
        }

        onVisibleChanged: {
            if (visible) {
                if (selectedDay > 0) {
                    // 通过 panelModel 找到当前选中日期的 allTimes
                    for (var i = 0; i < panelModel.count; i++) {
                        if (panelModel.get(i).day === selectedDay) {
                            loadTimesForDay(panelModel.get(i).allTimes)
                            break
                        }
                    }
                } else {
                    selectFirstDay()
                }
            }
        }
    }
}
