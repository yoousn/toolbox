import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string bgColor: "#5D9CEC" // Soft blue
    property string hoverColor: "#4A89DC"
    property string pressedColor: "#3B73C4"
    property string textColor: "#FFFFFF"
    
    property string shadowColor: Qt.darker(bgColor, 1.2)

    background: Item {
        implicitHeight: 40
        implicitWidth: 120
        
        Rectangle {
            id: shadowRect
            anchors.fill: parent
            anchors.topMargin: control.pressed ? 2 : 4
            radius: 6
            color: control.enabled ? control.shadowColor : "#B0B0B0"
            Behavior on anchors.topMargin { NumberAnimation { duration: 100 } }
        }
        
        Rectangle {
            id: mainRect
            anchors.fill: parent
            anchors.bottomMargin: control.pressed ? 0 : 4
            radius: 6
            color: control.enabled ? (control.pressed ? control.pressedColor : (control.hovered ? control.hoverColor : control.bgColor)) : "#D0D0D0"
            Behavior on anchors.bottomMargin { NumberAnimation { duration: 100 } }
            Behavior on color { ColorAnimation { duration: 100 } }
        }
    }

    contentItem: Label {
        text: control.text
        color: control.enabled ? control.textColor : "#F0F0F0"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 14
        font.bold: true
        anchors.verticalCenterOffset: control.pressed ? 2 : 0
        Behavior on anchors.verticalCenterOffset { NumberAnimation { duration: 100 } }
    }
}
