"""Rebuild app/qml/Sweep/fonts/lucide.ttf with exactly the icons named in Theme.qml.

    pip install fonttools
    python tools/make_icon_font.py path/to/lucide-static/font

The folder is the `font` directory of the lucide-static npm package (lucide.ttf + codepoints.json).
New icon names added to the `icons` map in Theme.qml get their codepoint filled in automatically."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "app" / "qml" / "Sweep" / "Theme.qml"
OUT = ROOT / "app" / "qml" / "Sweep" / "fonts" / "lucide.ttf"


def main(src: Path) -> int:
    codepoints = json.loads((src / "codepoints.json").read_text("utf-8"))
    theme = THEME.read_text("utf-8")
    block = re.search(r"readonly property var icons: \(\{(.*?)\}\)", theme, re.S)
    names = re.findall(r'"([a-z0-9-]+)":', block.group(1))
    missing = [n for n in names if n not in codepoints]
    if missing:
        print("not in Lucide:", ", ".join(missing))
        return 1
    body = ",\n".join(f'        "{n}": "\\u{codepoints[n]:04x}"' for n in names)
    theme = theme[:block.start(1)] + "\n" + body + "\n    " + theme[block.end(1):]
    THEME.write_text(theme, "utf-8")
    opts = subset.Options()
    opts.layout_features = []
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(str(src / "lucide.ttf"), opts)
    s = subset.Subsetter(opts)
    s.populate(unicodes=[codepoints[n] for n in names])
    s.subset(font)
    subset.save_font(font, str(OUT), opts)
    print(f"{len(names)} icons -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "lucide/font")))
