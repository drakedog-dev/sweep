import QtQuick
import Sweep

// Page switcher with fade + slide-up transition.
Item {
    id: root
    property int currentIndex: 0
    default property alias pages: holder.data
    Item { id: holder; anchors.fill: parent }
    onCurrentIndexChanged: refresh()
    Component.onCompleted: refresh()
    function refresh() {
        for (var i = 0; i < holder.children.length; i++) {
            var p = holder.children[i]
            p.anchors.fill = holder
            if (i === currentIndex) { p.visible = true; if (p.enterAnim) p.enterAnim.restart() } else { p.visible = false }
        }
    }
}
