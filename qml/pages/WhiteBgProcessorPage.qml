import QtQuick
import QtQuick.Controls
import "../components"
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    color: "#F5F6F8"
    property var selectedIndependentFiles: []
    property bool modelReady: u2netAvailable
    property string selectedUrl: ""
    property bool latencyTesting: false

    Connections {
        target: whiteBgProcessor
        function onU2netAvailableChanged(v) { modelReady = v }
    }

    Connections {
        target: modelDownloader
        function onProgressChanged(pct, label) {
            dlBar.value = pct / 100
            dlStatus.text = label
            dlStatus.color = "#555555"
        }
        function onSucceeded(modelId, path) {
            dlStatus.text = "下载完成,模型已就绪"
            dlStatus.color = "#388E3C"
            dlBar.value = 1
        }
        function onFailedSig(modelId, err) {
            dlStatus.text = err
            dlStatus.color = err === "已取消" ? "#888888" : "#D32F2F"
            dlBar.value = 0
            dlBtn.enabled = true
        }
        function onBusyChanged() {
            // 同步按钮启用状态(异步任务结束时)
            if (!modelDownloader.busy && modelReady === false) {
                dlBtn.enabled = true
            }
        }
    }

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

    // 模型未下载时显示的遮罩卡片
    Rectangle {
        anchors.fill: parent
        visible: !modelReady
        color: "#E6F5F6F8"

        // 用 ListModel 代替 JS 数组(ListView 对 JS 数组兼容性差)
        ListModel {
            id: mirrorModel
        }

        Component.onCompleted: {
            if (!modelReady) {
                // 立即填充镜像列表(延迟值 -2 表示等待测速)
                mirrorModel.append({ mId: "github",      mName: "GitHub 官方",   mUrl: "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",                                          mLatency: -2 })
                mirrorModel.append({ mId: "ghproxy",     mName: "GHProxy 加速",   mUrl: "https://mirror.ghproxy.com/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",             mLatency: -2 })
                mirrorModel.append({ mId: "huggingface", mName: "HuggingFace",    mUrl: "https://huggingface.co/BritishWerewolf/U-2-Net/resolve/main/u2net.onnx",                                           mLatency: -2 })
                mirrorModel.append({ mId: "sourceforge", mName: "SourceForge",    mUrl: "https://sourceforge.net/projects/bgremover-app/files/u2net/u2net.onnx/download",                                  mLatency: -2 })

                // 异步测延迟
                latencyTesting = true
                modelDownloader.testLatency()
                latencyTimeout.start()
            }
        }

        Timer {
            id: latencyTimeout
            interval: 10000
            repeat: false
            onTriggered: {
                if (latencyTesting) {
                    latencyTesting = false
                    for (var i = 0; i < mirrorModel.count; i++) {
                        if (mirrorModel.get(i).mLatency === -2)
                            mirrorModel.setProperty(i, "mLatency", -1)
                    }
                    autoSelectBest()
                }
            }
        }

        function autoSelectBest() {
            var best = -1
            var bestUrl = ""
            for (var i = 0; i < mirrorModel.count; i++) {
                var lat = mirrorModel.get(i).mLatency
                var url = mirrorModel.get(i).mUrl
                if (lat > 0 && (best === -1 || lat < best)) {
                    best = lat
                    bestUrl = url
                }
            }
            if (bestUrl !== "") selectedUrl = bestUrl
        }

        Connections {
            target: modelDownloader
            function onLatencyResult(jsonStr) {
                latencyTimeout.stop()
                var latencyData = JSON.parse(jsonStr)
                for (var i = 0; i < latencyData.length; i++) {
                    for (var j = 0; j < mirrorModel.count; j++) {
                        if (mirrorModel.get(j).mId === latencyData[i].id) {
                            mirrorModel.setProperty(j, "mLatency", latencyData[i].latency)
                            mirrorModel.setProperty(j, "mUrl", latencyData[i].url)
                            mirrorModel.setProperty(j, "mName", latencyData[i].name)
                            break
                        }
                    }
                }
                latencyTesting = false
                autoSelectBest()
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: 580
            height: 480
            radius: 10
            color: "#FFFFFF"
            border.color: "#E0E0E0"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 10

                // 标题行
                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: "🖼️ 智能白底图 - 首次使用需下载模型"
                        font.pixelSize: 16
                        font.bold: true
                        color: "#0078D4"
                        Layout.fillWidth: true
                    }
                    ModernButton {
                        text: latencyTesting ? "⏳ 测速中..." : "🔄 刷新延迟"
                        implicitHeight: 30
                        implicitWidth: 100
                        enabled: !latencyTesting
                        onClicked: {
                            latencyTesting = true
                            modelDownloader.testLatency()
                        }
                    }
                }

                Label {
                    text: "u2net 模型(约 " + modelDownloader.expectedSizeMb("u2net") + " MB),选择下载源后点击下载,或点击链接手动下载放入目录。"
                    color: "#555555"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                // 镜像源列表
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 6
                    border.color: "#E0E0E0"
                    color: "#FAFAFA"
                    clip: true

                    ListView {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6
                        model: mirrorModel

                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 42
                            radius: 6
                            color: selectedUrl === mUrl ? "#EAF4FC" : (mirrorHover.containsMouse ? "#F2F2F2" : "#FFFFFF")
                            border.color: selectedUrl === mUrl ? "#0078D4" : "#E8E8E8"

                            MouseArea {
                                id: mirrorHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: selectedUrl = mUrl

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 10
                                    // 阻止事件继续穿透到 MouseArea(避免子组件和父级冲突)
                                    Rectangle {
                                        anchors.fill: parent
                                        color: "transparent"
                                    }

                                    // 选中指示
                                    Rectangle {
                                        width: 16; height: 16; radius: 8
                                        border.color: selectedUrl === mUrl ? "#0078D4" : "#CCCCCC"
                                        border.width: 2
                                        color: "transparent"
                                        Rectangle {
                                            anchors.centerIn: parent
                                            width: 8; height: 8; radius: 4
                                            color: "#0078D4"
                                            visible: selectedUrl === mUrl
                                        }
                                    }

                                    // 源名称
                                    Label {
                                        text: mName
                                        font.pixelSize: 13
                                        font.bold: selectedUrl === mUrl
                                        color: "#333333"
                                        Layout.preferredWidth: 110
                                    }

                                    // 手动下载按钮(独立可点击区域)
                                    Text {
                                        text: "手动下载"
                                        font.pixelSize: 11
                                        color: "#0078D4"
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: Qt.openUrlExternally(mUrl)
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    // 延迟显示
                                    Label {
                                        text: {
                                            if (mLatency === -2) return latencyTesting ? "测速中..." : "等待测速..."
                                            if (mLatency < 0) return "超时"
                                            return mLatency + " ms"
                                        }
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: {
                                            if (mLatency === -2) return "#999999"
                                            if (mLatency < 0) return "#D32F2F"
                                            if (mLatency < 500) return "#388E3C"
                                            if (mLatency < 2000) return "#F57C00"
                                            return "#D32F2F"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // 手动放置提示
                Label {
                    text: "💡 也可手动下载后放入: " + modelDownloader.getModelDir("u2net")
                    color: "#888888"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                // 进度条
                ProgressBar {
                    id: dlBar
                    Layout.fillWidth: true
                    from: 0; to: 1; value: 0
                    contentItem: Item {
                        implicitHeight: 6
                        Rectangle { width: dlBar.visualPosition * parent.width; height: parent.height; radius: 3; color: "#0078D4" }
                    }
                }
                Label {
                    id: dlStatus
                    text: "选择下载源后点击下载"
                    color: "#888888"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                // 按钮行
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    ModernButton {
                        id: dlBtn
                        Layout.fillWidth: true
                        implicitHeight: 38
                        text: modelDownloader.busy ? "📥 下载中..." : "📥 开始下载"
                        enabled: !modelDownloader.busy && selectedUrl !== ""
                        onClicked: {
                            dlStatus.color = "#555555"
                            dlStatus.text = "连接中..."
                            dlBar.value = 0
                            modelDownloader.downloadFromMirror("u2net", selectedUrl)
                        }
                    }
                    ModernButton {
                        implicitHeight: 38
                        implicitWidth: 80
                        visible: modelDownloader.busy
                        text: "取消"
                        onClicked: modelDownloader.cancel()
                    }
                }
            }
        }
    }
}
