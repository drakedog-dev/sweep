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


def run_guard() -> None:
    """Scheduled Guard check (no window). Puts things back when allowed, otherwise asks with a notification."""
    from sweep import guard
    from sweep.i18n import I18n
    settings = P.load_settings()
    g = guard.state(settings)
    if not g["enabled"]:
        return
    found = guard.check(settings)
    drift = bool(found["privacy"] or found["apps"])
    fixed = False
    if drift and g["auto"] and P.is_admin():
        failed = guard.fix(found)
        fixed = not failed
    guard.record(settings, found, fixed)
    P.save_settings(settings)
    P.log(f"guard: build {found['build']}, reverted {found['privacy']}, apps back {found['apps']}, fixed={fixed}")
    if not drift:
        return
    t = I18n(settings.get("lang") or "ru")
    n = len(found["privacy"]) + len(found["apps"])
    text = t.t("guard.toast.fixed" if fixed else "guard.toast.ask", n)
    if found["buildChanged"]:
        text = t.t("guard.toast.after", found["build"]) + " " + text
    notify(t.t("guard.toast.title"), text)


def notify(title: str, text: str) -> None:
    """Windows notification from the tray; a click opens Sweep on the Guard page."""
    import subprocess
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    tray = QSystemTrayIcon(QIcon(str(HERE / "sweep.ico")))
    tray.setToolTip("Sweep")

    def open_sweep(*_):
        cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
        subprocess.Popen(cmd + ["--page", "guard"])
        tray.hide()
        app.quit()

    tray.messageClicked.connect(open_sweep)
    tray.activated.connect(open_sweep)
    tray.show()
    QTimer.singleShot(800, lambda: tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 30000))
    QTimer.singleShot(5 * 60 * 1000, app.quit)      # the tray icon stays a few minutes so the message can be clicked
    app.exec()


def main() -> int:
    if "--guard" in sys.argv:
        run_guard()      # never asks for UAC in the background; the scheduled task already runs elevated
        return 0
    if "--auto" in sys.argv:
        ensure_admin()
        run_auto()
        return 0
    ui_test = "--ui-test" in sys.argv
    if ui_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"    # CI: no visible window
    else:
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
    from sweep.bridge import AppIconProvider
    engine.addImageProvider("appicon", AppIconProvider())
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    engine.load(str(HERE / "qml" / "Main.qml"))
    if not engine.rootObjects():
        P.log("ui-test: Main.qml did not load: " + " | ".join(warnings))
        return 1
    if ui_test:
        return run_ui_test(qt_app, engine.rootObjects()[0], bridge, warnings)
    return qt_app.exec()


def run_ui_test(qt_app, root, bridge, warnings) -> int:
    """Opens every page of the real build, loads the real program list, fails on any QML warning."""
    from PySide6.QtCore import QTimer
    keys = list(root.property("navKeys").toVariant()) if hasattr(root.property("navKeys"), "toVariant") else list(root.property("navKeys"))
    steps = [lambda i=i: root.setProperty("current", i) for i in range(len(keys))] + [bridge.scanPrograms, bridge.scanBoot]
    result = {"code": 0}

    def step(n=0):
        if bridge.busy:
            QTimer.singleShot(300, lambda: step(n))
            return
        if n < len(steps):
            steps[n]()
            QTimer.singleShot(900, lambda: step(n + 1))
            return
        progs = bridge.programCount
        P.log(f"ui-test: pages {len(keys)}, programs {progs}, boots {len(bridge.bootData.get('boots', []))}, QML warnings {len(warnings)}")
        for w in warnings[:20]:
            P.log(f"ui-test QML: {w}")
        result["code"] = 1 if warnings or progs == 0 else 0
        qt_app.quit()

    QTimer.singleShot(4000, step)
    qt_app.exec()
    return result["code"]


if __name__ == "__main__":
    sys.exit(main())
