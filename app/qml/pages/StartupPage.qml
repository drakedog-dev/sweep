import QtQuick
import Sweep
import "../components"

Page {
    objectName: "startupPage"
    title: tr("nav.startup"); subtitle: tr("hdr.startup"); hint: tr("start.hint")
    bigLabel: tr("ov.startup"); bigValue: { var n = 0; var l = app.startupList; for (var i = 0; i < l.length; i++) if (l[i].enabled) n++; return String(n) }
    Card { pad: 10
        Column { width: parent.width
            Empty { msg: tr("start.empty"); visible: app.startupList.length === 0 }
            Repeater { model: app.startupList
                ToggleRow { title: modelData.name + "   ·   " + modelData.source; hint: modelData.command; checked: modelData.enabled
                            meta: modelData.isNew ? tr("start.new") : ""; disabledLook: modelData.locked
                            onToggled: v => app.setStartupKey(modelData.key, v) } }
        }
    }
    footer: [ AccentButton { text: tr("common.rescan"); primary: false; enabled: !app.busy; onClicked: app.scanStartup(true) } ]
}
