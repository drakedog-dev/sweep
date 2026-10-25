import QtQuick
import Sweep

Card {
    id: tile
    property string label: ""
    property string value: ""
    property string sub: ""
    property string icon: ""
    property var spark: []
    property color sparkColor: Theme.accent2
    property real bar: -1          // 0..1 shows a progress bar instead of a sparkline
    property bool alarm: false     // colour the bar amber/red when it is nearly full (disk space)
    pad: 18
    Column { width: parent.width; spacing: 2
        Row { spacing: 6; width: parent.width
            Icon { name: tile.icon; size: 13; color: Theme.muted; visible: tile.icon !== ""; anchors.verticalCenter: parent.verticalCenter }
            Label10 { text: tile.label; anchors.verticalCenter: parent.verticalCenter }
        }
        Txt { text: tile.value; font.pixelSize: 26; bold: true; font.weight: Font.Bold }
        Txt { text: tile.sub; muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; maximumLineCount: 1 }
        Item { width: parent.width; height: 34
            Sparkline { anchors.fill: parent; values: tile.spark; lineColor: tile.sparkColor; visible: tile.spark.length > 0 }
            Rectangle { visible: tile.bar >= 0; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: 6
                height: 6; radius: 3; color: Theme.track
                Rectangle { height: parent.height; radius: 3; width: parent.width * Math.max(0, Math.min(1, tile.bar))
                    color: tile.alarm && tile.bar > 0.9 ? Theme.bad : tile.alarm && tile.bar > 0.75 ? Theme.warn : tile.sparkColor
                    Behavior on width { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutCubic } } } }
        }
    }
}
