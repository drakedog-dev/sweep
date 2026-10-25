import QtQuick
import Sweep
import "../components"

Page {
    title: tr("nav.privacy"); subtitle: tr("hdr.privacy"); hint: tr("priv.hint")
    bigLabel: tr("priv.disabled"); bigValue: app.privacyOn + " " + tr("common.of") + " " + app.privacy.length
    Card { pad: 10
        Column { width: parent.width
            Repeater { model: app.privacy
                Column { width: parent.width
                    Label10 { text: modelData.group.toUpperCase(); leftPadding: 12; topPadding: 12; bottomPadding: 4; visible: index === 0 || app.privacy[index - 1].group !== modelData.group }
                    ToggleRow { title: modelData.name; hint: modelData.hint; checked: modelData.on; onToggled: v => app.setPrivacy(modelData.id, v) }
                } }
        }
    }
    footer: [ AccentButton { text: tr("priv.all"); enabled: !app.busy; onClicked: app.allPrivacy() } ]
}
