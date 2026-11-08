import QtQuick
import Sweep

// A rounded rectangle filled with a gradient, with smooth corners.
// Sweep is drawn by the CPU, and that renderer paints a gradient Rectangle with stair-stepped corners; a Canvas
// paints the same shape antialiased. GradRect { c1: Theme.accent; c2: Theme.accent2; radius: 12 }
Canvas {
    id: g
    property color c1: Theme.accent
    property color c2: Theme.accent2
    property var stops: null           // [[position, color], ...] instead of c1 and c2
    property real radius: 0
    property bool vertical: false
    property real shine: 0             // a white sheen from the top edge, 0..1 (page headers)

    function _repaint() { if (available) requestPaint() }
    onC1Changed: _repaint()
    onC2Changed: _repaint()
    onStopsChanged: _repaint()
    onRadiusChanged: _repaint()
    onVerticalChanged: _repaint()
    onShineChanged: _repaint()
    onWidthChanged: _repaint()
    onHeightChanged: _repaint()
    onAvailableChanged: _repaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        if (width <= 0 || height <= 0) return
        var gr = vertical ? ctx.createLinearGradient(0, 0, 0, height) : ctx.createLinearGradient(0, 0, width, 0)
        var st = stops || [[0, c1], [1, c2]]
        for (var i = 0; i < st.length; i++) gr.addColorStop(st[i][0], String(st[i][1]))
        var r = Math.max(0, Math.min(radius, width / 2, height / 2))
        ctx.beginPath()
        ctx.roundedRect(0, 0, width, height, r, r)
        ctx.closePath()
        ctx.fillStyle = gr
        ctx.fill()
        if (shine > 0) {
            var s = ctx.createLinearGradient(0, 0, 0, height)
            s.addColorStop(0, "rgba(255,255,255," + shine + ")")
            s.addColorStop(1, "rgba(255,255,255,0)")
            ctx.fillStyle = s
            ctx.fill()
        }
    }
}
