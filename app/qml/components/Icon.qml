import QtQuick
import Sweep

// One glyph from the bundled Lucide icon font: Icon { name: "trash-2"; size: 18 }
Text {
    property string name: ""
    property int size: 18
    text: Theme.icon(name)
    font.family: Theme.iconFont
    font.pixelSize: size
    color: Theme.text
    width: size; height: size
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    Behavior on color { ColorAnimation { duration: Theme.dur } }
}
