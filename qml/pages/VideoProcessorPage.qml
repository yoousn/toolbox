import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"

    // 扫描完成后启用清理按钮
    property bool scanDone: false
    property string scanInfo: ""
    // 会话级浏览位置记忆：重启后重置为 D:\1上款
    property string lastBrowseDir: "D:\\1上款"

    FolderDialog {
        id: dirDialog
        title: "选择目标目录"
        onAccepted: {
            dirInput.text = selectedFolder.toString().replace("file:///", "")
            lastBrowseDir = dirInput.text
            videoProcessor.rememberDefaultDir(dirInput.text)
        }
    }

    // 打开浏览对话框前，设置 currentFolder 为上次浏览位置
    function openDirDialog() {
        dirDialog.currentFolder = "file:///" + lastBrowseDir.replace(/\\/g, "/")
        dirDialog.open()
    }

    Connections {
        target: videoProcessor
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onProgressUpdated(cur, tot) { progressBar.value = tot > 0 ? cur/tot : 0 }
        function onTaskFinished(msg) { statusLabel.text = msg; statusLabel.color = "#0078D4" }
        function onTaskError(msg) { statusLabel.text = "错误: " + msg; statusLabel.color = "#D32F2F" }
        function onBusyChanged() { 
            var b = videoProcessor.isBusy()
            btnAnalyze.enabled = !b
            btnRename.enabled = !b
            btnCopy.enabled = !b
            btnFirstAnalyze.enabled = !b
            btnFirstRename.enabled = !b
            btnFirstCopy.enabled = !b
            btnScan.enabled = !b
            btnCleanup.enabled = !b && scanDone
        }
        function onScanSummary(count, sizeStr) {
            scanDone = true
            scanInfo = count + " 个文件, " + sizeStr
            btnCleanup.enabled = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 15

        Label { text: "🎬 视频批量处理专家"; color: "#333333"; font.pixelSize: 22; font.bold: true }

        // 配置卡片
        Rectangle {
            Layout.fillWidth: true
            height: 120
            radius: 6
            color: "#FFFFFF"
            border.color: "#E0E0E0"
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 12
                
                RowLayout {
                    spacing: 10
                    Label { text: "📁 目标总目录:"; color: "#333333"; font.pixelSize: 14; font.bold: true; Layout.preferredWidth: 100 }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        radius: 4
                        color: "#FFFFFF"
                        border.color: "#CCCCCC"
                        TextInput {
                            id: dirInput; anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; verticalAlignment: TextInput.AlignVCenter
                            text: "D:\\1上款"; color: "#333333"; font.pixelSize: 13
                        }
                    }
                    ModernButton {
                        text: "浏览"
                        implicitHeight: 34; implicitWidth: 80
                        onClicked: openDirDialog()
                    }
                }

                RowLayout {
                    spacing: 10
                    Label { text: "🎞️ 视频格式:"; color: "#333333"; font.pixelSize: 14; font.bold: true; Layout.preferredWidth: 100 }
                    ComboBox {
                        id: formatCombo
                        model: ["MOV", "MP4"]
                        implicitWidth: 120; implicitHeight: 34
                    }
                }
            }
        }

        // ===== 原有功能按钮 =====
        RowLayout {
            Layout.fillWidth: true
            spacing: 15
            
            ModernButton {
                id: btnAnalyze
                Layout.fillWidth: true; implicitHeight: 46; text: "🔍 仅分析检测"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "analyze", false) }
            }
            ModernButton {
                id: btnRename
                Layout.fillWidth: true; implicitHeight: 46; text: "✏️ 批量重命名"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "rename", false) }
            }
            ModernButton {
                id: btnCopy
                Layout.fillWidth: true; implicitHeight: 46; text: "📋 提取副本到总目录"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "copy", false) }
            }
        }

        // ===== 只取首个视频 按钮行 =====
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            ModernButton {
                id: btnFirstAnalyze
                Layout.fillWidth: true; implicitHeight: 46; text: "🔍 分析(仅首个视频)"
                bgColor: "#43A047"; hoverColor: "#388E3C"; pressedColor: "#2E7D32"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "analyze", true) }
            }
            ModernButton {
                id: btnFirstRename
                Layout.fillWidth: true; implicitHeight: 46; text: "✏️ 重命名(仅首个视频)"
                bgColor: "#43A047"; hoverColor: "#388E3C"; pressedColor: "#2E7D32"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "rename", true) }
            }
            ModernButton {
                id: btnFirstCopy
                Layout.fillWidth: true; implicitHeight: 46; text: "📋 提取首个视频到总目录"
                bgColor: "#43A047"; hoverColor: "#388E3C"; pressedColor: "#2E7D32"
                onClicked: { logModel.clear(); videoProcessor.startTask(dirInput.text, formatCombo.currentText, "copy", true) }
            }
        }

        // ===== 分隔线 =====
        Rectangle { Layout.fillWidth: true; height: 1; color: "#E0E0E0" }

        // ===== 视频清理区 =====
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            Label { text: "🗑️ 视频批量清理"; color: "#333333"; font.pixelSize: 14; font.bold: true }
            Item { Layout.fillWidth: true }
            Label {
                text: scanInfo ? ("📊 " + scanInfo) : ""
                color: "#F57C00"; font.pixelSize: 13; font.bold: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            ModernButton {
                id: btnScan
                Layout.fillWidth: true; implicitHeight: 46; text: "🔍 扫描「所有XXX」文件夹内视频"
                onClicked: {
                    logModel.clear()
                    scanDone = false
                    scanInfo = ""
                    statusLabel.text = "扫描中..."
                    statusLabel.color = "#666666"
                    progressBar.value = 0
                    videoProcessor.scanVideos(dirInput.text)
                }
            }
            ModernButton {
                id: btnCleanup
                Layout.fillWidth: true; implicitHeight: 46; text: "🗑️ 一键清理至回收站"
                enabled: scanDone
                bgColor: enabled ? "#E53935" : "#D0D0D0"
                hoverColor: "#C62828"
                pressedColor: "#B71C1C"
                onClicked: {
                    logModel.clear()
                    statusLabel.text = "清理中..."
                    statusLabel.color = "#666666"
                    progressBar.value = 0
                    scanDone = false
                    videoProcessor.cleanupVideos(dirInput.text)
                }
            }
        }

        // 状态与进度
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            RowLayout {
                Label { text: "处理进度"; color: "#666666"; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                Label { id: statusLabel; text: "就绪"; color: "#666666"; font.pixelSize: 12 }
            }
            ProgressBar { 
                id: progressBar
                Layout.fillWidth: true; value: 0
                
                contentItem: Item { 
                    implicitHeight: 6
                    Rectangle { 
                        width: progressBar.visualPosition * parent.width; height: parent.height; radius: 3; color: "#0078D4" 
                    }
                }
            }
        }

        // 日志
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 5
            Label { text: "系统日志输出区域:"; color: "#333333"; font.pixelSize: 14; font.bold: true }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 4; color: "#F4F4F4"; border.color: "#CCCCCC"
                ListView {
                    anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 4
                    model: ListModel { id: logModel }
                    delegate: Label { 
                        text: model.text; color: "#333333"; font.pixelSize: 12
                        font.family: "Consolas"
                        width: ListView.view ? ListView.view.width : 100; wrapMode: Text.Wrap 
                    }
                    ScrollBar.vertical: ScrollBar { active: true }
                    onCountChanged: positionViewAtEnd()
                }
            }
        }
    }
}
