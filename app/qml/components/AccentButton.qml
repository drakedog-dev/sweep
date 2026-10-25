import QtQuick
import QtQuick.Controls
import Sweep

Button {
    id: btn
    property bool primary: true
    property bool danger: false
    property bool compact: false
    implicitHeight: compact ? 34 : 42
    leftPadding: compact ? 14 : 22
    rightPadding: compact ? 14 : 22
    font.family: Theme.font
    font.pixelSize: compact ? 12 : 14
    font.weight: Font.DemiBold
    scale: pressed ? 0.97 : (hovered ? 1.03 : 1.0)
    Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    opacity: enabled ? 1 : 0.4
    contentItem: Text {
        text: btn.text; font: btn.font; color: primary ? "white" : Theme.text
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; renderType: Text.NativeRendering
    }
    background: Item {
        Rectangle { anchors.fill: parent; radius: Theme.radiusSm; visible: !primary; color: btn.hovered ? Theme.softHover : Theme.soft; Behavior on color { ColorAnimation { duration: Theme.dur } } }
        Rectangle { anchors.fill: parent; radius: Theme.radiusSm; visible: primary
            gradient: Gradient { orientation: Gradient.Horizontal
                GradientStop { position: 0; color: danger ? "#DC2626" : Theme.accent }
                GradientStop { position: 1; color: danger ? "#F87171" : Theme.accent2 } } }
    }
}
