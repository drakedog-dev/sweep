import QtQuick
import Sweep

// Window-modal card over the whole app: dims the background and blocks clicks behind it.
Item {
    id: m
    property bool open: false
    property int boxWidth: 620
    property string icon: ""
    property string title: ""
    property string subtitle: ""
    default property alias content: body.data
    anchors.fill: parent
    z: 100
    visible: opacity > 0.01
    opacity: open ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.dur } }
    Rectangle { anchors.fill: parent; color: "#000000"; opacity: Theme.dark ? 0.62 : 0.38 }
    MouseArea { anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.AllButtons; onWheel: wheel => wheel.accepted = true }
    Rectangle {
        id: box
        width: Math.min(m.boxWidth, m.width - 48)
        height: head.implicitHeight + body.implicitHeight + 76
        anchors.centerIn: parent
        radius: 22; color: Theme.card; border.color: Theme.border
        scale: m.open ? 1 : 0.94
        Behavior on scale { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutCubic } }
        Rectangle { z: -1; anchors.fill: parent; anchors.topMargin: 12; radius: parent.radius; color: "#000000"; opacity: 0.35 }
        Row { id: head; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 28; spacing: 16
            Rectangle { width: 52; height: 52; radius: 15; visible: m.icon !== ""
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent3 } }
                Icon { anchors.centerIn: parent; name: m.icon; size: 26; color: "white" } }
            Column { width: head.width - 70; spacing: 3; anchors.verticalCenter: parent.verticalCenter
                Txt { text: m.title; font.pixelSize: 20; bold: true; font.weight: Font.Bold; width: parent.width }
                Txt { text: m.subtitle; muted: true; width: parent.width; visible: m.subtitle !== "" } }
        }
        Column { id: body; anchors.left: parent.left; anchors.right: parent.right; anchors.top: head.bottom; anchors.topMargin: 20; anchors.leftMargin: 28; anchors.rightMargin: 28; spacing: 16 }
    }
}
