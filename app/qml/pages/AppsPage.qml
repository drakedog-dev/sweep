import QtQuick
import Sweep
import "../components"

// Programs: thorough uninstaller, updates from the vendors' sites (winget), pre-installed Windows apps
Page {
    id: pg
    objectName: "appsPage"
    title: tr("nav.apps"); subtitle: tr("hdr.apps")
    hint: tab === 0 ? tr("un.hint") : tab === 2 ? tr("pu.hint") : tr("apps.hint")
    property int tab: 0                  // 0 installed programs, 2 updates, 1 built-in apps
    property var picked: ({})
    property string query: ""
    property var pu: app.programUpdates
    property var shown: { var q = query.trim().toLowerCase(); var l = app.programList; if (!q) return l
        var out = []; for (var i = 0; i < l.length; i++) if (l[i].name.toLowerCase().indexOf(q) >= 0 || l[i].publisher.toLowerCase().indexOf(q) >= 0) out.push(l[i]); return out }
    bigLabel: tab === 0 ? tr("un.installed") : tab === 2 ? tr("pu.big") : tr("apps.found")
    bigValue: tab === 0 ? String(app.programCount) : tab === 2 ? (pu.checked ? String(pu.count) : "—") : String(app.appList.length)
    onTabChanged: if (tab === 2 && !pu.checked && !pu.checking) app.scanUpdates()

    component Tab: Rectangle {
        property string label: ""; property string icon: ""; property bool on: false; property int badge: 0; signal pick()
        width: tr_.implicitWidth + 50; height: 38; radius: 19
        color: on ? Theme.accent : Theme.soft
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Row { id: tr_; anchors.centerIn: parent; spacing: 8
            Icon { name: icon; size: 16; color: on ? "white" : Theme.muted; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: label; bold: true; color: on ? "white" : Theme.text; anchors.verticalCenter: parent.verticalCenter }
            Rectangle { visible: badge > 0; width: Math.max(20, bt.implicitWidth + 10); height: 20; radius: 10; anchors.verticalCenter: parent.verticalCenter
                color: on ? "#33FFFFFF" : Theme.accent
                Txt { id: bt; anchors.centerIn: parent; text: String(badge); color: "white"; bold: true; font.pixelSize: 11 } } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: pick() }
    }
    component SortChip: Rectangle {
        property string label: ""; property string key: ""
        width: sl.implicitWidth + 24; height: 30; radius: 15; color: app.programSort === key ? Theme.cardAlt : "transparent"; border.color: app.programSort === key ? Theme.accent : Theme.border
        Txt { id: sl; anchors.centerIn: parent; text: label; font.pixelSize: 12; bold: app.programSort === key }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.setProgramSort(key) }
    }
    component Box: Rectangle {
        property bool on: false; property bool partial: false; signal flip()
        width: 22; height: 22; radius: 7; color: on || partial ? Theme.accent : "transparent"; border.width: on || partial ? 0 : 2; border.color: Theme.faint
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Icon { anchors.centerIn: parent; name: "check"; size: 14; color: "white"; visible: parent.on }
        Rectangle { anchors.centerIn: parent; width: 10; height: 2; radius: 1; color: "white"; visible: parent.partial && !parent.on }
        MouseArea { anchors.fill: parent; cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: parent.flip() }
    }
    component Bar: Rectangle {
        property real value: -1                  // 0..1, or -1 while the size is unknown
        height: 6; radius: 3; color: Theme.track; clip: true
        Rectangle { visible: parent.value >= 0; height: parent.height; radius: 3; width: parent.width * Math.max(0, Math.min(1, parent.value))
            Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } } }
        Rectangle { id: stripe; visible: parent.value < 0; height: parent.height; radius: 3; width: parent.width * 0.28
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
            SequentialAnimation on x { running: stripe.visible; loops: Animation.Infinite
                NumberAnimation { from: -stripe.width; to: stripe.parent ? stripe.parent.width : 300; duration: 1300; easing.type: Easing.InOutQuad } } }
    }
    function phaseText(it) {
        if (it.phase === "download") {
            if (it.total === 100 && it.got <= 100) return tr1("pu.ph.downloadP", String(Math.round(it.got)))
            var t = it.total > 0 ? tr("pu.ph.download").replace("{0}", app.size(it.got)).replace("{1}", app.size(it.total)) : tr1("pu.ph.downloadN", app.size(it.got))
            return it.speed > 1024 ? t + "  ·  " + tr1("pu.speed", app.size(it.speed)) : t
        }
        return tr("pu.ph." + (it.phase || "prepare"))
    }
    function phaseValue(it) {
        if (it.phase === "download" && it.total > 0) return it.got / it.total
        return -1
    }
    component PickChip: Rectangle {
        property string label: ""; property string mode: ""
        width: pcT.implicitWidth + 26; height: 30; radius: 15; color: pcHov.containsMouse && enabled ? Theme.softHover : Theme.soft
        opacity: enabled ? 1 : 0.4; enabled: !pu.running
        Txt { id: pcT; anchors.centerIn: parent; text: label; font.pixelSize: 12; bold: true }
        MouseArea { id: pcHov; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: app.pickUpdates(mode) }
    }
    component Spin: Icon {
        name: "refresh-cw"; size: 18; color: Theme.accent2
        RotationAnimation on rotation { from: 0; to: 360; duration: 1100; loops: Animation.Infinite; running: parent.visible }
    }
    component AppIcon: Rectangle {
        property string src: ""
        width: 40; height: 40; radius: 11; color: Theme.soft
        Image { id: im; anchors.centerIn: parent; width: 28; height: 28; source: parent.src; sourceSize.width: 32; sourceSize.height: 32; asynchronous: true; visible: status === Image.Ready && parent.src !== "" }
        Icon { anchors.centerIn: parent; name: "app-window"; size: 18; color: Theme.accent2; visible: !im.visible }
    }

    Row { spacing: 10
        Tab { label: tr("un.tab.programs"); icon: "package"; on: pg.tab === 0; onPick: pg.tab = 0 }
        Tab { label: tr("pu.tab"); icon: "circle-arrow-up"; on: pg.tab === 2; badge: pu.count || 0; onPick: pg.tab = 2 }
        Tab { label: tr("un.tab.builtin"); icon: "layout-grid"; on: pg.tab === 1; onPick: { pg.tab = 1; if (app.appList.length === 0) app.scanApps() } }
    }

    // ---------- installed programs ----------
    Card { visible: pg.tab === 0; pad: 12
        Column { width: parent.width; spacing: 8
            Row { width: parent.width; spacing: 10
                Rectangle { width: parent.width - sorts.width - 10; height: 38; radius: 12; color: Theme.cardAlt; border.color: search.activeFocus ? Theme.accent : Theme.border
                    Icon { id: sIcon; name: "search"; size: 16; color: Theme.muted; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                    TextInput { id: search; anchors.left: sIcon.right; anchors.leftMargin: 10; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        color: Theme.text; font.family: Theme.font; font.pixelSize: 13; clip: true; selectByMouse: true
                        onTextChanged: pg.query = text
                        Txt { anchors.verticalCenter: parent.verticalCenter; text: tr("un.search"); muted: true; visible: search.text === "" && !search.activeFocus } } }
                Row { id: sorts; spacing: 6; anchors.verticalCenter: parent.verticalCenter
                    SortChip { label: tr("un.sort.size"); key: "size" }
                    SortChip { label: tr("un.sort.name"); key: "name" }
                    SortChip { label: tr("un.sort.date"); key: "date" } }
            }
            Empty { msg: app.programCount === 0 ? tr("un.empty") : tr("un.nothing"); visible: pg.shown.length === 0 }
            Repeater { model: pg.shown
                Rectangle { width: parent.width; height: 58; radius: 12
                    color: rowHov.containsMouse ? Theme.cardAlt : "transparent"
                    MouseArea { id: rowHov; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                    AppIcon { id: ico; src: modelData.icon; anchors.left: parent.left; anchors.leftMargin: 8; anchors.verticalCenter: parent.verticalCenter }
                    Column { anchors.left: ico.right; anchors.leftMargin: 12; anchors.right: sz.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                        Txt { text: modelData.name; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap; muted: true; font.pixelSize: 12
                            text: [modelData.publisher, modelData.version, modelData.date].filter(function (x) { return x }).join("  ·  ") } }
                    Txt { id: sz; anchors.right: rm.left; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; width: 80; horizontalAlignment: Text.AlignRight
                        text: modelData.size > 0 ? app.size(modelData.size) : ""; muted: true; font.pixelSize: 12 }
                    AccentButton { id: rm; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        compact: true; primary: false; text: tr("un.remove"); enabled: !app.busy; onClicked: app.startUninstall(modelData.id) }
                }
            }
        }
    }

    // ---------- updates from the vendors' sites ----------
    Card { visible: pg.tab === 2; pad: 16
        Row { width: parent.width; spacing: 14
            Rectangle { id: trustIcon; width: 44; height: 44; radius: 13; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter
                Icon { anchors.centerIn: parent; name: "badge-check"; size: 22; color: Theme.good } }
            Column { width: parent.width - trustIcon.width - autoRow.width - 28; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                Txt { text: tr("pu.trust"); bold: true; font.pixelSize: 14; width: parent.width }
                Txt { text: pu.checked ? tr1("pu.when", pu.when) + (pu.skipped > 0 ? "  ·  " + tr1("pu.showSkipped", String(pu.skipped)) : "") : tr("pu.never")
                      muted: true; font.pixelSize: 12; width: parent.width
                      MouseArea { anchors.fill: parent; enabled: pu.skipped > 0; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: app.resetSkipped() } } }
            Row { id: autoRow; spacing: 10; anchors.verticalCenter: parent.verticalCenter
                Column { anchors.verticalCenter: parent.verticalCenter
                    Txt { text: tr("pu.auto"); bold: true; font.pixelSize: 13; anchors.right: parent.right }
                    Txt { text: tr("pu.auto.hint"); muted: true; font.pixelSize: 11; anchors.right: parent.right } }
                Toggle { checked: pu.auto === true; anchors.verticalCenter: parent.verticalCenter; onToggled: v => app.setUpdatesAuto(v) } }
        }
    }
    // progress while updating
    Card { visible: pg.tab === 2 && pu.running === true; pad: 16
        Column { width: parent.width; spacing: 10
            Row { spacing: 12; width: parent.width
                Spin { anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("pu.progress").replace("{0}", String(Math.min((pu.done || 0) + 1, pu.total || 1))).replace("{1}", String(pu.total || 0)).replace("{2}", pu.current || "")
                      bold: true; width: parent.width - 40; anchors.verticalCenter: parent.verticalCenter } }
            Rectangle { width: parent.width; height: 6; radius: 3; color: Theme.track
                Rectangle { height: parent.height; radius: 3; width: parent.width * Math.min(1, ((pu.done || 0) + (pu.frac || 0)) / Math.max(1, pu.total || 1))
                    Behavior on width { NumberAnimation { duration: Theme.durSlow; easing.type: Easing.OutCubic } }
                    gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } } } }
            Txt { property var w: (pu.items || []).filter(function (x) { return x.state === "working" })[0]
                  visible: w !== undefined; text: w ? pg.phaseText(w) : ""; muted: true; font.pixelSize: 12; width: parent.width }
        }
    }
    // no winget on this PC
    Card { visible: pg.tab === 2 && pu.checked && pu.winget === false; pad: 18
        Column { width: parent.width; spacing: 12
            Row { spacing: 12; width: parent.width
                Icon { name: "circle-alert"; size: 20; color: Theme.warn; anchors.top: parent.top; anchors.topMargin: 1 }
                Txt { text: tr("pu.nowinget"); width: parent.width - 34 } }
            AccentButton { text: tr("pu.getwinget"); compact: true; onClicked: app.openUrl("ms-windows-store://pdp/?productid=9NBLGGH4NNS1") }
        }
    }
    Card { visible: pg.tab === 2 && pu.winget !== false; pad: 12
        Column { width: parent.width; spacing: 6
            Row { spacing: 12; visible: pu.checking === true; leftPadding: 10; topPadding: 8; bottomPadding: 8
                Spin { anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("pu.checking"); muted: true; anchors.verticalCenter: parent.verticalCenter } }
            Row { spacing: 12; visible: !pu.checking && pu.checked && (pu.items || []).length === 0; leftPadding: 10; topPadding: 8; bottomPadding: 8
                Icon { name: "circle-check"; size: 20; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("pu.none"); anchors.verticalCenter: parent.verticalCenter } }
            Empty { msg: tr("pu.never"); visible: !pu.checking && !pu.checked }
            // select all / none / everything except major upgrades, then "Update selected" installs them in a queue
            Rectangle { id: selBar; visible: !pu.checking && (pu.count || 0) > 0; width: parent.width; height: 50; radius: 12; color: Theme.cardAlt
                property int open_: pu.count || 0
                property int sel: pu.picked || 0
                property bool hasMajor: (pu.items || []).some(function (x) { return x.major && x.state !== "ok" })
                Box { id: allBox; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; enabled: !pu.running
                      on: selBar.sel > 0 && selBar.sel === selBar.open_; partial: selBar.sel > 0 && selBar.sel < selBar.open_
                      onFlip: app.pickUpdates(selBar.sel === selBar.open_ ? "none" : "all") }
                Txt { anchors.left: allBox.right; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; bold: true
                      text: tr2("pu.selected", String(selBar.sel), String(selBar.open_)) }
                Row { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                    PickChip { label: tr("pu.pick.all"); mode: "all" }
                    PickChip { label: tr("pu.pick.minor"); mode: "minor"; visible: selBar.hasMajor }
                    PickChip { label: tr("pu.pick.none"); mode: "none" } }
            }
            Repeater { model: pu.checking ? [] : (pu.items || [])
                Rectangle { id: urow; width: parent.width; height: 62; radius: 12
                    property bool done_: modelData.state === "ok"
                    property bool fail: modelData.state === "failed"
                    property bool active: modelData.state === "working" || modelData.state === "queued"
                    color: uHov.containsMouse ? Theme.cardAlt : "transparent"
                    MouseArea { id: uHov; anchors.fill: parent; hoverEnabled: true     // a click anywhere on the row ticks it
                        cursorShape: !urow.done_ && !pu.running ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (!urow.done_ && !pu.running) app.setUpdatePick(modelData.id, !modelData.picked) }
                    Box { id: ub; on: modelData.picked === true && !urow.done_; opacity: urow.done_ ? 0.3 : 1; enabled: !urow.done_ && !pu.running
                          anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                          onFlip: app.setUpdatePick(modelData.id, !modelData.picked) }
                    AppIcon { id: uico; src: modelData.icon || ""; anchors.left: ub.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                    Column { anchors.left: uico.right; anchors.leftMargin: 12; anchors.right: right_.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                        Txt { text: modelData.title || modelData.name; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Column { visible: modelData.state === "working"; width: parent.width; spacing: 4
                            Bar { width: Math.min(parent.width, 360); value: pg.phaseValue(modelData) }
                            Txt { text: pg.phaseText(modelData); muted: true; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                        Row { spacing: 6; width: parent.width; visible: modelData.state !== "working"
                            Txt { text: modelData.version; muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                            Icon { name: "arrow-right"; size: 12; color: Theme.faint; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: modelData.available; font.pixelSize: 12; bold: true; color: urow.done_ ? Theme.good : Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
                            Rectangle { visible: modelData.major === true && !urow.done_ && !urow.fail; height: 18; width: mj.implicitWidth + 14; radius: 9; color: "transparent"; border.color: Theme.warn; anchors.verticalCenter: parent.verticalCenter
                                Txt { id: mj; anchors.centerIn: parent; text: tr("pu.major"); color: Theme.warn; font.pixelSize: 10; bold: true } }
                            Txt { visible: urow.fail; text: tr("pu.r." + (modelData.reason || "code")) + (modelData.reason === "code" && modelData.code ? " " + modelData.code : "")
                                  color: Theme.bad; font.pixelSize: 12; elide: Text.ElideRight; wrapMode: Text.NoWrap; anchors.verticalCenter: parent.verticalCenter }
                            Txt { visible: urow.done_ && modelData.reason === "reboot"; text: tr("pu.r.reboot"); color: Theme.warn; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                    }
                    Row { id: right_; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                        // where it comes from: the vendor's own address, checked by SHA-256
                        Rectangle { visible: (modelData.host || "") !== ""; height: 28; width: Math.min(230, srcRow.implicitWidth + 20); radius: 14; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter; clip: true
                            Row { id: srcRow; anchors.verticalCenter: parent.verticalCenter; x: 10; spacing: 6
                                Icon { name: modelData.sha256 ? "lock" : "globe"; size: 13; color: modelData.sha256 ? Theme.good : Theme.muted; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData.host; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter; width: Math.min(implicitWidth, 190); elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.openUrl(modelData.homepage || modelData.installer) } }
                        Item { width: 112; height: 34; anchors.verticalCenter: parent.verticalCenter
                            AccentButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: !urow.active && !urow.done_
                                compact: true; primary: false; text: tr("pu.update"); enabled: !app.busy && !pu.running; onClicked: app.updateOne(modelData.id) }
                            Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 6; visible: urow.active
                                Spin { size: 15; visible: modelData.state === "working"; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData.state === "queued" ? tr1("pu.st.queuedN", String(modelData.queue || ""))
                                          : pg.phaseValue(modelData) >= 0 ? Math.round(pg.phaseValue(modelData) * 100) + "%" : tr("pu.st." + modelData.state)
                                      font.pixelSize: 12; muted: modelData.state === "queued"; anchors.verticalCenter: parent.verticalCenter } }
                            Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 6; visible: urow.done_
                                Icon { name: "circle-check"; size: 16; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: tr("pu.st.ok"); color: Theme.good; bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } } }
                        Rectangle { width: 30; height: 30; radius: 10; color: skHov.containsMouse ? Theme.soft : "transparent"; anchors.verticalCenter: parent.verticalCenter; opacity: urow.done_ || pu.running ? 0.25 : 1
                            Icon { anchors.centerIn: parent; name: "eye-off"; size: 15; color: Theme.muted }
                            MouseArea { id: skHov; anchors.fill: parent; hoverEnabled: true; enabled: !urow.done_ && !pu.running; cursorShape: Qt.PointingHandCursor; onClicked: app.skipUpdate(modelData.id) }
                            Rectangle { visible: skHov.containsMouse; z: 5; anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.right: parent.right
                                width: tipT.implicitWidth + 18; height: 28; radius: 8; color: Theme.dark ? "#2A1F5E" : "#1E1B3A"
                                Txt { id: tipT; anchors.centerIn: parent; text: tr("pu.skip"); color: "white"; font.pixelSize: 11 } } }
                    }
                }
            }
            Txt { visible: !pu.checking && (pu.items || []).some(function (x) { return x.major && x.state !== "ok" }); text: tr("pu.major.hint")
                  muted: true; font.pixelSize: 12; width: parent.width; leftPadding: 10; topPadding: 4 }
        }
    }

    // ---------- pre-installed Windows apps ----------
    Card { visible: pg.tab === 1; pad: 10
        Column { width: parent.width
            Empty { msg: tr("apps.empty"); visible: app.appList.length === 0 }
            Repeater { model: app.appList
                ToggleRow { title: modelData.name; hint: modelData.hint; checked: picked[modelData.id] === true; onToggled: v => { var p = picked; p[modelData.id] = v; picked = p } } }
        }
    }
    footer: [
        AccentButton { visible: pg.tab === 0; text: tr("common.rescan"); enabled: !app.busy; onClicked: app.scanPrograms() },
        AccentButton { visible: pg.tab === 2 && !pu.running && pu.winget !== false; text: tr1("pu.updateSel", String(pu.picked || 0)); enabled: !app.busy && !pu.checking && (pu.picked || 0) > 0; onClicked: app.installUpdates() },
        AccentButton { visible: pg.tab === 2 && pu.running === true; text: tr("pu.stop"); danger: true; onClicked: app.cancelUpdates() },
        AccentButton { visible: pg.tab === 2 && !pu.running; text: tr("pu.check"); primary: false; enabled: !pu.checking; onClicked: app.scanUpdates() },
        AccentButton { visible: pg.tab === 1; text: tr("apps.remove"); danger: true; enabled: !app.busy; onClicked: { var ids = []; for (var k in picked) if (picked[k]) ids.push(k); if (ids.length) { app.removeApps(ids); picked = ({}) } } },
        AccentButton { visible: pg.tab === 1; text: tr("common.scan"); primary: false; enabled: !app.busy; onClicked: app.scanApps() },
        AccentButton { visible: pg.tab === 1; text: tr("apps.store"); primary: false; onClicked: app.openStore() }
    ]
}
