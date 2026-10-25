import QtQuick
import Sweep

Item {
    id: tg
    property bool checked: false
    signal toggled(bool value)
    width: 46; height: 26
    Rectangle {
        anchors.fill: parent; radius: 13
        gradient: tg.checked ? g : null
        color: tg.checked ? "transparent" : Theme.track
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Gradient { id: g; orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
        Rectangle {
            width: 20; height: 20; radius: 10; y: 3
            x: tg.checked ? parent.width - width - 3 : 3
            color: tg.checked ? "white" : "#CBD5E1"
            Behavior on x { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutBack } }
        }
    }
    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { tg.checked = !tg.checked; tg.toggled(tg.checked) } }
}
