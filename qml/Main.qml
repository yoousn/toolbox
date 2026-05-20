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

    Connections {
        target: updateChecker
        function onUpdateAvailable(version, url, notes) {
            latestVersion = version
            downloadUrl = url
            releaseNotes = notes
            updateDialog.open()
        }
    }

    // 更新提示弹窗
    Dialog {
        id: updateDialog
        title: "发现新版本"
        anchors.centerIn: parent
        width: 420
        modal: true
        standardButtons: Dialog.NoButton

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
                text: releaseNotes || "有新的更新可用,建议下载最新版本。"
                font.pixelSize: 13
                color: "#333333"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.maximumHeight: 120
                elide: Text.ElideRight
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }
                ModernButton {
                    text: "稍后再说"
                    implicitHeight: 36
                    implicitWidth: 100
                    onClicked: updateDialog.close()
                }
                ModernButton {
                    text: "📥 下载更新"
                    implicitHeight: 36
                    implicitWidth: 120
                    onClicked: {
                        Qt.openUrlExternally(downloadUrl)
                        updateDialog.close()
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
