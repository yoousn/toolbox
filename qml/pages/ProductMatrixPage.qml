import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    property var currentColors: []

    FolderDialog {
        id: exportDirDlg
        title: "选择导出目录"
        currentFolder: pathInput.text ? ("file:///" + pathInput.text.replace(/\\/g, "/")) : "file:///D:/"
        onAccepted: pathInput.text = selectedFolder.toString().replace("file:///", "")
    }

    Connections {
        target: productMatrix
        function onLogMessage(msg) { logModel.append({"text": msg}) }
        function onQueueChanged() { refreshQueue() }
        function onGenerateFinished(msg) { statusLabel.text = msg; statusLabel.color = "#0078D4" }
        function onGenerateError(msg) { statusLabel.text = msg; statusLabel.color = "#D32F2F" }
    }

    function refreshQueue() {
        queueModel.clear()
        var q = productMatrix.getQueue()
        for (var i = 0; i < q.length; i++)
            queueModel.append({"mainCode": q[i].mainCode, "colors": q[i].colors, "sizeOption": q[i].sizeOption, "std": q[i].std})
    }

    function refreshColorTags() {
        colorTagModel.clear()
        for (var i = 0; i < currentColors.length; i++)
            colorTagModel.append({"color": currentColors[i]})
    }

    Component.onCompleted: {
        if (!productMatrix) return
        abbrCombo.model = productMatrix.getAbbrOptions()
        sizeCombo.model = productMatrix.getSizeOptions()
        sizeCombo.currentIndex = sizeCombo.find("M-4XL")
        stdQuickCombo.model = productMatrix.getStdQuickOptions()
        stdQuickCombo.currentIndex = stdQuickCombo.find("T恤")
        pathInput.text = productMatrix.getDefaultExportPath()
        stdInput.text = productMatrix.getSmartStd("上衣")
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 15

        // ==========================================
        // 栏目一：侧边导航区 (200px)
        // ==========================================
        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                spacing: 15

                Label { text: "大厂级商品矩阵引擎 - 老板专供版"; color: "#333333"; font.pixelSize: 18; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }

                Label { text: "导出目录:"; color: "#333333"; font.pixelSize: 13 }
                Rectangle { 
                    Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                    TextInput { id: pathInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 13; clip: true }
                }
                ModernButton { 
                    text: "📁 浏览目录"
                    Layout.fillWidth: true; implicitHeight: 34; onClicked: exportDirDlg.open()
                    
                    
                }

                Item { Layout.preferredHeight: 20 }

                Label { text: "系统状态:"; color: "#333333"; font.pixelSize: 13; font.bold: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 4; border.color: "#CCCCCC"; color: "#F4F4F4"
                    ListView {
                        anchors.fill: parent; anchors.margins: 5; clip: true; spacing: 4
                        model: ListModel { id: logModel }
                        delegate: Label { text: model.text; color: "#666666"; font.pixelSize: 11; font.family: "Consolas"; width: ListView.view ? ListView.view.width : 100; wrapMode: Text.Wrap }
                        onCountChanged: positionViewAtEnd()
                    }
                }
            }
        }

        // ==========================================
        // 栏目二：属性录入区 (卡片式)
        // ==========================================
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 15

                Label { text: "⚙️ 1. 全局默认属性配置 (自动继承)"; color: "#333333"; font.pixelSize: 15; font.bold: true }
                
                GridLayout {
                    columns: 2
                    columnSpacing: 20
                    rowSpacing: 10
                    Layout.fillWidth: true

                    // 左列
                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "尺码范围 (第二属性):"; color: "#333333"; font.pixelSize: 12 }
                        ComboBox { 
                            id: sizeCombo; Layout.fillWidth: true; implicitHeight: 34; 
                            
                            
                        }
                    }
                    // 右列
                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "商品简称:"; color: "#333333"; font.pixelSize: 12 }
                        ComboBox { 
                            id: abbrCombo; Layout.fillWidth: true; implicitHeight: 34; 
                            onCurrentTextChanged: { if(productMatrix) stdInput.text = productMatrix.getSmartStd(currentText) }
                            
                            
                        }
                    }

                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "基本单位:"; color: "#333333"; font.pixelSize: 12 }
                        Rectangle { 
                            Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: unitInput; text: "广州白云区柏纯服装厂"; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12; clip: true }
                        }
                    }
                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "产地:"; color: "#333333"; font.pixelSize: 12 }
                        Rectangle { 
                            Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: originInput; text: "广州市白云区松洲街松北李祠前街38号301"; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12; clip: true }
                        }
                    }

                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "成份:"; color: "#333333"; font.pixelSize: 12 }
                        Rectangle { 
                            Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: compInput; text: "其他材质100%"; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12 }
                        }
                    }
                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "供应商:"; color: "#333333"; font.pixelSize: 12 }
                        Rectangle { 
                            Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: supplierInput; text: "广州白云区柏纯服装厂"; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12 }
                        }
                    }

                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "执行标准快捷选择:"; color: "#333333"; font.pixelSize: 12 }
                        ComboBox { 
                            id: stdQuickCombo; Layout.fillWidth: true; implicitHeight: 34
                            onCurrentTextChanged: { if(productMatrix) stdInput.text = productMatrix.getStdByQuick(currentText) }
                            
                            
                        }
                    }
                    ColumnLayout {
                        spacing: 4; Layout.fillWidth: true
                        Label { text: "最终执行标准 (可手改):"; color: "#333333"; font.pixelSize: 12 }
                        Rectangle { 
                            Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                            TextInput { id: stdInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12; clip: true }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#EEEEEE"; Layout.topMargin: 10; Layout.bottomMargin: 5 }

                Label { text: "📝 2. 单品实例化 (每次入队将锁定上方属性)"; color: "#333333"; font.pixelSize: 15; font.bold: true }

                RowLayout {
                    spacing: 10
                    Label { text: "主商家编码:"; color: "#333333"; font.pixelSize: 12 }
                    Rectangle { 
                        Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        TextInput { id: codeInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter; color: "#333333"; font.pixelSize: 12
                            KeyNavigation.tab: customColorInput
                        } 
                    }
                }

                RowLayout {
                    spacing: 12
                    Layout.fillWidth: true
                    ComboBox { 
                        id: colorCombo; Layout.preferredWidth: 250; implicitHeight: 34
                        model: ["--选择颜色自动添加--"].concat(productMatrix ? productMatrix.getColorPresets() : [])
                        onCurrentTextChanged: { 
                            if(currentText && currentText !== "--选择颜色自动添加--"){ 
                                if(currentColors.indexOf(currentText) === -1){ currentColors.push(currentText); refreshColorTags() }
                                currentIndex = 0 
                            } 
                        }
                    }
                    Rectangle { 
                        Layout.fillWidth: true; implicitHeight: 34; radius: 4; border.color: "#CCCCCC"; color: "#FFFFFF"
                        TextInput { 
                            id: customColorInput; anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: TextInput.AlignVCenter
                            color: "#999999"; font.pixelSize: 12; text: "自定义颜色回车添加"
                            onFocusChanged: { if(focus && text==="自定义颜色回车添加"){ text=""; color="#333333" } else if(!focus && text===""){ text="自定义颜色回车添加"; color="#999999" } }
                            onAccepted: { 
                                if(text.trim() && text !== "自定义颜色回车添加"){ 
                                    currentColors.push(text.trim()); refreshColorTags(); text=""
                                } 
                            } 
                        } 
                    }
                }

                Label { text: "已选颜色 (双击标签删除):"; color: "#666666"; font.pixelSize: 12 }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "transparent"; clip: true
                    Flickable {
                        id: tagsFlick
                        anchors.fill: parent
                        contentWidth: width
                        contentHeight: flowLayout.implicitHeight
                        clip: true
                        ScrollBar.vertical: ScrollBar { width: 8; active: true }
                        Flow {
                            id: flowLayout
                            width: tagsFlick.width
                            spacing: 8
                            Repeater {
                                model: ListModel { id: colorTagModel }
                                Rectangle { 
                                    width: tagL.implicitWidth + 20; height: 26; radius: 13; color: "#EAF4FC"; border.color: "#0078D4"; border.width: 1
                                    Label { id: tagL; anchors.centerIn: parent; text: model.color; color: "#0078D4"; font.pixelSize: 12 }
                                    MouseArea { anchors.fill: parent; onDoubleClicked: { currentColors.splice(index, 1); refreshColorTags() } }
                                }
                            }
                        }
                    }
                }

                ModernButton {
                    Layout.fillWidth: true; implicitHeight: 46; text: "⬇️ 将此商品录入队列 (生成快照) ⬇️"
                    onClicked: { 
                        productMatrix.addToQueue(codeInput.text, currentColors, sizeCombo.currentText, abbrCombo.currentText, unitInput.text, originInput.text, compInput.text, stdInput.text, supplierInput.text)
                        codeInput.text = ""; currentColors = []; refreshColorTags() 
                    }
                    
                    
                }
            }
        }

        // ==========================================
        // 栏目三：任务队列面板 (350px)
        // ==========================================
        Rectangle {
            Layout.preferredWidth: 350
            Layout.fillHeight: true
            radius: 8
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 15

                Label { text: "📦 3. 待生成矩阵队列"; color: "#333333"; font.pixelSize: 15; font.bold: true }

                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; border.color: "#E0E0E0"; color: "#FFFFFF"
                    clip: true
                    
                    // 表头
                    Rectangle {
                        id: header
                        width: parent.width; height: 28; color: "#F0F0F0"; border.color: "#E0E0E0"
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 5; spacing: 5
                            Label { text: "商家编码"; color: "#333333"; font.pixelSize: 12; font.bold: true; Layout.preferredWidth: 100 }
                            Label { text: "颜色集"; color: "#333333"; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true }
                            Label { text: "尺码规"; color: "#333333"; font.pixelSize: 12; font.bold: true; Layout.preferredWidth: 60 }
                        }
                    }

                    ListView {
                        id: queueView; width: parent.width; anchors.top: header.bottom; anchors.bottom: parent.bottom; clip: true
                        model: ListModel { id: queueModel }
                        delegate: Rectangle {
                            width: queueView.width; height: 32; color: queueView.currentIndex === index ? "#EAF4FC" : (index % 2 === 0 ? "#FAFAFA" : "#FFFFFF")
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 5; anchors.rightMargin: 5; spacing: 5
                                Label { text: model.mainCode; color: "#333333"; font.pixelSize: 12; Layout.preferredWidth: 100 }
                                Label { text: model.colors; color: "#666666"; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: model.sizeOption; color: "#333333"; font.pixelSize: 12; Layout.preferredWidth: 60 }
                            }
                            MouseArea { anchors.fill: parent; onClicked: queueView.currentIndex = index }
                        }
                    }
                }

                ModernButton {
                    text: "🗑️ 移除选中商品"
                    Layout.fillWidth: true; implicitHeight: 38
                    onClicked: { if(queueView.currentIndex >= 0) productMatrix.deleteFromQueue(queueView.currentIndex) }
                    
                    
                }

                Label { id: statusLabel; text: "准备就绪"; color: "#666666"; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }

                ModernButton {
                    text: "🚀 严格按快照一键生成 Excel"
                    Layout.fillWidth: true; implicitHeight: 50
                    onClicked: productMatrix.generateExcel(pathInput.text)
                    
                    
                }
            }
        }
    }
}
