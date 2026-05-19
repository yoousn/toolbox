import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"

    // 防止联动递归
    property bool _updating: false

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

    FileDialog {
        id: excelFileDlg
        title: "选择考勤报表文件"
        currentFolder: "file:///D:/Desktop"
        nameFilters: ["Excel 文件 (*.xls *.xlsx)"]
        onAccepted: pathInput.text = selectedFile.toString().replace("file:///", "")
    }

    Connections {
        target: attendanceSync
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onSyncFinished(msg) { statusLabel.text = msg; statusLabel.color = "#0078D4" }
        function onSyncError(msg) { statusLabel.text = "错误: " + msg; statusLabel.color = "#D32F2F" }
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
                            id: pathInput; text: "D:\\Desktop\\1_标准报表.xls"
                            anchors.fill: parent; anchors.leftMargin: 8
                            verticalAlignment: TextInput.AlignVCenter
                            color: "#333"; font.pixelSize: 13; clip: true; selectByMouse: true
                        }
                    }
                    ModernButton { text: "浏览"; implicitHeight: 32; onClicked: excelFileDlg.open() }
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
                                selectByMouse: true; validator: IntValidator { bottom: 1; top: 9 }
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

            // ---- 启动 ----
            ModernButton {
                Layout.fillWidth: true; implicitHeight: 44; text: "🚀 启动同步"
                onClicked: {
                    logModel.clear(); statusLabel.text = "正在同步..."
                    attendanceSync.runSync(pathInput.text, buildSettings())
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
}
