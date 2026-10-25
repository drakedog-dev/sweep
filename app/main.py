"""Sweep 1.0 entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(HERE))

from sweep import platform as P  # noqa: E402


def ensure_admin() -> None:
    """On Windows relaunch elevated when not already administrator."""
    if not P.IS_WINDOWS or "--no-elevate" in sys.argv:
        return
    import ctypes
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except Exception:
        return
    exe = sys.executable
    params = " ".join(f'"{a}"' for a in sys.argv[1:]) if getattr(sys, "frozen", False) else " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


def run_auto() -> None:
    """Silent weekly clean, used by the scheduled task."""
    from sweep import cleaner
    session = cleaner.new_session()
    freed = 0
    for c in cleaner.CATEGORIES:
        if c.default and c.id != "bin":
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
    if P.IS_WINDOWS:
        os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
        if "--software" in sys.argv:
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
