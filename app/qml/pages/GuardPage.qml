import QtQuick
import Sweep
import "../components"

// Guard: Windows updates switch tracking back on and reinstall promoted apps; Sweep notices and puts it back
Page {
    id: gp
    title: tr("nav.guard"); subtitle: tr("hdr.guard")
    property var g: app.guardState
    property bool on: g["enabled"] === true
    property bool drift: (g["pending"] || []).length > 0
    property color stColor: drift ? Theme.warn : on ? Theme.good : Theme.muted
    bigLabel: tr("guard.status"); bigValue: on ? tr("guard.st.on") : tr("guard.st.off")

    // ---------- status ----------
    Card {
        Row { width: parent.width; spacing: 26
            Item { width: 128; height: 128; anchors.verticalCenter: parent.verticalCenter
                Repeater { model: 2   // calm radar pulse while Guard is watching
                    Rectangle { anchors.centerIn: parent; width: 84; height: 84; radius: 42; color: "transparent"; border.width: 2; border.color: gp.stColor
                        opacity: 0; visible: gp.on
                        SequentialAnimation on opacity { running: gp.on && Theme.anim; loops: Animation.Infinite
                            PauseAnimation { duration: index * 1100 }
                            NumberAnimation { from: 0.75; to: 0; duration: 2200; easing.type: Easing.OutCubic }
                            PauseAnimation { duration: (1 - index) * 1100 } }
                        SequentialAnimation on scale { running: gp.on && Theme.anim; loops: Animation.Infinite
                            PauseAnimation { duration: index * 1100 }
                            NumberAnimation { from: 1; to: 1.5; duration: 2200; easing.type: Easing.OutCubic }
                            PauseAnimation { duration: (1 - index) * 1100 } } } }
                Rectangle { anchors.centerIn: parent; width: 84; height: 84; radius: 42
                    color: gp.on || gp.drift ? gp.stColor : Theme.soft
                    Behavior on color { ColorAnimation { duration: Theme.dur } }
                    Icon { anchors.centerIn: parent; size: 40; color: gp.on || gp.drift ? "white" : Theme.muted
                        name: gp.drift ? "shield-alert" : gp.on ? "shield-check" : "shield" } }
            }
            Column { width: parent.width - 154; spacing: 8; anchors.verticalCenter: parent.verticalCenter
                Txt { width: parent.width; font.pixelSize: 21; bold: true; font.weight: Font.Bold
                    text: gp.drift ? tr("guard.drift.title") : gp.on ? tr("guard.ok.title") : tr("guard.off.title") }
                Txt { width: parent.width; muted: !gp.drift
                    text: gp.drift ? (g["pending"] || []).join(", ")
                         : gp.on ? tr2("guard.ok.text", String(g["watchedPrivacy"] || 0), String(g["watchedApps"] || 0)) : tr("guard.off.text") }
                Txt { width: parent.width; muted: true; font.pixelSize: 12; visible: gp.on
                    text: g["lastRun"] ? tr2("guard.last", g["lastRun"], g["build"] || "") : tr("guard.never") }
                Row { spacing: 10; topPadding: 4
                    AccentButton { visible: !gp.on; text: tr("guard.enable"); enabled: !app.busy; onClicked: app.setGuard(true) }
                    AccentButton { visible: gp.drift; text: tr("guard.fix"); enabled: !app.busy; onClicked: app.guardFix() }
                    AccentButton { visible: gp.on; text: tr("guard.check"); primary: false; enabled: !app.busy; onClicked: app.guardCheck() } }
            }
        }
    }

    // ---------- switches ----------
    Card { pad: 10
        Column { width: parent.width
            ToggleRow { icon: "radar"; title: tr("guard.sw"); hint: tr("guard.sw.hint"); checked: gp.on; onToggled: v => app.setGuard(v) }
            ToggleRow { icon: "rotate-ccw"; title: tr("guard.auto"); hint: tr("guard.auto.hint"); checked: g["auto"] === true; disabledLook: !gp.on
                onToggled: v => app.setGuardAuto(v) }
        }
    }

    // ---------- what is protected ----------
    Card {
        Column { width: parent.width; spacing: 10
            Txt { text: tr("guard.watched"); font.pixelSize: 15; bold: true }
            Txt { text: tr("guard.watched.none"); muted: true; width: parent.width; visible: (g["watched"] || []).length === 0 }
            Flow { width: parent.width; spacing: 8
                Repeater { model: g["watched"] || []
                    Rectangle { height: 30; radius: 15; width: chipRow.implicitWidth + 24; color: Theme.soft
                        Row { id: chipRow; anchors.centerIn: parent; spacing: 6
                            Icon { name: "lock"; size: 12; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: modelData; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } } } }
            }
        }
    }

    // ---------- history ----------
    Card {
        Column { width: parent.width; spacing: 10
            Txt { text: tr("guard.history"); font.pixelSize: 15; bold: true }
            Txt { text: tr("guard.history.none"); muted: true; visible: (g["events"] || []).length === 0 }
            Repeater { model: g["events"] || []
                Row { width: parent.width; spacing: 12
                    Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter; color: modelData.fixed ? Theme.good : Theme.warn }
                    Column { width: parent.width - 120; spacing: 1
                        Txt { text: modelData.when + (modelData.afterUpdate ? "  ·  " + tr1("guard.ev.after", modelData.build) : ""); bold: true; font.pixelSize: 13 }
                        Txt { text: modelData.items; muted: true; font.pixelSize: 12; width: parent.width } }
                    Txt { text: modelData.fixed ? tr("guard.ev.fixed") : tr("guard.ev.waiting"); color: modelData.fixed ? Theme.good : Theme.warn; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }
    }
}
