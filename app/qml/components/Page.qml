import QtQuick
import QtQuick.Controls
import Sweep

Item {
    id: page
    default property alias content: col.data
    property alias footer: footerRow.data
    property string title: ""
    property string subtitle: ""
    property string bigLabel: ""
    property string bigValue: ""
    property string hint: ""
    property real shift: 0
    property alias enterAnim: enterAnim
    transform: Translate { y: page.shift }
    ParallelAnimation { id: enterAnim
        NumberAnimation { target: page; property: "opacity"; from: 0; to: 1; duration: Theme.durSlow; easing.type: Easing.OutCubic }
        NumberAnimation { target: page; property: "shift"; from: 18; to: 0; duration: Theme.durSlow; easing.type: Easing.OutCubic } }
    PageHeader { id: hdr; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; title: page.title; subtitle: page.subtitle; bigLabel: page.bigLabel; bigValue: page.bigValue }
    Flickable {
        id: flick
        anchors.top: hdr.bottom; anchors.topMargin: 18; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: footerRow.visible ? footerRow.top : parent.bottom
        anchors.bottomMargin: footerRow.visible ? 12 : 0
        contentHeight: col.implicitHeight + 8; clip: true; boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; contentItem: Rectangle { implicitWidth: 6; radius: 3; color: Theme.border } }
        Column { id: col; width: flick.width - 12; spacing: 14
            Txt { text: page.hint; muted: true; width: parent.width; visible: page.hint !== ""; leftPadding: 4 }
        }
    }
    Rectangle { // fade at the bottom edge: there is more below
        anchors.left: flick.left; anchors.right: flick.right; anchors.rightMargin: 12; anchors.bottom: flick.bottom; height: 36
        visible: flick.contentHeight > flick.height + 4 && !flick.atYEnd
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(Theme.bg.r, Theme.bg.g, Theme.bg.b, 0) }
            GradientStop { position: 1; color: Theme.bg } }
    }
    Row { id: footerRow; anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.bottomMargin: 14; spacing: 10; visible: children.length > 0 }
}
