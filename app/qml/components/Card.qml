import QtQuick
import Sweep

Rectangle {
    id: card
    default property alias content: inner.data
    property int pad: 22
    property bool hoverGlow: false
    width: parent ? parent.width : 400
    implicitHeight: inner.implicitHeight + pad * 2
    radius: Theme.radius
    color: Theme.card
    border.color: Theme.border
    border.width: 1
    // soft shadow without GPU effects
    Rectangle { z: -1; anchors.fill: parent; anchors.topMargin: 6; anchors.leftMargin: 2; anchors.rightMargin: 2; radius: parent.radius; color: "#000000"; opacity: Theme.dark ? 0.28 : 0.08 }
    Behavior on color { ColorAnimation { duration: Theme.dur } }
    Item { id: inner; anchors.fill: parent; anchors.margins: card.pad; implicitHeight: childrenRect.height }
}
