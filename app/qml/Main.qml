import QtQuick
import QtQuick.Controls
import Sweep
import "components"
import "pages"

ApplicationWindow {
    id: win
    width: 1160; height: 760
    minimumWidth: 960; minimumHeight: 640
    visible: true
    title: "Sweep"
    color: Theme.bg
    font.family: Theme.font

    Component.onCompleted: {
        Theme.dark = app.theme !== "light"; Theme.accentName = app.accent; Theme.anim = app.animations
        var i = navKeys.indexOf(app.startPage)          // after a restart with administrator rights
        if (i > 0) current = i
    }
    Connections { target: app
        function onLangChanged() { Theme.dark = app.theme !== "light"; Theme.accentName = app.accent; Theme.anim = app.animations; langTick++ }
        function onToast(msg) { toastText.text = msg; toastAnim.restart() }
    }
    property int langTick: 0            // bump to re-evaluate translated texts
    function tr(key) { return langTick, app.t(key) }
    function tr1(key, a) { return langTick, app.t1(key, a) }

    property int current: 0
    property var visited: ({})
    onCurrentChanged: {
        app.setMonitorActive(current === 0)
        var key = navKeys[current]
        if (!visited[key]) {
            var v = visited; v[key] = true; visited = v
            if (key === "registry") app.regScan()
            else if (key === "apps") app.scanApps()
        }
    }
    readonly property var navKeys: ["overview", "junk", "privacy", "registry", "services", "startup", "boost", "disks", "apps", "system", "quarantine", "settings"]
    readonly property var navIcons: ["⌂", "⌘", "◉", "☰", "⚙", "⏻", "⚡", "▤", "▦", "≡", "⚑", "⚙"]

    // ---------- sidebar ----------
    Rectangle {
        id: side
        width: 236; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
        color: Theme.side
        Behavior on color { ColorAnimation { duration: Theme.dur } }

        Row { id: logo; anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 24; anchors.topMargin: 26; spacing: 12
            Rectangle { width: 40; height: 40; radius: 12
                gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
                Text { anchors.centerIn: parent; text: "S"; color: "white"; font.pixelSize: 20; font.weight: Font.Bold; font.family: Theme.font }
            }
            Column { anchors.verticalCenter: parent.verticalCenter; spacing: 0
                Txt { text: "Sweep"; font.pixelSize: 20; bold: true; font.weight: Font.Bold }
                Txt { text: tr("set.version") + " " + app.version; muted: true; font.pixelSize: 11 }
            }
        }

        // sliding indicator
        Rectangle {
            id: indicator; x: 12; width: side.width - 24; height: 40; radius: 12
            color: Theme.dark ? "#2A1F5E" : "#DDD6FE"
            y: navCol.y + current * 44
            Behavior on y { NumberAnimation { duration: Theme.dur + 80; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.dur } }
        }
        Column {
            id: navCol; anchors.top: logo.bottom; anchors.topMargin: 18; anchors.left: parent.left; anchors.right: parent.right; spacing: 4
            Repeater { model: navKeys.length
                Item { width: side.width; height: 40
                    Row { anchors.fill: parent; anchors.leftMargin: 26; spacing: 12
                        Text { text: navIcons[index]; width: 20; color: current === index ? Theme.accent2 : Theme.muted; font.pixelSize: 15; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter
                            Behavior on color { ColorAnimation { duration: Theme.dur } } }
                        Txt { text: tr("nav." + navKeys[index]); font.pixelSize: 14; bold: true; color: current === index ? Theme.text : Theme.muted; anchors.verticalCenter: parent.verticalCenter
                            Behavior on color { ColorAnimation { duration: Theme.dur } } }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true; onClicked: current = index
                        Rectangle { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; radius: 12; color: Theme.text; opacity: parent.containsMouse && current !== index ? 0.05 : 0 } }
                }
            }
        }

        // PC profile badge
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 16; anchors.bottomMargin: 18
            height: badgeCol.implicitHeight + 24; radius: 14; color: Theme.card; border.color: Theme.border
            Behavior on color { ColorAnimation { duration: Theme.dur } }
            Column { id: badgeCol; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                Label10 { text: tr("ov.profile").toUpperCase() }
                Row { spacing: 8
                    Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                        color: app.pcProfile["class"] === "strong" ? Theme.good : app.pcProfile["class"] === "weak" ? Theme.bad : Theme.warn }
                    Txt { text: tr("ov.profile." + (app.pcProfile["class"] || "mid")); bold: true; font.pixelSize: 13 }
                }
                Txt { text: (app.pcProfile["ram_gb"] || "") + " " + tr("u.gb") + " · " + (app.pcProfile["threads"] || "") + " thr · " + (app.pcProfile["ssd"] ? "SSD" : "HDD"); muted: true; font.pixelSize: 11 }
            }
        }
    }

    // ---------- content ----------
    Item {
        id: content
        anchors.left: side.right; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: statusBar.top
        anchors.margins: 26; anchors.bottomMargin: 14

        // no administrator rights: say so and offer the UAC prompt
        Rectangle {
            id: adminBar; visible: !app.isAdmin
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: visible ? Math.max(52, adminRow.implicitHeight + 20) : 0; radius: 14
            color: Theme.dark ? "#3A2A12" : "#FEF3C7"; border.color: Theme.warn
            Row { id: adminRow; anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 16; anchors.rightMargin: 12; spacing: 12
                Text { text: "\u26A0"; color: Theme.warn; font.pixelSize: 18; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("admin.banner"); width: parent.width - grantBtn.width - 48; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13 }
                AccentButton { id: grantBtn; text: tr("admin.grant"); compact: true; anchors.verticalCenter: parent.verticalCenter; onClicked: app.requestAdmin(navKeys[current]) }
            }
        }
        StackLayout_ { id: stack; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.top: adminBar.visible ? adminBar.bottom : parent.top; anchors.topMargin: adminBar.visible ? 14 : 0
            currentIndex: current
            OverviewPage {} JunkPage {} PrivacyPage {} RegistryPage {} ServicesPage {} StartupPage {}
            BoostPage {} DisksPage {} AppsPage {} SystemPage {} QuarantinePage {} SettingsPage {}
        }
    }

    // ---------- status bar ----------
    Rectangle {
        id: statusBar
        anchors.left: side.right; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 44; color: Theme.status
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Rectangle { // progress line
            anchors.top: parent.top; height: 2; width: parent.width * 0.3; color: Theme.accent2; visible: app.busy
            SequentialAnimation on x { running: app.busy; loops: Animation.Infinite
                NumberAnimation { from: -statusBar.width * 0.3; to: statusBar.width; duration: 1100; easing.type: Easing.InOutQuad } }
        }
        Row { anchors.left: parent.left; anchors.leftMargin: 26; anchors.verticalCenter: parent.verticalCenter; spacing: 10
            Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter; color: app.busy ? Theme.warn : Theme.good
                SequentialAnimation on opacity { running: app.busy; loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 500 } NumberAnimation { to: 1; duration: 500 } } }
            Text { text: app.status; color: Theme.statusText; font.family: Theme.font; font.pixelSize: 12; renderType: Text.NativeRendering; width: statusBar.width - 200; elide: Text.ElideRight }
        }
        Txt { anchors.right: parent.right; anchors.rightMargin: 26; anchors.verticalCenter: parent.verticalCenter; text: app.demo ? tr("common.demo") : ""; color: Theme.warn; font.pixelSize: 11 }
    }

    // ---------- toast ----------
    Rectangle {
        id: toast; anchors.horizontalCenter: content.horizontalCenter; y: win.height; width: toastText.implicitWidth + 44; height: 44; radius: 22
        color: Theme.dark ? "#2A1F5E" : "#1E1B3A"; border.color: Theme.accent
        Txt { id: toastText; anchors.centerIn: parent; color: "white"; bold: true }
        SequentialAnimation { id: toastAnim
            NumberAnimation { target: toast; property: "y"; to: win.height - 110; duration: 300; easing.type: Easing.OutBack }
            PauseAnimation { duration: 2600 }
            NumberAnimation { target: toast; property: "y"; to: win.height; duration: 250; easing.type: Easing.InCubic } }
    }
}
