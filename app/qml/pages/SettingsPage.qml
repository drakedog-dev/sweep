import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.settings"); subtitle: tr("hdr.settings")
    component Chip: Rectangle {
        property string label: ""; property bool on: false; property color dot: "transparent"; signal pick()
        width: ct.implicitWidth + 28 + (dot.a > 0 ? 18 : 0); height: 32; radius: 16
        color: on ? Theme.accent : Theme.soft; Behavior on color { ColorAnimation { duration: Theme.dur } }
        Row { anchors.centerIn: parent; spacing: 8
            Rectangle { width: 12; height: 12; radius: 6; color: dot; visible: dot.a > 0; anchors.verticalCenter: parent.verticalCenter }
            Txt { id: ct; text: label; color: on ? "white" : Theme.text; bold: true; font.pixelSize: 12 } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: pick() }
    }
    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("set.lang"); font.pixelSize: 15; bold: true }
        Row { spacing: 8
            Chip { label: "Русский"; on: app.lang === "ru"; onPick: app.setLang("ru") }
            Chip { label: "English"; on: app.lang === "en"; onPick: app.setLang("en") } }
    } }
    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("set.theme"); font.pixelSize: 15; bold: true }
        Row { spacing: 8
            Chip { label: tr("set.theme.dark"); on: Theme.dark; onPick: app.setTheme("dark") }
            Chip { label: tr("set.theme.light"); on: !Theme.dark; onPick: app.setTheme("light") } }
        Txt { text: tr("set.accent"); font.pixelSize: 15; bold: true; topPadding: 8 }
        Row { spacing: 8
            Repeater { model: ["violet", "cyan", "green", "amber", "rose"]
                Chip { label: modelData; dot: Theme.accents[modelData][1]; on: Theme.accentName === modelData; onPick: app.setAccent(modelData) } } }
        Row { spacing: 14; topPadding: 8
            Txt { text: tr("set.anim"); font.pixelSize: 15; bold: true; anchors.verticalCenter: parent.verticalCenter }
            Toggle { checked: Theme.anim; onToggled: v => app.setAnimations(v) } }
    } }
    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("set.renderer"); font.pixelSize: 15; bold: true }
        Txt { text: tr("set.renderer.hint"); muted: true; width: parent.width }
        Row { spacing: 8
            Chip { label: tr("set.renderer.gpu"); on: app.renderer === "gpu"; onPick: app.setRenderer("gpu") }
            Chip { label: tr("set.renderer.cpu"); on: app.renderer === "cpu"; onPick: app.setRenderer("cpu") }
            AccentButton { text: tr("set.restart"); compact: true; primary: false; onClicked: app.restartApp() } }
    } }
    Card { Column { width: parent.width; spacing: 10
        Txt { text: tr("set.updates"); font.pixelSize: 15; bold: true }
        Row { width: parent.width; spacing: 14
            Column { width: parent.width - 70; spacing: 2
                Txt { text: tr("set.autoupdate"); bold: true }
                Txt { text: tr("set.autoupdate.hint"); muted: true; font.pixelSize: 12; width: parent.width } }
            Toggle { anchors.verticalCenter: parent.verticalCenter; checked: app.autoUpdate; onToggled: v => app.setAutoUpdate(v) } }
        Txt { text: tr("set.about"); muted: true; width: parent.width }
        Row { spacing: 10
            AccentButton { text: tr("set.check"); primary: false; compact: true; enabled: !app.busy; onClicked: app.checkUpdates() }
            AccentButton { text: tr1("set.install", app.updateInfo["tag"] || ""); compact: true; visible: app.updateInfo["newer"] === true; onClicked: app.installUpdate() } }
    } }
    Card { Column { width: parent.width; spacing: 10
        Row { spacing: 12
            Rectangle { width: 44; height: 44; radius: 13
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
                Text { anchors.centerIn: parent; text: "S"; color: "white"; font.pixelSize: 22; font.weight: Font.Bold; font.family: Theme.font } }
            Column { anchors.verticalCenter: parent.verticalCenter
                Txt { text: tr("about.title") + "  ·  Sweep " + app.version; font.pixelSize: 15; bold: true }
                Txt { text: tr("about.author") + "  ·  " + tr("about.licence"); muted: true; font.pixelSize: 12 } }
        }
        Txt { text: tr("about.text"); muted: true; width: parent.width }
        Txt { text: tr("about.star"); width: parent.width }
        Txt { text: tr("about.issues"); width: parent.width }
        Row { spacing: 10; topPadding: 4
            AccentButton { text: "\u2605  " + tr("about.star.btn"); compact: true; onClicked: app.openUrl("https://github.com/pabloescobarbl-ops/sweep") }
            AccentButton { text: tr("about.issues.btn"); compact: true; primary: false; onClicked: app.openUrl("https://github.com/pabloescobarbl-ops/sweep/issues/new") }
            AccentButton { text: tr("about.source"); compact: true; primary: false; onClicked: app.openUrl("https://github.com/pabloescobarbl-ops/sweep") }
            AccentButton { text: tr("about.licence"); compact: true; primary: false; onClicked: app.openUrl("https://github.com/pabloescobarbl-ops/sweep/blob/main/LICENSE") } }
    } }
}
