"""Draw Sweep's program icon (app/sweep.ico and docs/logo.png) from shapes, smoothly at every size.

The icon is painted four times larger than 256 px and scaled down with Lanczos for each size Windows asks for
(title bar 16-24 px, taskbar 32-48 px, Explorer up to 256 px), so edges are antialiased instead of stair-stepped.
Run: python tools/make_app_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
TOP, BOTTOM = (29, 79, 214), (33, 194, 96)       # blue to green, as before
K = 8                                            # drawing scale: 256 px design units x 8


def master(bold: float = 1.0) -> Image.Image:
    """The icon at 2048 px. bold > 1 thickens the strokes for the tiny title bar sizes, where thin lines fade."""
    n = 256 * K
    grad = Image.new("RGBA", (1, n))
    for y in range(n):
        t = y / (n - 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM, strict=True)) + (255,))
    grad = grad.resize((n, n))
    tile = Image.new("L", (n, n), 0)
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, n - 1, n - 1), radius=56 * K, fill=255)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(grad, (0, 0), tile)

    mark = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mark)

    def p(x, y):
        return (x * K, y * K)

    # the hook of the broom handle
    cx, cy, r, w = 124, 110, 62, round(24 * bold)
    d.arc((p(cx - r, cy - r), p(cx + r, cy + r)), start=188, end=344, fill=255, width=w * K)
    # the handle
    d.line((p(166, 89), p(83, 172)), fill=255, width=round(23 * bold) * K)
    for x, y in ((166, 89), (83, 172)):                      # round off the joints a little
        d.ellipse((p(x - 4, y - 4), p(x + 4, y + 4)), fill=255)
    # three bristles
    for a, b in (((70, 176), (55, 191)), ((97, 178), (78, 197)), ((124, 176), (101, 199))):
        d.line((p(*a), p(*b)), fill=255, width=round(11 * bold) * K)
    white = Image.new("RGBA", (n, n), (255, 255, 255, 255))
    out.paste(white, (0, 0), mark)
    return out


def _small(src: Image.Image, s: int) -> Image.Image:
    """Scale down; the smallest sizes get a light sharpening of the colour (not the edge transparency) so the
    white mark stays crisp instead of soft."""
    im = src.resize((s, s), Image.LANCZOS)
    if s > 32:
        return im
    rgb = im.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.5, percent=45 if s > 20 else 60, threshold=0))
    rgb.putalpha(im.getchannel("A"))
    return rgb


def main() -> None:
    big, bold = master(), master(1.4)
    frames = [_small((bold if s <= 24 else big), s) for s in SIZES]
    frames[-1].save(ROOT / "docs" / "logo.png")
    frames[-1].save(ROOT / "app" / "sweep.ico", sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    print("sweep.ico:", ", ".join(map(str, SIZES)))


if __name__ == "__main__":
    main()
