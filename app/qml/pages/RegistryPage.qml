import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.registry"); subtitle: tr("hdr.registry"); hint: tr("reg.hint")
    property var picked: ({})
    bigLabel: tr("reg.found"); bigValue: { var n = 0, any = false; var r = app.registry; for (var i = 0; i < r.length; i++) { if (r[i].found >= 0) { any = true; n += r[i].found } } return any ? String(n) : "…" }
    Card { pad: 10
        Column { width: parent.width
            Repeater { model: app.registry
                ToggleRow { title: modelData.name; hint: modelData.hint; meta: modelData.found >= 0 ? String(modelData.found) : ""; checked: picked[modelData.id] !== false
                    onToggled: v => { var p = picked; p[modelData.id] = v; picked = p } } }
        }
    }
    Card { Column { width: parent.width; spacing: 8
        Txt { text: tr("reg.backups"); bold: true; font.pixelSize: 15 }
        Empty { msg: tr("reg.nobackups"); visible: app.regBackups.length === 0 }
        Repeater { model: app.regBackups
            Row { width: parent.width; spacing: 12
                Txt { text: tr1("reg.backup", modelData.date).replace("{1}", modelData.count); anchors.verticalCenter: parent.verticalCenter; width: parent.width - 130 }
                AccentButton { text: tr("common.restore"); compact: true; primary: false; onClicked: app.regRestore(modelData.session) } } }
    } }
    footer: [
        AccentButton { text: tr("reg.clean"); enabled: !app.busy && bigValue !== "…" && bigValue !== "0"; onClicked: { var ids = []; var r = app.registry; for (var i = 0; i < r.length; i++) if (picked[r[i].id] !== false) ids.push(r[i].id); app.regClean(ids) } },
        AccentButton { text: tr("common.scan"); primary: false; enabled: !app.busy; onClicked: app.regScan() }
    ]
}
