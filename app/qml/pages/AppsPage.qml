import QtQuick
import Sweep
import "../components"

// Programs: thorough uninstaller for installed programs + pre-installed Windows apps
Page {
    id: pg
    title: tr("nav.apps"); subtitle: tr("hdr.apps")
    hint: tab === 0 ? tr("un.hint") : tr("apps.hint")
    property int tab: 0
    property var picked: ({})
    property string query: ""
    property var shown: { var q = query.trim().toLowerCase(); var l = app.programList; if (!q) return l
        var out = []; for (var i = 0; i < l.length; i++) if (l[i].name.toLowerCase().indexOf(q) >= 0 || l[i].publisher.toLowerCase().indexOf(q) >= 0) out.push(l[i]); return out }
    bigLabel: tab === 0 ? tr("un.installed") : tr("apps.found")
    bigValue: tab === 0 ? String(app.programCount) : String(app.appList.length)

    component Tab: Rectangle {
        property string label: ""; property string icon: ""; property bool on: false; signal pick()
        width: tr_.implicitWidth + 50; height: 38; radius: 19
        color: on ? Theme.accent : Theme.soft
        Behavior on color { ColorAnimation { duration: Theme.dur } }
        Row { id: tr_; anchors.centerIn: parent; spacing: 8
            Icon { name: icon; size: 16; color: on ? "white" : Theme.muted; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: label; bold: true; color: on ? "white" : Theme.text; anchors.verticalCenter: parent.verticalCenter } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: pick() }
    }
    component SortChip: Rectangle {
        property string label: ""; property string key: ""
        width: sl.implicitWidth + 24; height: 30; radius: 15; color: app.programSort === key ? Theme.cardAlt : "transparent"; border.color: app.programSort === key ? Theme.accent : Theme.border
        Txt { id: sl; anchors.centerIn: parent; text: label; font.pixelSize: 12; bold: app.programSort === key }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.setProgramSort(key) }
    }

    Row { spacing: 10
        Tab { label: tr("un.tab.programs"); icon: "package"; on: pg.tab === 0; onPick: pg.tab = 0 }
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
                    Rectangle { id: ico; width: 40; height: 40; radius: 11; color: Theme.soft; anchors.left: parent.left; anchors.leftMargin: 8; anchors.verticalCenter: parent.verticalCenter
                        Image { id: img; anchors.centerIn: parent; width: 28; height: 28; source: modelData.icon; sourceSize.width: 32; sourceSize.height: 32; asynchronous: true; visible: status === Image.Ready && modelData.icon !== "" }
                        Icon { anchors.centerIn: parent; name: "app-window"; size: 18; color: Theme.accent2; visible: !img.visible } }
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
        AccentButton { visible: pg.tab === 1; text: tr("apps.remove"); danger: true; enabled: !app.busy; onClicked: { var ids = []; for (var k in picked) if (picked[k]) ids.push(k); if (ids.length) { app.removeApps(ids); picked = ({}) } } },
        AccentButton { visible: pg.tab === 1; text: tr("common.scan"); primary: false; enabled: !app.busy; onClicked: app.scanApps() },
        AccentButton { visible: pg.tab === 1; text: tr("apps.store"); primary: false; onClicked: app.openStore() }
    ]
}
