import QtQuick
import Sweep

Rectangle {
    id: row
    property string title: ""
    property string hint: ""
    property string meta: ""
    property bool checked: false
    property bool disabledLook: false
    signal toggled(bool value)
    width: parent ? parent.width : 400
    implicitHeight: col.implicitHeight + 18
    radius: Theme.radiusSm
    color: ma.containsMouse ? Theme.cardAlt : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }
    opacity: disabledLook ? 0.55 : 1
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { sw.checked = !sw.checked; row.checked = sw.checked; row.toggled(sw.checked) } }
    Column {
        id: col; anchors.left: parent.left; anchors.right: sw.left; anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 12; anchors.rightMargin: 16; spacing: 2
        Row { spacing: 10
            Txt { text: row.title; bold: true; font.pixelSize: 14 }
            Txt { text: row.meta; font.pixelSize: 14; color: Theme.accent2; visible: row.meta !== "" }
        }
        Txt { text: row.hint; muted: true; font.pixelSize: 12; width: col.width; visible: row.hint !== "" }
    }
    Toggle { id: sw; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; checked: row.checked; onToggled: v => { row.checked = v; row.toggled(v) } }
}
