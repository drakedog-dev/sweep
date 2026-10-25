import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.apps"); subtitle: tr("hdr.apps"); hint: tr("apps.hint")
    property var picked: ({})
    bigLabel: tr("apps.found"); bigValue: String(app.appList.length)
    Card { pad: 10
        Column { width: parent.width
            Empty { msg: tr("apps.empty"); visible: app.appList.length === 0 }
            Repeater { model: app.appList
                ToggleRow { title: modelData.name; hint: modelData.hint; checked: picked[modelData.id] === true; onToggled: v => { var p = picked; p[modelData.id] = v; picked = p } } }
        }
    }
    footer: [
        AccentButton { text: tr("apps.remove"); danger: true; enabled: !app.busy; onClicked: { var ids = []; for (var k in picked) if (picked[k]) ids.push(k); if (ids.length) { app.removeApps(ids); picked = ({}) } } },
        AccentButton { text: tr("common.scan"); primary: false; enabled: !app.busy; onClicked: app.scanApps() },
        AccentButton { text: tr("apps.store"); primary: false; onClicked: app.openStore() }
    ]
}
