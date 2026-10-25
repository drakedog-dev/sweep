"""Two-language UI strings. Keys are stable English identifiers; values per language."""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # navigation
    "nav.overview": {"ru": "Обзор", "en": "Overview"},
    "nav.junk": {"ru": "Мусор", "en": "Junk"},
    "nav.privacy": {"ru": "Приватность", "en": "Privacy"},
    "nav.registry": {"ru": "Реестр", "en": "Registry"},
    "nav.services": {"ru": "Службы", "en": "Services"},
    "nav.startup": {"ru": "Автозагрузка", "en": "Startup"},
    "nav.boost": {"ru": "Ускорение", "en": "Boost"},
    "nav.disks": {"ru": "Диски", "en": "Disks"},
    "nav.apps": {"ru": "Приложения", "en": "Apps"},
    "nav.system": {"ru": "Система", "en": "System"},
    "nav.quarantine": {"ru": "Карантин", "en": "Quarantine"},
    "nav.settings": {"ru": "Настройки", "en": "Settings"},
    # headers
    "hdr.overview": {"ru": "Состояние компьютера одним взглядом", "en": "Your PC at a glance"},
    "hdr.junk": {"ru": "Ничего не удаляется безвозвратно: всё попадает в карантин", "en": "Nothing is deleted for good: everything goes to quarantine"},
    "hdr.privacy": {"ru": "Телеметрия, реклама и сбор данных под вашим контролем", "en": "Telemetry, ads and data collection under your control"},
    "hdr.registry": {"ru": "Безопасная чистка с резервной копией каждой ветки", "en": "Safe cleaning with a backup of every key"},
    "hdr.services": {"ru": "Выключайте лишнее и возвращайте одним движением", "en": "Turn off what you do not need, flip it back any time"},
    "hdr.startup": {"ru": "Что запускается вместе с Windows", "en": "What launches with Windows"},
    "hdr.boost": {"ru": "Память, диски, эффекты и расписание", "en": "Memory, drives, effects and schedule"},
    "hdr.disks": {"ru": "Что занимает место на каждом диске", "en": "What takes up space on each drive"},
    "hdr.apps": {"ru": "Предустановленный мусор Windows", "en": "Pre-installed Windows bloat"},
    "hdr.system": {"ru": "Железо и Windows на одном экране", "en": "Hardware and Windows on one screen"},
    "hdr.quarantine": {"ru": "Всё, что убрано, можно вернуть", "en": "Everything removed can be restored"},
    "hdr.settings": {"ru": "Язык, тема, обновления, о программе", "en": "Language, theme, updates, about"},
    # common
    "common.scan": {"ru": "Проверить", "en": "Scan"},
    "common.rescan": {"ru": "Проверить заново", "en": "Scan again"},
    "common.clean": {"ru": "Очистить", "en": "Clean"},
    "common.restore": {"ru": "Вернуть", "en": "Restore"},
    "common.cancel": {"ru": "Отмена", "en": "Cancel"},
    "common.done": {"ru": "Готово", "en": "Done"},
    "common.copy": {"ru": "Скопировать", "en": "Copy"},
    "common.copied": {"ru": "Скопировано в буфер обмена", "en": "Copied to clipboard"},
    "common.on": {"ru": "Включено", "en": "On"},
    "common.off": {"ru": "Выключено", "en": "Off"},
    "common.canfree": {"ru": "МОЖНО ОСВОБОДИТЬ", "en": "CAN BE FREED"},
    "common.free": {"ru": "свободно", "en": "free"},
    "common.of": {"ru": "из", "en": "of"},
    "common.working": {"ru": "Работаю…", "en": "Working…"},
    "common.ready": {"ru": "Готово к работе", "en": "Ready"},
    "common.error": {"ru": "Ошибка: {0}", "en": "Error: {0}"},
    "common.demo": {"ru": "Демо-режим: данные условные, система не меняется", "en": "Demo mode: sample data, nothing is changed"},
    # overview
    "ov.health": {"ru": "Индекс здоровья", "en": "Health index"},
    "ov.health.good": {"ru": "Компьютер в хорошей форме", "en": "Your PC is in good shape"},
    "ov.health.mid": {"ru": "Есть что улучшить", "en": "Room for improvement"},
    "ov.health.bad": {"ru": "Компьютеру нужна забота", "en": "Your PC needs some care"},
    "ov.health.hint": {"ru": "Считается по мусору, автозагрузке, свободному месту и настройкам приватности", "en": "Based on junk, startup items, free space and privacy settings"},
    "ov.of100": {"ru": "из 100", "en": "of 100"},
    "ov.quick": {"ru": "Быстрая очистка", "en": "Quick clean"},
    "ov.quick.hint": {"ru": "Временные файлы, кэши и отчёты об ошибках с настройками по умолчанию. Корзина и куки не трогаются.", "en": "Temp files, caches and error reports with default settings. Recycle Bin and cookies are left alone."},
    "ov.quick.btn": {"ru": "Очистить сейчас", "en": "Clean now"},
    "ov.cpu": {"ru": "ПРОЦЕССОР", "en": "CPU"},
    "ov.ram": {"ru": "ПАМЯТЬ", "en": "MEMORY"},
    "ov.disk": {"ru": "ДИСК", "en": "DISK"},
    "ov.junk": {"ru": "МУСОР", "en": "JUNK"},
    "ov.startup": {"ru": "АВТОЗАГРУЗКА", "en": "STARTUP"},
    "ov.startup.sub": {"ru": "программ с Windows", "en": "programs with Windows"},
    "ov.profile": {"ru": "Профиль компьютера", "en": "PC profile"},
    "ov.profile.weak": {"ru": "Слабый компьютер", "en": "Low-end PC"},
    "ov.profile.mid": {"ru": "Средний компьютер", "en": "Mid-range PC"},
    "ov.profile.strong": {"ru": "Мощный компьютер", "en": "High-end PC"},
    "ov.profile.weak.hint": {"ru": "Рекомендуем всё: службы, эффекты, автозагрузку, индексирование. Каждая мелочь даёт ощутимый прирост.", "en": "We recommend everything: services, effects, startup, indexing. Every bit counts here."},
    "ov.profile.mid.hint": {"ru": "Стоит почистить мусор и автозагрузку, выключить лишние службы. Эффекты Windows можно оставить.", "en": "Clean junk and startup, turn off spare services. Windows effects can stay."},
    "ov.profile.strong.hint": {"ru": "Ресурсов хватает: службы и эффекты не трогаем, достаточно мусора и приватности.", "en": "Plenty of resources: leave services and effects alone, junk and privacy are enough."},
    "ov.recommend": {"ru": "Рекомендуем для вашего компьютера", "en": "Recommended for your PC"},
    "ov.apply": {"ru": "Применить рекомендации", "en": "Apply recommendations"},
    "ov.tip.junk": {"ru": "Много мусора: запустите очистку", "en": "Lots of junk: run a clean"},
    "ov.tip.junk2": {"ru": "Есть что почистить", "en": "Some junk to clean"},
    "ov.tip.startup": {"ru": "Автозагрузка перегружена: {0} программ", "en": "Startup is overloaded: {0} programs"},
    "ov.tip.startup2": {"ru": "В автозагрузке {0} программ, часть можно выключить", "en": "{0} programs in startup, some can be turned off"},
    "ov.tip.disk": {"ru": "На системном диске почти нет места", "en": "System drive is almost full"},
    "ov.tip.disk2": {"ru": "На системном диске мало места", "en": "System drive is low on space"},
    "ov.tip.privacy": {"ru": "Слежка и реклама Windows включены", "en": "Windows tracking and ads are on"},
    "ov.tip.privacy2": {"ru": "Часть телеметрии ещё включена", "en": "Some telemetry is still on"},
    "ov.tip.uptime": {"ru": "Компьютер не перезагружался {0} дней", "en": "PC has not been restarted for {0} days"},
    "ov.tip.ok": {"ru": "Всё в порядке, так держать", "en": "All good, keep it up"},
    # junk
    "junk.hint": {"ru": "Отметьте, что убрать. Всё, кроме корзины, переносится в карантин, откуда можно вернуть.", "en": "Tick what to remove. Everything except the Recycle Bin goes to quarantine and can be restored."},
    "junk.cleaning": {"ru": "Убираю: {0}", "en": "Removing: {0}"},
    "junk.scanning": {"ru": "Проверяю: {0}", "en": "Checking: {0}"},
    "junk.done": {"ru": "Убрано {0}. Файлы в карантине, занятые программами файлы пропущены.", "en": "Removed {0}. Files are in quarantine, files in use were skipped."},
    "junk.scanned": {"ru": "Проверка закончена: можно освободить {0}", "en": "Scan finished: {0} can be freed"},
    # privacy
    "priv.hint": {"ru": "Переключатель включён, значит слежка отключена. Любой пункт возвращается к стандартной настройке. Полностью подействует после перезагрузки.", "en": "Switch on means tracking is disabled. Any item can be reverted. Takes full effect after a restart."},
    "priv.all": {"ru": "Отключить всю слежку", "en": "Disable all tracking"},
    "priv.group.data": {"ru": "Сбор данных", "en": "Data collection"},
    "priv.group.ads": {"ru": "Реклама и подсказки", "en": "Ads and suggestions"},
    "priv.group.assist": {"ru": "Помощники Microsoft", "en": "Microsoft assistants"},
    "priv.disabled": {"ru": "ОТКЛЮЧЕНО", "en": "DISABLED"},
    # registry
    "reg.hint": {"ru": "Только безопасные разделы. Перед изменением каждая ветка сохраняется в файл .reg и возвращается одной кнопкой.", "en": "Safe keys only. Every key is exported to a .reg file first and can be restored with one click."},
    "reg.backups": {"ru": "Резервные копии", "en": "Backups"},
    "reg.nobackups": {"ru": "Резервных копий пока нет", "en": "No backups yet"},
    "reg.found": {"ru": "НАЙДЕНО ЗАПИСЕЙ", "en": "ENTRIES FOUND"},
    "reg.clean": {"ru": "Очистить реестр", "en": "Clean registry"},
    "reg.backup": {"ru": "Копия от {0}, веток: {1}", "en": "Backup from {0}, keys: {1}"},
    "reg.done": {"ru": "Удалено записей: {0}. Копия сохранена.", "en": "Entries removed: {0}. Backup saved."},
    # services
    "svc.hint": {"ru": "Переключатель включён, значит служба работает. Исходная настройка запоминается, всё обратимо.", "en": "Switch on means the service is running. The original setting is remembered, everything is reversible."},
    "svc.off": {"ru": "ВЫКЛЮЧЕНО", "en": "TURNED OFF"},
    "svc.warn.strong": {"ru": "У вас мощный компьютер: выключать службы не обязательно, прироста почти не будет.", "en": "Your PC is powerful: disabling services is optional, the gain will be small."},
    # startup
    "start.hint": {"ru": "Выключите переключатель, и программа перестанет запускаться вместе с Windows. Ничего не удаляется.", "en": "Turn the switch off and the program stops launching with Windows. Nothing is deleted."},
    "start.empty": {"ru": "В автозагрузке ничего нет", "en": "Nothing in startup"},
    # boost
    "boost.ram": {"ru": "Освободить оперативную память", "en": "Free up RAM"},
    "boost.ram.hint": {"ru": "Просит все программы отдать память, которую они держат про запас", "en": "Asks every program to release memory it holds in reserve"},
    "boost.ram.btn": {"ru": "Освободить", "en": "Free up"},
    "boost.ram.done": {"ru": "Память освобождена, прибавилось {0}", "en": "Memory freed, gained {0}"},
    "boost.disk": {"ru": "Оптимизировать диски", "en": "Optimise drives"},
    "boost.disk.hint": {"ru": "TRIM для SSD, дефрагментация для HDD. Может занять несколько минут", "en": "TRIM for SSD, defragmentation for HDD. May take a few minutes"},
    "boost.disk.btn": {"ru": "Оптимизировать", "en": "Optimise"},
    "boost.fx": {"ru": "Визуальные эффекты Windows", "en": "Windows visual effects"},
    "boost.fx.hint": {"ru": "Анимации окон, тени и прозрачность. На слабых компьютерах их отключение заметно ускоряет работу.", "en": "Window animations, shadows and transparency. Turning them off noticeably speeds up weak PCs."},
    "boost.fx.perf": {"ru": "Быстродействие", "en": "Performance"},
    "boost.fx.balanced": {"ru": "Сбалансированно", "en": "Balanced"},
    "boost.fx.pretty": {"ru": "Красота", "en": "Appearance"},
    "boost.power": {"ru": "Схема электропитания", "en": "Power plan"},
    "boost.power.hint": {"ru": "Максимальная производительность для стационарных ПК, сбалансированная для ноутбуков", "en": "High performance for desktops, balanced for laptops"},
    "boost.power.high": {"ru": "Производительность", "en": "High performance"},
    "boost.power.balanced": {"ru": "Сбалансированная", "en": "Balanced"},
    "boost.sched": {"ru": "Автоочистка по расписанию", "en": "Scheduled auto-clean"},
    "boost.sched.hint": {"ru": "Раз в неделю Sweep сам уберёт мусор с настройками по умолчанию, без окон. Всё попадает в карантин.", "en": "Once a week Sweep removes junk with default settings, silently. Everything goes to quarantine."},
    "boost.sched.next": {"ru": "Следующий запуск: {0}", "en": "Next run: {0}"},
    "boost.update": {"ru": "Обновления Windows", "en": "Windows Update"},
    "boost.update.hint": {"ru": "Обновления закрывают дыры в безопасности и часто исправляют тормоза", "en": "Updates close security holes and often fix slowdowns"},
    "boost.update.btn": {"ru": "Открыть обновления", "en": "Open Windows Update"},
    "boost.freemem": {"ru": "СВОБОДНО ПАМЯТИ", "en": "FREE MEMORY"},
    # disks
    "disk.hint": {"ru": "Sweep проверяет каждый диск на мусор, который можно убрать без раздумий: корзину, временные и недокачанные файлы, старые журналы, служебные файлы эскизов, остатки прошлых установок Windows. Документы, фото и программы не трогаются.", "en": "Sweep checks every drive for junk that is safe to remove: Recycle Bin, temporary and unfinished downloads, old logs, thumbnail leftovers, remains of previous Windows installations. Documents, photos and programs are not touched."},
    "disk.find": {"ru": "Проверить диски", "en": "Scan drives"},
    "disk.toq": {"ru": "Очистить отмеченное", "en": "Clean selected"},
    "disk.notscanned": {"ru": "Ещё не проверялся", "en": "Not scanned yet"},
    "disk.clean": {"ru": "Мусора нет", "en": "No junk"},
    "disk.files": {"ru": "файлов: {0}", "en": "files: {0}"},
    "disk.open": {"ru": "Открыть в Проводнике", "en": "Open in Explorer"},
    "disk.used": {"ru": "занято {0} из {1}", "en": "used {0} of {1}"},
        "disk.scanning": {"ru": "Проверяю диски {0}… На больших дисках это может занять пару минут", "en": "Scanning drives {0}… Large drives may take a couple of minutes"},
    "disk.freeLabel": {"ru": "СВОБОДНО", "en": "FREE"},
    # apps
    "apps.hint": {"ru": "Предустановленные приложения, которые редко кому нужны. Удаление освобождает место и чистит меню Пуск. Вернуть можно из Microsoft Store.", "en": "Pre-installed apps most people never use. Removing them frees space and declutters Start. Reinstall any from Microsoft Store."},
    "apps.remove": {"ru": "Удалить отмеченные", "en": "Remove selected"},
    "apps.store": {"ru": "Открыть Microsoft Store", "en": "Open Microsoft Store"},
    "apps.empty": {"ru": "Лишних предустановленных приложений не найдено", "en": "No bloat apps found"},
    "apps.found": {"ru": "НАЙДЕНО", "en": "FOUND"},
    # system
    "sys.hint": {"ru": "Собирается только по вашему нажатию и никуда не отправляется", "en": "Collected only when you ask, never sent anywhere"},
    "sys.collect": {"ru": "Собрать сведения", "en": "Collect info"},
    "sys.os": {"ru": "Система", "en": "System"}, "sys.cpu": {"ru": "Процессор", "en": "Processor"}, "sys.gpu": {"ru": "Видеокарта", "en": "Graphics"},
    "sys.board": {"ru": "Материнская плата", "en": "Motherboard"}, "sys.ram": {"ru": "Оперативная память", "en": "Memory"}, "sys.disks": {"ru": "Диски", "en": "Disks"},
    "sys.temp": {"ru": "Температура", "en": "Temperature"}, "sys.uptime": {"ru": "Работает без перезагрузки", "en": "Uptime"},
    "sys.temp.na": {"ru": "недоступно без драйвера", "en": "unavailable without a driver"},
    "sys.computer": {"ru": "КОМПЬЮТЕР", "en": "COMPUTER"},
    # quarantine
    "q.hint": {"ru": "Всё, что убрал Sweep, лежит здесь. «Вернуть» ставит файлы на место. Место освобождается окончательно после удаления карантина.", "en": "Everything Sweep removed is kept here. Restore puts files back. Space is freed for good only when you purge."},
    "q.empty": {"ru": "Карантин пуст", "en": "Quarantine is empty"},
    "q.purge": {"ru": "Удалить весь карантин навсегда", "en": "Purge quarantine permanently"},
    "q.purge.confirm": {"ru": "Точно удалить? Нажмите ещё раз", "en": "Really purge? Click again"},
    "q.session": {"ru": "Очистка {0}", "en": "Clean {0}"},
    "q.restored": {"ru": "Возвращено объектов: {0}", "en": "Items restored: {0}"},
    "q.in": {"ru": "В КАРАНТИНЕ", "en": "IN QUARANTINE"},
    # settings
    "set.lang": {"ru": "Язык интерфейса", "en": "Interface language"},
    "set.theme": {"ru": "Тема", "en": "Theme"},
    "set.theme.dark": {"ru": "Тёмная", "en": "Dark"}, "set.theme.light": {"ru": "Светлая", "en": "Light"},
    "set.accent": {"ru": "Акцентный цвет", "en": "Accent colour"},
    "set.anim": {"ru": "Анимации интерфейса", "en": "Interface animations"},
    "set.renderer": {"ru": "Отрисовка интерфейса", "en": "Interface rendering"},
    "set.renderer.hint": {"ru": "Если курсор мыши подёргивается, пока открыт Sweep, выберите «Процессор»: видеокарта тогда не используется вовсе. Применяется после перезапуска.", "en": "If the mouse cursor stutters while Sweep is open, choose CPU: the graphics card is not used at all. Applies after a restart."},
    "set.renderer.gpu": {"ru": "Видеокарта", "en": "Graphics card"},
    "set.renderer.cpu": {"ru": "Процессор", "en": "CPU"},
    "set.renderer.restart": {"ru": "Режим отрисовки сохранён, подействует после перезапуска", "en": "Rendering mode saved, applies after a restart"},
    "set.restart": {"ru": "Перезапустить сейчас", "en": "Restart now"},
    "set.updates": {"ru": "Обновления", "en": "Updates"},
    "set.check": {"ru": "Проверить обновления", "en": "Check for updates"},
    "set.latest": {"ru": "У вас последняя версия ({0})", "en": "You have the latest version ({0})"},
    "set.available": {"ru": "Доступна версия {0}", "en": "Version {0} is available"},
    "set.install": {"ru": "Обновить до {0}", "en": "Update to {0}"},
    "set.downloading": {"ru": "Скачиваю {0}…", "en": "Downloading {0}…"},
    "set.about": {"ru": "Sweep не выходит в интернет, кроме проверки обновлений по вашему нажатию. Открытый код: github.com/pabloescobarbl-ops/sweep", "en": "Sweep stays offline except for update checks you start. Open source: github.com/pabloescobarbl-ops/sweep"},
    "set.version": {"ru": "Версия", "en": "Version"},
    # about
    "about.title": {"ru": "О программе", "en": "About"},
    "about.text": {"ru": "Sweep бесплатна и распространяется с открытым исходным кодом по лицензии MIT. Весь код лежит на GitHub: любой может прочитать его, проверить и предложить улучшения. Программа не выходит в интернет, кроме проверки обновлений по вашему нажатию, и не собирает никаких данных.", "en": "Sweep is free and open source under the MIT licence. All the code is on GitHub: anyone can read it, verify it and suggest improvements. The app stays offline except for update checks you start, and collects no data."},
    "about.star": {"ru": "Если Sweep вам полезен, поставьте звёздочку на GitHub: это лучшая благодарность автору и помогает другим найти программу.", "en": "If Sweep is useful to you, star it on GitHub: it is the best thanks to the author and helps others find it."},
    "about.star.btn": {"ru": "Поставить звёздочку", "en": "Star on GitHub"},
    "about.issues": {"ru": "Нашли ошибку или есть идея? Напишите в Issues на GitHub, там же можно посмотреть, что уже в работе.", "en": "Found a bug or have an idea? Open an issue on GitHub, where you can also see what is already in progress."},
    "about.issues.btn": {"ru": "Сообщить об ошибке или предложить", "en": "Report a bug or suggest"},
    "about.source": {"ru": "Исходный код", "en": "Source code"},
    "about.licence": {"ru": "Лицензия MIT", "en": "MIT licence"},
    "about.author": {"ru": "Автор: Alex (Drakedog)", "en": "Author: Alex (Drakedog)"},
    # units
    "u.gb": {"ru": "ГБ", "en": "GB"}, "u.mb": {"ru": "МБ", "en": "MB"}, "u.kb": {"ru": "КБ", "en": "KB"}, "u.b": {"ru": "Б", "en": "B"},
    "u.days": {"ru": "{0} д {1} ч {2} мин", "en": "{0} d {1} h {2} min"},
}


class I18n:
    def __init__(self, lang: str = "ru"):
        self.lang = lang if lang in ("ru", "en") else "ru"

    def t(self, key: str, *args) -> str:
        entry = STRINGS.get(key)
        s = entry.get(self.lang, entry.get("en", key)) if entry else key
        if args:
            try:
                s = s.format(*args)
            except Exception:
                pass
        return s

    def size(self, n: float) -> str:
        n = float(n or 0)
        if n >= 1 << 30:
            return f"{n / (1 << 30):.1f} {self.t('u.gb')}"
        if n >= 1 << 20:
            return f"{n / (1 << 20):.0f} {self.t('u.mb')}"
        if n >= 1 << 10:
            return f"{n / (1 << 10):.0f} {self.t('u.kb')}"
        return f"{int(n)} {self.t('u.b')}"
