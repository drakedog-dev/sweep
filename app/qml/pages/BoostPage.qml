import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.boost"); subtitle: tr("hdr.boost")
    bigLabel: tr("boost.freemem"); bigValue: app.size((app.mon["ram_total"] || 0) - (app.mon["ram_used"] || 0))

    component ActionCard: Card {
        property string head: ""; property string body: ""; property string btn: ""; signal go()
        property bool needsIdle: true
        Row { width: parent.width; spacing: 20
            Column { width: parent.width - acBtn.width - 20; spacing: 4; anchors.verticalCenter: parent.verticalCenter
                Txt { text: head; font.pixelSize: 15; bold: true; width: parent.width } Txt { text: body; muted: true; width: parent.width } }
            AccentButton { id: acBtn; text: btn; anchors.verticalCenter: parent.verticalCenter; enabled: !needsIdle || !app.busy; onClicked: go() }
        }
    }
    component Chip: Rectangle {
        property string label: ""; property bool on: false; signal pick()
        width: ct.implicitWidth + 28; height: 32; radius: 16
        color: on ? Theme.accent : Theme.soft; Behavior on color { ColorAnimation { duration: Theme.dur } }
        Txt { id: ct; anchors.centerIn: parent; text: label; color: on ? "white" : Theme.text; bold: true; font.pixelSize: 12 }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: pick() }
    }

    ActionCard { head: tr("boost.ram"); body: tr("boost.ram.hint"); btn: tr("boost.ram.btn"); onGo: app.freeRam() }
    ActionCard { head: tr("boost.disk"); body: tr("boost.disk.hint"); btn: tr("boost.disk.btn"); onGo: app.optimizeDisks() }

    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("boost.fx"); font.pixelSize: 15; bold: true }
        Txt { text: tr("boost.fx.hint"); muted: true; width: parent.width }
        Row { spacing: 8
            Chip { label: tr("boost.fx.perf"); on: app.fxMode === "perf"; onPick: app.setFx("perf") }
            Chip { label: tr("boost.fx.balanced"); on: app.fxMode === "balanced"; onPick: app.setFx("balanced") }
            Chip { label: tr("boost.fx.pretty"); on: app.fxMode === "pretty"; onPick: app.setFx("pretty") } }
    } }
    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("boost.power"); font.pixelSize: 15; bold: true }
        Txt { text: tr("boost.power.hint"); muted: true; width: parent.width }
        Row { spacing: 8
            Chip { label: tr("boost.power.high"); on: app.powerPlan === "high"; onPick: app.setPower("high") }
            Chip { label: tr("boost.power.balanced"); on: app.powerPlan === "balanced"; onPick: app.setPower("balanced") } }
    } }
    Card { Row { width: parent.width; spacing: 20
        Column { width: parent.width - 70; spacing: 4
            Txt { text: tr("boost.sched"); font.pixelSize: 15; bold: true }
            Txt { text: tr("boost.sched.hint"); muted: true; width: parent.width }
            Txt { text: app.scheduleState["enabled"] ? tr1("boost.sched.next", app.scheduleState["next"] || "") : tr("common.off"); muted: true; font.pixelSize: 12 } }
        Toggle { anchors.verticalCenter: parent.verticalCenter; checked: app.scheduleState["enabled"] === true; onToggled: v => app.setSchedule(v) }
    } }
    ActionCard { head: tr("boost.update"); body: tr("boost.update.hint"); btn: tr("boost.update.btn"); needsIdle: false; onGo: app.openUpdate() }
}
