import QtQuick
import Sweep

Text {
    property bool muted: false
    property bool bold: false
    color: muted ? Theme.muted : Theme.text
    font.family: Theme.font
    font.pixelSize: 13
    font.weight: bold ? Font.DemiBold : Font.Normal
    wrapMode: Text.WordWrap
    renderType: Text.NativeRendering
    Behavior on color { ColorAnimation { duration: Theme.dur } }
}
