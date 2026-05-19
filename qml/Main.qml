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
