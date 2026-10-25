import QtQuick
import Sweep

Item {
    id: ring
    property real value: 0      // 0..100
    property color ringColor: Theme.accent2
    property int thickness: 9
    property real shown: 0
    Behavior on shown { NumberAnimation { duration: Theme.durSlow * 2; easing.type: Easing.OutCubic } }
    onValueChanged: shown = value
    Component.onCompleted: shown = value
    width: 104; height: 104
    onShownChanged: if (Math.abs(shown - _last) > 0.5) { _last = shown; canvas.requestPaint() }
    property real _last: -1
    onRingColorChanged: canvas.requestPaint()
    Canvas {
        id: canvas; anchors.fill: parent; antialiasing: true
    renderStrategy: Canvas.Threaded
    renderTarget: Canvas.FramebufferObject
        onPaint: {
            var ctx = getContext("2d"); ctx.reset();
            var c = width / 2, r = c - ring.thickness / 2 - 2;
            ctx.lineWidth = ring.thickness; ctx.lineCap = "round";
            ctx.strokeStyle = Theme.border; ctx.beginPath(); ctx.arc(c, c, r, 0, Math.PI * 2); ctx.stroke();
            ctx.strokeStyle = ring.ringColor; ctx.beginPath();
            ctx.arc(c, c, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.001, ring.shown / 100)); ctx.stroke();
        }
    }
    Connections { target: Theme; function onDarkChanged() { canvas.requestPaint() } }
}
