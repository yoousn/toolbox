import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../tools_config.js" as Tools

Rectangle {
    id: root
    color: "#FFFFFF"

    // currentIndex 是"拍平后"的工具索引,与 Main.qml 的 StackLayout 对应
    property int currentIndex: 0

    // 当前选中分类(用于折叠/展开,默认全部展开)
    property var expandedCategories: ({})

    Component.onCompleted: {
        var init = {}
        for (var i = 0; i < Tools.categories.length; i++) {
            init[Tools.categories[i].id] = true
        }
        root.expandedCategories = init
    }

    function toggleCategory(catId) {
        var copy = {}
        for (var k in root.expandedCategories) copy[k] = root.expandedCategories[k]
        copy[catId] = !copy[catId]
        root.expandedCategories = copy
    }

    function globalIndexOf(catIdx, toolIdx) {
        var idx = 0
        for (var i = 0; i < catIdx; i++) {
            idx += Tools.categories[i].tools.length
        }
        return idx + toolIdx
    }

    // 右侧分割线
    Rectangle {
        width: 1
        color: "#E0E0E0"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 8

        Label {
            text: "⚙️ 办公整合工具箱"
            font.pixelSize: 18
            font.bold: true
            color: "#0078D4"
            Layout.fillWidth: true
            elide: Text.ElideRight
            Layout.bottomMargin: 8
        }

        // 分类列表(可滚动)
        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                // 关键:用 ScrollView 的 availableWidth 作为宽度,确保子项有正确尺寸
                width: scroll.availableWidth
                spacing: 4

                Repeater {
                    model: Tools.categories

                    delegate: ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        readonly property var category: modelData
                        readonly property int categoryIndex: index
                        readonly property bool expanded: root.expandedCategories[category.id] === true
                        readonly property bool hasTools: category.tools.length > 0

                        // 分类标题
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 36
                            radius: 6
                            color: catHover.containsMouse ? "#F2F2F2" : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 6

                                Label {
                                    text: (category.icon || "") + " " + category.name
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: "#666666"
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: hasTools ? (expanded ? "▾" : "▸") : "·"
                                    color: "#999999"
                                    font.pixelSize: 12
                                }
                            }

                            MouseArea {
                                id: catHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: hasTools ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: if (hasTools) root.toggleCategory(category.id)
                            }
                        }

                        // 该分类下的工具列表
                        Repeater {
                            model: expanded ? category.tools : []
                            delegate: Rectangle {
                                id: toolItem
                                Layout.fillWidth: true
                                implicitHeight: 38
                                radius: 6

                                readonly property int globalIdx: root.globalIndexOf(categoryIndex, index)
                                readonly property bool selected: root.currentIndex === globalIdx

                                color: selected ? "#EAF4FC"
                                                : (toolHover.containsMouse ? "#F2F2F2" : "transparent")

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    Label {
                                        text: modelData.icon || "•"
                                        font.pixelSize: 14
                                    }
                                    Label {
                                        text: modelData.name
                                        color: toolItem.selected ? "#0078D4" : "#333333"
                                        font.pixelSize: 13
                                        font.bold: toolItem.selected
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }

                                MouseArea {
                                    id: toolHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.currentIndex = toolItem.globalIdx
                                }
                            }
                        }

                        // 空分类提示
                        Label {
                            visible: expanded && !hasTools
                            text: "  (暂无工具)"
                            color: "#BBBBBB"
                            font.pixelSize: 12
                            font.italic: true
                            Layout.leftMargin: 16
                            Layout.bottomMargin: 4
                        }
                    }
                }
            }
        }

        // 底部版本号
        Label {
            text: "v1.0.0"
            color: "#BBBBBB"
            font.pixelSize: 11
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
