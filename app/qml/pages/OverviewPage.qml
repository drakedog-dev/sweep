import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.overview"); subtitle: tr("hdr.overview")
    bigLabel: tr("common.canfree"); bigValue: app.analysis["state"] === "done" ? app.size(app.analysis["cleanable"]) : app.junkScanned ? app.size(app.junkTotal) : "—"

    // Analyze everything: one button for what used to run by itself at start
    Card { id: anCard
        property var an: app.analysis
        property var icons: ({ junk: "trash-2", drives: "hard-drive", registry: "database", startup: "power", privacy: "shield-check", updates: "circle-arrow-up" })
        function open(id) { if (id === "junk") go("junk"); else if (id === "drives") go("disks"); else if (id === "registry") go("registry")
                            else if (id === "startup") go("startup"); else if (id === "privacy") go("privacy"); else if (id === "updates") openAppsTab(2) }
        Column { width: parent.width; spacing: 16
            Row { width: parent.width; spacing: 18
                GradRect { width: 52; height: 52; radius: 15; anchors.verticalCenter: parent.verticalCenter; c1: Theme.accent; c2: Theme.accent3
                    Icon { id: radarIcon; anchors.centerIn: parent; name: "radar"; size: 26; color: "white"
                        RotationAnimation { target: radarIcon; property: "rotation"; from: 0; to: 360; duration: 2400; loops: Animation.Infinite
                            running: anCard.an.state === "running"; onRunningChanged: if (!running) radarIcon.rotation = 0 } } }
                Column { width: parent.width - 70 - (startBtn.visible ? startBtn.width + 18 : 0); spacing: 4; anchors.verticalCenter: parent.verticalCenter
                    Txt { text: tr("an.title"); font.pixelSize: 17; bold: true; font.weight: Font.Bold }
                    Txt { muted: true; width: parent.width; font.pixelSize: 12
                          text: anCard.an.state === "done" && anCard.an.freed > 0 ? tr("an.cleaned").replace("{0}", app.size(anCard.an.freed)).replace("{1}", String(anCard.an.fixed)) + ". " + tr("an.after")
                              : anCard.an.state === "done" ? tr("an.found.note") : tr("an.hint") } }
                AccentButton { id: startBtn; visible: anCard.an.state !== "done"; text: tr("an.btn"); anchors.verticalCenter: parent.verticalCenter
                    enabled: !app.busy && anCard.an.state !== "running"; onClicked: app.analyzeAll() }
            }
            Grid { id: anGrid; visible: anCard.an.state !== ""; width: parent.width; columns: 2; columnSpacing: 10; rowSpacing: 10
                Repeater { model: anCard.an.rows || []
                    Rectangle { width: (anGrid.width - 10) / 2; height: 54; radius: 12; color: rowHov.containsMouse && modelData.state === "done" ? Theme.softHover : Theme.cardAlt
                        Behavior on color { ColorAnimation { duration: Theme.dur } }
                        Rectangle { id: ic; width: 34; height: 34; radius: 10; color: Theme.soft; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                            Icon { anchors.centerIn: parent; name: anCard.icons[modelData.id] || "circle-check"; size: 17; color: modelData.bad ? Theme.warn : Theme.accentText } }
                        Column { anchors.left: ic.right; anchors.leftMargin: 12; anchors.right: mark.left; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                            Txt { text: tr("an.s." + modelData.id); bold: true; font.pixelSize: 13; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                            Txt { width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap; font.pixelSize: 12
                                text: modelData.state === "done" ? modelData.text : modelData.state === "working" ? tr("an.working") : tr("an.wait")
                                color: modelData.state === "done" ? (modelData.bad ? Theme.warn : Theme.good) : Theme.muted } }
                        Item { id: mark; width: 22; height: 22; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                            Icon { anchors.centerIn: parent; name: "refresh-cw"; size: 16; color: Theme.accentText; visible: modelData.state === "working"
                                RotationAnimation on rotation { from: 0; to: 360; duration: 1100; loops: Animation.Infinite; running: modelData.state === "working" } }
                            Icon { anchors.centerIn: parent; name: "arrow-right"; size: 16; color: Theme.faint; visible: modelData.state === "done" } }
                        MouseArea { id: rowHov; anchors.fill: parent; hoverEnabled: true; enabled: modelData.state === "done"; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: anCard.open(modelData.id) }
                    }
                }
            }
            Row { visible: anCard.an.state === "done"; spacing: 10
                AccentButton { visible: anCard.an.cleanable > 0 || anCard.an.registry > 0
                    text: anCard.an.cleanable > 0 ? tr1("an.cleanbtn", app.size(anCard.an.cleanable)) : tr("an.cleanbtn.reg"); enabled: !app.busy; onClicked: app.cleanFound() }
                AccentButton { text: tr("an.again"); primary: anCard.an.cleanable <= 0 && anCard.an.registry <= 0; enabled: !app.busy; onClicked: app.analyzeAll() } }
        }
    }

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
                    Txt { font.pixelSize: 17; bold: true; font.weight: Font.Bold; width: parent.width
                        text: { var s = app.health["score"] || 0; return tr(s >= 80 ? "ov.health.good" : s >= 55 ? "ov.health.mid" : "ov.health.bad") } }
                    Txt { text: tr("ov.health.hint"); muted: true; font.pixelSize: 12; width: parent.width }
                    Column { spacing: 3; width: parent.width
                        Repeater { model: app.health["tips"] || []
                            Row { spacing: 8; width: parent.width
                                Rectangle { width: 6; height: 6; radius: 3; color: Theme.accent2; anchors.top: parent.top; anchors.topMargin: 6 }
                                Txt { text: modelData; font.pixelSize: 12; width: parent.width - 14 } } }
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
            value: has ? tr1("boot.sec", num(b["last"], 1)) : "…"
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
        Row { width: parent.width; spacing: 14; y: Math.max(0, (parent.height - height) / 2)
            GradRect { width: 42; height: 42; radius: 12; anchors.verticalCenter: parent.verticalCenter; c1: Theme.accent; c2: Theme.accent3
                Icon { anchors.centerIn: parent; name: ac.icon; size: 20; color: "white" } }
            Column { width: parent.width - 56; spacing: 2; anchors.verticalCenter: parent.verticalCenter
                Txt { text: ac.title; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; maximumLineCount: 2; lineHeight: 0.95 }
                Txt { text: ac.sub; muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; maximumLineCount: 2; lineHeight: 0.95 } }
        }
        MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: ac.clicked() }
    }
    Row { id: qa; width: parent.width; spacing: 14
        property real w: (width - 14 * 2) / 3
        property real h: w < 260 ? 104 : 78          // room for two-line titles in a narrow window, the same for all three
        ActionCard { id: qa1; width: parent.w; height: qa.h; icon: "shield-check"; title: tr("ov.qa.privacy")
            sub: tr1("ov.qa.privacy.sub", app.privacyOn + " " + tr("common.of") + " " + app.privacy.length) + (app.guardState["enabled"] ? "  ·  " + tr("ov.qa.guard.on") : "")
            onClicked: go("privacy") }
        ActionCard { id: qa2; width: parent.w; height: qa.h; icon: "memory-stick"; title: tr("ov.qa.ram")
            sub: tr1("ov.qa.ram.sub", Math.round(app.mon["ram"] || 0) + "%"); onClicked: if (!app.busy) app.freeRam() }
        ActionCard { id: qa3; width: parent.w; height: qa.h; icon: "hard-drive"; title: tr("ov.qa.disks"); sub: tr("ov.qa.disks.sub")
            onClicked: { go("disks"); if (!app.busy) app.scanDrives() } }
    }

}
