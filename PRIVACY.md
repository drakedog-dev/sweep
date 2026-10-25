# Privacy policy

*Applies to Sweep 1.0.16 and later. Last updated: 25 October 2026.*

**Short version:** Sweep has no accounts, no analytics, no ads and no telemetry. It does not collect, store or send personal data.

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

## Network connections

Sweep makes exactly these connections, and no others:

| When | Who connects | Where | What is sent |
|---|---|---|---|
| On start-up (can be turned off: **Settings → Updates → Do not check**) and when you press **Check for updates** | Sweep | `api.github.com` | A standard request for the latest Sweep release |
| When you agree to install a new Sweep version | Sweep | `github.com` and GitHub's download servers | A download request for the installer |
| When you open **Programs → Updates**, press **Check**, or turn on **Check once a day** | Windows Package Manager (winget), part of Windows | The Microsoft winget catalogue (`cdn.winget.microsoft.com`) | A request for the package catalogue |
| When you choose to update a program | winget | The program vendor's own download address shown next to the program (for example `7-zip.org`) | A download request for that installer |

GitHub, Microsoft and the program vendors receive what any web server receives with a download request, such as your IP address. Their own privacy policies apply to those requests. Sweep adds no identifiers, statistics or information about your computer.

## Data stored on your computer

Everything Sweep keeps stays in `C:\ProgramData\Sweep` and never leaves your PC:

- `settings.json`: your choices (language, theme, ticked categories, Guard settings, hidden program updates);
- `log.txt`: a technical log of actions and errors, which you can open from the app and share yourself if you report a problem;
- `Quarantine` and `RegBackup`: removed files and registry backups, so changes can be undone.

Uninstalling Sweep removes the program and its scheduled tasks. The `ProgramData\Sweep` folder is kept so that quarantined files are not lost; delete it yourself when you no longer need them.

## Contact

Questions about privacy: [open an issue](https://github.com/drakedog-dev/sweep/issues/new/choose).

---

# Политика конфиденциальности

**Коротко:** в Sweep нет аккаунтов, аналитики, рекламы и телеметрии. Программа не собирает, не хранит и не отправляет персональные данные.

Программа не передаёт никакую информацию другим сетевым системам, если об этом специально не попросил пользователь или тот, кто её устанавливает или использует.

## Сетевые подключения

| Когда | Кто подключается | Куда | Что отправляется |
|---|---|---|---|
| При запуске (отключается: **Настройки → Обновления → Не проверять**) и по кнопке **Проверить обновления** | Sweep | `api.github.com` | Обычный запрос последней версии Sweep |
| Когда вы соглашаетесь установить новую версию | Sweep | `github.com` и серверы загрузки GitHub | Запрос на скачивание установщика |
| Когда вы открываете **Программы → Обновления**, нажимаете **Проверить** или включаете **Проверять раз в день** | Менеджер пакетов Windows (winget) | Каталог Microsoft winget (`cdn.winget.microsoft.com`) | Запрос каталога пакетов |
| Когда вы выбираете обновить программу | winget | Адрес производителя, показанный рядом с программой (например `7-zip.org`) | Запрос на скачивание установщика |

GitHub, Microsoft и производители программ получают то же, что любой веб-сервер при скачивании файла, например ваш IP-адрес. Sweep не добавляет никаких идентификаторов, статистики или сведений о компьютере.

## Что хранится на компьютере

Всё лежит в `C:\ProgramData\Sweep` и никуда не уходит: настройки (`settings.json`), технический журнал (`log.txt`), карантин и резервные копии реестра. При удалении Sweep папка остаётся, чтобы не потерять файлы из карантина; её можно удалить вручную.
