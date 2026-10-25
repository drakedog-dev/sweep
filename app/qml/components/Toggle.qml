import QtQuick
import Sweep

Item {
    id: tg
    property bool checked: false
    signal toggled(bool value)
    width: 46; height: 26
    Rectangle { anchors.fill: parent; radius: 13; color: Theme.track; Behavior on color { ColorAnimation { duration: Theme.dur } } }
    Rectangle {
        anchors.fill: parent; radius: 13
        opacity: tg.checked ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.dur } }
        gradient: Gradient { orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
    }
    Rectangle {
        width: 20; height: 20; radius: 10; y: 3
        x: tg.checked ? parent.width - width - 3 : 3
        color: tg.checked ? "white" : Theme.knobOff
        border.width: tg.checked || Theme.dark ? 0 : 1; border.color: "#A79FD6"
        Behavior on x { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutBack } }
        Behavior on color { ColorAnimation { duration: Theme.dur } }
    }
    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { tg.checked = !tg.checked; tg.toggled(tg.checked) } }
}
