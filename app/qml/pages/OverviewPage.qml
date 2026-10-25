import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.overview"); subtitle: tr("hdr.overview")
    bigLabel: tr("common.canfree"); bigValue: app.size(app.junkTotal)

    // Health + profile
    Row { width: parent.width; spacing: 14
        Card { width: (parent.width - 14) * 0.58
            Row { width: parent.width; spacing: 22
                Item { width: 104; height: 104
                    Ring { anchors.fill: parent; value: app.health["score"] || 0
                        ringColor: value >= 80 ? Theme.good : value >= 55 ? Theme.warn : Theme.bad }
                    Column { anchors.centerIn: parent; spacing: -4
                        Txt { text: app.health["score"] || "…"; font.pixelSize: 28; bold: true; font.weight: Font.Bold; anchors.horizontalCenter: parent.horizontalCenter }
                        Label10 { text: tr("ov.of100"); anchors.horizontalCenter: parent.horizontalCenter } }
                }
                Column { width: parent.width - 126; spacing: 6; anchors.verticalCenter: parent.verticalCenter
                    Txt { font.pixelSize: 17; bold: true; font.weight: Font.Bold
                        text: { var s = app.health["score"] || 0; return tr(s >= 80 ? "ov.health.good" : s >= 55 ? "ov.health.mid" : "ov.health.bad") } }
                    Txt { text: tr("ov.health.hint"); muted: true; font.pixelSize: 12; width: parent.width }
                    Column { spacing: 3; width: parent.width
                        Repeater { model: app.health["tips"] || []
                            Row { spacing: 8
                                Rectangle { width: 6; height: 6; radius: 3; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData; font.pixelSize: 12 } } }
                    }
                }
            }
        }
        Card { width: (parent.width - 14) * 0.42
            Column { width: parent.width; spacing: 8
                Row { spacing: 8
                    Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                        color: app.pcProfile["class"] === "strong" ? Theme.good : app.pcProfile["class"] === "weak" ? Theme.bad : Theme.warn }
                    Txt { text: tr("ov.profile." + (app.pcProfile["class"] || "mid")); font.pixelSize: 17; bold: true; font.weight: Font.Bold }
                }
                Txt { text: tr("ov.profile." + (app.pcProfile["class"] || "mid") + ".hint"); muted: true; font.pixelSize: 12; width: parent.width }
                AccentButton { text: tr("ov.apply"); compact: true; primary: false; onClicked: app.applyRecommendations() }
            }
        }
    }

    // Live tiles
    Row { width: parent.width; spacing: 14
        property real w: (width - 14 * 3) / 4
        Tile { width: parent.w; label: tr("ov.cpu"); value: Math.round(app.mon["cpu"] || 0) + "%"; sub: (app.pcProfile["threads"] || "") + " thr"; spark: app.cpuHistory; sparkColor: Theme.accent2 }
        Tile { width: parent.w; label: tr("ov.ram"); value: Math.round(app.mon["ram"] || 0) + "%"; sub: app.size(app.mon["ram_used"] || 0) + " " + tr("common.of") + " " + app.size(app.mon["ram_total"] || 0); spark: app.ramHistory; sparkColor: Theme.accent3 }
        Tile { width: parent.w; label: tr("ov.disk") + " " + app.selectedDrive + ":"
            property var v: { var vs = app.volumeList; for (var i = 0; i < vs.length; i++) if (vs[i].letter === app.selectedDrive) return vs[i]; return vs[0] || {} }
            value: app.size(v.free || 0); sub: tr("common.free") + " " + tr("common.of") + " " + app.size(v.total || 0) }
        Tile { width: parent.w; label: tr("ov.startup")
            value: { var n = 0; var l = app.startupList; for (var i = 0; i < l.length; i++) if (l[i].enabled) n++; return n }
            sub: tr("ov.startup.sub") }
    }

    // Quick clean
    Card {
        Row { width: parent.width; spacing: 20
            Column { width: parent.width - 220; spacing: 4; anchors.verticalCenter: parent.verticalCenter
                Txt { text: tr("ov.quick"); font.pixelSize: 17; bold: true; font.weight: Font.Bold }
                Txt { text: tr("ov.quick.hint"); muted: true; width: parent.width }
            }
            AccentButton { text: tr("ov.quick.btn"); anchors.verticalCenter: parent.verticalCenter; onClicked: app.quickClean(); enabled: !app.busy }
        }
    }
}
