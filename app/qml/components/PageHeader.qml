import QtQuick
import Sweep

GradRect {
    id: hero
    property string title: ""
    property string subtitle: ""
    property string bigLabel: ""
    property string bigValue: ""
    height: 96; radius: 20
    stops: [[0, Qt.darker(Theme.accent, 1.35)], [0.55, Theme.accent], [1, Theme.accent3]]
    shine: 0.18                      // soft light from the top
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
