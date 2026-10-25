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

    // Live tiles (same height: each has a 34 px chart or bar area)
    Row { width: parent.width; spacing: 14
        property real w: (width - 14 * 3) / 4
        Tile { width: parent.w; icon: "cpu"; label: tr("ov.cpu"); value: Math.round(app.mon["cpu"] || 0) + "%"
            sub: (app.pcProfile["threads"] || "") + " " + tr("u.thr"); spark: app.cpuHistory; sparkColor: Theme.accent2 }
        Tile { width: parent.w; icon: "memory-stick"; label: tr("ov.ram"); value: Math.round(app.mon["ram"] || 0) + "%"
            sub: app.size(app.mon["ram_used"] || 0) + " " + tr("common.of") + " " + app.size(app.mon["ram_total"] || 0); spark: app.ramHistory; sparkColor: Theme.accent3 }
        Tile { width: parent.w; icon: "hard-drive"; label: tr("ov.disk") + " " + app.selectedDrive + ":"
            property var v: { var vs = app.volumeList; for (var i = 0; i < vs.length; i++) if (vs[i].letter === app.selectedDrive) return vs[i]; return vs[0] || {} }
            value: app.size(v.free || 0); sub: tr("common.free") + " " + tr("common.of") + " " + app.size(v.total || 0)
            bar: v.total ? 1 - (v.free || 0) / v.total : -1; alarm: true }
        Tile { width: parent.w; icon: "timer"; label: tr("ov.boot")
            property var b: app.bootData
            property bool has: b["boots"] !== undefined && b["boots"].length > 0
            value: has ? tr1("boot.sec", Number(b["last"]).toFixed(1)) : "…"
            sub: has ? tr1("ov.boot.sub", Number(b["avg"]).toFixed(0)) : tr("ov.boot.none")
            sparkColor: !has ? Theme.accent2 : b["last"] < 30 ? Theme.good : b["last"] < 60 ? Theme.warn : Theme.bad
            bar: has ? Math.min(1, b["last"] / 90) : -1
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: go("boot") } }
    }

    // Quick actions
    component ActionCard: Card {
        id: ac
        property string icon: ""
        property string title: ""
        property string sub: ""
        signal clicked()
        pad: 16
        color: hov.containsMouse ? Theme.cardAlt : Theme.card
        Row { width: parent.width; spacing: 14
            Rectangle { width: 42; height: 42; radius: 12; anchors.verticalCenter: parent.verticalCenter
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent3 } }
                Icon { anchors.centerIn: parent; name: ac.icon; size: 20; color: "white" } }
            Column { width: parent.width - 56; spacing: 2; anchors.verticalCenter: parent.verticalCenter
                Txt { text: ac.title; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; maximumLineCount: 1 }
                Txt { text: ac.sub; muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; maximumLineCount: 1 } }
        }
        MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: ac.clicked() }
    }
    Row { width: parent.width; spacing: 14
        property real w: (width - 14 * 2) / 3
        ActionCard { width: parent.w; icon: "shield-check"; title: tr("ov.qa.privacy")
            sub: tr1("ov.qa.privacy.sub", app.privacyOn + " " + tr("common.of") + " " + app.privacy.length) + (app.guardState["enabled"] ? "  ·  " + tr("ov.qa.guard.on") : "")
            onClicked: go("privacy") }
        ActionCard { width: parent.w; icon: "memory-stick"; title: tr("ov.qa.ram")
            sub: tr1("ov.qa.ram.sub", Math.round(app.mon["ram"] || 0) + "%"); onClicked: if (!app.busy) app.freeRam() }
        ActionCard { width: parent.w; icon: "hard-drive"; title: tr("ov.qa.disks"); sub: tr("ov.qa.disks.sub")
            onClicked: { go("disks"); if (!app.busy) app.scanDrives() } }
    }

    // Quick clean
    Card {
        Row { width: parent.width; spacing: 18
            Rectangle { width: 52; height: 52; radius: 15; anchors.verticalCenter: parent.verticalCenter
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent3 } }
                Icon { anchors.centerIn: parent; name: "sparkles"; size: 26; color: "white" } }
            Column { width: parent.width - 290; spacing: 4; anchors.verticalCenter: parent.verticalCenter
                Txt { text: tr("ov.quick"); font.pixelSize: 17; bold: true; font.weight: Font.Bold }
                Txt { text: tr("ov.quick.hint"); muted: true; width: parent.width }
            }
            AccentButton { text: tr("ov.quick.btn"); anchors.verticalCenter: parent.verticalCenter; onClicked: app.quickClean(); enabled: !app.busy }
        }
    }
}
