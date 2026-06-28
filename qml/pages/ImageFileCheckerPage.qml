import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    ListModel { id: entryModel; Component.onCompleted: { for(var i=0; i<5; i++) append({"value": ""}) } }

    FolderDialog {
        id: folderDlg
        title: "选择目标文件夹"
        currentFolder: imageFileChecker.getDefaultFolder() ? ("file:///" + imageFileChecker.getDefaultFolder().replace(/\\/g, "/")) : "file:///D:/"
        onAccepted: {
            folderInput.text = selectedFolder.toString().replace("file:///", "")
            imageFileChecker.rememberDefaultFolder(folderInput.text)
        }
    }

    FolderDialog {
        id: restoreFolderDlg
        title: "选择恢复目标文件夹"
        currentFolder: imageFileChecker.getDefaultFolder() ? ("file:///" + imageFileChecker.getDefaultFolder().replace(/\\/g, "/")) : "file:///D:/"
        onAccepted: { imageFileChecker.restoreFiles(getSelectedRecycleNames(), false, selectedFolder.toString().replace("file:///", "")) }
    }

    function getFilenames() {
        var names = []
        for (var i = 0; i < entryRepeater.count; i++) {
            var item = entryRepeater.itemAt(i)
            if (item && item.inputValue) {
                var t = item.inputValue.trim()
                if (t) names.push(t)
            }
        }
        return names
    }

    function getSelectedRecycleNames() {
        var names = []
        var items = imageFileChecker.getDeletedFiles()
        for (var i = 0; i < recycleList.count; i++) {
            if (recycleList.itemAtIndex(i) && recycleList.itemAtIndex(i).selected)
                names.push(items[i].recycleName)
        }
        return names
    }

    Connections {
        target: imageFileChecker
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onOperationFinished(msg) { statusLabel.text = msg }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 20

        // 区域一：目标文件夹选择
        Rectangle {
            Layout.fillWidth: true; height: 60; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
            RowLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 10
                Label { text: "目标文件夹:"; color: "#333333"; font.pixelSize: 14 }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                    TextInput { 
                        id: folderInput; anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; text: imageFileChecker.getDefaultFolder() 
                    }
                }
                ModernButton {
                    text: "浏览..."
                    implicitHeight: 34; implicitWidth: 80
                    onClicked: folderDlg.open()
                    
                    
                }
            }
        }

        // 区域二：文件名输入
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 250; radius: 6; color: "#FFFFFF"; border.color: "#E0E0E0"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 10
                RowLayout {
                    Label { text: "要操作的文件名 (不含.jpg)"; color: "#333333"; font.pixelSize: 14; Layout.fillWidth: true }
                    ModernButton {
                        text: "+"
                        implicitHeight: 30; implicitWidth: 40
                        onClicked: { entryModel.append({"value": ""}) }
                        
                        
                    }
                }
                Flickable {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentHeight: entryCol.height
                    ColumnLayout {
                        id: entryCol; width: parent.width; spacing: 8
                        Repeater {
                            id: entryRepeater; model: entryModel
                            RowLayout {
                                property alias inputValue: inputField.text
                                Layout.fillWidth: true; height: 34
                                Rectangle {
                                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; color: "#FFFFFF"; border.color: "#CCCCCC"
                                    TextInput {
                                        id: inputField
                                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; verticalAlignment: TextInput.AlignVCenter
                                        color: "#333333"; font.pixelSize: 13; text: model.value
                                    }
                                }
                                Rectangle {
                                    width: 34; height: 34; radius: 4; color: "#FFF0F0"; border.color: "#FFCDD2"
                                    Label { anchors.centerIn: parent; text: "X"; color: "#D32F2F"; font.bold: true }
                                    MouseArea { anchors.fill: parent; onClicked: entryModel.remove(index) }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 区域三：操作按钮
        RowLayout {
            Layout.fillWidth: true; height: 46; spacing: 10
            ModernButton {
                Layout.fillWidth: true; implicitHeight: 40; text: "检查文件"
                onClicked: { logModel.clear(); imageFileChecker.checkFiles(folderInput.text, getFilenames()) }
                
                
            }
            ModernButton {
                Layout.fillWidth: true; implicitHeight: 40; text: "删除文件 (移至回收站)"
                onClicked: { logModel.clear(); imageFileChecker.deleteFiles(folderInput.text, getFilenames()) }
                
                
            }
            ModernButton {
                Layout.fillWidth: true; implicitHeight: 40; text: "恢复文件"
                onClicked: {
                    var items = imageFileChecker.getDeletedFiles()
                    if (items.length === 0) { statusLabel.text = "没有可恢复的文件"; return }
                    recycleModel.clear()
                    for (var i = 0; i < items.length; i++) recycleModel.append({"name": items[i].recycleName, "orig": items[i].originalPath, "sel": false})
                    restorePopup.open()
                }
                
                
            }
        }

        Label { id: statusLabel; text: "准备就绪"; color: "#0078D4"; font.pixelSize: 13 }

        // 区域四：日志输出
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; color: "#F4F4F4"; border.color: "#CCCCCC"
            ListView {
                anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 4
                model: ListModel { id: logModel }
                delegate: Label { 
                    text: model.text; color: "#333333"; font.pixelSize: 12
                    font.family: "Consolas"; width: ListView.view ? ListView.view.width : 100; wrapMode: Text.Wrap 
                }
                onCountChanged: positionViewAtEnd()
            }
        }
    }

    // 恢复弹窗
    Popup {
        id: restorePopup
        anchors.centerIn: parent
        width: 500; height: 350; modal: true
        
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 15; spacing: 10
            Label { text: "可恢复的文件"; color: "#333333"; font.pixelSize: 16; font.bold: true }
            ListView {
                id: recycleList
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                model: ListModel { id: recycleModel }
                delegate: Rectangle {
                    property bool selected: false
                    width: recycleList.width; height: 32; radius: 4
                    color: selected ? "#EAF4FC" : "#FFFFFF"
                    border.color: selected ? "#0078D4" : "#E0E0E0"
                    Label { 
                        anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 10
                        text: model.name; color: "#333333"; font.pixelSize: 13; elide: Text.ElideRight; width: parent.width - 20 
                    }
                    MouseArea { anchors.fill: parent; onClicked: parent.selected = !parent.selected }
                }
            }
            RowLayout {
                spacing: 15
                ModernButton {
                    Layout.fillWidth: true; text: "恢复到原位置"; implicitHeight: 36
                    onClicked: {
                        var names = []
                        for (var i = 0; i < recycleList.count; i++) { 
                            var item = recycleList.itemAtIndex(i)
                            if (item && item.selected) names.push(recycleModel.get(i).name) 
                        }
                        if (names.length > 0) { imageFileChecker.restoreFiles(names, true, ""); restorePopup.close() }
                    }
                    
                    
                }
                ModernButton {
                    Layout.fillWidth: true; text: "自定义目录恢复"; implicitHeight: 36
                    onClicked: restoreFolderDlg.open()
                    
                    
                }
            }
        }
    }
}
