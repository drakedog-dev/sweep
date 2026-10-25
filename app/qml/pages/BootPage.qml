import QtQuick
import Sweep
import "../components"

// Boot X-ray: data comes from Windows' own Diagnostics-Performance log
Page {
    id: bp
    title: tr("nav.boot"); subtitle: tr("hdr.boot")
    property var d: app.bootData
    property bool has: d["boots"] !== undefined && d["boots"].length > 0
    property var last: has ? d["boots"][0] : ({ total: 0, main: 0, post: 0 })
    bigLabel: tr("boot.last"); bigValue: has ? tr1("boot.sec", num(d["last"], 1)) : "…"
    function secColor(s) { return s < 30 ? Theme.good : s < 60 ? Theme.warn : Theme.bad }
    function fmt(s) { return tr1("boot.sec", num(s, 1)) }

    // ---------- nothing recorded yet ----------
    Card { visible: !bp.has
        Row { width: parent.width; spacing: 18
            Rectangle { width: 56; height: 56; radius: 16
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent3 } }
                Icon { anchors.centerIn: parent; name: "timer"; size: 28; color: "white" } }
            Column { width: parent.width - 74; spacing: 6
                Txt { text: tr("boot.empty.title"); font.pixelSize: 18; bold: true; font.weight: Font.Bold; width: parent.width }
                Txt { text: tr("boot.empty"); muted: true; width: parent.width } }
        }
    }

    // ---------- verdict and where the time goes ----------
    Card { visible: bp.has
        Column { width: parent.width; spacing: 14
            Row { width: parent.width; spacing: 12
                Rectangle { width: 12; height: 12; radius: 6; color: bp.secColor(bp.last.total); anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("boot.verdict." + (d["verdict"] || "ok")); font.pixelSize: 19; bold: true; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
            }
            Txt { text: tr("boot.verdict." + (d["verdict"] || "ok") + ".hint"); muted: true; width: parent.width }
            Item { width: parent.width; height: 20
                property real total: Math.max(0.1, bp.last.total)
                Rectangle { id: mainBar; height: 20; radius: 10; color: Theme.accent
                    width: Math.max(10, (parent.width - 4) * bp.last.main / parent.total)
                    Behavior on width { NumberAnimation { duration: Theme.durSlow * 2; easing.type: Easing.OutCubic } } }
                Rectangle { x: mainBar.width + 4; height: 20; radius: 10; color: Theme.accent3
                    width: Math.max(10, parent.width - mainBar.width - 4)
                    Behavior on width { NumberAnimation { duration: Theme.durSlow * 2; easing.type: Easing.OutCubic } } }
            }
            Row { spacing: 26
                Row { spacing: 8
                    Rectangle { width: 10; height: 10; radius: 5; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: tr("boot.main") + "  "; muted: true; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: bp.fmt(bp.last.main); bold: true; anchors.verticalCenter: parent.verticalCenter } }
                Row { spacing: 8
                    Rectangle { width: 10; height: 10; radius: 5; color: Theme.accent3; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: tr("boot.post") + "  "; muted: true; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: bp.fmt(bp.last.post); bold: true; anchors.verticalCenter: parent.verticalCenter } }
            }
        }
    }

    // ---------- recent boots chart ----------
    Card { visible: bp.has
        Column { width: parent.width; spacing: 10
            Row { width: parent.width; spacing: 10
                Txt { id: histT; text: tr("boot.history"); font.pixelSize: 15; bold: true }
                Txt { text: tr2("boot.avg", num(d["avg"] || 0, 1), String((d["boots"] || []).length)) + "  ·  " + tr1("boot.best", num(d["best"] || 0, 1)); muted: true; font.pixelSize: 12; anchors.baseline: histT.baseline }
            }
            Item { id: chart; width: parent.width; height: 190
                property var boots: bp.has ? d["boots"].slice(0, 12).reverse() : []
                property real maxv: { var m = 30; for (var i = 0; i < boots.length; i++) m = Math.max(m, boots[i].total); return m * 1.18 }
                property real plotH: 150
                property real colW: boots.length ? (width - (boots.length - 1) * 10) / boots.length : 0
                Rectangle { // average line
                    x: 0; width: chart.width; height: 1; color: Theme.muted; opacity: 0.45
                    y: chart.plotH - (d["avg"] || 0) / chart.maxv * chart.plotH
                    Txt { anchors.right: parent.right; anchors.bottom: parent.top; anchors.bottomMargin: 2; text: tr("boot.avgline"); muted: true; font.pixelSize: 10 } }
                Repeater { model: chart.boots
                    Item { x: index * (chart.colW + 10); width: chart.colW; height: chart.height
                        property bool newest: index === chart.boots.length - 1
                        Rectangle { id: bar; anchors.bottom: parent.bottom; anchors.bottomMargin: chart.height - chart.plotH
                            width: parent.width; radius: 7; color: bp.secColor(modelData.total); opacity: newest ? 1 : 0.78
                            height: Math.max(6, modelData.total / chart.maxv * chart.plotH)
                            Behavior on height { NumberAnimation { duration: Theme.durSlow * 2; easing.type: Easing.OutCubic } } }
                        Txt { anchors.horizontalCenter: bar.horizontalCenter; anchors.bottom: bar.top; anchors.bottomMargin: 4
                            text: Number(modelData.total).toFixed(0); font.pixelSize: 11; bold: newest; muted: !newest }
                        Txt { anchors.horizontalCenter: parent.horizontalCenter; y: chart.plotH + 10; text: modelData.label; font.pixelSize: 10; muted: !newest; bold: newest
                            width: parent.width + 10; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; wrapMode: Text.WordWrap; maximumLineCount: 2; lineHeight: 0.9 }
                    }
                }
            }
            Txt { text: tr("boot.tip"); muted: true; font.pixelSize: 12; width: parent.width }
        }
    }

    // ---------- what slows the boot down ----------
    Card { visible: bp.has; pad: 12
        Column { width: parent.width; spacing: 2
            Column { width: parent.width; spacing: 4; leftPadding: 10; rightPadding: 10; topPadding: 6; bottomPadding: 8
                Txt { text: tr("boot.culprits"); font.pixelSize: 15; bold: true }
                Txt { text: tr1("boot.culprits.hint", String(d["window"] || 0)); muted: true; font.pixelSize: 12; width: parent.width - 20 }
                Txt { text: tr("boot.culprits.none"); visible: (d["culprits"] || []).length === 0; color: Theme.good; topPadding: 6 }
            }
            Repeater { model: d["culprits"] || []
                Rectangle { id: crow; width: parent.width; height: 62; radius: 12
                    color: hov.containsMouse ? Theme.cardAlt : "transparent"
                    MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                    Rectangle { id: ib; width: 38; height: 38; radius: 11; color: Theme.soft; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                        Icon { anchors.centerIn: parent; size: 18; color: Theme.accent2
                            name: ({app: "app-window", driver: "cpu", service: "server", device: "hard-drive", policy: "layers"})[modelData.kind] || "layers" } }
                    Column { anchors.left: ib.right; anchors.leftMargin: 12; anchors.right: pill.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                        Txt { text: modelData.name; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { text: modelData.kindText + "  ·  " + tr2("boot.times", String(modelData.count), String(d["window"] || 0)); muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                    Rectangle { id: pill; anchors.right: act.left; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                        width: pt.implicitWidth + 22; height: 28; radius: 14
                        color: modelData.avg >= 5 ? Qt.rgba(Theme.bad.r, Theme.bad.g, Theme.bad.b, 0.18) : modelData.avg >= 2 ? Qt.rgba(Theme.warn.r, Theme.warn.g, Theme.warn.b, 0.18) : Theme.soft
                        Txt { id: pt; anchors.centerIn: parent; text: tr1("boot.plus", num(modelData.avg, 1)); bold: true
                            color: modelData.avg >= 5 ? Theme.bad : modelData.avg >= 2 ? Theme.warn : Theme.muted } }
                    Item { id: act; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                        width: 210; height: 34
                        AccentButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; compact: true; primary: false
                            visible: modelData.startupIndex >= 0 && modelData.startupOn; text: tr("boot.disable"); enabled: !app.busy
                            onClicked: app.setStartup(modelData.startupIndex, false) }
                        Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                            visible: modelData.startupIndex >= 0 && !modelData.startupOn
                            Icon { name: "check"; size: 15; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: tr("boot.disabled"); color: Theme.good; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                        AccentButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; compact: true; primary: false
                            visible: modelData.kind === "service"; text: tr("boot.services"); onClicked: go("services") }
                    }
                }
            }
        }
    }

    footer: [
        AccentButton { text: tr("boot.refresh"); enabled: !app.busy; onClicked: app.scanBoot() },
        AccentButton { text: tr("boot.restart"); primary: false
            onClicked: ask(tr("boot.confirm.title"), tr("boot.confirm.text"), tr("boot.restart"), function () { app.restartForBoot() }) }
    ]
}
