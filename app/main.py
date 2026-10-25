"""Sweep 1.0 entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(HERE))

from sweep import platform as P  # noqa: E402


def ensure_admin() -> None:
    """On Windows ask for administrator rights (UAC) when the process is not elevated.
    If the user declines, Sweep keeps running with limited rights and shows a banner with a button to ask again."""
    if not P.IS_WINDOWS or "--no-elevate" in sys.argv or "--limited" in sys.argv:
        return
    if P.is_admin():
        return
    if P.relaunch_elevated():
        sys.exit(0)
    P.log("started without administrator rights")


def run_auto() -> None:
    """Silent weekly clean, used by the scheduled task."""
    from sweep import cleaner
    session = cleaner.new_session()
    freed = 0
    chosen = P.load_settings().get("junk", {})   # the ticks saved on the Junk page
    for c in cleaner.CATEGORIES:
        if chosen.get(c.id, c.default) and c.id != "bin":
            freed += cleaner.quarantine(c, session)
    cleaner.purge(max_age_days=30)
    P.log(f"auto clean {session}: freed {freed}")


def main() -> int:
    if "--auto" in sys.argv:
        ensure_admin()
        run_auto()
        return 0
    ensure_admin()
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    # The interface is always drawn by the CPU (Qt Quick software renderer): the graphics card is not used at all,
    # which keeps the mouse cursor and games smooth while Sweep is open.
    os.environ["QT_QUICK_BACKEND"] = "software"
    from PySide6.QtGui import QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication
    from sweep.bridge import App

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Sweep")
    qt_app.setOrganizationName("Sweep")
    icon = HERE / "sweep.ico"
    if icon.exists():
        qt_app.setWindowIcon(QIcon(str(icon)))
    bridge = App()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(HERE / "qml"))
    engine.rootContext().setContextProperty("app", bridge)
    engine.load(str(HERE / "qml" / "Main.qml"))
    if not engine.rootObjects():
        return 1
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
