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
    readonly property color status:    dark ? "#0A0816" : "#ECE8FB"
    readonly property color statusText:dark ? "#8B86B0" : "#5B5680"
    readonly property color good:   "#34D399"
    readonly property color warn:   "#FBBF24"
    readonly property color bad:    "#F87171"
    readonly property color track:  dark ? "#2F2A5A" : "#C4BCEB"
    readonly property color knobOff: dark ? "#CBD5E1" : "#FFFFFF"

    readonly property int radius: 18
    readonly property int radiusSm: 12
    readonly property int dur: anim ? 220 : 0
    readonly property int durSlow: anim ? 420 : 0
    readonly property string font: Qt.platform.os === "windows" ? "Segoe UI" : "DejaVu Sans"

    // Lucide icons (ISC licence, fonts/LICENSE-lucide.txt), subset to the glyphs Sweep uses
    readonly property FontLoader iconLoader: FontLoader { source: "fonts/lucide.ttf" }
    readonly property string iconFont: iconLoader.name
    readonly property var icons: ({
        "layout-dashboard": "\ue1c1",
        "trash-2": "\ue18e",
        "shield-check": "\ue1ff",
        "database": "\ue0ad",
        "server": "\ue153",
        "power": "\ue140",
        "rocket": "\ue286",
        "hard-drive": "\ue0ed",
        "package": "\ue129",
        "cpu": "\ue0a9",
        "archive": "\ue041",
        "settings": "\ue154",
        "file-clock": "\ue315",
        "image": "\ue0f6",
        "download": "\ue0b2",
        "bug": "\ue20c",
        "scroll-text": "\ue45f",
        "globe": "\ue0e8",
        "history": "\ue1f5",
        "cookie": "\ue26b",
        "memory-stick": "\ue445",
        "triangle-alert": "\ue193",
        "sparkles": "\ue412",
        "check": "\ue06c",
        "star": "\ue176",
        "github": "\ue0e6",
        "folder-open": "\ue247",
        "refresh-cw": "\ue145",
        "gauge": "\ue1bf",
        "zap": "\ue1b4",
        "clock": "\ue087",
        "calendar-clock": "\ue304",
        "activity": "\ue038",
        "external-link": "\ue0b9",
        "archive-restore": "\ue2cd",
        "eraser": "\ue28f",
        "broom": "\ue730",
        "lock": "\ue10b",
        "monitor": "\ue11d",
        "layout-grid": "\ue0ff",
        "file-x": "\ue0cd",
        "shield": "\ue158",
        "info": "\ue0f9",
        "circle-check": "\ue226",
        "languages": "\ue0fe",
        "palette": "\ue1dd",
        "brush": "\ue1d3",
        "list-checks": "\ue1d0",
        "undo-2": "\ue2a1",
        "search": "\ue151",
        "timer": "\ue1e0",
        "radar": "\ue497",
        "shield-alert": "\ue1fe",
        "bell-ring": "\ue224",
        "rotate-ccw": "\ue148",
        "app-window": "\ue426",
        "layers": "\ue529",
        "circle-alert": "\ue077",
        "trending-down": "\ue190",
        "arrow-right": "\ue049",
        "life-buoy": "\ue101",
        "users": "\ue1a4",
        "user-cog": "\ue342",
        "circle-arrow-up": "\ue07b",
        "eye-off": "\ue0bb",
        "badge-check": "\ue241",
        "x": "\ue1b2",
        "eye": "\ue0ba",
        "git-branch": "\ue0e2",
        "heart": "\ue0f2",
        "package-plus": "\ue268",
        "loader": "\ue109",
        "hourglass": "\ue296",
        "monitor-down": "\ue421",
        "briefcase": "\ue062",
        "gamepad-2": "\ue0df",
        "messages-square": "\ue40d",
        "clapperboard": "\ue29b",
        "file-text": "\ue0cc",
        "wrench": "\ue1b1",
        "code": "\ue093",
        "puzzle": "\ue29c"
    })
    function icon(name) { return icons[name] || "" }
}
