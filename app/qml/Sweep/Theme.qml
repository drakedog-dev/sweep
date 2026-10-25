pragma Singleton
import QtQuick

QtObject {
    id: theme
    property bool dark: true
    property string accentName: "violet"
    property bool anim: true

    readonly property var accents: ({
        "violet": ["#7C3AED", "#A78BFA", "#2563EB"],
        "cyan":   ["#0891B2", "#22D3EE", "#2563EB"],
        "green":  ["#059669", "#34D399", "#0EA5E9"],
        "amber":  ["#D97706", "#FBBF24", "#EF4444"],
        "rose":   ["#E11D48", "#FB7185", "#A855F7"]
    })
    readonly property color accent:  accents[accentName][0]
    readonly property color accent2: accents[accentName][1]
    readonly property color accent3: accents[accentName][2]

    readonly property color bg:        dark ? "#0D0B1A" : "#F5F3FF"
    readonly property color side:      dark ? "#110E24" : "#ECE8FB"
    readonly property color card:      dark ? "#181433" : "#FFFFFF"
    readonly property color cardAlt:   dark ? "#1E1940" : "#F3F0FF"
    readonly property color border:    dark ? "#262052" : "#DDD6FE"
    readonly property color text:      dark ? "#EDE9FE" : "#1E1B3A"
    readonly property color muted:     dark ? "#8B86B0" : "#6B6790"
    readonly property color faint:     dark ? "#5B5680" : "#9B97BF"
    readonly property color soft:      dark ? "#221C47" : "#E4DEFA"
    readonly property color softHover: dark ? "#2C2559" : "#D8D0F7"
    readonly property color status:    dark ? "#0A0816" : "#1E1B3A"
    readonly property color statusText:dark ? "#8B86B0" : "#C4BFE6"
    readonly property color good:   "#34D399"
    readonly property color warn:   "#FBBF24"
    readonly property color bad:    "#F87171"
    readonly property color track:  dark ? "#2F2A5A" : "#CFC8F0"

    readonly property int radius: 18
    readonly property int radiusSm: 12
    readonly property int dur: anim ? 220 : 0
    readonly property int durSlow: anim ? 420 : 0
    readonly property string font: Qt.platform.os === "windows" ? "Segoe UI" : "DejaVu Sans"
}
