import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import "components"
import "tools_config.js" as Tools

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1400
    height: 800
    title: "工具箱整合版"
    color: "#F5F6F8"

    // 拍平后的工具列表(供主内容区按索引取页面路径)
    property var allTools: Tools.flatTools()

    // 更新检查
    property string latestVersion: ""
    property string downloadUrl: ""
    property string releaseNotes: ""
    property bool updateDownloading: false
    property bool updateReady: false

    Connections {
        target: updateChecker
        function onUpdateAvailable(version, url, notes) {
            latestVersion = version
            downloadUrl = url
            releaseNotes = notes
            updateDialog.open()
        }
        function onDownloadProgress(pct, label) {
            updateBar.value = pct / 100
            updateStatusLabel.text = label
        }
        function onDownloadFinished() {
            updateDownloading = false
            updateReady = true
            updateStatusLabel.text = "下载完成,点击安装更新"
            updateBar.value = 1
        }
        function onDownloadFailed(err) {
            updateDownloading = false
            updateStatusLabel.text = "失败: " + err
            updateStatusLabel.color = "#D32F2F"
        }
    }

    // 更新提示弹窗
    Dialog {
        id: updateDialog
        title: "发现新版本"
        anchors.centerIn: parent
        width: 440
        modal: true
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                text: "🎉 新版本 v" + latestVersion + " 可用"
                font.pixelSize: 16
                font.bold: true
                color: "#0078D4"
            }
            Label {
                text: "当前版本: v" + appVersion
                font.pixelSize: 13
                color: "#666666"
            }
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#E0E0E0"
            }
            Label {
                text: releaseNotes || "有新的更新可用,建议更新到最新版本。"
                font.pixelSize: 12
                color: "#333333"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.maximumHeight: 80
                elide: Text.ElideRight
            }

            // 下载进度区
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                visible: updateDownloading || updateReady

                ProgressBar {
                    id: updateBar
                    Layout.fillWidth: true
                    from: 0; to: 1; value: 0
                    contentItem: Item {
                        implicitHeight: 6
                        Rectangle { width: updateBar.visualPosition * parent.width; height: parent.height; radius: 3; color: "#0078D4" }
                    }
                }
                Label {
                    id: updateStatusLabel
                    text: "准备下载..."
                    color: "#555555"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }

            // 按钮行
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }

                ModernButton {
                    text: "稍后再说"
                    implicitHeight: 36
                    implicitWidth: 100
                    visible: !updateDownloading
                    onClicked: updateDialog.close()
                }
                ModernButton {
                    text: updateReady ? "🔄 安装并重启" : (updateDownloading ? "下载中..." : "📥 立即更新")
                    implicitHeight: 36
                    implicitWidth: 130
                    enabled: !updateDownloading
                    onClicked: {
                        if (updateReady) {
                            updateChecker.applyUpdate()
                        } else {
                            updateDownloading = true
                            updateStatusLabel.color = "#555555"
                            updateStatusLabel.text = "连接中..."
                            updateBar.value = 0
                            updateChecker.downloadUpdate(downloadUrl)
                        }
                    }
                }
                ModernButton {
                    text: "取消"
                    implicitHeight: 36
                    implicitWidth: 70
                    visible: updateDownloading
                    onClicked: {
                        updateChecker.cancelDownload()
                        updateDownloading = false
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideBar {
            id: sideBar
            Layout.fillHeight: true
            Layout.preferredWidth: 260
        }

        // 主内容区:用 Loader 按需加载页面,新增工具不用改这里
        StackLayout {
            id: mainStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 20
            currentIndex: sideBar.currentIndex

            Repeater {
                model: mainWindow.allTools
                delegate: Loader {
                    // 全部预加载,避免页面切换时丢失内部状态
                    source: modelData.page
                }
            }
        }
    }
}
