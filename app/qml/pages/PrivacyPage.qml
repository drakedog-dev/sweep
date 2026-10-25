import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.privacy"); subtitle: tr("hdr.privacy"); hint: tr("priv.hint")
    bigLabel: tr("priv.disabled"); bigValue: app.privacyOn + " " + tr("common.of") + " " + app.privacy.length
    Rectangle {
        width: parent.width; visible: app.privacyHint !== ""; height: visible ? hintCol.implicitHeight + 30 : 0; radius: 14
        color: Theme.dark ? "#3A2A12" : "#FEF3C7"; border.color: Theme.warn
        Column { id: hintCol; anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 6
            Txt { text: "\u26A0  " + tr("priv.blocked.title"); bold: true; font.pixelSize: 14; width: parent.width; color: Theme.warn }
            Txt { text: app.privacyHint; width: parent.width; font.pixelSize: 13; wrapMode: Text.WordWrap } }
    }
    Card { pad: 10
        Column { width: parent.width
            Repeater { model: app.privacy
                Column { width: parent.width
                    Label10 { text: modelData.group.toUpperCase(); leftPadding: 12; topPadding: 12; bottomPadding: 4; visible: index === 0 || app.privacy[index - 1].group !== modelData.group }
                    ToggleRow { title: modelData.name; hint: modelData.hint; checked: modelData.on; onToggled: v => app.setPrivacy(modelData.id, v) }
                } }
        }
    }
    footer: [
        AccentButton { text: tr("priv.all"); enabled: !app.busy; onClicked: app.allPrivacy() },
        AccentButton { text: tr("common.log"); primary: false; onClicked: app.openLog() }
    ]
}
