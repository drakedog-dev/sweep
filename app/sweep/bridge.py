"""Qt bridge: exposes application state and actions to QML. Long operations run in worker threads."""
from __future__ import annotations

import os
import sys
import threading
import traceback
import webbrowser
from datetime import datetime

from PySide6.QtCore import Property, QObject, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from . import cleaner, extras, platform as P, tweaks
from .i18n import I18n


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:  # noqa: BLE001
            P.log(traceback.format_exc())
            self.failed.emit(str(e))


class App(QObject):
    changed = Signal()            # generic: any list/property changed
    statusChanged = Signal()
    busyChanged = Signal()
    monitorChanged = Signal()
    langChanged = Signal()
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
        self.categories = cleaner.CATEGORIES
        self.checked = {c.id: c.default for c in self.categories}
        self.privacy_state = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
        self.services = []
        self.startup = []
        self.reg_backups = []
        self.volumes = extras.volumes()
        self.selected_drive = extras.system_drive()
        self.drive_junk: dict = {}
        self.drive_checked: dict = {}
        self.apps = []
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

    # ---------- helpers ----------
    @staticmethod
    def _system_is_ru() -> bool:
        try:
            import locale
            loc = locale.getlocale()[0] or ""
            return loc.lower().startswith("ru")
        except Exception:
            return False

    def _run(self, fn, on_done=None, status: str | None = None):
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

        def failed(msg):
            self._set_busy(False)
            self._workers.remove(w)
            self._set_status(self.i18n.t("common.error", msg))

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

    @Property(bool, notify=langChanged)
    def animations(self):
        return bool(self.settings.get("animations", True))

    @Slot(str, result=str)
    def t(self, key):
        return self.i18n.t(key)

    @Slot(str, str, result=str)
    def t1(self, key, a):
        return self.i18n.t(key, a)

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
        return [{"id": p.id, "group": self.i18n.t(groups[p.group]), "name": self._loc(p.name), "hint": self._loc(p.hint), "on": self.privacy_state[p.id]} for p in tweaks.PRIVACY]

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
        return [{"name": e["name"], "command": e.get("command", ""), "source": e.get("source", ""), "enabled": bool(e.get("enabled"))} for e in self.startup]

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
            info = extras.system_info()
            return {"info": info, "services": self._load_services(), "startup": tweaks.startup_entries(), "schedule": tweaks.schedule_state()}

        def done(res):
            self.sysinfo = res["info"]
            self.profile = extras.pc_profile(self.sysinfo)
            self.services = res["services"]
            self.startup = res["startup"]
            self.schedule = res["schedule"]
            self.changed.emit()
            self.scan()

        self._run(work, done)

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
        self.changed.emit()

    @Slot()
    def clean(self):
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
        self.checked = {c.id: c.default for c in self.categories}
        self.changed.emit()
        self.clean()

    # ---------- privacy ----------
    @Slot(str, bool)
    def setPrivacy(self, pid, on):
        p = next(x for x in tweaks.PRIVACY if x.id == pid)
        self.privacy_state[pid] = on
        self.changed.emit()
        self._run(lambda: tweaks.set_privacy(p, on), lambda _: (self._compute_health(), self.changed.emit()))

    @Slot()
    def allPrivacy(self):
        def work():
            for p in tweaks.PRIVACY:
                tweaks.set_privacy(p, True)
                self.privacy_state[p.id] = True
            return True

        self._run(work, lambda _: (self._compute_health(), self.changed.emit(), self._set_status(self.i18n.t("priv.disabled").capitalize())), self.i18n.t("common.working"))

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
        session = cleaner.new_session()
        cats = [c for c in extras.REG_CATEGORIES if c.id in ids]

        def work():
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
        for s in self.services:
            if s["name"] == name:
                s["enabled"] = on
        self.changed.emit()
        self._run(lambda: tweaks.set_service(name, on))

    @Slot(int, bool)
    def setStartup(self, index, on):
        e = self.startup[index]
        e["enabled"] = on
        self.changed.emit()
        self._run(lambda: tweaks.set_startup(e, on), lambda _: (self._compute_health(), self.changed.emit()))

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
        cls = self.profile.get("class", "mid")

        def work():
            for p in tweaks.PRIVACY:
                tweaks.set_privacy(p, True)
                self.privacy_state[p.id] = True
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

        self._run(work, done, self.i18n.t("common.working"))

    # ---------- disks ----------
    @Slot(str)
    def selectDrive(self, letter):
        self.selected_drive = letter
        self.changed.emit()

    @Slot()
    def scanDrives(self):
        letters = [v["letter"] for v in self.volumes]

        def work():
            return {l: extras.drive_junk(l) for l in letters}

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
        ids = set(ids)

        def work():
            for i in ids:
                extras.remove_app(i)
            return len(ids)

        self._run(work, lambda n: (setattr(self, "apps", [a for a in self.apps if a["id"] not in ids]), self.changed.emit(), self._set_status(self.i18n.t("common.done"))), self.i18n.t("common.working"))

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
        rows.append({"section": t("sys.cpu"), "items": [["", i.get("cpu", "")], ["", f"{i.get('cores', 0)} / {i.get('threads', 0)}  ·  {i.get('mhz', 0)} MHz"]]})
        rows.append({"section": t("sys.gpu"), "items": [[g.get("name", ""), (sz(g["ram"]) + "  ·  " if g.get("ram") else "") + str(g.get("driver", ""))] for g in i.get("gpu", [])]})
        rows.append({"section": t("sys.board"), "items": [["", i.get("board", "")], ["BIOS", i.get("bios", "")]]})
        mods = [[m.get("slot", ""), f"{sz(m['size'])}  ·  {m.get('speed', '')} MHz  ·  {m.get('maker', '')}"] for m in i.get("mods", [])]
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

    @Slot()
    def checkUpdates(self):
        def work():
            import json
            import urllib.request
            req = urllib.request.Request(f"https://api.github.com/repos/{P.UPDATE_REPO}/releases/latest", headers={"User-Agent": f"Sweep/{P.APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=20) as r:
                rel = json.loads(r.read().decode("utf-8"))
            tag = rel.get("tag_name", "").lstrip("v")
            asset = next((a for a in rel.get("assets", []) if a["name"].startswith("Sweep-Setup") and a["name"].endswith(".exe")), None)
            return {"tag": tag, "url": asset["browser_download_url"] if asset else "", "newer": self._newer(tag, P.APP_VERSION)}

        def done(info):
            self.update_info = info
            self.changed.emit()
            self._set_status(self.i18n.t("set.available", info["tag"]) if info["newer"] else self.i18n.t("set.latest", P.APP_VERSION))

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
                subprocess.Popen([dst, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])
            return dst

        def done(_):
            from PySide6.QtWidgets import QApplication
            QApplication.quit()

        self._run(work, done, self.i18n.t("set.downloading", info["tag"]))

    @Slot(str)
    def openUrl(self, url):
        QDesktopServices.openUrl(QUrl(url))
