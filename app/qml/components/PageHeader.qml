import QtQuick
import Sweep

Rectangle {
    id: hero
    property string title: ""
    property string subtitle: ""
    property string bigLabel: ""
    property string bigValue: ""
    height: 96; radius: 20
    gradient: Gradient { orientation: Gradient.Horizontal
        GradientStop { position: 0; color: Qt.darker(Theme.accent, 1.35) }
        GradientStop { position: 0.55; color: Theme.accent }
        GradientStop { position: 1; color: Theme.accent3 } }
    Rectangle { // soft light sweep
        anchors.fill: parent; radius: parent.radius; opacity: 0.18
        gradient: Gradient { orientation: Gradient.Vertical; GradientStop { position: 0; color: "white" } GradientStop { position: 1; color: "transparent" } }
    }
    Column { anchors.left: parent.left; anchors.leftMargin: 26; anchors.verticalCenter: parent.verticalCenter; spacing: 2
        width: hero.width - 26 - (bigBox.visible ? bigBox.width + 22 + 18 : 26)
        Text { text: hero.title; color: "white"; font.family: Theme.font; font.pixelSize: 26; font.weight: Font.Bold; renderType: Text.NativeRendering
               width: parent.width; elide: Text.ElideRight }
        Text { text: hero.subtitle; color: "#E9E3FF"; font.family: Theme.font; font.pixelSize: 13; renderType: Text.NativeRendering
               width: parent.width; elide: Text.ElideRight }
    }
    Rectangle {
        id: bigBox
        anchors.right: parent.right; anchors.rightMargin: 22; anchors.verticalCenter: parent.verticalCenter
        width: bigCol.implicitWidth + 40; height: 64; radius: 16; color: "#26FFFFFF"
        visible: hero.bigValue !== ""
        Column { id: bigCol; anchors.centerIn: parent; spacing: -2
            Text { text: hero.bigLabel; color: "#E9E3FF"; font.family: Theme.font; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 0.8; renderType: Text.NativeRendering
                   font.capitalization: Font.AllUppercase }
            Text { text: hero.bigValue; color: "white"; font.family: Theme.font; font.pixelSize: 30; font.weight: Font.Bold; renderType: Text.NativeRendering }
        }
    }
}
