import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    property var folderList: []
    property bool backendBusy: false

    FileDialog {
        id: imageFileDialog
        title: "选择图片"
        currentFolder: imageDistributor.getDefaultImageDir() ? ("file:///" + imageDistributor.getDefaultImageDir().replace(/\\/g, "/")) : ""
        nameFilters: ["图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)", "所有文件 (*.*)"]
        onAccepted: {
            imageDistributor.setSourceImage(selectedFile.toString())
            sourceLabel.text = selectedFile.toString().replace("file:///", "")
        }
    }

    FolderDialog {
        id: folderDialog
        title: "选择主文件夹"
        currentFolder: imageDistributor.getLastTargetDir() ? ("file:///" + imageDistributor.getLastTargetDir().replace(/\\/g, "/")) : ""
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            if (imageDistributor.addTargetFolder(path)) {
                folderList.push(path)
                folderListModel.append({"folderPath": path})
            }
        }
    }

    Connections {
        target: imageDistributor
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onBusyChanged() { backendBusy = imageDistributor.isBusy() }
        function onDistributionFinished(count) {
            statusLabel.text = "图片分发完毕！\n共成功放入 " + count + " 个子文件夹中。"
            statusLabel.color = "#0078D4"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 15

        Label { text: "尺码表批量分发"; color: "#333333"; font.pixelSize: 22; font.bold: true }

        // 步骤1：选择源图片
        Rectangle {
            Layout.fillWidth: true
            Layout.minimumHeight: 100
            radius: 6
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 8
                Label { text: "1. 选择要分发的图片 (如: 尺码表.jpg)"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                RowLayout {
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        Label {
                            id: sourceLabel; text: ""
                            color: "#333333"; font.pixelSize: 13
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.leftMargin: 8; anchors.rightMargin: 8
                            elide: Text.ElideMiddle
                        }
                    }
                    ModernButton {
                        text: "浏览图片..."
                        implicitHeight: 34; implicitWidth: 100
                        onClicked: imageFileDialog.open()
                        
                        
                    }
                }
            }
        }

        // 步骤2：目标文件夹列表
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 150
            Layout.preferredHeight: 250
            radius: 6
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 10
                
                Label { text: "2. 添加目标主文件夹 (包含众多子文件夹的父目录)"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                
                RowLayout {
                    spacing: 10
                    ModernButton {
                        text: "添加文件夹"
                        implicitHeight: 34; implicitWidth: 100
                        onClicked: folderDialog.open()
                        
                        
                    }
                    ModernButton {
                        text: "清空列表"
                        implicitHeight: 34; implicitWidth: 100
                        onClicked: { 
                            imageDistributor.clearFolders()
                            folderListModel.clear()
                            folderList = [] 
                        }
                        
                        
                    }
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    border.color: "#CCCCCC"
                    color: "#FFFFFF"
                    ListView {
                        anchors.fill: parent
                        anchors.margins: 4
                        clip: true
                        spacing: 2
                        model: ListModel { id: folderListModel }
                        delegate: Rectangle {
                            width: ListView.view ? ListView.view.width : 100
                            height: 28
                            color: folderHover.containsMouse ? "#F5F5F5" : "transparent"
                            MouseArea {
                                id: folderHover
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                            }
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 4
                                spacing: 4
                                Label {
                                    text: model.folderPath
                                    color: "#333333"
                                    font.pixelSize: 13
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }
                                Label {
                                    text: "✕"
                                    color: delArea.containsMouse ? "#D32F2F" : "#999999"
                                    font.pixelSize: 14
                                    Layout.preferredWidth: 20
                                    horizontalAlignment: Text.AlignHCenter
                                    MouseArea {
                                        id: delArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            imageDistributor.removeFolder(index)
                                            folderList.splice(index, 1)
                                            folderListModel.remove(index)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 步骤3：执行区与输出
        ModernButton {
            id: btnStart
            Layout.fillWidth: true
            implicitHeight: 46
            text: backendBusy ? "分发中..." : "开始分发图片"
            enabled: !backendBusy
            onClicked: imageDistributor.startDistribution()
            
            
        }

        // 日志区域
        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
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
