import QtQuick
import Sweep

Card {
    property string label: ""
    property string value: ""
    property string sub: ""
    property var spark: []
    property color sparkColor: Theme.accent2
    pad: 18
    Column { width: parent.width; spacing: 2
        Label10 { text: label }
        Txt { text: value; font.pixelSize: 26; bold: true; font.weight: Font.Bold }
        Txt { text: sub; muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; maximumLineCount: 2 }
        Sparkline { width: parent.width; height: 34; values: spark; lineColor: sparkColor; visible: spark.length > 0 }
    }
}
