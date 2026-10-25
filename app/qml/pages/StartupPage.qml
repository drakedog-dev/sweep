import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.startup"); subtitle: tr("hdr.startup"); hint: tr("start.hint")
    bigLabel: tr("ov.startup"); bigValue: { var n = 0; var l = app.startupList; for (var i = 0; i < l.length; i++) if (l[i].enabled) n++; return String(n) }
    Card { pad: 10
        Column { width: parent.width
            Empty { msg: tr("start.empty"); visible: app.startupList.length === 0 }
            Repeater { model: app.startupList
                ToggleRow { title: modelData.name + "   ·   " + modelData.source; hint: modelData.command; checked: modelData.enabled; onToggled: v => app.setStartup(index, v) } }
        }
    }
}
