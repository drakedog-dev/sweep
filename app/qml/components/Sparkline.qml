import QtQuick
import Sweep

Canvas {
    id: sp
    property var values: []
    property color lineColor: Theme.accent2
    property real maxValue: 100
    onValuesChanged: requestPaint()
    onLineColorChanged: requestPaint()
    antialiasing: true
    renderStrategy: Canvas.Threaded
    renderTarget: Canvas.FramebufferObject
    onPaint: {
        var ctx = getContext("2d"); ctx.reset();
        var n = values.length; if (n < 2) return;
        var w = width, h = height, step = w / (n - 1);
        ctx.beginPath();
        for (var i = 0; i < n; i++) { var x = i * step, y = h - (Math.min(maxValue, values[i]) / maxValue) * (h - 4) - 2; if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
        ctx.lineWidth = 2; ctx.strokeStyle = lineColor; ctx.stroke();
        ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath();
        var g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0.35)); g.addColorStop(1, Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0));
        ctx.fillStyle = g; ctx.fill();
    }
}
