import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    property bool backendBusy: false
    // 会话级浏览位置记忆：重启后重置为 D:\1上款
    property string lastBrowseDir: "D:\\1上款"

    FolderDialog {
        id: sizeChartDialog
        title: "选择尺码表目录"
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            sizeChartLabel.text = path
            sizeMatcher.setSizeChartDir(path)
            lastBrowseDir = path
        }
    }

    FolderDialog {
        id: targetRootDialog
        title: "选择目标文件夹主目录"
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            targetRootLabel.text = path
            sizeMatcher.setTargetRootDir(path)
            lastBrowseDir = path
        }
    }

    Connections {
        target: sizeMatcher
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onBusyChanged() { backendBusy = sizeMatcher.isBusy() }
        function onMatchFinished(success, unmatched) {
            statusLabel.text = "匹配完成：成功 " + success + " 个，未匹配 " + unmatched + " 个"
            statusLabel.color = unmatched > 0 ? "#D32F2F" : "#0078D4"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 15

        Label { text: "尺码表自动匹配"; color: "#333333"; font.pixelSize: 22; font.bold: true }

        // 步骤1：选择尺码表目录
        Rectangle {
            Layout.fillWidth: true
            Layout.minimumHeight: 90
            radius: 8
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 8
                Label { text: "1. 选择尺码表所在目录 (如: D:\\1上款\\尺码)"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                RowLayout {
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        Label {
                            id: sizeChartLabel
                            text: sizeMatcher.getSizeChartDir()
                            color: "#333333"; font.pixelSize: 13
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.leftMargin: 8; anchors.rightMargin: 8
                            elide: Text.ElideMiddle
                        }
                    }
                    ModernButton {
                        text: "浏览..."
                        implicitHeight: 34; implicitWidth: 90
                        onClicked: {
                            sizeChartDialog.currentFolder = "file:///" + lastBrowseDir.replace(/\\/g, "/")
                            sizeChartDialog.open()
                        }
                    }
                }
            }
        }

        // 步骤2：选择目标文件夹主目录
        Rectangle {
            Layout.fillWidth: true
            Layout.minimumHeight: 90
            radius: 8
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 8
                Label { text: "2. 选择目标文件夹主目录 (包含 A180黑、A181黑 等子文件夹)"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                RowLayout {
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        Label {
                            id: targetRootLabel
                            text: sizeMatcher.getTargetRootDir()
                            color: "#333333"; font.pixelSize: 13
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.leftMargin: 8; anchors.rightMargin: 8
                            elide: Text.ElideMiddle
                        }
                    }
                    ModernButton {
                        text: "浏览..."
                        implicitHeight: 34; implicitWidth: 90
                        onClicked: {
                            targetRootDialog.currentFolder = "file:///" + lastBrowseDir.replace(/\\/g, "/")
                            targetRootDialog.open()
                        }
                    }
                }
            }
        }

        // 匹配规则说明
        Rectangle {
            Layout.fillWidth: true
            Layout.minimumHeight: 60
            radius: 8
            color: "#F0F6FF"
            border.color: "#B3D7F7"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 4
                Label { text: "匹配规则"; color: "#0078D4"; font.pixelSize: 13; font.bold: true }
                Label {
                    text: "根据子文件夹名前面的货号自动匹配尺码表图片。例如：文件夹 'A180黑' 会匹配 'A180.jpg'，匹配成功后会将尺码表复制到该文件夹内。"
                    color: "#333333"; font.pixelSize: 12
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                }
            }
        }

        // 执行按钮
        ModernButton {
            id: btnStart
            Layout.fillWidth: true
            implicitHeight: 46
            text: backendBusy ? "匹配中..." : "开始自动匹配"
            enabled: !backendBusy
            onClicked: {
                logModel.clear()
                statusLabel.text = ""
                sizeMatcher.startMatch()
            }
        }

        // 日志区域
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 5
            RowLayout {
                Label { text: "执行日志:"; color: "#333333"; font.pixelSize: 13 }
                Item { Layout.fillWidth: true }
                Label { id: statusLabel; text: ""; color: "#0078D4"; font.pixelSize: 13 }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 4
                color: "#F4F4F4"
                border.color: "#CCCCCC"
                ListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 2
                    model: ListModel { id: logModel }
                    delegate: Label {
                        text: model.text; color: "#333333"; font.pixelSize: 12
                        font.family: "Consolas"
                        width: ListView.view ? ListView.view.width : 100
                        wrapMode: Text.Wrap
                    }
                    onCountChanged: positionViewAtEnd()
                }
            }
        }
    }
}
