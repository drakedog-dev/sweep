import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.services"); subtitle: tr("hdr.services"); hint: tr("svc.hint")
    bigLabel: tr("svc.off"); bigValue: { var n = 0; var l = app.serviceList; for (var i = 0; i < l.length; i++) if (!l[i].enabled) n++; return n + " " + tr("common.of") + " " + l.length }
    Card { visible: app.pcProfile["class"] === "strong"; pad: 14
        Row { spacing: 10
            Rectangle { width: 8; height: 8; radius: 4; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: tr("svc.warn.strong"); width: 700 } } }
    Card { pad: 10
        Column { width: parent.width
            Repeater { model: app.serviceList
                ToggleRow { title: modelData.title; hint: modelData.hint; checked: modelData.enabled; onToggled: v => app.setService(modelData.name, v) } }
        }
    }
}
