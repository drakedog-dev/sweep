"""Qt bridge: exposes application state and actions to QML. Long operations run in worker threads."""
from __future__ import annotations

import os
import re
import sys
import traceback
from datetime import datetime
from urllib.parse import quote, unquote

from PySide6.QtCore import Property, QFileInfo, QObject, QSize, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtQuick import QQuickImageProvider

from . import boot as bootx
from . import catalog as CAT
from . import cleaner, extras, guard, tweaks
from . import platform as P
from . import uninstall as U
from . import updates as UPD
from .i18n import I18n

TERMS_VERSION = 3   # raise when the terms of use change: everyone is asked to accept them again (2: winget updates, 3: installing programs)


def changelog_notes(text: str, version: str | None = None) -> list[str]:
    """Bullet lines of one CHANGELOG.md section (or of a whole release body when version is None)."""
    lines = text.splitlines()
    if version is not None:
        out, inside = [], False
        for line in lines:
            if line.startswith("## "):
                inside = line[3:].strip().lstrip("v") == version
                continue
            if inside:
                out.append(line)
        lines = out
    return [ln.strip()[2:].strip() for ln in lines if ln.strip().startswith(("- ", "* "))][:12]


def bundled_changelog() -> str:
    from pathlib import Path
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    for p in (base / "CHANGELOG.md", Path(__file__).resolve().parents[2] / "CHANGELOG.md"):
        try:
            return p.read_text("utf-8")
        except OSError:
            continue
    return ""


class Worker(QThread):
    done = Signal(object)
    failed = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:  # noqa: BLE001
            P.log(traceback.format_exc())
            self.failed.emit(e)


class AppIconProvider(QQuickImageProvider):
    """image://appicon/<path>: the real icon of a program, taken from its exe or ico by Windows."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        self._cache: dict[str, QPixmap] = {}

    def requestPixmap(self, id_, size, requested):  # noqa: N802
        path = unquote(id_)
        if path not in self._cache:
            from PySide6.QtWidgets import QFileIconProvider
            side = requested.width() if requested and requested.width() > 0 else 40
            pm = QPixmap(path) if path.lower().endswith((".png", ".jpg", ".jpeg")) else QPixmap()
            if not pm.isNull():       # a Store app's logo is a picture, not a program file
                pm = pm.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                pm = QFileIconProvider().icon(QFileInfo(path)).pixmap(QSize(side, side))
            self._cache[path] = pm
        return self._cache[path]


class App(QObject):
    changed = Signal()            # generic: any list/property changed
    statusChanged = Signal()
    busyChanged = Signal()
    monitorChanged = Signal()
    langChanged = Signal()
    updatesChanged = Signal()      # program updates list and progress (emitted from worker threads too)
    installChanged = Signal()      # programs to install, search results and install progress (worker threads too)
    toast = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = P.load_settings()
        lang = self.settings.get("lang") or ("ru" if self._system_is_ru() else "en")
        self.i18n = I18n(lang)
        self._status = ""
        self._busy = False
        self._progress = -1.0
        self._workers: list[Worker] = []
        self._health = {"score": 0, "tips": []}
        self._lang_counter = 0
        # data
        self._admin = P.is_admin() and "--limited" not in sys.argv
        self._priv_hint: tuple[str, str] | None = None   # why privacy changes did not stick
        self._start_page = self._arg("--page")
        self._pending = self._arg("--do")
        self.categories = cleaner.CATEGORIES
        saved = self.settings.get("junk", {})
        self.checked = {c.id: bool(saved.get(c.id, c.default)) for c in self.categories}
        self.privacy_state = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
        guard.init_baseline(self.settings, self.privacy_state)
        self.boot_data: dict = {}
        self.services = []
        self.startup = []
        self.reg_backups = []
        self.volumes = extras.volumes()
        self.selected_drive = extras.system_drive()
        self.drive_junk: dict = {}
        self.drive_checked: dict = {}
        self.apps = []
        self.programs: list[dict] = []
        self._prog_search = ""
        self._prog_sort = "size"
        self._un: dict = {}            # uninstall wizard state
        self._un_cancel = False
        # program updates through winget
        self._pu = {"checked": False, "checking": False, "winget": True, "running": False, "current": "", "done": 0, "total": 0, "frac": 0.0, "when": "",
                    "stage": "", "sdone": 0, "stotal": 0, "eta": 12.0}
        self._pu_items: list[dict] = []
        self._pu_cancel = False
        self._pu_pending: list[str] = []
        self._notes: dict = {}
        # installing programs through winget
        self._ins = {"loaded": False, "loading": False, "running": False, "done": 0, "total": 0, "current": "", "frac": 0.0,
                     "searching": False, "searched": False, "query": ""}
        self._ins_state: dict[str, dict] = {}
        self._ins_installed: set[str] = set()
        self._ins_results: list[dict] = []
        self._ins_cancel = False
        self.sysinfo = {}
        self.profile = {"class": "mid"}
        self.quarantine = cleaner.sessions()
        self.fx = tweaks.visual_fx_mode()
        self.power = tweaks.power_plan()
        self.schedule = {"enabled": False, "next": ""}
        self.update_info = None
        # live monitor
        self.monitor = extras.Monitor()
        self._mon = {"cpu": 0, "ram": 0, "ram_used": 0, "ram_total": 1, "disk_mbps": 0}
        self.cpu_hist = [0.0] * 30
        self.ram_hist = [0.0] * 30
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._set_status(self.i18n.t("common.ready"))
        QTimer.singleShot(300, self.boot)
        # updates: "ask" (default) shows a reminder, "auto" installs silently, "off" never checks
        had_settings = bool(self.settings)
        if "updateMode" not in self.settings:
            self.settings["updateMode"] = "off" if self.settings.get("autoUpdate") is False else "ask"
        self._update_prompt: dict = {}
        self._whats_new: dict = {}
        last = self.settings.get("lastVersion")
        updated = (last and self._newer(P.APP_VERSION, last)) or (last is None and had_settings)
        if updated and (P.IS_WINDOWS or "--whatsnew" in sys.argv):
            self._whats_new = {"tag": P.APP_VERSION, "notes": changelog_notes(bundled_changelog(), P.APP_VERSION)}
        if last != P.APP_VERSION:
            self.settings["lastVersion"] = P.APP_VERSION
        P.save_settings(self.settings)
        self._need_terms = int(self.settings.get("termsAccepted", 0)) < TERMS_VERSION and (P.IS_WINDOWS or "--terms" in sys.argv)
        if P.IS_WINDOWS and self.settings["updateMode"] != "off":
            QTimer.singleShot(8000, self.autoUpdateCheck)
        if P.IS_WINDOWS and self._pu_conf().get("auto") and self._pu_due():
            QTimer.singleShot(25000, lambda: self._scan_updates(quiet=True))

    # ---------- helpers ----------
    @staticmethod
    def _arg(name: str) -> str:
        a = sys.argv
        return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else ""

    @staticmethod
    def _system_is_ru() -> bool:
        try:
            import locale
            loc = locale.getlocale()[0] or ""
            return loc.lower().startswith("ru")
        except Exception:
            return False

    def _err_text(self, e) -> str:
        if P.is_access_denied(e):
            return self.i18n.t("admin.denied") if self._admin else self.i18n.t("admin.need")
        return self.i18n.t("common.error", str(e))

    def _need_admin(self, action: str, page: str) -> bool:
        """Without administrator rights: show the UAC prompt and repeat the action in the elevated copy.
        Returns True when the caller must stop (Sweep is restarting or the user said no)."""
        if self._admin:
            return False
        if P.relaunch_elevated(["--page", page] + (["--do", action] if action else [])):
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
        else:
            self._set_status(self.i18n.t("admin.declined"))
            self.toast.emit(self.i18n.t("admin.declined"))
        return True

    def _run(self, fn, on_done=None, status: str | None = None, on_fail=None):
        if status:
            self._set_status(status)
        self._set_busy(True)
        w = Worker(fn, self)
        self._workers.append(w)

        def finished(res):
            self._set_busy(False)
            self._workers.remove(w)
            if on_done:
                try:
                    on_done(res)
                except Exception as e:  # noqa: BLE001
                    P.log(traceback.format_exc())
                    self._set_status(self.i18n.t("common.error", str(e)))

        def failed(e):
            self._set_busy(False)
            self._workers.remove(w)
            if on_fail:
                try:
                    on_fail(e)
                except Exception:  # noqa: BLE001
                    P.log(traceback.format_exc())
            self._set_status(self._err_text(e))
            self.changed.emit()

        w.done.connect(finished)
        w.failed.connect(failed)
        w.start()

    def _bg(self, fn, on_done=None, on_fail=None):
        """Like _run, but the rest of Sweep stays usable meanwhile (no busy flag)."""
        w = Worker(fn, self)
        self._workers.append(w)

        def finished(res):
            self._workers.remove(w)
            try:
                if on_done:
                    on_done(res)
            except Exception:  # noqa: BLE001
                P.log(traceback.format_exc())

        def failed(e):
            self._workers.remove(w)
            try:
                if on_fail:
                    on_fail(e)
            except Exception:  # noqa: BLE001
                P.log(traceback.format_exc())

        w.done.connect(finished)
        w.failed.connect(failed)
        w.start()

    def _set_status(self, s: str):
        self._status = s
        self.statusChanged.emit()

    def _set_busy(self, b: bool):
        self._busy = b
        self.busyChanged.emit()

    def _loc(self, d: dict) -> str:
        return d.get(self.i18n.lang) or d.get("en") or ""

    # ---------- properties ----------
    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=langChanged)
    def lang(self):
        return self.i18n.lang

    @Property(bool, constant=True)
    def demo(self):
        return not P.IS_WINDOWS

    @Property(str, constant=True)
    def version(self):
        return P.APP_VERSION

    @Property(str, notify=langChanged)
    def theme(self):
        return self.settings.get("theme", "dark")

    @Property(str, notify=langChanged)
    def accent(self):
        return self.settings.get("accent", "violet")

    @Property(bool, constant=True)
    def isAdmin(self):
        return self._admin

    @Property(str, constant=True)
    def startPage(self):
        return self._start_page

    @Slot(str)
    def requestAdmin(self, page):
        """Banner button: restart Sweep with administrator rights on the same page."""
        self._need_admin("", page or "overview")

    @Property(str, notify=langChanged)
    def updateMode(self):
        return self.settings.get("updateMode", "ask")

    @Slot(str)
    def setUpdateMode(self, mode):
        self.settings["updateMode"] = mode
        P.save_settings(self.settings)
        self.langChanged.emit()

    @Property("QVariantMap", notify=changed)
    def updatePrompt(self):
        return self._update_prompt

    @Property("QVariantMap", notify=changed)
    def whatsNew(self):
        return self._whats_new

    @Property(bool, notify=changed)
    def needTerms(self):
        return self._need_terms

    @Slot()
    def acceptTerms(self):
        self._need_terms = False
        self.settings["termsAccepted"] = TERMS_VERSION
        P.save_settings(self.settings)
        self.changed.emit()

    @Slot()
    def declineTerms(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    @Slot()
    def dismissWhatsNew(self):
        self._whats_new = {}
        self.changed.emit()

    def _offer_update(self, info: dict) -> None:
        self._update_prompt = {"tag": info["tag"], "notes": info.get("notes", [])}
        self.changed.emit()

    @Slot()
    def acceptUpdate(self):
        """Reminder: the user agreed to install the new version."""
        self._update_prompt = {}
        self.changed.emit()
        self.installUpdate()

    @Slot()
    def remindLater(self):
        self._update_prompt = {}
        self.changed.emit()

    @Slot()
    def skipVersion(self):
        if self._update_prompt.get("tag"):
            self.settings["skipVersion"] = self._update_prompt["tag"]
            P.save_settings(self.settings)
        self._update_prompt = {}
        self.changed.emit()

    @Slot()
    def autoUpdateCheck(self):
        """Start-up check. "ask" shows a reminder with the changes, "auto" installs silently."""
        mode = self.settings.get("updateMode", "ask")
        if mode == "off":
            return
        if self._busy or self._need_terms or self._whats_new:
            QTimer.singleShot(5000, self.autoUpdateCheck)
            return

        def work():
            return self._fetch_release()

        def done(info):
            self.update_info = info
            self.changed.emit()
            if not (info.get("newer") and info.get("url")) or info["tag"] == self.settings.get("skipVersion"):
                return
            if mode == "auto":
                self.toast.emit(self.i18n.t("set.autoinstalling", info["tag"]))
                QTimer.singleShot(1500, self.installUpdate)
            else:
                self._offer_update(info)

        w = Worker(work, self)
        self._workers.append(w)
        w.done.connect(lambda r: (self._workers.remove(w), done(r)))
        w.failed.connect(lambda e: (self._workers.remove(w), P.log(f"auto update: {e}")))
        w.start()

    @Property(bool, notify=langChanged)
    def animations(self):
        return bool(self.settings.get("animations", True))

    @Slot(str, result=str)
    def t(self, key):
        return self.i18n.t(key)

    @Slot(str, str, result=str)
    def t1(self, key, a):
        return self.i18n.t(key, a)

    @Slot(str, str, str, result=str)
    def t2(self, key, a, b):
        return self.i18n.t(key, a, b)

    @Slot(float, result=str)
    def size(self, n):
        return self.i18n.size(n)

    @Property("QVariantList", notify=changed)
    def junk(self):
        return [{"id": c.id, "name": self._loc(c.name), "hint": self._loc(c.hint), "size": float(c.size), "checked": self.checked[c.id]} for c in self.categories]

    @Property(float, notify=changed)
    def junkTotal(self):
        return float(sum(c.size for c in self.categories if self.checked[c.id]))

    @Property("QVariantList", notify=changed)
    def privacy(self):
        groups = {"data": "priv.group.data", "ads": "priv.group.ads", "assist": "priv.group.assist"}
        return [{"id": p.id, "group": self.i18n.t(groups[p.group]), "name": self._loc(p.name), "hint": self._loc(p.hint), "on": not self.privacy_state[p.id]} for p in tweaks.PRIVACY]

    @Property(int, notify=changed)
    def privacyOn(self):
        return sum(1 for v in self.privacy_state.values() if v)

    @Property("QVariantList", notify=changed)
    def registry(self):
        return [{"id": c.id, "name": self._loc(c.name), "hint": self._loc(c.hint), "found": c.found} for c in extras.REG_CATEGORIES]

    @Property("QVariantList", notify=changed)
    def regBackups(self):
        return self.reg_backups

    @Property("QVariantList", notify=changed)
    def serviceList(self):
        return self.services

    @Property("QVariantList", notify=changed)
    def startupList(self):
        src = {"User": "start.src.user", "System": "start.src.system", "System32": "start.src.system32", "Folder": "start.src.folder"}
        return [{"name": e["name"], "command": e.get("command", ""), "source": self.i18n.t(src[e.get("source", "")]) if e.get("source") in src else e.get("source", ""),
                 "enabled": bool(e.get("enabled"))} for e in self.startup]

    @Property("QVariantList", notify=changed)
    def volumeList(self):
        return self.volumes

    @Property(str, notify=changed)
    def selectedDrive(self):
        return self.selected_drive

    @Property("QVariantList", notify=changed)
    def driveJunk(self):
        out = []
        for v in self.volumes:
            cats = self.drive_junk.get(v["letter"])
            rows = []
            if cats:
                for cid, name, hint in extras.DRIVE_JUNK:
                    c = cats.get(cid, {"size": 0, "count": 0})
                    if c["size"] <= 0:
                        continue
                    rows.append({"id": cid, "name": self._loc(name), "hint": self._loc(hint), "size": float(c["size"]), "count": c["count"],
                                 "checked": self.drive_checked.get((v["letter"], cid), cid != "oldwin")})
            out.append({"letter": v["letter"], "scanned": cats is not None, "rows": rows, "total": float(sum(r["size"] for r in rows if r["checked"]))})
        return out

    @Property(float, notify=changed)
    def driveJunkTotal(self):
        return float(sum(d["total"] for d in self.driveJunk))

    @Property("QVariantList", notify=changed)
    def appList(self):
        return [{"id": a["id"], "name": a["name"], "hint": self._loc(a["hint"])} for a in self.apps]

    @Property("QVariantList", notify=changed)
    def quarantineList(self):
        return self.quarantine

    @Property(float, notify=changed)
    def quarantineTotal(self):
        return float(sum(s["size"] for s in self.quarantine))

    @Property("QVariantMap", notify=changed)
    def health(self):
        return self._health

    @Property("QVariantMap", notify=changed)
    def pcProfile(self):
        return self.profile

    @Property("QVariantList", notify=changed)
    def systemRows(self):
        return self._system_rows()

    @Property(str, notify=changed)
    def fxMode(self):
        return self.fx

    @Property(str, notify=changed)
    def powerPlan(self):
        return self.power

    @Property("QVariantMap", notify=changed)
    def scheduleState(self):
        return self.schedule

    @Property("QVariantMap", notify=changed)
    def updateInfo(self):
        return self.update_info or {}

    @Property("QVariantMap", notify=monitorChanged)
    def mon(self):
        return self._mon

    @Property("QVariantList", notify=monitorChanged)
    def cpuHistory(self):
        return self.cpu_hist

    @Property("QVariantList", notify=monitorChanged)
    def ramHistory(self):
        return self.ram_hist

    @Slot(bool)
    def setMonitorActive(self, active):
        if active and not self._timer.isActive():
            self._timer.start()
        elif not active and self._timer.isActive():
            self._timer.stop()

    # ---------- lifecycle ----------
    def boot(self):
        def work():
            P.log_context()
            info = extras.system_info()
            try:
                bd = bootx.analyse(bootx.read_events())
            except Exception as e:  # noqa: BLE001
                P.log(f"boot x-ray: {e}")
                bd = {}
            return {"info": info, "services": self._load_services(), "startup": tweaks.startup_entries(), "schedule": tweaks.schedule_state(), "boot": bd}

        def done(res):
            self.sysinfo = res["info"]
            self.profile = extras.pc_profile(self.sysinfo)
            self.services = res["services"]
            self.startup = res["startup"]
            self.schedule = res["schedule"]
            self.boot_data = res.get("boot") or {}
            self.changed.emit()
            self.scan()
            if self._pending:
                QTimer.singleShot(1200, self._do_pending)

        self._run(work, done)

    def _do_pending(self):
        """Continue the action the user started before Sweep restarted with administrator rights."""
        if self._busy:
            QTimer.singleShot(800, self._do_pending)
            return
        act, self._pending = self._pending, ""
        kind, _, rest = act.partition(":")
        name, _, flag = rest.rpartition(":")
        on = flag == "1"
        if kind == "allPrivacy":
            self.allPrivacy()
        elif kind == "applyRecommendations":
            self.applyRecommendations()
        elif kind == "guardFix":
            self.guardFix()
        elif kind == "clean":
            self.clean()
        elif kind == "quickClean":
            self.quickClean()
        elif kind == "privacy":
            self.setPrivacy(name, on)
        elif kind == "service":
            self.setService(name, on)
        elif kind == "schedule":
            self.setSchedule(flag == "1")
        elif kind == "progupdates":
            self._pu_pending = [x for x in name.split("|") if x]
            self._scan_updates()
        elif kind == "proginstall":
            names = {i: n for i, n, _ in CAT.PROGRAMS}
            for pid in [x for x in name.split("|") if x]:
                self._ins_item(pid, names.get(pid, pid))["picked"] = True
            self.installChanged.emit()
            self.installPicked()
        elif kind == "startup":
            idx = next((i for i, e in enumerate(self.startup) if e["name"] == name), -1)
            if idx >= 0:
                self.setStartup(idx, on)

    def _load_services(self):
        out = []
        for s in tweaks.SERVICES:
            st = tweaks.service_state(s.name)
            if st is None:
                continue
            out.append({"name": s.name, "title": self._loc(s.title), "hint": self._loc(s.hint), "enabled": bool(st), "weakOnly": s.weak_only})
        return out

    def _tick(self):
        try:
            self._mon = self.monitor.sample()
            self.cpu_hist = self.cpu_hist[1:] + [float(self._mon["cpu"])]
            self.ram_hist = self.ram_hist[1:] + [float(self._mon["ram"])]
            self.monitorChanged.emit()
        except Exception:
            pass

    def _compute_health(self):
        score, tips = 100, []
        junk = self.junkTotal
        if junk > 5 * 2**30:
            score -= 25; tips.append(self.i18n.t("ov.tip.junk"))
        elif junk > 1 * 2**30:
            score -= 12; tips.append(self.i18n.t("ov.tip.junk2"))
        elif junk > 300 * 2**20:
            score -= 5
        st = sum(1 for e in self.startup if e.get("enabled"))
        if st > 12:
            score -= 20; tips.append(self.i18n.t("ov.tip.startup", st))
        elif st > 7:
            score -= 10; tips.append(self.i18n.t("ov.tip.startup2", st))
        sysv = next((v for v in self.volumes if v["letter"] == extras.system_drive()), None)
        if sysv and sysv["total"]:
            fr = sysv["free"] / sysv["total"]
            if fr < 0.07:
                score -= 25; tips.append(self.i18n.t("ov.tip.disk"))
            elif fr < 0.15:
                score -= 12; tips.append(self.i18n.t("ov.tip.disk2"))
        pr = self.privacyOn
        if pr < 3:
            score -= 15; tips.append(self.i18n.t("ov.tip.privacy"))
        elif pr < 8:
            score -= 6; tips.append(self.i18n.t("ov.tip.privacy2"))
        last_boot = float(self.boot_data.get("last") or 0)
        if last_boot >= 60:
            score -= 8; tips.append(self.i18n.t("ov.tip.boot", f"{last_boot:.0f}"))
        pend = guard.state(self.settings).get("pending") or {}
        if pend.get("privacy") or pend.get("apps"):
            tips.insert(0, self.i18n.t("ov.tip.guard", len(pend.get("privacy", [])) + len(pend.get("apps", []))))
        n_upd = len(self._pu_safe())
        if n_upd:
            score -= 6 if n_upd >= 5 else 3
            tips.append(self.i18n.t("ov.tip.updates", n_upd))
        up_days = int(self.sysinfo.get("uptime", 0) // 86400)
        if up_days > 14:
            score -= 8; tips.append(self.i18n.t("ov.tip.uptime", up_days))
        score = max(5, min(100, score))
        if not tips:
            tips.append(self.i18n.t("ov.tip.ok"))
        self._health = {"score": score, "tips": tips[:3]}

    # ---------- junk ----------
    @Slot()
    def scan(self):
        def work():
            for c in self.categories:
                cleaner.scan(c)
            return True

        def done(_):
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("junk.scanned", self.i18n.size(self.junkTotal)))

        self._run(work, done, self.i18n.t("junk.scanning", "…"))

    @Slot(str, bool)
    def setChecked(self, cid, val):
        self.checked[cid] = val
        self.settings["junk"] = dict(self.checked)
        P.save_settings(self.settings)
        self.changed.emit()

    @Slot()
    def clean(self):
        if self._need_admin("clean", "junk"):
            return
        session = cleaner.new_session()
        todo = [c for c in self.categories if self.checked[c.id]]

        def work():
            freed = 0
            for c in todo:
                freed += cleaner.quarantine(c, session)
                c.size = 0
            P.log(f"clean {session}: freed {freed}")
            return freed

        def done(freed):
            self.quarantine = cleaner.sessions()
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("junk.done", self.i18n.size(freed)))
            self.toast.emit(self.i18n.t("junk.done", self.i18n.size(freed)))

        self._run(work, done, self.i18n.t("common.working"))

    @Slot()
    def quickClean(self):
        if self._need_admin("quickClean", "overview"):
            return
        self.checked = {c.id: c.default for c in self.categories}
        self.changed.emit()
        self.clean()

    # ---------- privacy ----------
    def _restore_point_due(self) -> bool:
        if not self.settings.get("restorePoint", True):
            return False
        last = self.settings.get("lastRestorePoint", "")
        try:
            return (datetime.now() - datetime.fromisoformat(last)).total_seconds() > 24 * 3600
        except Exception:
            return True

    def _restore_point(self, what: str) -> None:
        """Worker thread: Windows restore point before a big change, at most once a day."""
        if self._restore_point_due() and extras.create_restore_point(f"Sweep: {what}"):
            self.settings["lastRestorePoint"] = datetime.now().isoformat(timespec="seconds")
            P.save_settings(self.settings)

    def _working_text(self) -> str:
        return self.i18n.t("rp.creating") if self._restore_point_due() else self.i18n.t("common.working")

    @Property(bool, notify=langChanged)
    def restorePoint(self):
        return bool(self.settings.get("restorePoint", True))

    @Slot(bool)
    def setRestorePoint(self, on):
        self.settings["restorePoint"] = on
        P.save_settings(self.settings)
        self.langChanged.emit()

    def _apply_privacy(self, items, protect: bool = True) -> list:
        """Runs in a worker thread. Applies every item even if some fail, then re-reads the real state.
        An item that was written fine but is off again a moment later (an antivirus rolled it back) also counts as failed."""
        self._last_protect = protect
        failed = [p for p in items if tweaks.set_privacy(p, protect)]
        self.privacy_state = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
        if protect:
            for p in items:
                if p not in failed and not self.privacy_state[p.id]:
                    P.log(f"privacy {p.id}: written, but switched back right after")
                    failed.append(p)
        for p in items:      # Guard watches exactly what the user chose
            if self.privacy_state[p.id] == protect:
                guard.remember_privacy(self.settings, p.id, protect)
        P.save_settings(self.settings)
        return failed

    @Property(str, notify=changed)
    def privacyHint(self):
        if not self._priv_hint:
            return ""
        key, arg = self._priv_hint
        return self.i18n.t(key, arg)

    def _privacy_report(self, failed: list) -> None:
        self._compute_health()
        self.changed.emit()
        ok, total = self.privacyOn, len(tweaks.PRIVACY)
        want = getattr(self, "_last_protect", True)
        # a value Windows refused does not matter when the item still ended up in the wanted state
        # (for example widgets switched off by the other of its two settings): log it, do not alarm
        partial = [p for p in failed if self.privacy_state.get(p.id) == want]
        failed = [p for p in failed if self.privacy_state.get(p.id) != want]
        av = P.third_party_av()
        if not failed:
            self._priv_hint = None
        elif "kaspersky" in av.lower():
            self._priv_hint = ("priv.blocked.kaspersky", av)
        elif av:
            self._priv_hint = ("priv.blocked.av", av)
        elif self._admin:
            self._priv_hint = ("priv.blocked.generic", "")
        else:
            self._priv_hint = None
        self.changed.emit()
        if failed:
            names = ", ".join(self._loc(p.name) for p in failed[:3]) + ("…" if len(failed) > 3 else "")
            self._set_status(self.i18n.t("priv.partial", ok, total, names) + " " + (self.i18n.t("admin.denied") if self._admin else self.i18n.t("admin.need")))
        elif partial:
            names = ", ".join(self._loc(p.name) for p in partial[:3])
            self._set_status(self.i18n.t("priv.result", ok, total) + ". " + self.i18n.t("priv.partly", names))
            self.toast.emit(self.i18n.t("priv.result", ok, total))
        else:
            self._set_status(self.i18n.t("priv.result", ok, total))
            self.toast.emit(self.i18n.t("priv.result", ok, total))

    @Slot(str, bool)
    def setPrivacy(self, pid, on):
        """on = the Windows feature works (switch on, like in Windows Settings); off = tracking disabled."""
        if self._need_admin(f"privacy:{pid}:{int(on)}", "privacy"):
            self.changed.emit()      # put the switch back
            return
        p = next(x for x in tweaks.PRIVACY if x.id == pid)
        self.privacy_state[pid] = not on
        self.changed.emit()
        self._run(lambda: self._apply_privacy([p], not on), self._privacy_report)

    @Slot()
    def allPrivacy(self):
        if self._need_admin("allPrivacy", "privacy"):
            return
        status = self._working_text()
        self._run(lambda: (self._restore_point("disable tracking"), self._apply_privacy(tweaks.PRIVACY, True))[1], self._privacy_report, status)

    # ---------- boot x-ray ----------
    @Property("QVariantMap", notify=changed)
    def bootData(self):
        d = dict(self.boot_data or {})
        if not d:
            return {}
        rows = []
        for c in d.get("culprits", []):
            idx, on = -1, False
            f = (c.get("file") or "").lower()
            if c["kind"] == "app" and f:
                for i, e in enumerate(self.startup):
                    if f in (e.get("command") or "").lower() or f.rsplit(".", 1)[0] == e.get("name", "").lower():
                        idx, on = i, bool(e.get("enabled"))
                        break
            rows.append(dict(c, kindText=self.i18n.t("boot.kind." + c["kind"]), startupIndex=idx, startupOn=on))
        d["culprits"] = rows
        d["verdict"] = bootx.verdict(d.get("last", 0))
        d["boots"] = [dict(b, label=self._when(b["t"], short=True)) for b in d.get("boots", [])]
        return d

    @Slot()
    def scanBoot(self):
        def done(bd):
            self.boot_data = bd
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("boot.scanned", f"{bd.get('last', 0):.1f}") if bd.get("boots") else self.i18n.t("boot.empty.short"))

        self._run(lambda: bootx.analyse(bootx.read_events()), done, self.i18n.t("common.working"))

    @Slot()
    def restartForBoot(self):
        bootx.restart_now()
        self._set_status(self.i18n.t("boot.restarting"))

    def _when(self, iso: str, short: bool = False) -> str:
        try:
            t = datetime.fromisoformat(iso)
        except Exception:
            return ""
        days = (datetime.now().date() - t.date()).days
        if days == 0:
            day = self.i18n.t("when.today")
        elif days == 1:
            day = self.i18n.t("when.yesterday")
        else:
            day = t.strftime("%d.%m")
        return day if short and days > 1 else f"{day} {t:%H:%M}"

    # ---------- guard ----------
    @Property("QVariantMap", notify=changed)
    def guardState(self):
        g = guard.state(self.settings)
        names = {p.id: self._loc(p.name) for p in tweaks.PRIVACY}
        apps = {i: n for i, n, _ in extras.BLOAT}
        pend = g.get("pending") or {}
        return {
            "enabled": bool(g["enabled"]), "auto": bool(g["auto"]),
            "watched": [names[i] for i in (g["privacy"] or []) if i in names] + [apps.get(a, a) for a in g["apps"]],
            "watchedPrivacy": len(g["privacy"] or []), "watchedApps": len(g["apps"]),
            "lastRun": self._when(g["lastRun"]) if g["lastRun"] else "", "build": g["lastBuild"] or guard.windows_build(),
            "pending": [names.get(i, i) for i in pend.get("privacy", [])] + [apps.get(a, a) for a in pend.get("apps", [])],
            "events": [{"when": self._when(e["t"]), "build": e.get("build", ""), "afterUpdate": bool(e.get("buildChanged")),
                        "items": ", ".join([names.get(i, i) for i in e.get("privacy", [])] + [apps.get(a, a) for a in e.get("apps", [])]),
                        "fixed": bool(e.get("fixed"))} for e in g["events"][:8]],
        }

    @Slot(bool)
    def setGuard(self, on):
        g = guard.state(self.settings)
        if on and self._need_admin("", "guard"):
            self.changed.emit()
            return
        g["enabled"] = on
        P.save_settings(self.settings)
        self.changed.emit()
        exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

        def done(_):
            self._set_status(self.i18n.t("guard.on" if on else "guard.off"))
            if on:
                self.guardCheck()

        self._run(lambda: guard.set_task(on, exe), done)

    @Slot(bool)
    def setGuardAuto(self, on):
        guard.state(self.settings)["auto"] = on
        P.save_settings(self.settings)
        self.changed.emit()

    @Slot()
    def guardCheck(self):
        def work():
            found = guard.check(self.settings)
            guard.record(self.settings, found, False)
            P.save_settings(self.settings)
            return found

        def done(found):
            self.privacy_state = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
            self._compute_health()
            self.changed.emit()
            n = len(found["privacy"]) + len(found["apps"])
            self._set_status(self.i18n.t("guard.found", n) if n else self.i18n.t("guard.clean"))

        self._run(work, done, self.i18n.t("common.working"))

    @Slot()
    def guardFix(self):
        if self._need_admin("guardFix", "guard"):
            return
        pend = dict(guard.state(self.settings).get("pending") or {})

        def work():
            failed = guard.fix(pend)
            found = guard.check(self.settings)
            guard.record(self.settings, found, not failed and not (found["privacy"] or found["apps"]))
            g = guard.state(self.settings)
            if g["events"] and not failed:
                g["events"][0]["fixed"] = True
            P.save_settings(self.settings)
            return failed

        def done(failed):
            self.privacy_state = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("guard.fixed") if not failed else self.i18n.t("guard.fixfail", len(failed)))
            if not failed:
                self.toast.emit(self.i18n.t("guard.fixed"))

        self._run(work, done, self.i18n.t("common.working"))

    # ---------- registry ----------
    @Slot()
    def regScan(self):
        def work():
            for c in extras.REG_CATEGORIES:
                extras.reg_scan(c)
            return sum(c.found for c in extras.REG_CATEGORIES)

        self._run(work, lambda n: (self.changed.emit(), self._set_status(self.i18n.t("reg.found").capitalize() + f": {n}")), self.i18n.t("common.working"))

    @Slot("QVariantList")
    def regClean(self, ids):
        if self._need_admin("", "registry"):
            return
        session = cleaner.new_session()
        cats = [c for c in extras.REG_CATEGORIES if c.id in ids]

        def work():
            self._restore_point("registry cleaning")
            return sum(extras.reg_clean(c, session) for c in cats)

        def done(n):
            self.reg_backups = extras.reg_backups()
            self.changed.emit()
            self._set_status(self.i18n.t("reg.done", n))

        self._run(work, done, self.i18n.t("common.working"))

    @Slot(str)
    def regRestore(self, session):
        self._run(lambda: extras.reg_restore(session), lambda n: (setattr(self, "reg_backups", extras.reg_backups()), self.changed.emit(), self._set_status(self.i18n.t("q.restored", n))))

    # ---------- services / startup ----------
    @Slot(str, bool)
    def setService(self, name, on):
        if self._need_admin(f"service:{name}:{int(on)}", "services"):
            self.changed.emit()
            return
        row = next((s for s in self.services if s["name"] == name), None)
        if row is None:
            return
        row["enabled"] = on
        self.changed.emit()

        def work():
            tweaks.set_service(name, on)
            return tweaks.service_state(name)

        def done(state):
            if state is not None:
                row["enabled"] = bool(state)
            self.changed.emit()
            if state is not None and bool(state) != on:
                self._set_status(self.i18n.t("svc.failed", row["title"]))
            else:
                self._set_status(self.i18n.t("common.done"))

        self._run(work, done, on_fail=lambda _: row.__setitem__("enabled", not on))

    @Slot(int, bool)
    def setStartup(self, index, on):
        if index < 0 or index >= len(self.startup):
            return
        e = self.startup[index]
        if e.get("source", "").startswith("System") and self._need_admin(f"startup:{e['name']}:{int(on)}", "startup"):
            self.changed.emit()
            return
        e["enabled"] = on
        self.changed.emit()

        def done(_):
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("start.on" if on else "start.off", e["name"]))

        self._run(lambda: tweaks.set_startup(e, on), done, on_fail=lambda _: e.__setitem__("enabled", not on))

    # ---------- boost ----------
    @Slot()
    def freeRam(self):
        def work():
            import psutil
            before = psutil.virtual_memory().available
            if P.IS_WINDOWS:
                import ctypes
                psapi = ctypes.windll.psapi
                for p in psutil.process_iter(["pid"]):
                    try:
                        h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, p.pid)
                        if h:
                            psapi.EmptyWorkingSet(h)
                            ctypes.windll.kernel32.CloseHandle(h)
                    except Exception:
                        pass
            else:
                import time
                time.sleep(0.8)
                return 1.3 * 2**30
            import time
            time.sleep(0.6)
            return max(0, psutil.virtual_memory().available - before)

        self._run(work, lambda g: self._set_status(self.i18n.t("boost.ram.done", self.i18n.size(g))), self.i18n.t("common.working"))

    @Slot()
    def optimizeDisks(self):
        def work():
            if P.IS_WINDOWS:
                P.powershell("Get-Volume | ? {$_.DriveLetter -and $_.DriveType -eq 'Fixed' -and $_.FileSystem -eq 'NTFS'} | % { Optimize-Volume -DriveLetter $_.DriveLetter -EA SilentlyContinue }", 1800)
            else:
                import time
                time.sleep(1.5)
            return True

        self._run(work, lambda _: self._set_status(self.i18n.t("common.done")), self.i18n.t("common.working"))

    @Slot(str)
    def setFx(self, mode):
        self.fx = mode
        self.changed.emit()
        self._run(lambda: tweaks.set_visual_fx(mode))

    @Slot(str)
    def setPower(self, plan):
        self.power = plan
        self.changed.emit()
        self._run(lambda: tweaks.set_power_plan(plan))

    @Slot(bool)
    def setSchedule(self, on):
        if self._need_admin(f"schedule:{int(on)}", "boost"):
            self.changed.emit()
            return
        exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

        def done(_):
            self.schedule = tweaks.schedule_state() if P.IS_WINDOWS else {"enabled": on, "next": "Sunday 12:00" if on else ""}
            self.changed.emit()

        self._run(lambda: tweaks.set_schedule(on, exe), done)

    @Slot()
    def openUpdate(self):
        if P.IS_WINDOWS:
            os.startfile("ms-settings:windowsupdate")  # type: ignore[attr-defined]

    @Slot()
    def applyRecommendations(self):
        if self._need_admin("applyRecommendations", "overview"):
            return
        cls = self.profile.get("class", "mid")

        status = self._working_text()

        def work():
            self._restore_point("recommendations")
            self._apply_privacy(tweaks.PRIVACY, True)
            if cls in ("weak", "mid"):
                for s in self.services:
                    svc = next(x for x in tweaks.SERVICES if x.name == s["name"])
                    if cls == "weak" or not svc.weak_only:
                        tweaks.set_service(s["name"], False)
                        s["enabled"] = False
            if cls == "weak":
                tweaks.set_visual_fx("perf")
                self.fx = "perf"
            return True

        def done(_):
            self._compute_health()
            self.changed.emit()
            self._set_status(self.i18n.t("common.done"))

        self._run(work, done, status)

    # ---------- disks ----------
    @Slot(str)
    def selectDrive(self, letter):
        self.selected_drive = letter
        self.changed.emit()

    @Slot()
    def scanDrives(self):
        letters = [v["letter"] for v in self.volumes]

        def work():
            return {letter: extras.drive_junk(letter) for letter in letters}

        def done(res):
            self.drive_junk = res
            self.changed.emit()
            self._set_status(self.i18n.t("junk.scanned", self.i18n.size(self.driveJunkTotal)))

        self._run(work, done, self.i18n.t("disk.scanning", ", ".join(letters)))

    @Slot(str, str, bool)
    def setDriveChecked(self, letter, cid, val):
        self.drive_checked[(letter, cid)] = val
        self.changed.emit()

    @Slot()
    def cleanDrives(self):
        if self._need_admin("", "disks"):
            return
        session = cleaner.new_session()
        todo = [(d["letter"], r["id"]) for d in self.driveJunk for r in d["rows"] if r["checked"]]

        def work():
            freed = 0
            for letter, cid in todo:
                c = self.drive_junk[letter][cid]
                if cid == "bin":
                    extras.empty_drive_bin(letter)
                    freed += c["size"]
                elif P.IS_WINDOWS:
                    freed += cleaner.quarantine_files(c["paths"], session, f"{letter}_{cid}")
                else:
                    freed += c["size"]
                c["size"], c["count"], c["paths"] = 0, 0, []
            return freed

        def done(freed):
            self.quarantine = cleaner.sessions()
            self.volumes = extras.volumes()
            self.changed.emit()
            self._set_status(self.i18n.t("junk.done", self.i18n.size(freed)))
            self.toast.emit(self.i18n.t("junk.done", self.i18n.size(freed)))

        self._run(work, done, self.i18n.t("common.working"))

    @Slot()
    def openDrive(self):
        if P.IS_WINDOWS:
            os.startfile(f"{self.selected_drive}:\\")  # type: ignore[attr-defined]

    # ---------- apps ----------
    @Slot()
    def scanApps(self):
        self._run(extras.installed_bloat, lambda res: (setattr(self, "apps", res), self.changed.emit(), self._set_status(self.i18n.t("apps.found").capitalize() + f": {len(res)}")), self.i18n.t("common.working"))

    @Slot("QVariantList")
    def removeApps(self, ids):
        if self._need_admin("", "apps"):
            return
        ids = set(ids)

        def work():
            self._restore_point("remove apps")
            for i in ids:
                extras.remove_app(i)
            guard.remember_apps(self.settings, ids)
            P.save_settings(self.settings)
            return len(ids)

        self._run(work, lambda n: (setattr(self, "apps", [a for a in self.apps if a["id"] not in ids]), self.changed.emit(), self._set_status(self.i18n.t("common.done"))), self.i18n.t("common.working"))

    # ---------- installed programs and the thorough uninstaller ----------
    @Property("QVariantList", notify=changed)
    def programList(self):
        q = self._prog_search.strip().lower()
        rows = [p for p in self.programs if not q or q in p["name"].lower() or q in p.get("publisher", "").lower()]
        key = {"size": lambda p: -p.get("size", 0), "name": lambda p: p["name"].lower(), "date": lambda p: p.get("date", "")}[self._prog_sort]
        rows.sort(key=key, reverse=self._prog_sort == "date")
        return [{"id": p["id"], "name": p["name"], "publisher": p.get("publisher", ""), "version": p.get("version", ""), "size": float(p.get("size", 0)),
                 "date": self._fmt_date(p.get("date", "")), "icon": ("image://appicon/" + quote(p["iconPath"], safe="")) if p.get("iconPath") else ""} for p in rows]

    @Property(int, notify=changed)
    def programCount(self):
        return len(self.programs)

    @Property(str, notify=changed)
    def programSort(self):
        return self._prog_sort

    @Slot(str)
    def setProgramSearch(self, q):
        self._prog_search = q
        self.changed.emit()

    @Slot(str)
    def setProgramSort(self, key):
        self._prog_sort = key
        self.changed.emit()

    def _fmt_date(self, iso: str) -> str:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return ""

    @staticmethod
    def _load_programs():
        progs = U.list_programs()
        for p in progs:
            p["iconPath"] = U.uninstall_icon_key(p) if P.IS_WINDOWS else ""
        return progs

    @Slot()
    def scanPrograms(self):
        work = self._load_programs

        def done(progs):
            self.programs = progs
            self.changed.emit()
            self._set_status(self.i18n.t("un.found", len(progs)))

        self._run(work, done, self.i18n.t("common.working"))

    @Property("QVariantMap", notify=changed)
    def uninstallState(self):
        if not self._un:
            return {}
        u = dict(self._un)
        u["leftovers"] = [dict(it, kindText=self.i18n.t("un.kind." + it["kind"]), sizeText=self.i18n.size(it["size"]) if it.get("size") else "")
                          for it in self._un.get("leftovers", [])]
        u["checkedCount"] = sum(1 for it in self._un.get("leftovers", []) if it.get("checked"))
        u["checkedSize"] = float(sum(it.get("size", 0) for it in self._un.get("leftovers", []) if it.get("checked")))
        return u

    def _prog(self, pid):
        return next((p for p in self.programs if p["id"] == pid), None)

    @Slot(str)
    def startUninstall(self, pid):
        """Step 0: show the program, running processes and the options."""
        if self._need_admin("", "apps"):
            return
        p = self._prog(pid)
        if not p:
            return
        running = U.running_processes(p)
        self._un = {"stage": "confirm", "id": pid, "name": p["name"], "publisher": p.get("publisher", ""), "version": p.get("version", ""),
                    "icon": ("image://appicon/" + quote(p["iconPath"], safe="")) if p.get("iconPath") else "",
                    "quietAvailable": bool(p.get("quiet")), "quiet": False, "running": sorted({r["name"] for r in running}),
                    "leftovers": [], "result": {}, "still": False, "forced": False}
        self.changed.emit()

    @Slot(bool)
    def setUninstallQuiet(self, on):
        if self._un:
            self._un["quiet"] = on
            self.changed.emit()

    @Slot(bool)
    def confirmUninstall(self, forced):
        """Steps 1-3: close the program, run its own uninstaller (unless forced), then look for leftovers."""
        u = self._un
        p = self._prog(u.get("id"))
        if not p:
            return
        u["forced"] = forced
        u["stage"] = "uninstalling"
        self._un_cancel = False
        self.changed.emit()

        def work():
            self._restore_point(f"uninstall {p['name']}")
            U.close_processes(p)
            if forced:
                return {"ok": False, "still": U.still_installed(p), "forced": True}
            return U.run_uninstaller(p, quiet=bool(u.get("quiet")), cancel=lambda: self._un_cancel)

        def scanned(items):
            for it in items:
                it["checked"] = bool(it["exact"])
            u["leftovers"] = items
            u["stage"] = "leftovers" if items else "done"
            self._set_status(self.i18n.t("un.found.text", len(items), sum(1 for it in items if it["checked"])))
            if not items:
                u["result"] = {"removed": 0, "reboot": 0, "failed": [], "freed": 0}
                self._after_uninstall(p)
            self.changed.emit()

        def uninstalled(r):
            u["still"] = bool(r.get("still"))
            u["stage"] = "scanning"
            self.changed.emit()
            self._run(lambda: U.find_leftovers(p), scanned, self.i18n.t("un.scanning"))

        self._run(work, uninstalled, self.i18n.t("un.running", p["name"]))

    @Slot()
    def skipWaiting(self):
        self._un_cancel = True

    @Slot(int, bool)
    def setLeftover(self, idx, on):
        for it in self._un.get("leftovers", []):
            if it["id"] == idx:
                it["checked"] = on
        self.changed.emit()

    @Slot(bool)
    def setAllLeftovers(self, on):
        for it in self._un.get("leftovers", []):
            it["checked"] = on
        self.changed.emit()

    @Slot()
    def removeLeftovers(self):
        """Step 4: remove what is ticked; everything stays restorable."""
        u = self._un
        p = self._prog(u.get("id")) or {"name": u.get("name", "program")}
        items = [it for it in u.get("leftovers", []) if it.get("checked")]
        session = cleaner.new_session()
        u["stage"] = "removing"
        self.changed.emit()

        def done(res):
            u["result"] = res
            u["stage"] = "done"
            self._after_uninstall(p)
            self.changed.emit()
            self._set_status(self.i18n.t("un.done.text", res.get("removed", 0), self.i18n.size(res.get("freed", 0))))

        self._run(lambda: U.remove_leftovers(items, session, p["name"]), done, self.i18n.t("common.working"))

    def _after_uninstall(self, p):
        if not P.IS_WINDOWS or not U.still_installed(p):
            self.programs = [x for x in self.programs if x["id"] != p.get("id")]
        self.quarantine = cleaner.sessions()
        self.reg_backups = extras.reg_backups()
        self.startup = tweaks.startup_entries() if P.IS_WINDOWS else self.startup

    @Slot()
    def closeUninstall(self):
        self._un = {}
        self.changed.emit()

    # ---------- program updates (winget) ----------
    def _pu_conf(self) -> dict:
        conf = self.settings.setdefault("progUpdates", {"auto": False, "skip": [], "lastCheck": ""})
        conf.setdefault("trust", [])
        return conf

    def _pu_due(self) -> bool:
        try:
            return (datetime.now() - datetime.fromisoformat(self._pu_conf().get("lastCheck", ""))).total_seconds() > 20 * 3600
        except Exception:
            return True

    def _pu_open(self) -> list[dict]:
        """Updates still to do: not skipped by the user and not installed yet."""
        skip = set(self._pu_conf().get("skip", []))
        return [it for it in self._pu_items if it["id"] not in skip and it.get("state") != "ok"]

    def _pu_safe(self) -> list[dict]:
        """Open updates that surely belong to the installed program (no fork or look-alike from the catalogue)."""
        return [it for it in self._pu_open() if not it.get("suspect")]

    @staticmethod
    def _major(v: str) -> str:
        m = re.search(r"\d+", v or "")
        return m.group(0) if m else ""

    def _wg_running(self) -> bool:
        return bool(self._pu["running"] or self._ins["running"])

    @Property("QVariantMap", notify=updatesChanged)
    def programUpdates(self):
        skip = set(self._pu_conf().get("skip", []))
        items = [{k: v for k, v in it.items() if not k.startswith("_")} for it in self._pu_items if it["id"] not in skip]
        open_ = [it for it in items if it.get("state") != "ok"]
        safe = sum(1 for it in open_ if not it.get("suspect"))
        return dict(self._pu, items=items, count=safe, safe=safe, suspects=len(open_) - safe,
                    picked=sum(1 for it in open_ if it.get("picked")), skipped=len(skip), auto=bool(self._pu_conf().get("auto")),
                    busy=self._wg_running())

    @Slot()
    def scanUpdates(self):
        self._scan_updates()

    def _pu_stage(self, stage: str, done: int, total: int) -> None:
        """Worker thread: which step of the check is running, for the progress bar."""
        import time
        self._pu.update(stage=stage, sdone=done, stotal=total)
        now = time.monotonic()
        if stage != self._pu.get("_lastStage") or now - self._pu.get("_emit", 0.0) > 0.15:
            self._pu["_lastStage"], self._pu["_emit"] = stage, now
            self.updatesChanged.emit()

    def _scan_updates(self, quiet: bool = False):
        if self._pu["checking"] or self._wg_running():
            return
        self._pu.update(checking=True, stage="list", sdone=0, stotal=0, eta=float(self._pu_conf().get("listSecs", 12) or 12))
        self.updatesChanged.emit()
        if not quiet:
            self._set_status(self.i18n.t("pu.checking"))
        progs = list(self.programs)

        def work():
            return UPD.scan(progress=self._pu_stage, programs=progs or U.list_programs())

        def done(res):
            old = {it["id"]: it for it in self._pu_items}
            trust = set(self._pu_conf().get("trust", []))
            for it in res["items"]:
                if it["id"] in trust:
                    it["suspect"] = False
                if it.get("suspect"):
                    it["title"] = it.get("installedName") or it["name"]     # show what is installed, not the catalogue's name
                arp = it.get("_arp")
                path = U.uninstall_icon_key(arp) if arp and P.IS_WINDOWS else (it.get("_store") or {}).get("icon", "")
                it["icon"] = ("image://appicon/" + quote(path, safe="")) if path else ""
                major = self._major(it.get("current") or it["version"]) != self._major(it["available"])
                keep = old[it["id"]]["picked"] if it["id"] in old else False      # nothing is ticked by itself
                it.update(major=major, state="", reason="", code="", now="", picked=bool(keep) and not it.get("suspect"))
            self._pu_items = res["items"]
            self._pu.update(checking=False, checked=True, winget=res["winget"], when=datetime.now().strftime("%H:%M"), stage="")
            conf = self._pu_conf()
            conf["lastCheck"] = datetime.now().isoformat(timespec="seconds")
            if res.get("listSecs"):
                conf["listSecs"] = res["listSecs"]
            P.save_settings(self.settings)
            self._compute_health()
            self.updatesChanged.emit()
            self.changed.emit()
            n = len(self._pu_safe())
            if not quiet:
                self._set_status(self.i18n.t("pu.found", n) if n else self.i18n.t("pu.none") if res["winget"] else self.i18n.t("pu.nowinget.short"))
            if self._pu_pending:
                want, self._pu_pending = set(self._pu_pending), []
                for it in self._pu_items:
                    it["picked"] = it["id"] in want
                self.installUpdates()

        def failed(e):
            self._pu.update(checking=False, stage="")
            self.updatesChanged.emit()
            if not quiet:
                self._set_status(self._err_text(e))

        self._bg(work, done, failed)

    @Slot(str, bool)
    def setUpdatePick(self, pid, on):
        for it in self._pu_items:
            if it["id"] == pid and not it.get("suspect"):
                it["picked"] = on
        self.updatesChanged.emit()

    @Slot(bool)
    def setAllUpdatePicks(self, on):
        self.pickUpdates("all" if on else "none")

    @Slot(str)
    def pickUpdates(self, mode):
        """Quick selection: "all", "none" or "minor" (everything except major upgrades). Look-alikes are never picked."""
        if self._pu["running"]:
            return
        for it in self._pu_open():
            it["picked"] = not it.get("suspect") and (mode == "all" or (mode == "minor" and not it.get("major")))
        self.updatesChanged.emit()

    @Slot(str)
    def trustUpdate(self, pid):
        """The user says the catalogue entry is the same program after all."""
        conf = self._pu_conf()
        if pid not in conf["trust"]:
            conf["trust"].append(pid)
        P.save_settings(self.settings)
        for it in self._pu_items:
            if it["id"] == pid:
                it.update(suspect=False, why="")
        self.updatesChanged.emit()

    @Slot(str)
    def skipUpdate(self, pid):
        conf = self._pu_conf()
        if pid not in conf["skip"]:
            conf["skip"].append(pid)
        P.save_settings(self.settings)
        self._compute_health()
        self.updatesChanged.emit()
        self.changed.emit()

    @Slot()
    def resetSkipped(self):
        self._pu_conf()["skip"] = []
        P.save_settings(self.settings)
        self._compute_health()
        self.updatesChanged.emit()
        self.changed.emit()

    @Slot(bool)
    def setUpdatesAuto(self, on):
        self._pu_conf()["auto"] = on
        P.save_settings(self.settings)
        self.updatesChanged.emit()

    @Slot()
    def installUpdates(self):
        self._install_updates([it for it in self._pu_safe() if it.get("picked")])

    @Slot()
    def installAllUpdates(self):
        todo = self._pu_safe()
        for it in todo:
            it["picked"] = True
        self._install_updates(todo)

    @Slot(str)
    def updateOne(self, pid):
        self._install_updates([it for it in self._pu_safe() if it["id"] == pid])

    def _q_progress(self, st: dict, sig, it: dict, phase: str, got: float, total: float) -> None:
        """Worker thread: live download numbers for one row and the overall bar, at most five redraws a second."""
        import time
        now = time.monotonic()
        last_t, last_got = it.get("_t", 0.0), it.get("_g", 0.0)
        if last_t and now > last_t and got >= last_got and total != 100.0:
            inst = (got - last_got) / (now - last_t)
            it["speed"] = inst if not it.get("speed") else it["speed"] * 0.6 + inst * 0.4
        it.update(_t=now, _g=got)
        changed = phase != it.get("phase")
        if changed and phase == "install":
            it["installFrom"] = time.time() * 1000.0
        it.update(phase=phase, got=float(got), total=float(total))
        st["frac"] = 0.03 if phase == "prepare" else 0.85 if phase == "install" else 0.03 + 0.82 * (got / total if total else 0.0)
        if changed or now - it.get("_emit", 0.0) > 0.2:
            it["_emit"] = now
            sig.emit()

    @Slot()
    def cancelUpdates(self):
        self._pu_cancel = True
        self._set_status(self.i18n.t("pu.stopping"))

    def _install_updates(self, todo: list[dict]):
        """One package after another: winget downloads it from the vendor, checks the SHA-256, installs silently."""
        if not todo or self._wg_running() or self._busy:
            return
        if self._need_admin("progupdates:" + "|".join(it["id"] for it in todo) + ":1", "apps"):
            return
        for n, it in enumerate(todo):
            it.update(state="queued", queue=n + 1, reason="", code="", now="")
        self._pu.update(running=True, done=0, total=len(todo), current="", frac=0.0)
        self._pu_cancel = False
        self.updatesChanged.emit()

        def still_there(it):
            arp = it.get("_arp")
            return (lambda: U.still_installed(arp)) if arp and P.IS_WINDOWS else (lambda: not P.IS_WINDOWS)

        def work():
            import time
            self._restore_point("update programs")
            ok = 0
            for n, it in enumerate(todo):
                if self._pu_cancel:
                    it["state"] = ""
                    continue
                it.update(state="working", phase="prepare", got=0.0, total=0.0, speed=0.0, startedAt=time.time() * 1000.0, installFrom=0.0)
                self._pu.update(current=it.get("title") or it["name"], done=n, frac=0.0)
                self.updatesChanged.emit()
                r = UPD.upgrade(it["id"], progress=lambda ph, got, total, it=it: self._q_progress(self._pu, self.updatesChanged, it, ph, got, total),
                                before=it.get("version", ""), over=still_there(it), target=it.get("available", ""))
                reason = r["reason"]
                if reason in ("nochange", "inuse") and UPD.is_running(it):
                    reason = "running"           # the program was open, so its installer could not replace it
                state = "warn" if reason in ("nochange", "running") else "ok" if r["ok"] else "failed"
                it.update(state=state, reason=reason, code=f"{r['code']:#x}" if r["code"] else "", now=r.get("after", ""),
                          route=r.get("route", ""), picked=state != "ok" and it.get("picked", False), running=reason == "running")
                ok += state == "ok"
                self._pu.update(done=n + 1, frac=0.0)
                self.updatesChanged.emit()
            return ok

        def done(ok):
            self._pu.update(running=False, current="", done=len(todo), frac=0.0)
            msg = self.i18n.t("pu.done", ok, len(todo))
            if any(it.get("reason") == "reboot" for it in todo):
                msg += ". " + self.i18n.t("pu.r.reboot")
            self._set_status(msg)
            self.toast.emit(msg)
            self._compute_health()
            self.updatesChanged.emit()
            self.changed.emit()
            self._bg(self._load_programs, lambda progs: (setattr(self, "programs", progs), self.changed.emit()))   # new versions in the list

        def failed(e):
            self._pu.update(running=False, current="")
            for it in todo:
                if it.get("state") in ("queued", "working"):
                    it["state"] = ""
            self.updatesChanged.emit()

        self._run(work, done, self.i18n.t("pu.installing"), failed)

    # what changed in a new version: release notes from the catalogue, shown in a window
    @Property("QVariantMap", notify=updatesChanged)
    def releaseNotes(self):
        return self._notes

    @Slot(str)
    def showNotes(self, pid):
        it = next((x for x in self._pu_items if x["id"] == pid), None)
        if it:
            self._notes = {"title": it.get("title") or it["name"], "version": it.get("available", ""), "text": it.get("notes", ""),
                           "url": it.get("notesUrl") or it.get("homepage", "")}
            self.updatesChanged.emit()

    @Slot()
    def closeNotes(self):
        self._notes = {}
        self.updatesChanged.emit()

    # ---------- installing programs (winget) ----------
    def _ins_item(self, pid: str, name: str = "", version: str = "") -> dict:
        it = self._ins_state.setdefault(pid, {"id": pid, "picked": False, "state": "", "reason": "", "code": ""})
        if name:
            it["name"] = name
        if version:
            it["version"] = version
        return it

    def _ins_row(self, pid: str, name: str, cat: str = "") -> dict:
        it = self._ins_item(pid, name)
        k = CAT.key(pid)
        installed = pid in self._ins_installed or it.get("state") == "ok"
        return {"id": pid, "name": name, "cat": cat, "desc": self.i18n.t("ins.d." + k) if cat else pid,
                "version": it.get("version", ""), "installed": installed, "picked": bool(it.get("picked")) and not installed,
                "state": it.get("state", ""), "reason": it.get("reason", ""), "code": it.get("code", ""), "queue": it.get("queue", 0),
                "phase": it.get("phase", ""), "got": float(it.get("got", 0.0)), "total": float(it.get("total", 0.0)), "speed": float(it.get("speed", 0.0)),
                "installFrom": float(it.get("installFrom", 0.0)), "icon": self._ins_icon(name) if installed else ""}

    def _ins_icon(self, name: str) -> str:
        n = re.sub(r"[^a-z0-9]+", "", name.lower())
        if not n or not P.IS_WINDOWS:
            return ""
        hit = next((p for p in self.programs if re.sub(r"[^a-z0-9]+", "", p["name"].lower()).startswith(n)), None)
        path = U.uninstall_icon_key(hit) if hit else ""
        return ("image://appicon/" + quote(path, safe="")) if path else ""

    @Property("QVariantMap", notify=installChanged)
    def installData(self):
        cats = []
        for cat, icon in CAT.CATEGORIES:
            items = [self._ins_row(pid, name, cat) for pid, name, c in CAT.PROGRAMS if c == cat]
            cats.append({"key": cat, "icon": icon, "title": self.i18n.t("ins.cat." + cat), "items": items})
        results = [self._ins_row(r["id"], r["name"]) | {"version": r.get("version", "")} for r in self._ins_results]
        picked = [it for it in self._ins_state.values() if it.get("picked") and it["id"] not in self._ins_installed and it.get("state") != "ok"]
        return dict({k: v for k, v in self._ins.items() if not k.startswith("_")}, cats=cats, results=results, picked=len(picked),
                    presets=[{"key": k, "title": self.i18n.t("ins.preset." + k), "count": len(v)} for k, v in CAT.PRESETS.items()],
                    busy=self._wg_running(), winget=self._winget_ok())

    def _winget_ok(self) -> bool:
        if getattr(self, "_wg_ok", None) is None:
            self._wg_ok = UPD.available()
        return self._wg_ok

    @Slot()
    def loadInstall(self):
        """Which of the picks are already on this PC (winget's own list)."""
        if self._ins["loading"]:
            return
        self._ins["loading"] = True
        self.installChanged.emit()

        def done(ids):
            self._ins_installed = set(ids)
            self._ins.update(loading=False, loaded=True)
            self.installChanged.emit()

        def failed(e):
            self._ins.update(loading=False, loaded=True)
            self.installChanged.emit()

        self._bg(UPD.installed_ids, done, failed)

    @Slot(str, bool)
    def setInstallPick(self, pid, on):
        if self._ins["running"]:
            return
        name = next((n for i, n, _ in CAT.PROGRAMS if i == pid), "") or next((r["name"] for r in self._ins_results if r["id"] == pid), pid)
        self._ins_item(pid, name)["picked"] = on
        self.installChanged.emit()

    @Slot(str)
    def pickPreset(self, key):
        if self._ins["running"]:
            return
        names = {i: n for i, n, _ in CAT.PROGRAMS}
        for pid in CAT.PRESETS.get(key, []):
            if pid not in self._ins_installed:
                self._ins_item(pid, names.get(pid, pid))["picked"] = True
        self.installChanged.emit()

    @Slot()
    def clearInstallPicks(self):
        if self._ins["running"]:
            return
        for it in self._ins_state.values():
            it["picked"] = False
        self.installChanged.emit()

    @Slot(str)
    def searchCatalog(self, query):
        q = (query or "").strip()
        if not q:
            self._ins_results = []
            self._ins.update(query="", searched=False)
            self.installChanged.emit()
            return
        if self._ins["searching"]:
            return
        self._ins.update(searching=True, query=q)
        self.installChanged.emit()

        def done(rows):
            self._ins_results = rows
            for r in rows:
                self._ins_item(r["id"], r["name"], r.get("version", ""))
            self._ins.update(searching=False, searched=True)
            self.installChanged.emit()

        def failed(e):
            self._ins.update(searching=False, searched=True)
            self._ins_results = []
            self.installChanged.emit()

        self._bg(lambda: UPD.search(q), done, failed)

    @Slot()
    def installPicked(self):
        todo = [it for it in self._ins_state.values() if it.get("picked") and it["id"] not in self._ins_installed and it.get("state") != "ok"]
        order = {p[0]: n for n, p in enumerate(CAT.PROGRAMS)}
        todo.sort(key=lambda it: order.get(it["id"], 999))
        self._install_programs(todo)

    @Slot(str)
    def installOne(self, pid):
        name = next((n for i, n, _ in CAT.PROGRAMS if i == pid), "") or next((r["name"] for r in self._ins_results if r["id"] == pid), pid)
        self._install_programs([self._ins_item(pid, name)])

    @Slot()
    def cancelInstall(self):
        self._ins_cancel = True
        self._set_status(self.i18n.t("pu.stopping"))

    def _install_programs(self, todo: list[dict]):
        if not todo or self._wg_running() or self._busy:
            return
        if self._need_admin("proginstall:" + "|".join(it["id"] for it in todo) + ":1", "apps"):
            return
        for n, it in enumerate(todo):
            it.update(state="queued", queue=n + 1, reason="", code="")
        self._ins.update(running=True, done=0, total=len(todo), current="", frac=0.0)
        self._ins_cancel = False
        self.installChanged.emit()

        def work():
            import time
            self._restore_point("install programs")
            ok = 0
            for n, it in enumerate(todo):
                if self._ins_cancel:
                    it["state"] = ""
                    continue
                it.update(state="working", phase="prepare", got=0.0, total=0.0, speed=0.0, startedAt=time.time() * 1000.0, installFrom=0.0)
                self._ins.update(current=it.get("name") or it["id"], done=n, frac=0.0)
                self.installChanged.emit()
                r = UPD.install(it["id"], progress=lambda ph, got, total, it=it: self._q_progress(self._ins, self.installChanged, it, ph, got, total))
                it.update(state="ok" if r["ok"] else "failed", reason=r["reason"], code=f"{r['code']:#x}" if r["code"] else "", picked=False)
                if r["ok"]:
                    self._ins_installed.add(it["id"])
                ok += bool(r["ok"])
                self._ins.update(done=n + 1, frac=0.0)
                self.installChanged.emit()
            return ok

        def done(ok):
            self._ins.update(running=False, current="", done=len(todo), frac=0.0)
            msg = self.i18n.t("ins.done", ok, len(todo))
            if any(it.get("reason") == "reboot" for it in todo):
                msg += ". " + self.i18n.t("pu.r.reboot")
            self._set_status(msg)
            self.toast.emit(msg)
            self.installChanged.emit()
            self._bg(self._load_programs, lambda progs: (setattr(self, "programs", progs), self.changed.emit(), self.installChanged.emit()))

        def failed(e):
            self._ins.update(running=False, current="")
            for it in todo:
                if it.get("state") in ("queued", "working"):
                    it["state"] = ""
            self.installChanged.emit()

        self._run(work, done, self.i18n.t("ins.installing"), failed)

    @Slot()
    def openStore(self):
        if P.IS_WINDOWS:
            os.startfile("ms-windows-store://home")  # type: ignore[attr-defined]

    # ---------- system ----------
    def _system_rows(self):
        i = self.sysinfo
        if not i:
            return []
        t, sz = self.i18n.t, self.i18n.size
        rows = [{"section": t("sys.os"), "items": [["Windows", i.get("os", "")], [t("sys.computer").capitalize(), i.get("pc", "")], [t("sys.uptime"), self._uptime()]]}]
        rows.append({"section": t("sys.cpu"), "items": [["", i.get("cpu", "")], ["", t("sys.cores", i.get('cores', 0), i.get('threads', 0)) + f"  ·  {i.get('mhz', 0)} " + t("u.mhz")]]})
        rows.append({"section": t("sys.gpu"), "items": [[g.get("name", ""), (sz(g["ram"]) + "  ·  " if g.get("ram") else "") + (t("sys.driver", g["driver"]) if g.get("driver") else "")] for g in i.get("gpu", [])]})
        rows.append({"section": t("sys.board"), "items": [["", i.get("board", "")], ["BIOS", i.get("bios", "")]]})
        mods = [[m.get("slot", ""), f"{sz(m['size'])}  ·  {m.get('speed', '')} " + t("u.mhz") + f"  ·  {m.get('maker', '')}"] for m in i.get("mods", [])]
        rows.append({"section": t("sys.ram"), "items": [["", f"{sz(i.get('ram_total', 0))}  ·  {t('common.free')} {sz(i.get('ram_free', 0))}"]] + mods})
        rows.append({"section": t("sys.disks"), "items": [[d.get("name", ""), f"{sz(d['size'])}  ·  {d.get('media', '')}  ·  {d.get('bus', '')}"] for d in i.get("disks", [])]})
        temps = i.get("temps") or []
        rows.append({"section": t("sys.temp"), "items": [["", ", ".join(f"{x} °C" for x in temps) if temps else t("sys.temp.na")]]})
        return rows

    def _uptime(self):
        s = int(self.sysinfo.get("uptime", 0))
        return self.i18n.t("u.days", s // 86400, (s % 86400) // 3600, (s % 3600) // 60)

    @Slot()
    def collectSystem(self):
        def done(info):
            self.sysinfo = info
            self.profile = extras.pc_profile(info)
            self.changed.emit()
            self._set_status(self.i18n.t("common.done"))

        self._run(extras.system_info, done, self.i18n.t("common.working"))

    @Slot(result=str)
    def systemText(self):
        lines = []
        for sec in self._system_rows():
            lines.append(f"[{sec['section']}]")
            for k, v in sec["items"]:
                lines.append(f"{k}: {v}" if k else str(v))
        return "\n".join(lines)

    @Slot(str)
    def copyText(self, text):
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(text)
        self._set_status(self.i18n.t("common.copied"))

    # ---------- quarantine ----------
    @Slot(str)
    def restore(self, path):
        def work():
            if not P.IS_WINDOWS and path.startswith("demo"):
                return 1
            return cleaner.restore(path)

        def done(n):
            self.quarantine = [s for s in self.quarantine if s["path"] != path] if not P.IS_WINDOWS else cleaner.sessions()
            self.changed.emit()
            self._set_status(self.i18n.t("q.restored", n))

        self._run(work, done, self.i18n.t("common.working"))

    @Slot()
    def purge(self):
        def done(_):
            self.quarantine = [] if not P.IS_WINDOWS else cleaner.sessions()
            self.changed.emit()
            self._set_status(self.i18n.t("common.done"))

        self._run(lambda: cleaner.purge() if P.IS_WINDOWS else True, done)

    # ---------- settings / updates ----------
    @Slot(str)
    def setLang(self, lang):
        self.i18n = I18n(lang)
        self.settings["lang"] = lang
        P.save_settings(self.settings)
        by_name = {x.name: x for x in tweaks.SERVICES}
        for s in self.services:
            svc = by_name.get(s["name"])
            if svc:
                s["title"], s["hint"] = self._loc(svc.title), self._loc(svc.hint)
        self._compute_health()
        self.langChanged.emit()
        self.changed.emit()
        self._set_status(self.i18n.t("common.ready"))

    @Slot(str)
    def setTheme(self, theme):
        self.settings["theme"] = theme
        P.save_settings(self.settings)
        self.langChanged.emit()

    @Slot(str)
    def setAccent(self, accent):
        self.settings["accent"] = accent
        P.save_settings(self.settings)
        self.langChanged.emit()

    @Slot(bool)
    def setAnimations(self, on):
        self.settings["animations"] = on
        P.save_settings(self.settings)
        self.langChanged.emit()

    def _fetch_release(self) -> dict:
        import json
        import urllib.request
        req = urllib.request.Request(f"https://api.github.com/repos/{P.UPDATE_REPO}/releases/latest", headers={"User-Agent": f"Sweep/{P.APP_VERSION}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rel = json.loads(r.read().decode("utf-8"))
        tag = rel.get("tag_name", "").lstrip("v")
        asset = next((a for a in rel.get("assets", []) if a["name"].startswith("Sweep-Setup") and a["name"].endswith(".exe")), None)
        return {"tag": tag, "url": asset["browser_download_url"] if asset else "", "newer": self._newer(tag, P.APP_VERSION),
                "notes": changelog_notes(rel.get("body") or "")}

    @Slot()
    def checkUpdates(self):
        work = self._fetch_release

        def done(info):
            self.update_info = info
            self.changed.emit()
            self._set_status(self.i18n.t("set.available", info["tag"]) if info["newer"] else self.i18n.t("set.latest", P.APP_VERSION))
            if info["newer"] and info.get("url"):
                self._offer_update(info)

        self._run(work, done, self.i18n.t("common.working"))

    @staticmethod
    def _newer(a: str, b: str) -> bool:
        def v(s):
            return tuple(int(x) for x in "".join(ch if ch.isdigit() or ch == "." else "" for ch in s).split(".") if x)
        try:
            return v(a) > v(b)
        except Exception:
            return False

    @Slot()
    def installUpdate(self):
        info = self.update_info
        if not info or not info.get("url"):
            return

        def work():
            import tempfile
            import urllib.request
            dst = os.path.join(tempfile.gettempdir(), f"Sweep-Setup-{info['tag']}.exe")
            urllib.request.urlretrieve(info["url"], dst)
            if P.IS_WINDOWS:
                import subprocess
                subprocess.Popen([dst, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RELAUNCH=1"])
            return dst

        def done(_):
            from PySide6.QtWidgets import QApplication
            QApplication.quit()

        self._run(work, done, self.i18n.t("set.downloading", info["tag"]))

    @Slot()
    def openLog(self):
        """Open ProgramData\\Sweep\\log.txt in Notepad (the folder is hidden, people cannot find it)."""
        if not P.LOG_FILE.exists():
            P.log("log opened")
        if P.IS_WINDOWS:
            import subprocess
            subprocess.Popen(["notepad.exe", str(P.LOG_FILE)])
        else:
            self._set_status(str(P.LOG_FILE))

    @Slot(str)
    def openUrl(self, url):
        QDesktopServices.openUrl(QUrl(url))
