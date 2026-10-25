import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.system"); subtitle: tr("hdr.system"); hint: tr("sys.hint")
    bigLabel: tr("sys.computer"); bigValue: (app.pcProfile["ram_gb"] || "") + " " + tr("u.gb") + " · " + (app.pcProfile["threads"] || "") + " thr"
    Repeater { model: app.systemRows
        Card { pad: 18
            Column { width: parent.width; spacing: 6
                Label10 { text: modelData.section.toUpperCase() }
                Repeater { model: modelData.items
                    Row { width: parent.width; spacing: 12
                        Txt { text: modelData[0]; muted: true; width: modelData[0] ? 190 : 0; visible: modelData[0] !== "" }
                        Txt { text: modelData[1]; bold: true; width: parent.width - (modelData[0] ? 202 : 0) } } }
            }
        } }
    footer: [
        AccentButton { text: tr("sys.collect"); enabled: !app.busy; onClicked: app.collectSystem() },
        AccentButton { text: tr("common.copy"); primary: false; onClicked: app.copyText(app.systemText()) }
    ]
}
