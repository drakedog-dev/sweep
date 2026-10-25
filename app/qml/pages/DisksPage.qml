import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.disks"); subtitle: tr("hdr.disks"); hint: tr("disk.hint")
    bigLabel: tr("common.canfree")
    bigValue: (app.driveJunk || []).some(function (d) { return d.scanned }) ? app.size(app.driveJunkTotal) : "—"
    Repeater { model: app.driveJunk
        Card { id: card; pad: 14
            property var vol: { var vs = app.volumeList; for (var i = 0; i < vs.length; i++) if (vs[i].letter === modelData.letter) return vs[i]; return {} }
            Column { width: parent.width; spacing: 8
                Item { width: parent.width; height: dName.implicitHeight
                    Txt { id: dName; x: 10; text: (vol.label ? vol.label + " (" : "") + modelData.letter + ":" + (vol.label ? ")" : ""); bold: true; font.pixelSize: 16
                          width: Math.min(implicitWidth, parent.width * 0.4); elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { anchors.left: dName.right; anchors.leftMargin: 12; anchors.right: dState.left; anchors.rightMargin: 12; anchors.baseline: dName.baseline
                          text: tr("disk.used").replace("{0}", app.size(vol.used || 0)).replace("{1}", app.size(vol.total || 0)) + "  ·  " + (vol.pct || 0) + "%"; muted: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                    Txt { id: dState; anchors.right: parent.right; anchors.rightMargin: 10; anchors.baseline: dName.baseline
                          text: modelData.scanned ? (modelData.rows.length ? app.size(modelData.total) : tr("disk.clean")) : tr("disk.notscanned"); bold: true; wrapMode: Text.NoWrap
                          color: modelData.scanned && modelData.rows.length ? Theme.accent2 : Theme.muted }
                }
                Rectangle { width: parent.width - 20; x: 10; height: 8; radius: 4; color: Theme.track
                    Rectangle { width: Math.max(6, parent.width * (vol.pct || 0) / 100); height: parent.height; radius: 4
                        color: (vol.pct || 0) >= 90 ? Theme.bad : (vol.pct || 0) >= 75 ? Theme.warn : Theme.accent2
                        Behavior on width { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutCubic } } } }
                Column { width: parent.width; topPadding: 4
                    Repeater { model: modelData.rows
                        ToggleRow { title: modelData.name; hint: modelData.hint + "  ·  " + tr1("disk.files", modelData.count); meta: app.size(modelData.size); checked: modelData.checked
                            onToggled: v => app.setDriveChecked(card.letter, modelData.id, v) } }
                }
            }
            property string letter: modelData.letter
        }
    }
    footer: [
        AccentButton { text: tr("disk.find"); enabled: !app.busy; onClicked: app.scanDrives() },
        AccentButton { text: tr("disk.toq"); primary: false; enabled: !app.busy && app.driveJunkTotal > 0; onClicked: app.cleanDrives() },
        AccentButton { text: tr("disk.open"); primary: false; onClicked: app.openDrive() }
    ]
}
