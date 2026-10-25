import QtQuick
import Sweep
import "../components"

// Programs: thorough uninstaller, updates and installs from the vendors' sites (winget), pre-installed Windows apps
Page {
    id: pg
    objectName: "appsPage"
    title: tr("nav.apps"); subtitle: tr("hdr.apps")
    hint: tab === 0 ? tr("un.hint") : tab === 2 ? tr("pu.hint") : tab === 3 ? tr("ins.hint") : tr("apps.hint")
    property int tab: 0                  // 0 installed programs, 2 updates, 3 install, 1 built-in apps
    property var picked: ({})
    property string query: ""
    property var pu: app.programUpdates
    property var ins: app.installData
    property var insAll: { var l = []; (ins.cats || []).forEach(function (c) { l = l.concat(c.items) }); return l.concat(ins.results || []) }
    property var shown: { var q = query.trim().toLowerCase(); var l = app.programList; if (!q) return l
        var out = []; for (var i = 0; i < l.length; i++) if (l[i].name.toLowerCase().indexOf(q) >= 0 || l[i].publisher.toLowerCase().indexOf(q) >= 0) out.push(l[i]); return out }
    bigLabel: tab === 0 ? tr("un.installed") : tab === 2 ? tr("pu.big") : tab === 3 ? tr("ins.big") : tr("apps.found")
    bigValue: tab === 0 ? String(app.programCount) : tab === 2 ? (pu.checked ? String(pu.count) : "—") : tab === 3 ? String(ins.picked || 0) : String(app.appList.length)
    onTabChanged: {
        if (tab === 2 && !pu.checked && !pu.checking) app.scanUpdates()
        if (tab === 3 && !ins.loaded && !ins.loading) app.loadInstall()
    }

    // ---------- clock for "installing… 0:12" and the estimated part of the progress ----------
    property real nowMs: Date.now()
    Timer { interval: 500; repeat: true; running: pg.visible && (pu.running === true || ins.running === true); onTriggered: pg.nowMs = Date.now() }
    function clock(ms) { var s = Math.max(0, Math.round(ms / 1000)); return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60) }

    // progress of one program, 0..100: the download is measured, the silent install is estimated and never reaches 100 by itself
    function rowPct(it) {
        if (!it || it.state !== "working") return it && it.state === "ok" ? 100 : 0
        if (it.phase === "download") return it.total > 0 ? 3 + 82 * Math.min(1, it.got / it.total) : -1
        if (it.phase === "install") { var t = it.installFrom > 0 ? (nowMs - it.installFrom) / 1000 : 0; return 85 + 14 * (1 - Math.exp(-t / 14)) }
        return 2
    }
    function phaseText(it) {
        if (it.phase === "download") {
            if (it.total === 100 && it.got <= 100) return tr1("pu.ph.downloadP", String(Math.round(it.got)))
            var t = it.total > 0 ? tr("pu.ph.download").replace("{0}", app.size(it.got)).replace("{1}", app.size(it.total)) : tr1("pu.ph.downloadN", app.size(it.got))
            return it.speed > 1024 ? t + "  ·  " + tr1("pu.speed", app.size(it.speed)) : t
        }
        if (it.phase === "install") return it.installFrom > 0 ? tr1("pu.ph.installT", clock(nowMs - it.installFrom)) : tr("pu.ph.install")
        return tr("pu.ph." + (it.phase || "prepare"))
    }
    function working(list) { for (var i = 0; i < (list || []).length; i++) if (list[i].state === "working") return list[i]; return null }
    function queuePct(st, list) {
        var w = working(list); var p = w ? Math.max(0, rowPct(w)) / 100 : 0
        return Math.min(1, ((st.done || 0) + p) / Math.max(1, st.total || 1))
    }

    // ---------- scan progress: winget's own comparison is estimated from the last run, the rest is counted ----------
    property real listFill: 0
    NumberAnimation { id: listAnim; target: pg; property: "listFill"; from: 0; to: 0.4; duration: Math.max(3000, (pu.eta || 12) * 1300); easing.type: Easing.OutQuad }
    property bool scanning: pu.checking === true
    onScanningChanged: if (scanning) { listFill = 0; listAnim.restart() } else listAnim.stop()
    Component.onCompleted: if (scanning) listAnim.restart()
    property real scanPct: pu.stage === "details" ? 0.4 + 0.55 * (pu.sdone || 0) / Math.max(1, pu.stotal || 1) : pu.stage === "match" ? 0.98 : listFill

    component Tab: Rectangle {
        property string label: ""; property string icon: ""; property bool on: false; property int badge: 0; signal pick()
        width: tr_.implicitWidth + (pg.width < 760 ? 30 : 44); height: 38; radius: 19
        color: on ? Theme.accent : tabHov.containsMouse ? Theme.softHover : Theme.soft
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Row { id: tr_; anchors.centerIn: parent; spacing: 8
            Icon { name: icon; size: 16; color: on ? "white" : Theme.muted; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: label; bold: true; color: on ? "white" : Theme.text; anchors.verticalCenter: parent.verticalCenter }
            Rectangle { visible: badge > 0; width: Math.max(20, bt.implicitWidth + 10); height: 20; radius: 10; anchors.verticalCenter: parent.verticalCenter
                color: on ? "#33FFFFFF" : Theme.accent
                Txt { id: bt; anchors.centerIn: parent; text: String(badge); color: "white"; bold: true; font.pixelSize: 11 } } }
        MouseArea { id: tabHov; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: pick() }
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
        MouseArea { anchors.fill: parent; enabled: parent.enabled; cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: parent.flip() }
    }
    component Bar: Rectangle {
        property real value: -1                  // 0..1, or -1 while the size is unknown
        height: 6; radius: height / 2; color: Theme.track; clip: true
        Rectangle { visible: parent.value >= 0; height: parent.height; radius: parent.radius; width: parent.width * Math.max(0, Math.min(1, parent.value))
            Behavior on width { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } } }
        Rectangle { id: stripe; visible: parent.value < 0; height: parent.height; radius: parent.radius; width: parent.width * 0.28
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
            SequentialAnimation on x { running: stripe.visible; loops: Animation.Infinite
                NumberAnimation { from: -stripe.width; to: stripe.parent ? stripe.parent.width : 300; duration: 1300; easing.type: Easing.InOutQuad } } }
    }
    component Chip: Rectangle {
        property string label: ""; property string icon: ""; property bool active: false; property bool small: false; signal hit()
        width: chRow.implicitWidth + (small ? 20 : 26); height: small ? 28 : 32; radius: height / 2
        color: active ? Theme.accent : chHov.containsMouse && enabled ? Theme.softHover : Theme.soft
        opacity: enabled ? 1 : 0.4
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Row { id: chRow; anchors.centerIn: parent; spacing: 6
            Icon { visible: icon !== ""; name: icon; size: small ? 13 : 14; color: active ? "white" : Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: label; font.pixelSize: small ? 11 : 12; bold: true; color: active ? "white" : Theme.text; anchors.verticalCenter: parent.verticalCenter } }
        MouseArea { id: chHov; anchors.fill: parent; hoverEnabled: true; enabled: parent.enabled; cursorShape: Qt.PointingHandCursor; onClicked: parent.hit() }
    }
    component Tip: Rectangle {
        property string text: ""; property bool show: false
        visible: show; z: 20; width: tipT.implicitWidth + 18; height: 28; radius: 8; color: Theme.dark ? "#2A1F5E" : "#1E1B3A"
        Txt { id: tipT; anchors.centerIn: parent; text: parent.text; color: "white"; font.pixelSize: 11; wrapMode: Text.NoWrap }
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
    // a letter on a colour of its own for programs that are not installed yet (the real icon once they are)
    component Mono: Rectangle {
        property string label: ""; property string src: ""
        width: 40; height: 40; radius: 11; color: Theme.soft
        property real hue: { var h = 7; for (var i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) % 997; return (h % 360) / 360 }
        Rectangle { anchors.fill: parent; radius: parent.radius; visible: !mi.visible
            gradient: Gradient { GradientStop { position: 0; color: Qt.hsla(hue, 0.62, Theme.dark ? 0.52 : 0.58, 1) } GradientStop { position: 1; color: Qt.hsla((hue + 0.07) % 1, 0.7, Theme.dark ? 0.36 : 0.44, 1) } }
            Text { anchors.centerIn: parent; color: "white"; font.family: Theme.font; font.pixelSize: 17; font.weight: Font.Bold; renderType: Text.NativeRendering
                text: { var s = label.replace(/[^A-Za-zЀ-ӿ0-9]/g, ""); return s.length ? s.charAt(0).toUpperCase() : "?" } } }
        Image { id: mi; anchors.centerIn: parent; width: 28; height: 28; source: parent.src; sourceSize.width: 32; sourceSize.height: 32; asynchronous: true; visible: status === Image.Ready && parent.src !== "" }
    }
    // the queue card shown while updating or installing
    component QueueCard: Card {
        property var st: ({}); property var list: []; property string textKey: ""
        pad: 18
        Column { width: parent.width; spacing: 10
            Row { width: parent.width; spacing: 12
                Spin { anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr(textKey).replace("{0}", String(Math.min((st.done || 0) + 1, st.total || 1))).replace("{1}", String(st.total || 0)).replace("{2}", st.current || "")
                      bold: true; font.pixelSize: 14; width: parent.width - 40 - qPct.width - 12; elide: Text.ElideRight; wrapMode: Text.NoWrap; anchors.verticalCenter: parent.verticalCenter }
                Txt { id: qPct; text: Math.round(pg.queuePct(st, list) * 100) + "%"; bold: true; font.pixelSize: 20; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter } }
            Bar { width: parent.width; height: 8; value: pg.queuePct(st, list) }
            Txt { property var w: pg.working(list); visible: w !== null; text: w ? (w.title || w.name) + ":  " + pg.phaseText(w) : ""; muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
        }
    }

    Row { spacing: 10
        Tab { label: tr("un.tab.programs"); icon: "package"; on: pg.tab === 0; onPick: pg.tab = 0 }
        Tab { label: tr("pu.tab"); icon: "circle-arrow-up"; on: pg.tab === 2; badge: pu.count || 0; onPick: pg.tab = 2 }
        Tab { label: tr("ins.tab"); icon: "package-plus"; on: pg.tab === 3; badge: ins.picked || 0; onPick: pg.tab = 3 }
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
    // looking for updates: three steps with a percentage
    Card { visible: pg.tab === 2 && pu.checking === true; pad: 18
        Column { width: parent.width; spacing: 12
            Row { width: parent.width; spacing: 12
                Spin { anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("pu.scan.title"); bold: true; font.pixelSize: 15; width: parent.width - 40 - sPct.width - 12; anchors.verticalCenter: parent.verticalCenter }
                Txt { id: sPct; text: Math.round(pg.scanPct * 100) + "%"; bold: true; font.pixelSize: 20; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter } }
            Bar { width: parent.width; height: 8; value: pg.scanPct }
            Txt { width: parent.width; muted: true; font.pixelSize: 12
                  text: pu.stage === "details" ? tr("pu.scan.details").replace("{0}", String(pu.sdone || 0)).replace("{1}", String(pu.stotal || 0))
                      : pu.stage === "match" ? tr("pu.scan.match") : tr("pu.scan.list") }
            Row { spacing: 8
                Repeater { model: ["list", "details", "match"]
                    Rectangle { property int idx: index
                        property int cur: pu.stage === "match" ? 2 : pu.stage === "details" ? 1 : 0
                        property bool done_: idx < cur
                        property bool now_: idx === cur
                        width: stR.implicitWidth + 22; height: 28; radius: 14
                        color: now_ ? Theme.soft : "transparent"; border.color: done_ ? Theme.good : now_ ? Theme.accent : Theme.border
                        Row { id: stR; anchors.centerIn: parent; spacing: 6
                            Icon { name: done_ ? "check" : now_ ? "loader" : "clock"; size: 13; color: done_ ? Theme.good : now_ ? Theme.accent2 : Theme.faint; anchors.verticalCenter: parent.verticalCenter
                                RotationAnimation on rotation { from: 0; to: 360; duration: 1400; loops: Animation.Infinite; running: now_ && pg.visible } }
                            Txt { text: tr("pu.step." + modelData); font.pixelSize: 11; bold: now_; muted: !now_ && !done_; anchors.verticalCenter: parent.verticalCenter } } } }
            }
        }
    }
    QueueCard { visible: pg.tab === 2 && pu.running === true; st: pu; list: pu.items || []; textKey: "pu.progress" }
    // no winget on this PC
    Card { visible: (pg.tab === 2 && pu.checked && pu.winget === false) || (pg.tab === 3 && ins.winget === false); pad: 18
        Column { width: parent.width; spacing: 12
            Row { spacing: 12; width: parent.width
                Icon { name: "circle-alert"; size: 20; color: Theme.warn; anchors.top: parent.top; anchors.topMargin: 1 }
                Txt { text: tr("pu.nowinget"); width: parent.width - 34 } }
            AccentButton { text: tr("pu.getwinget"); compact: true; onClicked: app.openUrl("ms-windows-store://pdp/?productid=9NBLGGH4NNS1") }
        }
    }
    Card { visible: pg.tab === 2 && pu.winget !== false && !pu.checking; pad: 12
        Column { width: parent.width; spacing: 6
            Row { spacing: 12; visible: pu.checked && (pu.items || []).length === 0; leftPadding: 10; topPadding: 8; bottomPadding: 8
                Icon { name: "circle-check"; size: 20; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("pu.none"); anchors.verticalCenter: parent.verticalCenter } }
            Empty { msg: tr("pu.never"); visible: !pu.checked }
            // nothing is ticked by itself: tick programs one by one, or take all of them with one click
            Rectangle { id: selBar; visible: (pu.safe || 0) > 0; width: parent.width; height: 50; radius: 12; color: Theme.cardAlt
                property int open_: pu.safe || 0
                property int sel: pu.picked || 0
                property bool hasMajor: (pu.items || []).some(function (x) { return x.major && x.state !== "ok" && !x.suspect })
                Box { id: allBox; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; enabled: !pu.running
                      on: selBar.sel > 0 && selBar.sel === selBar.open_; partial: selBar.sel > 0 && selBar.sel < selBar.open_
                      onFlip: app.pickUpdates(selBar.sel === selBar.open_ ? "none" : "all") }
                Txt { anchors.left: allBox.right; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; bold: true
                      text: tr2("pu.selected", String(selBar.sel), String(selBar.open_)) }
                Row { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                    Chip { small: true; label: tr("pu.pick.all"); enabled: !pu.running; onHit: app.pickUpdates("all") }
                    Chip { small: true; label: tr("pu.pick.minor"); visible: selBar.hasMajor; enabled: !pu.running; onHit: app.pickUpdates("minor") }
                    Chip { small: true; label: tr("pu.pick.none"); enabled: !pu.running && selBar.sel > 0; onHit: app.pickUpdates("none") } }
            }
            Repeater { model: pu.items || []
                Rectangle { id: urow; width: parent.width; height: urow.suspect ? 96 : urow.warn ? 86 : 66; radius: 12
                    property bool done_: modelData.state === "ok"
                    property bool warn: modelData.state === "warn"
                    property bool fail: modelData.state === "failed"
                    property bool active: modelData.state === "working" || modelData.state === "queued"
                    property bool suspect: modelData.suspect === true && !done_
                    property bool canPick: !done_ && !suspect && !pu.running
                    color: uHov.containsMouse && canPick ? Theme.cardAlt : modelData.picked === true && !done_ ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.07) : "transparent"
                    border.color: urow.suspect ? Qt.rgba(Theme.warn.r, Theme.warn.g, Theme.warn.b, 0.45) : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.dur } }
                    MouseArea { id: uHov; anchors.fill: parent; hoverEnabled: true     // a click anywhere on the row ticks it
                        cursorShape: urow.canPick ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (urow.canPick) app.setUpdatePick(modelData.id, !modelData.picked) }
                    Box { id: ub; on: modelData.picked === true && !urow.done_; opacity: urow.canPick || modelData.picked === true ? 1 : 0.3; enabled: urow.canPick
                          anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                          onFlip: app.setUpdatePick(modelData.id, !modelData.picked) }
                    AppIcon { id: uico; src: modelData.icon || ""; anchors.left: ub.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                    Column { anchors.left: uico.right; anchors.leftMargin: 12; anchors.right: right_.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                        Txt { text: modelData.title || modelData.name; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Column { visible: modelData.state === "working"; width: parent.width; spacing: 4
                            Bar { width: Math.min(parent.width, 380); value: pg.rowPct(modelData) < 0 ? -1 : pg.rowPct(modelData) / 100 }
                            Txt { text: pg.phaseText(modelData); muted: true; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                        Row { spacing: 6; width: parent.width; visible: modelData.state !== "working"
                            Txt { visible: !urow.done_; text: modelData.current || modelData.version; muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                            Icon { visible: !urow.done_; name: "arrow-right"; size: 12; color: Theme.faint; anchors.verticalCenter: parent.verticalCenter }
                            Txt { visible: !urow.done_; text: modelData.available; font.pixelSize: 12; bold: true; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
                            Rectangle { visible: modelData.major === true && !urow.done_ && !urow.fail && !urow.suspect; height: 18; width: mj.implicitWidth + 14; radius: 9; color: "transparent"; border.color: Theme.warn; anchors.verticalCenter: parent.verticalCenter
                                Txt { id: mj; anchors.centerIn: parent; text: tr("pu.major"); color: Theme.warn; font.pixelSize: 10; bold: true } }
                            // the program is open right now: its installer may not be able to replace it
                            Rectangle { visible: modelData.running === true && !urow.done_ && !urow.active; height: 18; width: rnRow.implicitWidth + 14; radius: 9; color: Qt.rgba(Theme.warn.r, Theme.warn.g, Theme.warn.b, 0.14); anchors.verticalCenter: parent.verticalCenter
                                Row { id: rnRow; anchors.centerIn: parent; spacing: 4
                                    Rectangle { width: 6; height: 6; radius: 3; color: Theme.warn; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: tr("pu.running"); color: Theme.warn; font.pixelSize: 10; bold: true; anchors.verticalCenter: parent.verticalCenter } }
                                MouseArea { id: rnHov; anchors.fill: parent; hoverEnabled: true }
                                Tip { show: rnHov.containsMouse; text: tr("pu.running.tip"); anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.left: parent.left } }
                            // result
                            Icon { visible: urow.done_; name: "circle-check"; size: 14; color: modelData.reason === "reboot" ? Theme.warn : Theme.good; anchors.verticalCenter: parent.verticalCenter }
                            Txt { visible: urow.done_; font.pixelSize: 12; bold: true; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                  color: modelData.reason === "reboot" ? Theme.warn : Theme.good
                                  text: modelData.reason === "reboot" ? tr("pu.r.reboot") : modelData.reason === "uptodate" ? tr("pu.r.uptodate") : tr1("pu.st.okTo", modelData.now || modelData.available) }
                            Txt { visible: urow.fail; text: tr("pu.r." + (modelData.reason || "code")) + (modelData.reason === "code" && modelData.code ? " " + modelData.code : "")
                                  color: Theme.bad; font.pixelSize: 12; elide: Text.ElideRight; wrapMode: Text.NoWrap; anchors.verticalCenter: parent.verticalCenter }
                            Txt { visible: modelData.state === "queued"; text: tr1("pu.st.queuedN", String(modelData.queue || "")); muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                        Row { visible: urow.warn; spacing: 6; width: parent.width
                            Icon { name: "circle-alert"; size: 13; color: Theme.warn; anchors.top: parent.top; anchors.topMargin: 2 }
                            Txt { width: parent.width - 20; color: Theme.warn; font.pixelSize: 12; elide: Text.ElideRight; maximumLineCount: 2
                                  text: tr("pu.r." + (modelData.reason || "nochange")) } }
                        Row { visible: urow.suspect; spacing: 6; width: parent.width
                            Icon { name: "triangle-alert"; size: 13; color: Theme.warn; anchors.top: parent.top; anchors.topMargin: 2 }
                            Txt { width: parent.width - 20; color: Theme.warn; font.pixelSize: 12; elide: Text.ElideRight; maximumLineCount: 2
                                  text: (modelData.why === "owner" ? tr2("pu.suspect.owner", modelData.mineOwner || "", modelData.theirOwner || "")
                                                                   : tr2("pu.suspect.edition", modelData.installedName || modelData.name, modelData.catName || "")) + ". " + tr("pu.suspect.hint") } }
                    }
                    Row { id: right_; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                        // what is new in this version: release notes straight from the catalogue
                        Rectangle { visible: !urow.done_ && ((modelData.notes || "") !== "" || (modelData.notesUrl || "") !== ""); width: 30; height: 30; radius: 10; anchors.verticalCenter: parent.verticalCenter
                            color: nHov.containsMouse ? Theme.soft : "transparent"
                            Icon { anchors.centerIn: parent; name: "sparkles"; size: 15; color: Theme.accent2 }
                            MouseArea { id: nHov; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: app.showNotes(modelData.id) }
                            Tip { show: nHov.containsMouse; text: tr("pu.notes"); anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.right: parent.right } }
                        // where it comes from: the vendor's own address, checked by SHA-256
                        Rectangle { visible: (modelData.host || "") !== ""; height: 28; width: Math.min(200, srcRow.implicitWidth + 20); radius: 14; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter; clip: true
                            Row { id: srcRow; anchors.verticalCenter: parent.verticalCenter; x: 10; spacing: 6
                                Icon { name: modelData.sha256 ? "lock" : "globe"; size: 13; color: modelData.sha256 ? Theme.good : Theme.muted; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData.host; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter; width: Math.min(implicitWidth, 160); elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.openUrl(modelData.homepage || modelData.installer) } }
                        Item { width: 112; height: 34; anchors.verticalCenter: parent.verticalCenter
                            AccentButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: !urow.active && !urow.done_ && !urow.suspect
                                compact: true; primary: false; text: tr("pu.update"); enabled: !app.busy && !pu.busy; onClicked: app.updateOne(modelData.id) }
                            AccentButton { id: sameBtn; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: urow.suspect && !pu.running
                                compact: true; primary: false; text: tr("pu.itsSame"); onClicked: app.trustUpdate(modelData.id)
                                Tip { show: sameBtn.hovered; text: tr("pu.itsSame.tip"); anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.right: parent.right } }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "working"
                                  text: pg.rowPct(modelData) >= 0 ? Math.round(pg.rowPct(modelData)) + "%" : ""; bold: true; font.pixelSize: 15; color: Theme.accent2 }
                            Icon { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "queued"; name: "hourglass"; size: 16; color: Theme.faint }
                            Icon { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; visible: urow.done_; name: "circle-check"; size: 22
                                   color: Theme.good } }
                        Rectangle { width: 30; height: 30; radius: 10; color: skHov.containsMouse ? Theme.soft : "transparent"; anchors.verticalCenter: parent.verticalCenter; opacity: urow.done_ || pu.running ? 0.25 : 1
                            Icon { anchors.centerIn: parent; name: "eye-off"; size: 15; color: Theme.muted }
                            MouseArea { id: skHov; anchors.fill: parent; hoverEnabled: true; enabled: !urow.done_ && !pu.running; cursorShape: Qt.PointingHandCursor; onClicked: app.skipUpdate(modelData.id) }
                            Tip { show: skHov.containsMouse; text: tr("pu.skip"); anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.right: parent.right } }
                    }
                }
            }
            Txt { visible: (pu.items || []).some(function (x) { return x.major && x.state !== "ok" && !x.suspect }); text: tr("pu.major.hint")
                  muted: true; font.pixelSize: 12; width: parent.width; leftPadding: 10; topPadding: 4 }
        }
    }

    // ---------- install: picks by category, ready-made sets and the whole winget catalogue ----------
    Card { visible: pg.tab === 3 && ins.winget !== false; pad: 16
        Column { width: parent.width; spacing: 14
            Row { width: parent.width; spacing: 14
                Rectangle { id: insIcon; width: 44; height: 44; radius: 13; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter
                    Icon { anchors.centerIn: parent; name: "badge-check"; size: 22; color: Theme.good } }
                Column { width: parent.width - insIcon.width - 14; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                    Txt { text: tr("ins.trust"); bold: true; font.pixelSize: 14; width: parent.width }
                    Txt { text: tr("ins.trust.sub"); muted: true; font.pixelSize: 12; width: parent.width } } }
            Row { width: parent.width; spacing: 10
                Rectangle { width: parent.width - findBtn.width - 10; height: 40; radius: 12; color: Theme.cardAlt; border.color: catSearch.activeFocus ? Theme.accent : Theme.border
                    Icon { id: csIcon; name: "search"; size: 16; color: Theme.muted; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                    TextInput { id: catSearch; anchors.left: csIcon.right; anchors.leftMargin: 10; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        color: Theme.text; font.family: Theme.font; font.pixelSize: 13; clip: true; selectByMouse: true; maximumLength: 60
                        onAccepted: app.searchCatalog(text)
                        Txt { anchors.verticalCenter: parent.verticalCenter; text: tr("ins.search"); muted: true; visible: catSearch.text === "" && !catSearch.activeFocus } } }
                AccentButton { id: findBtn; compact: true; text: tr("ins.find"); enabled: catSearch.text.trim() !== "" && !ins.searching; onClicked: app.searchCatalog(catSearch.text) } }
        }
    }
    QueueCard { visible: pg.tab === 3 && ins.running === true; st: ins; list: pg.insAll; textKey: "ins.progress" }
    // search results
    Card { visible: pg.tab === 3 && (ins.searching === true || ins.searched === true); pad: 12
        Column { width: parent.width; spacing: 4
            Row { width: parent.width; spacing: 10; leftPadding: 6; topPadding: 2; bottomPadding: 4
                Spin { visible: ins.searching === true; anchors.verticalCenter: parent.verticalCenter }
                Txt { anchors.verticalCenter: parent.verticalCenter; bold: true; width: parent.width - 40 - hideRes.width
                      text: ins.searching ? tr("ins.searching") : (ins.results || []).length ? tr1("ins.results", String((ins.results || []).length)) : tr("ins.noresults") }
                Chip { id: hideRes; small: true; icon: "x"; label: tr("ins.closeSearch"); visible: !ins.searching; anchors.verticalCenter: parent.verticalCenter
                       onHit: { catSearch.text = ""; app.searchCatalog("") } } }
            Repeater { model: ins.searching ? [] : (ins.results || [])
                Rectangle { id: rrow; width: parent.width; height: 58; radius: 12
                    property bool can: !modelData.installed && !ins.running && modelData.state !== "ok"
                    color: rHov.containsMouse && can ? Theme.cardAlt : modelData.picked ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.07) : "transparent"
                    MouseArea { id: rHov; anchors.fill: parent; hoverEnabled: true; cursorShape: rrow.can ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (rrow.can) app.setInstallPick(modelData.id, !modelData.picked) }
                    Box { id: rb; on: modelData.picked === true; enabled: rrow.can; opacity: rrow.can ? 1 : 0.3; anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                          onFlip: app.setInstallPick(modelData.id, !modelData.picked) }
                    Mono { id: rm_; label: modelData.name; src: modelData.icon || ""; anchors.left: rb.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter }
                    Column { anchors.left: rm_.right; anchors.leftMargin: 12; anchors.right: rAct.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                        Txt { text: modelData.name; bold: true; font.pixelSize: 14; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { visible: modelData.state !== "working"; text: modelData.id + (modelData.version ? "  ·  " + modelData.version : ""); muted: true; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Bar { visible: modelData.state === "working"; width: Math.min(parent.width, 360); value: pg.rowPct(modelData) < 0 ? -1 : pg.rowPct(modelData) / 100 } }
                    Item { id: rAct; width: 150; height: 34; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        AccentButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: rrow.can && modelData.state !== "queued" && modelData.state !== "working"
                            compact: true; primary: false; text: tr("ins.install"); enabled: !app.busy && !ins.busy; onClicked: app.installOne(modelData.id) }
                        Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 6; visible: modelData.installed || modelData.state === "ok"
                            Icon { name: "circle-check"; size: 16; color: Theme.good; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: tr("ins.installed"); color: Theme.good; bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "working" && pg.rowPct(modelData) >= 0
                              text: Math.round(pg.rowPct(modelData)) + "%"; bold: true; font.pixelSize: 15; color: Theme.accent2 }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "queued"; text: tr1("pu.st.queuedN", String(modelData.queue || "")); muted: true; font.pixelSize: 12 }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "failed"; width: parent.width; horizontalAlignment: Text.AlignRight
                              text: tr("pu.r." + (modelData.reason || "code")); color: Theme.bad; font.pixelSize: 11; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
                }
            }
        }
    }
    // ready-made sets
    Card { visible: pg.tab === 3 && ins.winget !== false; pad: 16
        Column { width: parent.width; spacing: 10
            Row { width: parent.width; spacing: 10
                Icon { name: "sparkles"; size: 18; color: Theme.accent2; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("ins.presets"); bold: true; font.pixelSize: 15; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("ins.presets.hint"); muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 220; elide: Text.ElideRight; wrapMode: Text.NoWrap } }
            Flow { width: parent.width; spacing: 8
                Repeater { model: ins.presets || []
                    Chip { icon: modelData.key === "games" ? "gamepad-2" : modelData.key === "work" ? "briefcase" : "monitor-down"
                           label: modelData.title + "  ·  " + modelData.count; enabled: !ins.running && ins.loaded === true; onHit: app.pickPreset(modelData.key) } } }
            Row { spacing: 10; visible: ins.loading === true
                Spin { size: 15; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: tr("ins.checking"); muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
        }
    }
    // the picks, by category
    Repeater { model: pg.tab === 3 && ins.winget !== false ? (ins.cats || []) : []
        Card { pad: 16
            Column { width: parent.width; spacing: 12
                Row { spacing: 10
                    Rectangle { width: 30; height: 30; radius: 9; color: Theme.soft; anchors.verticalCenter: parent.verticalCenter
                        Icon { anchors.centerIn: parent; name: modelData.icon; size: 15; color: Theme.accent2 } }
                    Txt { text: modelData.title; bold: true; font.pixelSize: 15; anchors.verticalCenter: parent.verticalCenter } }
                Flow { id: grid; width: parent.width; spacing: 10
                    property int cols: width > 820 ? 3 : 2
                    property real tileW: (width - spacing * (cols - 1)) / cols
                    Repeater { model: modelData.items
                        Rectangle { id: tile; width: grid.tileW; height: 70; radius: 14
                            property bool can: !modelData.installed && !ins.running && modelData.state !== "ok"
                            property bool on: modelData.picked === true
                            color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.10) : tHov.containsMouse && can ? Theme.softHover : Theme.cardAlt
                            border.color: on ? Theme.accent : "transparent"; border.width: 1.5
                            Behavior on color { ColorAnimation { duration: Theme.dur } }
                            scale: tHov.pressed && can ? 0.98 : 1
                            Behavior on scale { NumberAnimation { duration: 110 } }
                            MouseArea { id: tHov; anchors.fill: parent; hoverEnabled: true; cursorShape: tile.can ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: if (tile.can) app.setInstallPick(modelData.id, !modelData.picked) }
                            Mono { id: tm; label: modelData.name; src: modelData.icon || ""; anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                   opacity: modelData.installed ? 0.75 : 1 }
                            Column { anchors.left: tm.right; anchors.leftMargin: 12; anchors.right: tState.left; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                                Txt { text: modelData.name; bold: true; font.pixelSize: 13; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                Txt { visible: modelData.state !== "working" && modelData.state !== "failed"; text: modelData.desc; muted: true; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight; maximumLineCount: 2; lineHeight: 0.95 }
                                Txt { visible: modelData.state === "failed"; text: tr("pu.r." + (modelData.reason || "code")); color: Theme.bad; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                Bar { visible: modelData.state === "working"; width: parent.width; height: 5; value: pg.rowPct(modelData) < 0 ? -1 : pg.rowPct(modelData) / 100 } }
                            Item { id: tState; width: 44; height: 30; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                                Box { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: tile.can && modelData.state !== "queued" && modelData.state !== "working"
                                      on: tile.on; onFlip: app.setInstallPick(modelData.id, !modelData.picked) }
                                Icon { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.installed || modelData.state === "ok"; name: "circle-check"; size: 20; color: Theme.good
                                    MouseArea { id: okHov; anchors.fill: parent; hoverEnabled: true }
                                    Tip { show: okHov.containsMouse; text: tr("ins.installed"); anchors.bottom: parent.top; anchors.bottomMargin: 6; anchors.right: parent.right } }
                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "working"
                                      text: pg.rowPct(modelData) >= 0 ? Math.round(pg.rowPct(modelData)) + "%" : ""; bold: true; font.pixelSize: 13; color: Theme.accent2 }
                                Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 3; visible: modelData.state === "queued"
                                    Icon { name: "hourglass"; size: 14; color: Theme.faint; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: String(modelData.queue || ""); muted: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } } }
                        }
                    }
                }
            }
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
        AccentButton { visible: pg.tab === 2 && !pu.running && pu.winget !== false; text: tr1("pu.updateSel", String(pu.picked || 0)); enabled: !app.busy && !pu.checking && !pu.busy && (pu.picked || 0) > 0; onClicked: app.installUpdates() },
        AccentButton { visible: pg.tab === 2 && !pu.running && pu.winget !== false && (pu.safe || 0) > 0; text: tr1("pu.updateAll", String(pu.safe || 0)); primary: false; enabled: !app.busy && !pu.checking && !pu.busy; onClicked: app.installAllUpdates() },
        AccentButton { visible: pg.tab === 2 && pu.running === true; text: tr("pu.stop"); danger: true; onClicked: app.cancelUpdates() },
        AccentButton { visible: pg.tab === 2 && !pu.running; text: tr("pu.check"); primary: false; enabled: !pu.checking && !pu.busy; onClicked: app.scanUpdates() },
        AccentButton { visible: pg.tab === 3 && !ins.running && ins.winget !== false; text: tr1("ins.installSel", String(ins.picked || 0)); enabled: !app.busy && !ins.busy && (ins.picked || 0) > 0; onClicked: app.installPicked() },
        AccentButton { visible: pg.tab === 3 && !ins.running && (ins.picked || 0) > 0; text: tr("ins.clear"); primary: false; onClicked: app.clearInstallPicks() },
        AccentButton { visible: pg.tab === 3 && ins.running === true; text: tr("pu.stop"); danger: true; onClicked: app.cancelInstall() },
        AccentButton { visible: pg.tab === 1; text: tr("apps.remove"); danger: true; enabled: !app.busy; onClicked: { var ids = []; for (var k in picked) if (picked[k]) ids.push(k); if (ids.length) { app.removeApps(ids); picked = ({}) } } },
        AccentButton { visible: pg.tab === 1; text: tr("common.scan"); primary: false; enabled: !app.busy; onClicked: app.scanApps() },
        AccentButton { visible: pg.tab === 1; text: tr("apps.store"); primary: false; onClicked: app.openStore() }
    ]
}
