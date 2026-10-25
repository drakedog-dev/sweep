import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.quarantine"); subtitle: tr("hdr.quarantine"); hint: tr("q.hint")
    bigLabel: tr("q.in"); bigValue: app.size(app.quarantineTotal)
    property bool confirm: false
    Card { pad: 14
        Column { width: parent.width; spacing: 6
            Empty { msg: tr("q.empty"); visible: app.quarantineList.length === 0 }
            Repeater { model: app.quarantineList
                Row { width: parent.width; spacing: 12
                    Column { width: parent.width - 130; anchors.verticalCenter: parent.verticalCenter
                        Txt { text: tr1("q.session", modelData.date); bold: true; font.pixelSize: 14 }
                        Txt { text: app.size(modelData.size); muted: true; font.pixelSize: 12 } }
                    AccentButton { text: tr("common.restore"); compact: true; primary: false; anchors.verticalCenter: parent.verticalCenter; onClicked: app.restore(modelData.path) } } }
        }
    }
    footer: [ AccentButton { text: confirm ? tr("q.purge.confirm") : tr("q.purge"); primary: confirm; danger: true; enabled: app.quarantineList.length > 0
        onClicked: { if (confirm) { app.purge(); confirm = false } else { confirm = true; resetTimer.restart() } }
        Timer { id: resetTimer; interval: 4000; onTriggered: confirm = false } } ]
}
