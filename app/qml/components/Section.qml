import QtQuick
import Sweep

Column {
    property string title: ""
    width: parent.width; spacing: 6
    Label10 { text: title.toUpperCase(); leftPadding: 12; topPadding: 10 }
}
