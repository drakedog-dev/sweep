import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.junk"); subtitle: tr("hdr.junk"); hint: tr("junk.hint")
    bigLabel: tr("common.canfree"); bigValue: app.size(app.junkTotal)
    Card { pad: 10
        Column { width: parent.width
            Repeater { model: app.junk
                ToggleRow { title: modelData.name; hint: modelData.hint; meta: app.size(modelData.size); checked: modelData.checked; onToggled: v => app.setChecked(modelData.id, v) } }
        }
    }
    footer: [
        AccentButton { text: tr("common.clean"); enabled: !app.busy && app.junkTotal > 0; onClicked: app.clean() },
        AccentButton { text: tr("common.rescan"); primary: false; enabled: !app.busy; onClicked: app.scan() }
    ]
}
