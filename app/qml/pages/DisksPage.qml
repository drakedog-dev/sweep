import QtQuick
import Sweep
import "../components"

Page {
    id: pg
    title: tr("nav.disks"); subtitle: tr("hdr.disks"); hint: tr("disk.hint")
    property var picked: ({})
    bigLabel: tr("disk.freeLabel"); bigValue: { var vs = app.volumeList; for (var i = 0; i < vs.length; i++) if (vs[i].letter === app.selectedDrive) return app.size(vs[i].free); return "" }
    Card { pad: 10
        Column { width: parent.width; spacing: 4
            Repeater { model: app.volumeList
                Rectangle { width: parent.width; height: 74; radius: Theme.radiusSm
                    color: app.selectedDrive === modelData.letter ? Theme.cardAlt : "transparent"; border.color: app.selectedDrive === modelData.letter ? Theme.accent : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.dur } }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.selectDrive(modelData.letter) }
                    Column { anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                        Row { spacing: 10
                              Txt { text: (modelData.label ? modelData.label + " (" : "") + modelData.letter + ":" + (modelData.label ? ")" : ""); bold: true; font.pixelSize: 14 }
                              Txt { text: tr("disk.used").replace("{0}", app.size(modelData.used)).replace("{1}", app.size(modelData.total)) + "  ·  " + modelData.pct + "%"; muted: true; font.pixelSize: 12; anchors.baseline: parent.children[0].baseline } }
                        Rectangle { width: parent.width; height: 8; radius: 4; color: Theme.track
                            Rectangle { width: Math.max(6, parent.width * modelData.pct / 100); height: parent.height; radius: 4
                                color: modelData.pct >= 90 ? Theme.bad : modelData.pct >= 75 ? Theme.warn : Theme.accent2
                                Behavior on width { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutCubic } } } }
                    }
                } }
        }
    }
    Card { pad: 10
        Column { width: parent.width
            Txt { text: tr("disk.find") + " · " + app.selectedDrive + ":"; bold: true; font.pixelSize: 15; leftPadding: 12; topPadding: 8; bottomPadding: 6 }
            Empty { msg: tr("disk.empty"); visible: app.largeFiles.length === 0 }
            Repeater { model: app.largeFiles
                ToggleRow { title: modelData.name; hint: modelData.dir; meta: app.size(modelData.size); checked: picked[modelData.path] === true; onToggled: v => { var p = picked; p[modelData.path] = v; picked = p } } }
        }
    }
    footer: [
        AccentButton { text: tr("disk.find"); enabled: !app.busy; onClicked: app.scanLarge() },
        AccentButton { text: tr("disk.toq"); primary: false; enabled: !app.busy; onClicked: { var ps = []; for (var k in picked) if (picked[k]) ps.push(k); if (ps.length) { app.quarantineLarge(ps); picked = ({}) } } },
        AccentButton { text: tr("disk.open"); primary: false; onClicked: app.openDrive() }
    ]
}
