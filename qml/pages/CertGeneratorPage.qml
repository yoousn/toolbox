import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"

    FileDialog {
        id: imageFileDlg
        title: "选择模板图片"
        currentFolder: "file:///D:/Desktop/上款"
        onAccepted: imageInput.text = selectedFile.toString().replace("file:///", "")
    }

    FolderDialog {
        id: rootDirDlg
        title: "选择工作子主目录"
        currentFolder: certGenerator.getDefaultBrowseFolder() ? ("file:///" + certGenerator.getDefaultBrowseFolder()) : "file:///D:/"
        onAccepted: { 
            rootInput.text = selectedFolder.toString().replace("file:///", "")
            certGenerator.setSelectedFolder(rootInput.text)
        }
    }

    Connections {
        target: certGenerator
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onGenerateFinished(success, fail) { 
            statusLabel.text = "完成: 成功 " + success + " 个，失败 " + fail + " 个"; 
            statusLabel.color = fail > 0 ? "#D32F2F" : "#107C41" 
        }
        function onSubdirsDetected(texts) {
            textListModel.clear()
            for(var i=0; i<texts.length; i++){
                textListModel.append({"value": texts[i]})
            }
        }
    }

    ListModel { id: textListModel }

    Component.onCompleted: {
        // Initialize with default values
        imageInput.text = certGenerator.getImagePath()
        rootInput.text = certGenerator.getDefaultBrowseFolder()
        certGenerator.setSelectedFolder(rootInput.text)
        
        // Add 5 empty inputs by default like original
        for(var i=0; i<5; i++){ textListModel.append({"value": ""}) }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        Label { text: "📑 合格证生成器 - 批量生成带文字图片"; color: "#333333"; font.pixelSize: 20; font.bold: true }

        // 1. 目录设置
        Rectangle {
            Layout.fillWidth: true; Layout.minimumHeight: 110; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 15; spacing: 12
                Label { text: "📁 1. 目录设置"; color: "#333333"; font.pixelSize: 15; font.bold: true }
                RowLayout {
                    spacing: 10
                    Label { text: "工作主目录:"; color: "#333333"; font.pixelSize: 13; Layout.preferredWidth: 80 }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        TextInput { id: rootInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; onTextChanged: certGenerator.setSelectedFolder(text) }
                    }
                    ModernButton { text: "浏览目录..."; implicitHeight: 34; implicitWidth: 100; onClicked: rootDirDlg.open() }
                }
                ModernButton {
                    Layout.fillWidth: true; implicitHeight: 36; text: "🔍 检查并提取子目录填写文字"
                    onClicked: { certGenerator.checkSubdirectories() }
                    
                    
                }
            }
        }

        // 2. 文本列表
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 15; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "📝 2. 要生成的文本"; color: "#333333"; font.pixelSize: 15; font.bold: true }
                    Item { Layout.fillWidth: true }
                    ModernButton { text: "+ 增加输入框"; implicitHeight: 30; implicitWidth: 100; onClicked: textListModel.append({"value": ""}) }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "transparent"
                    ListView {
                        anchors.fill: parent; clip: true; spacing: 8; model: textListModel
                        delegate: RowLayout {
                            width: ListView.view.width - 20; height: 34
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                                TextInput { 
                                    anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; text: model.value; 
                                    onTextChanged: { model.value = text }
                                }
                            }
                            Rectangle {
                                width: 34; height: 34; radius: 4; color: "#FFF0F0"; border.color: "#FFCDD2"
                                Label { anchors.centerIn: parent; text: "X"; color: "#D32F2F"; font.bold: true }
                                MouseArea { anchors.fill: parent; onClicked: textListModel.remove(index) }
                            }
                        }
                    }
                }
            }
        }

        // 3. 模板与生成
        Rectangle {
            Layout.fillWidth: true; Layout.minimumHeight: 120; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 15; spacing: 12
                Label { text: "🖼️ 3. 模板及生成设置"; color: "#333333"; font.pixelSize: 15; font.bold: true }
                RowLayout {
                    spacing: 10
                    Label { text: "模板图片:"; color: "#333333"; font.pixelSize: 13; Layout.preferredWidth: 80 }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        TextInput { id: imageInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; onTextChanged: certGenerator.setImagePath(text) }
                    }
                    ModernButton { text: "选择图片..."; implicitHeight: 34; implicitWidth: 100; onClicked: imageFileDlg.open() }
                }
            }
        }

        ModernButton {
            Layout.fillWidth: true; implicitHeight: 46; text: "🚀 批 量 生 成"
            onClicked: { 
                logModel.clear()
                statusLabel.text = "生成中..."
                statusLabel.color = "#333333"
                
                var texts = []
                for(var i=0; i<textListModel.count; i++){
                    texts.push(textListModel.get(i).value)
                }
                certGenerator.batchGenerate(texts)
            }
            
            
        }

        RowLayout {
            Label { text: "执行日志:"; color: "#333333"; font.pixelSize: 13 }
            Item { Layout.fillWidth: true }
            Label { id: statusLabel; text: "就绪"; color: "#0078D4"; font.pixelSize: 13 }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: 4; color: "#F4F4F4"; border.color: "#CCCCCC"
            ListView {
                anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 4
                model: ListModel { id: logModel }
                delegate: Label { text: model.text; color: "#333333"; font.pixelSize: 12; font.family: "Consolas"; width: ListView.view.width; wrapMode: Text.Wrap }
                onCountChanged: positionViewAtEnd()
            }
        }
    }
}
