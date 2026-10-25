import QtQuick
import QtQuick.Controls
import Sweep
import "components"
import "pages"

ApplicationWindow {
    id: win
    width: 1160; height: 760
    minimumWidth: 980; minimumHeight: 680
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
    function tr2(key, a, b) { return langTick, app.t2(key, a, b) }
    // confirmation dialog for actions that cannot wait (restart and the like)
    property var confirmFn: null
    property string confirmTitle: ""
    property string confirmText: ""
    property string confirmOk: ""
    function ask(title, text, okText, fn) { confirmTitle = title; confirmText = text; confirmOk = okText; confirmFn = fn }

    property int current: 0
    property var visited: ({})
    onCurrentChanged: {
        app.setMonitorActive(current === 0)
        var key = navKeys[current]
        if (!visited[key]) {
            var v = visited; v[key] = true; visited = v
            if (key === "registry") app.regScan()
            else if (key === "apps") app.scanPrograms()
        }
    }
    readonly property var navKeys: ["overview", "junk", "privacy", "guard", "boot", "startup", "services", "registry", "boost", "disks", "apps", "system", "quarantine", "settings"]
    readonly property var navIcons: ["layout-dashboard", "trash-2", "shield-check", "radar", "timer", "power", "server", "database", "rocket", "hard-drive", "package", "cpu", "archive", "settings"]
    function go(key) { var i = navKeys.indexOf(key); if (i >= 0) current = i }

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
            id: indicator; x: 12; width: side.width - 24; height: 36; radius: 11
            color: Theme.dark ? "#2A1F5E" : "#DDD6FE"
            y: navCol.y + current * 40
            Behavior on y { NumberAnimation { duration: Theme.dur + 80; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.dur } }
        }
        Column {
            id: navCol; anchors.top: logo.bottom; anchors.topMargin: 18; anchors.left: parent.left; anchors.right: parent.right; spacing: 4
            Repeater { model: navKeys.length
                Item { width: side.width; height: 36
                    Row { anchors.fill: parent; anchors.leftMargin: 26; spacing: 12
                        Icon { name: navIcons[index]; size: 18; color: current === index ? Theme.accent2 : Theme.muted; anchors.verticalCenter: parent.verticalCenter
                            Behavior on color { ColorAnimation { duration: Theme.dur } } }
                        Txt { text: tr("nav." + navKeys[index]); font.pixelSize: 14; bold: true; color: current === index ? Theme.text : Theme.muted; anchors.verticalCenter: parent.verticalCenter
                            Behavior on color { ColorAnimation { duration: Theme.dur } } }
                    }
                    Rectangle { // updates waiting on the Programs page
                        property int n: navKeys[index] === "apps" ? (app.programUpdates["count"] || 0) : 0
                        visible: n > 0; anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(20, nb.implicitWidth + 10); height: 20; radius: 10; color: Theme.accent
                        Txt { id: nb; anchors.centerIn: parent; text: String(parent.n); color: "white"; bold: true; font.pixelSize: 11 } }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true; onClicked: current = index
                        Rectangle { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; radius: 12; color: Theme.text; opacity: parent.containsMouse && current !== index ? 0.05 : 0 } }
                }
            }
        }

        // PC profile badge (hidden when the window is too short for it)
        Rectangle {
            visible: navCol.y + navCol.height + 16 < y
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
                Txt { text: (app.pcProfile["ram_gb"] || "") + " " + tr("u.gb") + " · " + (app.pcProfile["threads"] || "") + " " + tr("u.thr") + " · " + (app.pcProfile["ssd"] ? "SSD" : "HDD"); muted: true; font.pixelSize: 11 }
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
                Icon { name: "triangle-alert"; size: 20; color: Theme.warn; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("admin.banner"); width: parent.width - grantBtn.width - 48; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13 }
                AccentButton { id: grantBtn; text: tr("admin.grant"); compact: true; anchors.verticalCenter: parent.verticalCenter; onClicked: app.requestAdmin(navKeys[current]) }
            }
        }
        StackLayout_ { id: stack; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.top: adminBar.visible ? adminBar.bottom : parent.top; anchors.topMargin: adminBar.visible ? 14 : 0
            currentIndex: current
            OverviewPage {} JunkPage {} PrivacyPage {} GuardPage {} BootPage {} StartupPage {} ServicesPage {}
            RegistryPage {} BoostPage {} DisksPage {} AppsPage {} SystemPage {} QuarantinePage {} SettingsPage {}
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

    // ---------- notes list used by the update dialogs (changes are written in English) ----------
    component Notes: Rectangle {
        property var notes: []
        width: parent ? parent.width : 400
        height: notesCol.implicitHeight + 28; radius: 14; color: Theme.cardAlt; border.color: Theme.border
        Column { id: notesCol; anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.margins: 16; spacing: 7
            Repeater { model: notes.length ? notes : [tr("upd.nonotes")]
                Row { spacing: 10; width: notesCol.width
                    Icon { name: "check"; size: 15; color: Theme.good; anchors.top: parent.top; anchors.topMargin: 1 }
                    Txt { text: modelData; width: notesCol.width - 26; font.pixelSize: 13 } } }
        }
    }

    // ---------- terms of use: first start and whenever the terms change ----------
    Modal { open: app.needTerms; icon: "shield-check"; title: tr("terms.title"); subtitle: tr("terms.sub")
        Repeater { model: ["terms.1", "terms.2", "terms.3", "terms.4"]
            Row { spacing: 12; width: parent.width
                Icon { name: "circle-check"; size: 18; color: Theme.accent2; anchors.top: parent.top; anchors.topMargin: 1 }
                Txt { text: tr(modelData); width: parent.width - 30 } } }
        Row { spacing: 10; topPadding: 6
            AccentButton { text: tr("terms.accept"); onClicked: app.acceptTerms() }
            AccentButton { text: tr("terms.licence"); primary: false; onClicked: app.openUrl("https://github.com/pabloescobarbl-ops/sweep/blob/main/LICENSE") }
            AccentButton { text: tr("terms.decline"); primary: false; onClicked: app.declineTerms() } }
    }

    // ---------- after an update: what is new ----------
    Modal { open: !app.needTerms && app.whatsNew["tag"] !== undefined; icon: "sparkles"
        title: tr1("new.title", app.whatsNew["tag"] || ""); subtitle: tr("new.sub")
        Notes { notes: app.whatsNew["notes"] || [] }
        AccentButton { text: tr("new.ok"); onClicked: app.dismissWhatsNew() }
    }

    // ---------- a new version is out: reminder with the changes, the user decides ----------
    Modal { open: !app.needTerms && app.whatsNew["tag"] === undefined && app.updatePrompt["tag"] !== undefined; icon: "download"
        title: tr1("upd.title", app.updatePrompt["tag"] || ""); subtitle: tr1("upd.current", app.version)
        Notes { notes: app.updatePrompt["notes"] || [] }
        Txt { text: tr("upd.consent"); muted: true; font.pixelSize: 12; width: parent.width }
        Row { spacing: 10
            AccentButton { text: tr("upd.install"); enabled: !app.busy; onClicked: app.acceptUpdate() }
            AccentButton { text: tr("upd.later"); primary: false; onClicked: app.remindLater() }
            AccentButton { text: tr("upd.skip"); primary: false; onClicked: app.skipVersion() } }
    }

    Modal { open: confirmFn !== null; icon: "triangle-alert"; title: confirmTitle; boxWidth: 520
        Txt { text: confirmText; width: parent.width }
        Row { spacing: 10
            AccentButton { text: confirmOk; onClicked: { var f = confirmFn; confirmFn = null; if (f) f() } }
            AccentButton { text: tr("common.cancel"); primary: false; onClicked: confirmFn = null } }
    }

    // ---------- thorough uninstall wizard ----------
    component Check: Rectangle {
        property bool on: false; signal flip()
        width: 22; height: 22; radius: 7; color: on ? Theme.accent : "transparent"; border.width: on ? 0 : 2; border.color: Theme.faint
        Icon { anchors.centerIn: parent; name: "check"; size: 14; color: "white"; visible: parent.on }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.flip() }
    }
    component Spinner: Icon {
        name: "refresh-cw"; size: 22; color: Theme.accent2
        RotationAnimation on rotation { from: 0; to: 360; duration: 1100; loops: Animation.Infinite; running: parent.visible }
    }
    Modal {
        id: unModal
        property var u: app.uninstallState
        property string st: u["stage"] || ""
        open: st !== ""
        boxWidth: 760
        icon: st === "done" ? "circle-check" : st === "leftovers" ? "search" : "package"
        title: st === "confirm" ? tr1("un.title.confirm", u["name"] || "") : st === "uninstalling" ? tr1("un.title.running", u["name"] || "")
             : st === "scanning" ? tr("un.title.scanning") : st === "leftovers" ? tr("un.title.leftovers") : st === "removing" ? tr("un.title.removing")
             : tr1("un.title.done", u["name"] || "")
        subtitle: st === "confirm" ? [u["publisher"], u["version"]].filter(function (x) { return x }).join("  ·  ") : ""

        // confirm
        Column { width: parent.width; spacing: 12; visible: unModal.st === "confirm"
            Txt { text: tr("un.confirm.text"); width: parent.width }
            Row { spacing: 10; visible: (unModal.u["running"] || []).length > 0; width: parent.width
                Icon { name: "triangle-alert"; size: 16; color: Theme.warn; anchors.top: parent.top; anchors.topMargin: 1 }
                Txt { text: tr1("un.running.warn", (unModal.u["running"] || []).join(", ")); color: Theme.warn; width: parent.width - 30 } }
            ToggleRow { visible: unModal.u["quietAvailable"] === true; icon: "zap"; title: tr("un.quiet"); hint: tr("un.quiet.hint"); checked: unModal.u["quiet"] === true
                onToggled: v => app.setUninstallQuiet(v) }
            Txt { text: tr("un.forced.hint"); muted: true; font.pixelSize: 12; width: parent.width }
            Row { spacing: 10
                AccentButton { text: tr("un.go"); onClicked: app.confirmUninstall(false) }
                AccentButton { text: tr("un.forced"); primary: false; onClicked: app.confirmUninstall(true) }
                AccentButton { text: tr("common.cancel"); primary: false; onClicked: app.closeUninstall() } }
        }
        // waiting
        Column { width: parent.width; spacing: 14; visible: unModal.st === "uninstalling" || unModal.st === "scanning" || unModal.st === "removing"
            Row { spacing: 14; width: parent.width
                Spinner { anchors.verticalCenter: parent.verticalCenter }
                Txt { width: parent.width - 40; anchors.verticalCenter: parent.verticalCenter
                    text: unModal.st === "uninstalling" ? (unModal.u["forced"] ? tr("un.wait.forced") : tr("un.wait.vendor"))
                         : unModal.st === "scanning" ? tr("un.wait.scan") : tr("un.wait.remove") } }
            AccentButton { visible: unModal.st === "uninstalling" && !unModal.u["forced"]; text: tr("un.skip"); primary: false; onClicked: app.skipWaiting() }
        }
        // leftovers
        Column { width: parent.width; spacing: 10; visible: unModal.st === "leftovers"
            Txt { width: parent.width
                text: tr2("un.found.text", String((unModal.u["leftovers"] || []).length), String(unModal.u["checkedCount"] || 0)) + (unModal.u["checkedSize"] > 0 ? "  ·  " + app.size(unModal.u["checkedSize"]) : "") }
            Txt { visible: unModal.u["still"] === true; text: tr("un.still"); color: Theme.warn; width: parent.width; font.pixelSize: 12 }
            Rectangle { width: parent.width; height: Math.min(330, list.contentHeight + 12); radius: 14; color: Theme.cardAlt; border.color: Theme.border; clip: true
                Flickable { id: list; anchors.fill: parent; anchors.margins: 6; contentHeight: lcol.implicitHeight; clip: true; boundsBehavior: Flickable.StopAtBounds
                    Column { id: lcol; width: list.width
                        Repeater { model: unModal.u["leftovers"] || []
                            Item { width: lcol.width; height: 44
                                Check { id: ck; on: modelData.checked; anchors.left: parent.left; anchors.leftMargin: 8; anchors.verticalCenter: parent.verticalCenter
                                    onFlip: app.setLeftover(modelData.id, !modelData.checked) }
                                Rectangle { id: kd; anchors.left: ck.right; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                                    width: 96; height: 24; radius: 12; color: Theme.soft
                                    Txt { anchors.centerIn: parent; text: modelData.kindText; font.pixelSize: 11; bold: true } }
                                Txt { anchors.left: kd.right; anchors.leftMargin: 10; anchors.right: meta.left; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.path; font.pixelSize: 12; elide: Text.ElideMiddle; wrapMode: Text.NoWrap }
                                Row { id: meta; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                    Txt { text: tr("un.similar"); color: Theme.warn; font.pixelSize: 11; visible: !modelData.exact }
                                    Txt { text: modelData.sizeText; muted: true; font.pixelSize: 11 } }
                            }
                        }
                    }
                }
            }
            Txt { text: tr("un.safe"); muted: true; font.pixelSize: 12; width: parent.width }
            Row { spacing: 10
                AccentButton { text: tr("un.clean"); danger: true; enabled: (unModal.u["checkedCount"] || 0) > 0; onClicked: app.removeLeftovers() }
                AccentButton { text: tr("un.all"); primary: false; onClicked: app.setAllLeftovers(true) }
                AccentButton { text: tr("un.none"); primary: false; onClicked: app.setAllLeftovers(false) }
                AccentButton { text: tr("un.leave"); primary: false; onClicked: app.closeUninstall() } }
        }
        // done
        Column { width: parent.width; spacing: 12; visible: unModal.st === "done"
            property var r: unModal.u["result"] || ({})
            Txt { width: parent.width
                text: tr2("un.done.text", String(parent.r["removed"] || 0), app.size(parent.r["freed"] || 0)) }
            Txt { visible: (parent.r["reboot"] || 0) > 0; width: parent.width; color: Theme.warn; text: tr1("un.done.reboot", String(parent.r["reboot"] || 0)) }
            Txt { visible: (parent.r["failed"] || []).length > 0; width: parent.width; color: Theme.bad; text: tr1("un.done.failed", String((parent.r["failed"] || []).length)) }
            Txt { text: tr("un.done.safe"); muted: true; width: parent.width; font.pixelSize: 12 }
            AccentButton { text: tr("un.close"); onClicked: app.closeUninstall() }
        }
    }
}
