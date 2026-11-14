import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.quarantine"); subtitle: tr("hdr.quarantine"); hint: tr("q.hint")
    bigLabel: tr("q.in"); bigValue: app.size(app.quarantineTotal)
    property bool confirm: false
    // what Sweep did, newest first; "Restore" works while the quarantine session or the registry backup still exists
    Card { pad: 14
        Column { width: parent.width; spacing: 4
            Item { width: parent.width; height: 30
                Txt { id: histT; text: tr("hist.title"); bold: true; font.pixelSize: 15; anchors.verticalCenter: parent.verticalCenter }
                Txt { x: histT.width + 10; text: tr("hist.note"); muted: true; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter
                      width: parent.width - histT.width - clearBtn.width - 24; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                AccentButton { id: clearBtn; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; compact: true; primary: false
                    property bool sure: false; visible: app.historyList.length > 0
                    text: sure ? tr("hist.clear.confirm") : tr("hist.clear")
                    onClicked: { if (sure) { app.clearHistory(); sure = false } else { sure = true; clearTimer.restart() } }
                    Timer { id: clearTimer; interval: 4000; onTriggered: clearBtn.sure = false } } }
            Empty { msg: tr("hist.empty"); visible: app.historyList.length === 0 }
            Repeater { model: app.historyList
                Item { id: hrow; width: parent.width; height: Math.max(46, hcol.implicitHeight + 14)
                    Rectangle { visible: index > 0; width: parent.width; height: 1; color: Theme.border; opacity: 0.6 }
                    Rectangle { id: hic; width: 30; height: 30; radius: 9; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter
                        Icon { anchors.centerIn: parent; name: modelData.icon; size: 15; color: Theme.accentText } }
                    Column { id: hcol; x: 42; width: parent.width - 42 - hbtns.width - 12; anchors.verticalCenter: parent.verticalCenter; spacing: 1
                        Txt { text: modelData.title; font.pixelSize: 13; bold: true; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { text: modelData.when + (modelData.detail ? "  ·  " + modelData.detail : ""); muted: true; font.pixelSize: 11
                              width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                    Row { id: hbtns; spacing: 8; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        AccentButton { visible: modelData.files !== ""; text: tr("hist.undo.files"); compact: true; primary: false; enabled: !app.busy; onClicked: app.restore(modelData.files) }
                        AccentButton { visible: modelData.reg !== ""; text: tr("hist.undo.reg"); compact: true; primary: false; enabled: !app.busy; onClicked: app.regRestore(modelData.reg) } } } }
        }
    }
    Card { pad: 14
        Column { width: parent.width; spacing: 6
            Txt { text: tr("q.title"); bold: true; font.pixelSize: 15 }
            Empty { msg: tr("q.empty"); visible: app.quarantineList.length === 0 }
            Repeater { model: app.quarantineList
                Row { id: qrow; width: parent.width; spacing: 10
                    property bool sure: false
                    Column { width: parent.width - btns.width - 10; anchors.verticalCenter: parent.verticalCenter
                        Txt { text: tr1("q.session", modelData.date); bold: true; font.pixelSize: 14 }
                        Txt { text: app.size(modelData.size); muted: true; font.pixelSize: 12 } }
                    Row { id: btns; spacing: 8; anchors.verticalCenter: parent.verticalCenter
                        AccentButton { text: tr("common.restore"); compact: true; primary: false; enabled: !app.busy; onClicked: app.restore(modelData.path) }
                        AccentButton { text: qrow.sure ? tr("q.delete.confirm") : tr("q.delete"); compact: true; danger: true; primary: qrow.sure; enabled: !app.busy
                            onClicked: { if (qrow.sure) app.deleteSession(modelData.path); else { qrow.sure = true; sureTimer.restart() } }
                            Timer { id: sureTimer; interval: 4000; onTriggered: qrow.sure = false } } } } }
        }
    }
    footer: [ AccentButton { text: confirm ? tr("q.purge.confirm") : tr("q.purge"); primary: confirm; danger: true; enabled: app.quarantineList.length > 0
        onClicked: { if (confirm) { app.purge(); confirm = false } else { confirm = true; resetTimer.restart() } }
        Timer { id: resetTimer; interval: 4000; onTriggered: confirm = false } } ]
}
