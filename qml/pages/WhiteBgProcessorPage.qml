import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    property var selectedIndependentFiles: []

    FolderDialog {
        id: dirDialog
        title: "选择当前目录"
        currentFolder: "file:///D:/1上款"
        onAccepted: dirInput.text = selectedFolder.toString().replace("file:///", "")
    }

    FileDialog {
        id: filesDialog
        title: "选择独立图片文件"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Images (*.png *.jpg *.jpeg)"]
        onAccepted: {
            var paths = selectedIndependentFiles
            for (var i = 0; i < selectedFiles.length; i++) {
                var path = selectedFiles[i].toString().replace("file:///", "")
                if (paths.indexOf(path) === -1) {
                    paths.push(path)
                    fileListModel.append({"text": path})
                }
            }
            selectedIndependentFiles = paths
        }
    }

    Connections {
        target: whiteBgProcessor
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onProgressUpdated(cur, tot) { progressBar.value = tot > 0 ? cur/tot : 0 }
        function onResultItemAdded(name, isMissing) {
            resultModel.append({"text": name, "isMissing": isMissing})
        }
        function onProcessingFinished(msg) {
            statusLabel.text = msg
            statusLabel.color = "#0078D4"
            btnGen1.enabled = true
            btnGen2.enabled = true
            btnDetect.enabled = true
        }
        function onErrorOccurred(msg) {
            statusLabel.text = "错误: " + msg
            statusLabel.color = "#D32F2F"
            btnGen1.enabled = true
            btnGen2.enabled = true
            btnDetect.enabled = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 15

        Label { text: "智能白底图处理引擎"; color: "#333333"; font.pixelSize: 22; font.bold: true }

        TabBar {
            id: modeTab
            Layout.fillWidth: true
            
            TabButton {
                text: "📁 模式一: 依文件名检测目录"
                width: implicitWidth + 40
                
                
            }
            TabButton {
                text: "🖼️ 模式二: 处理独立指定文件"
                width: implicitWidth + 40
                
                
            }
        }

        StackLayout {
            currentIndex: modeTab.currentIndex
            Layout.fillWidth: true
            Layout.maximumHeight: modeTab.currentIndex === 0 ? 150 : 250
            Layout.preferredHeight: modeTab.currentIndex === 0 ? 150 : 250

            // 模式一：目录检测
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 8
                    RowLayout {
                        spacing: 10
                        Label { text: "当前目录:"; color: "#333333"; font.pixelSize: 14; font.bold: true; Layout.preferredWidth: 80 }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: dirInput; text: "D:\\1上款"; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; clip: true }
                        }
                        ModernButton {
                            text: "浏览目录"
                            implicitHeight: 34; implicitWidth: 80; onClicked: dirDialog.open()
                        }
                    }
                    RowLayout {
                        spacing: 12
                        Label { text: "目标文件名:"; color: "#333333"; font.pixelSize: 14; font.bold: true; Layout.preferredWidth: 80 }
                        ComboBox { 
                            id: fileCombo; Layout.fillWidth: true; implicitHeight: 34; model: ["主图1", "主图2", "主图3", "详情图1", "详情图2", "网批海报主视图"] 
                            editable: true
                        }
                    }
                    RowLayout {
                        ModernButton {
                            id: btnDetect
                            Layout.fillWidth: true; implicitHeight: 40; text: "🔍 开始检测匹配文件"
                            onClicked: {
                                resultModel.clear()
                                logModel.clear()
                                statusLabel.text = "检测中..."
                                whiteBgProcessor.detectImages(dirInput.text, fileCombo.currentText)
                            }
                        }
                        ModernButton {
                            id: btnGen1
                            Layout.fillWidth: true; implicitHeight: 40; text: "⚙️ 检测无误，对检测结果生成白底图"
                            onClicked: {
                                logModel.clear()
                                statusLabel.text = "处理中..."
                                btnGen1.enabled = false; btnDetect.enabled = false
                                whiteBgProcessor.processImages(formatCombo.currentText)
                            }
                            
                            
                        }
                    }
                }
            }

            // 模式二：独立文件
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 15; spacing: 12
                    ModernButton {
                        Layout.fillWidth: true; implicitHeight: 40; text: "🖼️ 选择多张独立图片"
                        onClicked: filesDialog.open()
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; border.color: "#CCCCCC"; color: "#F9F9F9"
                        ListView {
                            anchors.fill: parent; anchors.margins: 5; clip: true; spacing: 4
                            model: ListModel { id: fileListModel }
                            delegate: RowLayout {
                                width: ListView.view.width
                                Label { text: model.text; color: "#333333"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                ModernButton {
                                    text: "删除"
                                    implicitHeight: 24; implicitWidth: 50
                                    onClicked: {
                                        var idx = selectedIndependentFiles.indexOf(model.text)
                                        if (idx !== -1) {
                                            var newArr = selectedIndependentFiles
                                            newArr.splice(idx, 1)
                                            selectedIndependentFiles = newArr
                                        }
                                        fileListModel.remove(index)
                                    }
                                }
                            }
                        }
                    }
                    ModernButton {
                        id: btnGen2
                        Layout.fillWidth: true; implicitHeight: 40; text: "⚙️ 生成上述指定文件的白底图"
                        onClicked: {
                            if (selectedIndependentFiles.length === 0) return
                            logModel.clear()
                            statusLabel.text = "处理独立文件中..."
                            btnGen2.enabled = false
                            whiteBgProcessor.processSpecificFiles(selectedIndependentFiles, formatCombo.currentText)
                        }
                        
                        
                    }
                }
            }
        }

        // 统一输出设置
        RowLayout {
            spacing: 12
            Label { text: "共有参数 -> 目标格式:"; color: "#333333"; font.pixelSize: 14; font.bold: true }
            ComboBox { 
                id: formatCombo; implicitWidth: 150; implicitHeight: 34; model: ["PNG 背景透明", "JPG 背景纯白"]; currentIndex: 1
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; spacing: 5
            RowLayout {
                Label { text: "处理进度"; color: "#666666"; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                Label { id: statusLabel; text: "就绪"; color: "#666666"; font.pixelSize: 12 }
            }
            ProgressBar { 
                id: progressBar; Layout.fillWidth: true; value: 0
                
                contentItem: Item { 
                    implicitHeight: 6
                    Rectangle { width: progressBar.visualPosition * parent.width; height: parent.height; radius: 3; color: "#0078D4" }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
            
            // 结果列表（模式一专用的树形结果平铺显示）
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 5
                Label { text: "目录检测结果 (模式一):"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; color: "#FFFFFF"; border.color: "#CCCCCC"
                    ListView {
                        anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 4
                        model: ListModel { id: resultModel }
                        delegate: Label { text: model.text; color: model.isMissing ? "#D32F2F" : "#388E3C"; font.pixelSize: 12; width: ListView.view.width; elide: Text.ElideLeft }
                    }
                }
            }

            // 运行日志
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 5
                Label { text: "运行日志:"; color: "#333333"; font.pixelSize: 14; font.bold: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; color: "#2D2D2D"; border.color: "#CCCCCC"
                    ListView {
                        anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 4
                        model: ListModel { id: logModel }
                        delegate: Label { text: model.text; color: "#00FF00"; font.pixelSize: 12; font.family: "Consolas"; width: ListView.view.width; wrapMode: Text.Wrap }
                        onCountChanged: positionViewAtEnd()
                    }
                }
            }
        }
    }
}
