#requires -version 5.1
<#
    Sweep 0.8 — чистка, приватность и ускорение Windows.
    Windows 10 и 11. Ничего не отправляет в интернет.
    Правила безопасности:
      1. Файлы не удаляются, а переносятся в карантин, откуда их можно вернуть одной кнопкой.
      2. Любая настройка приватности и любая служба включается обратно той же галочкой.
      3. Документы, фотографии, программы и лицензии не затрагиваются.
    Запуск: Start.bat
#>

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    if ($PSCommandPath) {
        Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`""
    } else {
        # Скомпилированный exe: перезапускаем сам файл с правами администратора
        Start-Process ([System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName) -Verb RunAs
    }
    exit
}

Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
Add-Type -Namespace Sweep -Name Mem -MemberDefinition '[DllImport("psapi.dll")] public static extern bool EmptyWorkingSet(IntPtr hProcess);'

$Root       = Join-Path $env:ProgramData 'Sweep'
$Quarantine = Join-Path $Root 'Quarantine'
$LogFile    = Join-Path $Root 'log.txt'
$SvcBackup  = Join-Path $Root 'services-backup.json'
New-Item -ItemType Directory -Path $Quarantine -Force | Out-Null

# =====================================================================
#  ЯЗЫК. Интерфейс написан по-русски; английский берётся из словаря $EN.
#  Ключи с {0} это шаблоны: совпадение по регулярному выражению, подстановка захваченных частей.
# =====================================================================
$SettingsFile = Join-Path $Root 'settings.json'
function Get-Settings { try { if (Test-Path $SettingsFile) { return (Get-Content $SettingsFile -Raw -Encoding UTF8 | ConvertFrom-Json) } } catch {}; return [pscustomobject]@{} }
function Save-Setting([string]$name, $value) {
    try { $st = Get-Settings; $st | Add-Member -NotePropertyName $name -NotePropertyValue $value -Force; [IO.File]::WriteAllText($SettingsFile, ($st | ConvertTo-Json), [Text.Encoding]::UTF8) } catch {}
}
$script:Lang = 'ru'
try { $saved = (Get-Settings).lang; if ($saved -eq 'en') { $script:Lang = 'en' } elseif (-not $saved -and (Get-Culture).TwoLetterISOLanguageName -ne 'ru') { $script:Lang = 'en' } } catch {}
$EN = @{

# Static UI
'Обзор'='Overview'; 'Мусор'='Junk'; 'Приватность'='Privacy'; 'Реестр'='Registry'; 'Службы'='Services'; 'Автозагрузка'='Startup'; 'Ускорение'='Boost'; 'Диски'='Disks'; 'Система'='System'; 'Приложения'='Apps'; 'Карантин'='Quarantine'
'версия 0.8'='version 0.8'; 'Светлая тема'='Light theme'; 'Тёмная тема'='Dark theme'; 'Проверить обновления'='Check for updates'; 'Обновить'='Update'
'Не выходит в интернет. Обновления только по вашему нажатию.'='Works offline. Updates are checked only when you ask.'
'ОТКЛЮЧЕНО'='DISABLED'; 'НАЙДЕНО ЗАПИСЕЙ'='ENTRIES FOUND'; 'СВОБОДНО ПАМЯТИ'='FREE MEMORY'; 'В КАРАНТИНЕ'='IN QUARANTINE'; 'НАЙДЕНО'='FOUND'
'ДИСК C:'='DRIVE C:'; 'ПАМЯТЬ'='MEMORY'; 'Выключено (служба)'='Turned off'; 
'Состояние компьютера одним взглядом'='Your PC at a glance'; 'Ничего не удаляется безвозвратно: всё попадает в карантин'='Nothing is deleted for good: everything goes to quarantine'
'Телеметрия, реклама и сбор данных под вашим контролем'='Telemetry, ads and data collection under your control'; 'Безопасная чистка с резервной копией каждой ветки'='Safe cleaning with a backup of every key'
'Выключайте то, что вам не нужно, и возвращайте одним движением'='Turn off what you do not need, turn it back on with one flip'; 'Что запускается вместе с Windows'='What launches with Windows'
'Память, диски и обновления'='Memory, drives and updates'; 'Что занимает место на каждом диске'='What takes up space on each drive'; 'Железо и Windows на одном экране'='Hardware and Windows on one screen'
'Предустановленный мусор Windows'='Pre-installed Windows bloat'; 'Всё, что убрано, можно вернуть'='Everything removed can be restored'
'можно освободить'='can be freed'; 'свободно'='free'; 'программ запускается с Windows'='programs launch with Windows'; 'из 100'='of 100'
'Индекс здоровья'='Health index'; 'Считается по мусору, автозагрузке, свободному месту и настройкам приватности.'='Based on junk, startup items, free space and privacy settings.'
'Компьютер в хорошей форме'='Your PC is in good shape'; 'Есть что улучшить'='Room for improvement'; 'Компьютеру нужна забота'='Your PC needs some care'
'Быстрая очистка'='Quick clean'; 'Очистить сейчас'='Clean now'
'Уберёт временные файлы, кэши и отчёты об ошибках с настройками по умолчанию. Корзина и куки не трогаются. Всё попадает в карантин.'='Removes temp files, caches and error reports with default settings. Recycle Bin and cookies are left alone. Everything goes to quarantine.'
'Как это работает'='How it works'
'• Файлы не удаляются, а переносятся в карантин. Кнопка «Вернуть» ставит их на место.'='• Files are moved to quarantine, not deleted. The Restore button puts them back.'
'• Настройки приватности и службы включаются обратно тем же переключателем.'='• Privacy settings and services are reversible with the same switch.'
'• Перед чисткой реестра каждая ветка сохраняется в файл .reg.'='• Every registry key is exported to a .reg file before cleaning.'
'• Программа не выходит в интернет и не собирает данные.'='• The app does not go online and collects no data.'
'• Всё в порядке, так держать'='• All good, keep it up'
'Очистить'='Clean'; 'Проверить заново'='Scan again'; 'Проверить'='Scan'; 'Отключить всю слежку'='Disable all tracking'; 'Очистить реестр'='Clean registry'; 'Обновить список'='Refresh list'
'Освободить'='Free up'; 'Оптимизировать'='Optimise'; 'Открыть обновления'='Open Windows Update'; 'Собрать сведения'='Collect info'; 'Скопировать'='Copy'
'Удалить весь карантин навсегда'='Purge quarantine permanently'; 'Точно удалить? Нажмите ещё раз'='Really purge? Click again'; 'Вернуть'='Restore'
'Найти крупные файлы'='Find large files'; 'Отмеченные в карантин'='Quarantine selected'; 'Открыть в Проводнике'='Open in Explorer'; 'Крупные файлы'='Large files'
'Удалить отмеченные'='Remove selected'; 'Открыть Microsoft Store'='Open Microsoft Store'
'Переключатель включён, значит слежка отключена. Любой пункт можно вернуть к стандартной настройке. Полностью подействует после перезагрузки.'='Switch on means tracking is disabled. Any item can be reverted to the Windows default. Takes full effect after a restart.'
'Только безопасные разделы: списки недавних файлов, кэши оболочки и записи, которые ссылаются на удалённые программы. Перед изменением каждая ветка сохраняется в файл .reg, и её можно вернуть одной кнопкой.'='Safe keys only: recent-file lists, shell caches and entries pointing to deleted programs. Every key is exported to a .reg file first and can be restored with one click.'
'Резервные копии реестра'='Registry backups'; 'Резервных копий пока нет.'='No backups yet.'
'Переключатель включён, значит служба работает. Выключите, чтобы освободить ресурсы. Исходная настройка запоминается, всё обратимо.'='Switch on means the service is running. Turn it off to free resources. The original setting is remembered, everything is reversible.'
'Выключите переключатель, и программа перестанет запускаться вместе с Windows. Ничего не удаляется.'='Turn the switch off and the program will stop launching with Windows. Nothing is deleted.'
'Освободить оперативную память'='Free up RAM'; 'Просит все программы отдать память, которую они держат про запас.'='Asks every program to release memory it holds in reserve.'
'Оптимизировать диски'='Optimise drives'; 'TRIM для SSD, дефрагментация для HDD. Windows сама определяет тип диска. Может занять несколько минут.'='TRIM for SSD, defragmentation for HDD. Windows detects the drive type. May take a few minutes.'
'Автоочистка по расписанию'='Scheduled auto-clean'
'Раз в неделю Sweep сам уберёт временные файлы и кэши с настройками по умолчанию, без окон и вопросов. Всё, как обычно, попадает в карантин.'='Once a week Sweep removes temp files and caches with default settings, silently. Everything goes to quarantine as usual.'
'Обновления Windows'='Windows Update'; 'Открывает окно обновлений. Обновления закрывают дыры в безопасности и часто исправляют тормоза.'='Opens Windows Update. Updates close security holes and often fix slowdowns.'
'Выберите диск, и Sweep найдёт на нём самые крупные файлы. Системные папки Windows и Program Files не проверяются. Отмеченные файлы переносятся в карантин, откуда их можно вернуть.'='Pick a drive and Sweep will find its largest files. Windows and Program Files folders are skipped. Selected files go to quarantine and can be restored.'
'Выберите диск и нажмите «Найти крупные файлы».'='Pick a drive and click "Find large files".'
'Сведения о компьютере. Собираются только по вашему нажатию и никуда не отправляются.'='Information about this PC. Collected only when you ask, never sent anywhere.'
'Предустановленные приложения Microsoft, которые редко кому нужны. Удаление освобождает место и убирает лишнее из меню Пуск. Любое из них можно бесплатно вернуть из Microsoft Store.'='Pre-installed Microsoft and partner apps most people never use. Removing them frees space and declutters the Start menu. Any of them can be reinstalled for free from Microsoft Store.'
'Нажмите «Проверить», чтобы увидеть установленные.'='Click "Scan" to see which ones are installed.'
'Всё, что убрал Sweep, лежит здесь. Нажмите «Вернуть», и файлы встанут на свои места. Место освобождается окончательно после удаления карантина.'='Everything Sweep removed is kept here. Click "Restore" to put files back. Space is freed for good only when you purge the quarantine.'
'Карантин пуст.'='Quarantine is empty.'; 'В автозагрузке ничего нет.'='Nothing in startup.'; 'Лишних записей не найдено.'='No stale entries found.'; 'Лишних предустановленных приложений не найдено.'='No bloat apps found.'
'Файлов крупнее 50 МБ вне системных папок не найдено.'='No files larger than 50 MB outside system folders.'; 'Выключено'='Off'; 'Готово'='Done'; 'скоро'='soon'
# Junk categories
'Временные файлы'='Temporary files'; 'Папки Temp пользователя и Windows'='User and Windows Temp folders'; 'Корзина'='Recycle Bin'; 'Очищается без карантина, вернуть будет нельзя'='Emptied without quarantine, cannot be undone'
'Кэш эскизов Проводника'='Explorer thumbnail cache'; 'Картинки предпросмотра, Windows создаёт их заново'='Preview images, Windows rebuilds them'; 'Кэш обновлений Windows'='Windows Update cache'; 'Установщики уже установленных обновлений'='Installers of updates already applied'
'Отчёты об ошибках и дампы'='Error reports and dumps'; 'Файлы о сбоях программ, нужны только разработчикам'='Crash files, useful only to developers'; 'Старые журналы Windows'='Old Windows logs'; 'Логи установки и обслуживания старше 30 дней'='Setup and servicing logs older than 30 days'
'Кэш браузеров'='Browser caches'; 'Chrome, Edge, Яндекс, Brave, Vivaldi, Opera, Firefox. Лучше закрыть браузеры'='Chrome, Edge, Yandex, Brave, Vivaldi, Opera, Firefox. Close browsers first'; 'Куки браузеров'='Browser cookies'; 'Выйдете из всех сайтов. По умолчанию выключено'='You will be signed out of all sites. Off by default'
# Privacy
'Сбор данных'='Data collection'; 'Реклама и подсказки'='Ads and suggestions'; 'Помощники Microsoft'='Microsoft assistants'
'Телеметрия и сбор диагностики'='Telemetry and diagnostics'; 'Служба DiagTrack и задания сбора данных'='DiagTrack service and data collection tasks'; 'Рекламный идентификатор'='Advertising ID'; 'Приложения не смогут показывать рекламу по вашим интересам'='Apps cannot target ads to your interests'
'Реклама в Пуске и уведомлениях'='Ads in Start and notifications'; 'Предложения приложений, советы и автоустановка рекламных приложений'='App suggestions, tips and silent installs of promoted apps'; 'История активности'='Activity history'; 'Windows не будет собирать, что вы открывали, и отправлять это в облако'='Windows stops recording what you open and uploading it'
'Поиск в интернете из меню Пуск'='Web search from Start menu'; 'Пуск ищет только на компьютере и не отправляет запросы в Bing'='Start searches only this PC and sends nothing to Bing'; 'Кортана'='Cortana'; 'Голосовой помощник Microsoft'='Microsoft voice assistant'
'Запросы отзывов'='Feedback prompts'; 'Windows перестанет спрашивать «Как вам Windows?»'='Windows stops asking "How do you like Windows?"'; 'Отправка отчётов об ошибках'='Error reporting'; 'Сведения о сбоях не уходят в Microsoft'='Crash details are not sent to Microsoft'
'Отслеживание запуска программ'='App launch tracking'; 'Используется для подсказок в Пуске'='Used for Start menu suggestions'; 'Реклама на экране блокировки'='Lock screen ads'; 'Windows: интересные факты и советы поверх картинки экрана блокировки'='Fun facts and tips over the lock screen picture'
'Экран «Что нового» после обновлений'='"What is new" screen after updates'; 'Windows не будет показывать приветствие и предложения после каждого обновления'='No welcome screen and offers after every update'; 'Реклама в Проводнике'='Ads in File Explorer'; 'Баннеры OneDrive и Microsoft 365 в окнах папок'='OneDrive and Microsoft 365 banners in folder windows'
'Рекомендации в меню Пуск (Windows 11)'='Start menu recommendations (Windows 11)'; 'Раздел «Рекомендуем» перестанет подсовывать сайты и приложения'='The Recommended section stops pushing sites and apps'; 'Картинки и новости в строке поиска'='Search box highlights'; 'Поле поиска на панели задач станет пустым, без «главного за день»'='Taskbar search box stays empty, no daily highlights'
'Новости и виджеты на панели задач'='News and widgets on the taskbar'; '«Новости и интересы» в Windows 10, виджеты в Windows 11'='News and Interests in Windows 10, Widgets in Windows 11'; 'Copilot'='Copilot'; 'Кнопка и панель Copilot исчезнут с панели задач'='Copilot button and panel disappear from the taskbar'
'Сбор данных браузером Edge'='Edge data collection'; 'Edge перестанет отправлять историю и данные об использовании'='Edge stops sending browsing and usage data'
# Registry
'Списки недавних документов и команд'='Recent documents and commands'; 'RecentDocs, RunMRU, история диалогов «Открыть» и «Сохранить»'='RecentDocs, RunMRU, Open and Save dialog history'; 'Кэш названий программ (MuiCache)'='Program name cache (MuiCache)'; 'Названия давно удалённых программ, Windows пересоздаёт при необходимости'='Names of long-removed programs, Windows rebuilds it'
'Пути к удалённым программам (App Paths)'='Paths to removed programs (App Paths)'; 'Записи, у которых исполняемый файл уже не существует'='Entries whose executable no longer exists'; 'Автозагрузка несуществующих программ'='Startup entries for missing programs'; 'Записи Run, чей файл удалён с диска'='Run entries whose file was deleted'
# Services
'SysMain (Superfetch)'='SysMain (Superfetch)'; 'Предзагрузка программ. На старых HDD чаще мешает, на SSD не нужна'='Preloads programs. Hurts on old HDDs, unnecessary on SSDs'; 'Индексирование поиска Windows'='Windows Search indexing'; 'Ускоряет поиск файлов, но постоянно грузит диск на слабых ПК'='Speeds up file search but keeps the disk busy on weak PCs'
'Xbox: вход'='Xbox: sign-in'; 'Xbox: сохранения'='Xbox: game saves'; 'Xbox: сеть'='Xbox: networking'; 'Xbox: геймпад'='Xbox: controller'; 'Нужна только для игр Xbox'='Only needed for Xbox games'; 'Нужна только для геймпада Xbox'='Only needed for an Xbox controller'
'Загрузка карт'='Maps download'; 'Офлайн-карты Windows'='Windows offline maps'; 'Демо-режим магазина'='Retail demo mode'; 'Нужна только витринным компьютерам в магазине'='Only for display PCs in shops'; 'Факс'='Fax'; 'Если нет факса, не нужна'='Not needed without a fax machine'
'Удалённый реестр'='Remote Registry'; 'Позволяет менять реестр по сети. Дома не нужна'='Lets the registry be edited over the network. Not for home use'; 'Общий доступ Media Player'='Media Player sharing'; 'Раздача музыки по домашней сети'='Streams music over the home network'; 'Телефонная служба'='Phone service'; 'Связь с телефоном через «Связь с Windows»'='Phone Link connection'
'Пользователь'='User'; 'Система (32)'='System (32-bit)'; 'Папка автозагрузки'='Startup folder'
# Apps
'Игровой клиент Xbox'='Xbox game client'; 'Xbox (новое приложение)'='Xbox (new app)'; 'Магазин игр Xbox'='Xbox game store'; 'Оверлей для записи игр. Если не играете, не нужен'='Game recording overlay. Unneeded if you do not play'; 'Media Player / Музыка Groove'='Media Player / Groove Music'; 'Проигрыватель Microsoft'='Microsoft media player'
'Кино и ТВ'='Movies and TV'; 'Видеопроигрыватель и магазин фильмов'='Video player and movie store'; 'Новости'='News'; 'Лента новостей Microsoft'='Microsoft news feed'; 'Погода'='Weather'; 'Погода от MSN'='MSN weather'; 'Поиск Bing'='Bing Search'; 'Веб-поиск в меню Пуск'='Web search in Start menu'
'Техническая поддержка'='Get Help'; 'Чат с поддержкой Microsoft'='Microsoft support chat'; 'Советы'='Tips'; 'Приложение «Начало работы»'='Get Started app'; 'Пасьянсы с рекламой'='Card games with ads'; 'Люди'='People'; 'Контакты Microsoft'='Microsoft contacts'
'Реклама подписки Microsoft 365'='Microsoft 365 subscription promo'; 'Мессенджер'='Messenger'; 'Центр отзывов'='Feedback Hub'; 'Отправка отзывов в Microsoft'='Sends feedback to Microsoft'; 'Просмотр 3D-моделей'='3D model viewer'; 'Портал смешанной реальности'='Mixed Reality Portal'; 'Нужен только для VR-шлема'='Only for a VR headset'
'Карты'='Maps'; 'Голосовой помощник'='Voice assistant'; 'Видеоредактор с подпиской'='Video editor with subscription'; 'Список задач'='To-do list'; 'Teams (личный)'='Teams (personal)'; 'Чат Teams для дома'='Teams chat for home'; 'Чат Teams'='Teams chat'; 'Автоматизация для бизнеса'='Business automation'
'Приложение помощника Microsoft'='Microsoft assistant app'; 'Outlook (новый)'='Outlook (new)'; 'Почтовый клиент с рекламой'='Mail client with ads'; 'Рукописные заметки'='Handwritten notes'; 'Доска для рисования'='Drawing board'; 'Игра'='Game'; 'Spotify (предустановка)'='Spotify (pre-installed)'; 'Рекламная предустановка'='Promotional pre-install'
# Status templates: {n} are wildcards
'Проверяю, что можно освободить…'='Checking what can be freed…'; 'Проверяю: {0}…'='Checking: {0}…'; 'Убираю: {0}…'='Removing: {0}…'; 'Отключаю: {0}…'='Disabling: {0}…'
'Проверка закончена. Отметьте, что убрать, и нажмите «Очистить». Всё, кроме корзины, попадёт в карантин.'='Scan finished. Tick what to remove and click "Clean". Everything except the Recycle Bin goes to quarantine.'
'Готово. Убрано: {0}. Файлы лежат в карантине, их можно вернуть в разделе «Карантин». Занятые программами файлы пропущены.'='Done. Removed: {0}. Files are in quarantine and can be restored from the Quarantine section. Files in use were skipped.'
'Вся слежка отключена. Подействует полностью после перезагрузки.'='All tracking disabled. Takes full effect after a restart.'
'{0}: отключено.'='{0}: disabled.'; '{0}: включено обратно.'='{0}: enabled again.'
'Проверяю реестр: {0}…'='Checking registry: {0}…'; 'Найдено записей: {0}. Перед очисткой каждая ветка будет сохранена в .reg.'='Entries found: {0}. Every key will be saved to .reg before cleaning.'
'Сохраняю копию и чищу: {0}…'='Backing up and cleaning: {0}…'; 'Готово. Удалено записей: {0}. Резервная копия сохранена, её можно вернуть ниже.'='Done. Entries removed: {0}. A backup was saved and can be restored below.'
'Возвращаю записи реестра…'='Restoring registry entries…'; 'Восстановлено веток: {0}.'='Keys restored: {0}.'; 'Чистка реестра {0}   файлов: {1}'='Registry clean {0}   files: {1}'
'Служба «{0}» включена.'='Service "{0}" enabled.'; 'Служба «{0}» выключена.'='Service "{0}" disabled.'; 'Не удалось изменить службу: {0}'='Could not change service: {0}'
'Автозагрузка «{0}» включена. Подействует после перезагрузки.'='Startup entry "{0}" enabled. Takes effect after a restart.'; 'Автозагрузка «{0}» отключена. Подействует после перезагрузки.'='Startup entry "{0}" disabled. Takes effect after a restart.'
'Не удалось изменить «{0}»: {1}'='Could not change "{0}": {1}'
'Освобождаю память…'='Freeing memory…'; 'Свободно сейчас: {0}'='Free now: {0}'; 'Память освобождена. Прибавилось: {0}.'='Memory freed. Gained: {0}.'
'Оптимизирую диск {0}: …'='Optimising drive {0}: …'; 'Диски оптимизированы.'='Drives optimised.'
'Автоочистка включена: каждое воскресенье в 12:00, или при первом включении компьютера после этого.'='Auto-clean enabled: every Sunday at 12:00, or the next time the PC is on.'; 'Автоочистка выключена.'='Auto-clean disabled.'; 'Включено. Следующий запуск: {0}'='Enabled. Next run: {0}'; 'Не удалось изменить расписание: {0}'='Could not change schedule: {0}'
'Ищу крупные файлы на диске {0}: … На большом диске это может занять минуту.'='Looking for large files on drive {0}: … A big drive may take a minute.'
'Найдено крупных файлов: {0}. Отметьте ненужные и нажмите «Отмеченные в карантин». Видео, архивы и образы дисков часто оказываются именно здесь.'='Large files found: {0}. Tick the ones you do not need and click "Quarantine selected". Videos, archives and disk images often end up here.'
'В карантин перенесено: {0}. Вернуть можно в разделе «Карантин».'='Moved to quarantine: {0}. Restore from the Quarantine section.'; 'Крупные файлы на диске {0}:'='Large files on drive {0}:'
'занято {0} из {1}  ·  свободно {2}  ·  {3}%'='used {0} of {1}  ·  free {2}  ·  {3}%'; 'Диск {0}:'='Drive {0}:'
'Проверяю установленные приложения…'='Checking installed apps…'; 'Найдено предустановленных приложений: {0}. Отметьте ненужные и нажмите «Удалить отмеченные».'='Bloat apps found: {0}. Tick the ones to remove and click "Remove selected".'
'Удаляю {0}…'='Removing {0}…'; 'Удалено приложений: {0}. Вернуть любое можно из Microsoft Store.'='Apps removed: {0}. Any can be reinstalled from Microsoft Store.'
'Собираю сведения о системе…'='Collecting system info…'; 'Сведения собраны. Кнопка «Скопировать» положит их в буфер обмена текстом.'='Info collected. "Copy" puts it on the clipboard as text.'; 'Не удалось собрать часть сведений: {0}'='Some info could not be collected: {0}'
'Скопировано в буфер обмена.'='Copied to clipboard.'; 'Не удалось скопировать.'='Could not copy.'
'Возвращаю файлы на место…'='Restoring files…'; 'Возвращено объектов: {0}.'='Items restored: {0}.'; 'Очистка {0}   {1}'='Clean {0}   {1}'; 'Удаляю карантин…'='Purging quarantine…'; 'Карантин очищен, место освобождено окончательно.'='Quarantine purged, space freed for good.'
'Проверяю обновления…'='Checking for updates…'; 'У вас последняя версия ({0}).'='You have the latest version ({0}).'; 'Доступна новая версия {0}. Нажмите «Обновить до {0}».'='Version {0} is available. Click "Update to {0}".'; 'Обновить до {0}'='Update to {0}'
'Скачиваю {0}…'='Downloading {0}…'; 'Не удалось обновить: {0}'='Update failed: {0}'; 'Проверка обновлений: {0}'='Update check: {0}'; 'Репозиторий обновлений не указан.'='Update repository is not set.'
'Не удалось переключить тему: {0}'='Could not switch theme: {0}'; 'Ошибка: {0} (записано в журнал)'='Error: {0} (written to log)'
# Health tips
'Много мусора: запустите очистку'='Lots of junk: run a clean'; 'Есть что почистить'='Some junk to clean'; 'Автозагрузка перегружена: {0} программ'='Startup is overloaded: {0} programs'; 'В автозагрузке {0} программ, часть можно выключить'='{0} programs in startup, some can be turned off'
'На системном диске почти нет места'='System drive is almost full'; 'На системном диске мало места'='System drive is low on space'; 'Слежка и реклама Windows включены'='Windows tracking and ads are on'; 'Часть телеметрии ещё включена'='Some telemetry is still on'; 'Компьютер не перезагружался {0} дней'='PC has not been restarted for {0} days'
# System info
'Windows'='Windows'; 'Компьютер'='Computer'; 'Работает без перезагрузки'='Uptime'; 'Процессор'='Processor'; 'Модель'='Model'; 'Ядра / потоки'='Cores / threads'; 'Частота'='Clock'; 'Загрузка сейчас'='Load now'; 'Видеокарта'='Graphics'; 'Видеопамять'='Video memory'; 'Драйвер'='Driver'
'Материнская плата'='Motherboard'; 'Оперативная память'='Memory'; 'Всего'='Total'; 'Свободно сейчас'='Free now'; 'Температура'='Temperature'; 'Датчики'='Sensors'; 'недоступно без драйвера (датчики не отдаёт Windows)'='unavailable without a driver (Windows exposes no sensors)'; 'нет данных'='no data'
'{0} д {1} ч {2} мин'='{0} d {1} h {2} min'; '{0} ({1} план.)'='{0} ({1} modules)'; 'Планка {0}'='Module {0}'; 'свободно {0} из {1}'='free {0} of {1}'; '{0} от {1}'='{0} dated {1}'
# Units
'ГБ'='GB'; 'МБ'='MB'; 'КБ'='KB'; 'Б'='B'; '{0} из {1}'='{0} of {1}'

'свободно из {0}'='free of {0}'; 'Язык: English'='Language: Русский'; 'Перезапуск для смены языка…'='Restarting to switch language…'
}
$EnTemplates = @()
foreach ($k in $EN.Keys) {
    if ($k -notmatch '\{\d\}') { continue }
    $order = @([regex]::Matches($k, '\{(\d)\}') | ForEach-Object { [int]$_.Groups[1].Value })
    $rx = '^' + ([regex]::Replace([regex]::Escape($k), '\\\{(\d)\}', '(.+?)')) + '$'
    $EnTemplates += @{ Rx = [regex]$rx; Order = $order; En = $EN[$k] }
}
function T([string]$s) {
    if ($script:Lang -ne 'en' -or [string]::IsNullOrEmpty($s)) { return $s }
    if ($EN.ContainsKey($s)) { $r = $EN[$s]; if ($s -ceq $s.ToUpperInvariant() -and $s -cne $s.ToLowerInvariant()) { return $r.ToUpperInvariant() }; return $r }
    foreach ($t in $EnTemplates) {
        $m = $t.Rx.Match($s)
        if ($m.Success) {
            $max = ($t.Order | Measure-Object -Maximum).Maximum
            $args2 = @(0..$max | ForEach-Object { $n = $_; $i = [array]::IndexOf($t.Order, $n); if ($i -ge 0) { $v = $m.Groups[$i + 1].Value; if ($EN.ContainsKey($v)) { $EN[$v] } else { $v } } else { '' } })
            try { return ($t.En -f $args2) } catch { return $t.En }
        }
    }
    return $s
}

function Write-Log([string]$msg) { try { Add-Content -Path $LogFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) -Encoding UTF8 } catch {} }

# =====================================================================
#  МУСОР
# =====================================================================
$LA = $env:LOCALAPPDATA; $RA = $env:APPDATA
# Папки профилей браузеров на движке Chromium: кэш лежит в <профиль>\Cache и т.д.
$ChromiumRoots = @(
    "$LA\Google\Chrome\User Data", "$LA\Microsoft\Edge\User Data", "$LA\Yandex\YandexBrowser\User Data",
    "$LA\BraveSoftware\Brave-Browser\User Data", "$LA\Vivaldi\User Data", "$LA\Chromium\User Data",
    "$LA\Opera Software\Opera Stable", "$LA\Opera Software\Opera GX Stable"
)
$ChromiumCache = @(); $ChromiumCookies = @()
foreach ($r in $ChromiumRoots) {
    foreach ($sub in 'Cache\*', 'Code Cache\*', 'GPUCache\*', 'Service Worker\CacheStorage\*', 'Media Cache\*') { $ChromiumCache += "$r\*\$sub"; $ChromiumCache += "$r\$sub" }
    $ChromiumCookies += "$r\*\Network\Cookies*"; $ChromiumCookies += "$r\Network\Cookies*"
}
$Categories = @(
    @{ Id='temp';   Name='Временные файлы';           Default=$true;  Hint='Папки Temp пользователя и Windows'; Paths=@("$env:TEMP\*", "$env:WINDIR\Temp\*") }
    @{ Id='bin';    Name='Корзина';                   Default=$false; Hint='Очищается без карантина, вернуть будет нельзя'; Paths=@() }
    @{ Id='thumbs'; Name='Кэш эскизов Проводника';    Default=$true;  Hint='Картинки предпросмотра, Windows создаёт их заново'; Paths=@("$LA\Microsoft\Windows\Explorer\thumbcache_*.db", "$LA\Microsoft\Windows\Explorer\iconcache_*.db") }
    @{ Id='wu';     Name='Кэш обновлений Windows';    Default=$true;  Hint='Установщики уже установленных обновлений'; Paths=@("$env:WINDIR\SoftwareDistribution\Download\*") }
    @{ Id='dumps';  Name='Отчёты об ошибках и дампы'; Default=$true;  Hint='Файлы о сбоях программ, нужны только разработчикам'; Paths=@("$LA\CrashDumps\*", "$env:WINDIR\Minidump\*", "$env:ProgramData\Microsoft\Windows\WER\ReportQueue\*", "$env:ProgramData\Microsoft\Windows\WER\ReportArchive\*") }
    @{ Id='logs';   Name='Старые журналы Windows';    Default=$true;  Hint='Логи установки и обслуживания старше 30 дней'; Paths=@("$env:WINDIR\Logs\CBS\*.log", "$env:WINDIR\Logs\DISM\*.log", "$env:WINDIR\Panther\*.log"); OlderThanDays=30 }
    @{ Id='cache';  Name='Кэш браузеров';             Default=$true;  Hint='Chrome, Edge, Яндекс, Brave, Vivaldi, Opera, Firefox. Лучше закрыть браузеры'; Paths=($ChromiumCache + @("$LA\Mozilla\Firefox\Profiles\*\cache2\*", "$LA\Mozilla\Firefox\Profiles\*\startupCache\*")) }
    @{ Id='cookies'; Name='Куки браузеров';           Default=$false; Hint='Выйдете из всех сайтов. По умолчанию выключено'; Paths=($ChromiumCookies + @("$RA\Mozilla\Firefox\Profiles\*\cookies.sqlite*")) }
)

function Get-ItemSize($it) {
    if ($it.PSIsContainer) { return [long](Get-ChildItem -LiteralPath $it.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum }
    return [long]$it.Length
}
function Get-CatItems($c) {
    $items = @()
    foreach ($p in $c.Paths) { $items += Get-ChildItem -Path $p -Force -ErrorAction SilentlyContinue }
    if ($c.OlderThanDays) { $limit = (Get-Date).AddDays(-$c.OlderThanDays); $items = $items | Where-Object { $_.LastWriteTime -lt $limit } }
    return $items
}
function Get-CatSize($c) { $t = [long]0; foreach ($it in (Get-CatItems $c)) { $t += Get-ItemSize $it }; return $t }
function Get-RecycleBinSize { try { $t = [long]0; foreach ($i in (New-Object -ComObject Shell.Application).Namespace(0xA).Items()) { $t += $i.Size }; return $t } catch { return [long]0 } }
function Format-Size([long]$b) {
    if ($b -ge 1GB) { return ('{0:N1} ' -f ($b / 1GB)) + (T 'ГБ') }; if ($b -ge 1MB) { return ('{0:N0} ' -f ($b / 1MB)) + (T 'МБ') }; if ($b -ge 1KB) { return ('{0:N0} ' -f ($b / 1KB)) + (T 'КБ') }; return "$b " + (T 'Б')
}

function Move-ToQuarantine($c, [string]$session) {
    $freed = [long]0
    $dest = Join-Path $Quarantine "$session\$($c.Id)"; New-Item -ItemType Directory -Path $dest -Force | Out-Null
    $manifest = Join-Path $Quarantine "$session\manifest.txt"; $n = 0
    foreach ($it in (Get-CatItems $c)) {
        $size = Get-ItemSize $it; $n++
        $target = Join-Path $dest ("{0:D5}_{1}" -f $n, $it.Name)
        try { Move-Item -LiteralPath $it.FullName -Destination $target -Force -ErrorAction Stop; Add-Content -Path $manifest -Value ("{0}|{1}" -f $target, $it.FullName) -Encoding UTF8; $freed += $size } catch {}
    }
    return $freed
}
function Get-QuarantineSessions {
    $list = @()
    foreach ($d in (Get-ChildItem -Path $Quarantine -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
        $size = [long](Get-ChildItem -LiteralPath $d.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $date = $d.Name; try { $date = [datetime]::ParseExact($d.Name, 'yyyyMMdd_HHmmss', $null).ToString('d MMMM yyyy, HH:mm') } catch {}
        $list += [pscustomobject]@{ Path=$d.FullName; Date=$date; Size=$size }
    }
    return $list
}
function Restore-Session([string]$sessionPath) {
    $manifest = Join-Path $sessionPath 'manifest.txt'; if (-not (Test-Path $manifest)) { return 0 }
    $n = 0
    foreach ($line in (Get-Content -Path $manifest -Encoding UTF8)) {
        $parts = $line -split '\|', 2; if ($parts.Count -ne 2) { continue }
        if (-not (Test-Path -LiteralPath $parts[0])) { continue }
        try { $parent = Split-Path $parts[1] -Parent; if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }; Move-Item -LiteralPath $parts[0] -Destination $parts[1] -Force -ErrorAction Stop; $n++ } catch { Write-Log "Не удалось вернуть $($parts[1]): $($_.Exception.Message)" }
    }
    Remove-Item -LiteralPath $sessionPath -Recurse -Force -ErrorAction SilentlyContinue
    return $n
}

# =====================================================================
#  ПРИВАТНОСТЬ. Галочка стоит = защита включена (слежка отключена).
#  Reg: Path, Name, Off (значение при защите), On (значение при откате; $null = удалить параметр)
# =====================================================================
$Privacy = @(
    @{ Group='Сбор данных'; Id='telemetry'; Name='Телеметрия и сбор диагностики'; Hint='Служба DiagTrack и задания сбора данных';
       Reg=@(@{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection'; Name='AllowTelemetry'; Off=0; On=$null});
       Services=@('DiagTrack','dmwappushservice');
       Tasks=@('\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser','\Microsoft\Windows\Application Experience\ProgramDataUpdater','\Microsoft\Windows\Customer Experience Improvement Program\Consolidator','\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip','\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector') }
    @{ Group='Сбор данных'; Id='adid'; Name='Рекламный идентификатор'; Hint='Приложения не смогут показывать рекламу по вашим интересам';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo'; Name='Enabled'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='tips'; Name='Реклама в Пуске и уведомлениях'; Hint='Предложения приложений, советы и автоустановка рекламных приложений';
       Reg=@(
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-338388Enabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-338389Enabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-353694Enabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-353696Enabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SystemPaneSuggestionsEnabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SilentInstalledAppsEnabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SoftLandingEnabled'; Off=0; On=1}) }
    @{ Group='Сбор данных'; Id='activity'; Name='История активности'; Hint='Windows не будет собирать, что вы открывали, и отправлять это в облако';
       Reg=@(
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'; Name='EnableActivityFeed'; Off=0; On=$null},
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'; Name='PublishUserActivities'; Off=0; On=$null},
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'; Name='UploadUserActivities'; Off=0; On=$null}) }
    @{ Group='Реклама и подсказки'; Id='search'; Name='Поиск в интернете из меню Пуск'; Hint='Пуск ищет только на компьютере и не отправляет запросы в Bing';
       Reg=@(
         @{Path='HKCU:\Software\Policies\Microsoft\Windows\Explorer'; Name='DisableSearchBoxSuggestions'; Off=1; On=$null},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\Search'; Name='BingSearchEnabled'; Off=0; On=$null}) }
    @{ Group='Помощники Microsoft'; Id='cortana'; Name='Кортана'; Hint='Голосовой помощник Microsoft';
       Reg=@(@{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search'; Name='AllowCortana'; Off=0; On=$null}) }
    @{ Group='Сбор данных'; Id='feedback'; Name='Запросы отзывов'; Hint='Windows перестанет спрашивать «Как вам Windows?»';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Siuf\Rules'; Name='NumberOfSIUFInPeriod'; Off=0; On=$null}) }
    @{ Group='Сбор данных'; Id='wer'; Name='Отправка отчётов об ошибках'; Hint='Сведения о сбоях не уходят в Microsoft';
       Reg=@(@{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting'; Name='Disabled'; Off=1; On=$null}); Services=@('WerSvc') }
    @{ Group='Сбор данных'; Id='trackprogs'; Name='Отслеживание запуска программ'; Hint='Используется для подсказок в Пуске';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'; Name='Start_TrackProgs'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='lockscreen'; Name='Реклама на экране блокировки'; Hint='Windows: интересные факты и советы поверх картинки экрана блокировки';
       Reg=@(
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='RotatingLockScreenOverlayEnabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-338387Enabled'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='welcome'; Name='Экран «Что нового» после обновлений'; Hint='Windows не будет показывать приветствие и предложения после каждого обновления';
       Reg=@(
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager'; Name='SubscribedContent-310093Enabled'; Off=0; On=1},
         @{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement'; Name='ScoobeSystemSettingEnabled'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='explorerads'; Name='Реклама в Проводнике'; Hint='Баннеры OneDrive и Microsoft 365 в окнах папок';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'; Name='ShowSyncProviderNotifications'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='startrec'; Name='Рекомендации в меню Пуск (Windows 11)'; Hint='Раздел «Рекомендуем» перестанет подсовывать сайты и приложения';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'; Name='Start_IrisRecommendations'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='searchhl'; Name='Картинки и новости в строке поиска'; Hint='Поле поиска на панели задач станет пустым, без «главного за день»';
       Reg=@(@{Path='HKCU:\Software\Microsoft\Windows\CurrentVersion\SearchSettings'; Name='IsDynamicSearchBoxEnabled'; Off=0; On=1}) }
    @{ Group='Реклама и подсказки'; Id='feeds'; Name='Новости и виджеты на панели задач'; Hint='«Новости и интересы» в Windows 10, виджеты в Windows 11';
       Reg=@(
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds'; Name='EnableFeeds'; Off=0; On=$null},
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Dsh'; Name='AllowNewsAndInterests'; Off=0; On=$null}) }
    @{ Group='Помощники Microsoft'; Id='copilot'; Name='Copilot'; Hint='Кнопка и панель Copilot исчезнут с панели задач';
       Reg=@(@{Path='HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot'; Name='TurnOffWindowsCopilot'; Off=1; On=$null}) }
    @{ Group='Помощники Microsoft'; Id='edgetelemetry'; Name='Сбор данных браузером Edge'; Hint='Edge перестанет отправлять историю и данные об использовании';
       Reg=@(
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Edge'; Name='MetricsReportingEnabled'; Off=0; On=$null},
         @{Path='HKLM:\SOFTWARE\Policies\Microsoft\Edge'; Name='PersonalizationReportingEnabled'; Off=0; On=$null}) }
)
function Get-PrivacyState($p) {
    $r = $p.Reg[0]
    try { $v = (Get-ItemProperty -Path $r.Path -Name $r.Name -ErrorAction Stop).($r.Name); return ($v -eq $r.Off) } catch { return $false }
}
function Set-Privacy($p, [bool]$protect) {
    foreach ($r in $p.Reg) {
        if ($protect) {
            if (-not (Test-Path $r.Path)) { New-Item -Path $r.Path -Force | Out-Null }
            Set-ItemProperty -Path $r.Path -Name $r.Name -Value $r.Off -Type DWord
        } else {
            if ($null -eq $r.On) { Remove-ItemProperty -Path $r.Path -Name $r.Name -ErrorAction SilentlyContinue }
            else { if (-not (Test-Path $r.Path)) { New-Item -Path $r.Path -Force | Out-Null }; Set-ItemProperty -Path $r.Path -Name $r.Name -Value $r.On -Type DWord }
        }
    }
    foreach ($s in @($p.Services)) { Set-ServiceState $s (-not $protect) }
    foreach ($t in @($p.Tasks)) {
        $name = Split-Path $t -Leaf; $path = (Split-Path $t -Parent) + '\'
        try { if ($protect) { Disable-ScheduledTask -TaskName $name -TaskPath $path -ErrorAction Stop | Out-Null } else { Enable-ScheduledTask -TaskName $name -TaskPath $path -ErrorAction Stop | Out-Null } } catch {}
    }
}

# =====================================================================
#  СЛУЖБЫ. Галочка стоит = служба работает. Исходный тип запуска сохраняется в файл для отката.
# =====================================================================
$ServicesList = @(
    @{ Name='SysMain';        Title='SysMain (Superfetch)';           Hint='Предзагрузка программ. На старых HDD чаще мешает, на SSD не нужна' }
    @{ Name='WSearch';        Title='Индексирование поиска Windows';  Hint='Ускоряет поиск файлов, но постоянно грузит диск на слабых ПК' }
    @{ Name='XblAuthManager'; Title='Xbox: вход';                     Hint='Нужна только для игр Xbox' }
    @{ Name='XblGameSave';    Title='Xbox: сохранения';               Hint='Нужна только для игр Xbox' }
    @{ Name='XboxNetApiSvc';  Title='Xbox: сеть';                     Hint='Нужна только для игр Xbox' }
    @{ Name='XboxGipSvc';     Title='Xbox: геймпад';                  Hint='Нужна только для геймпада Xbox' }
    @{ Name='MapsBroker';     Title='Загрузка карт';                  Hint='Офлайн-карты Windows' }
    @{ Name='RetailDemo';     Title='Демо-режим магазина';            Hint='Нужна только витринным компьютерам в магазине' }
    @{ Name='Fax';            Title='Факс';                           Hint='Если нет факса, не нужна' }
    @{ Name='RemoteRegistry'; Title='Удалённый реестр';               Hint='Позволяет менять реестр по сети. Дома не нужна' }
    @{ Name='WMPNetworkSvc';  Title='Общий доступ Media Player';      Hint='Раздача музыки по домашней сети' }
    @{ Name='PhoneSvc';       Title='Телефонная служба';              Hint='Связь с телефоном через «Связь с Windows»' }
)
function Get-SvcBackup { if (Test-Path $SvcBackup) { try { return (Get-Content $SvcBackup -Raw | ConvertFrom-Json) } catch {} }; return [pscustomobject]@{} }
function Set-ServiceState([string]$name, [bool]$enabled) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue; if (-not $svc) { return }
    $backup = Get-SvcBackup
    if ($enabled) {
        $type = 'Manual'; if ($backup.PSObject.Properties[$name]) { $type = $backup.$name }
        if ($type -eq 'Disabled') { $type = 'Manual' }
        Set-Service -Name $name -StartupType $type -ErrorAction SilentlyContinue
        if ($type -eq 'Automatic') { Start-Service -Name $name -ErrorAction SilentlyContinue }
    } else {
        if (-not $backup.PSObject.Properties[$name]) {
            $cur = (Get-CimInstance Win32_Service -Filter "Name='$name'").StartMode
            $map = @{ 'Auto'='Automatic'; 'Manual'='Manual'; 'Disabled'='Disabled' }
            $backup | Add-Member -NotePropertyName $name -NotePropertyValue ($map[$cur]) -Force
            $backup | ConvertTo-Json | Set-Content $SvcBackup -Encoding UTF8
        }
        Stop-Service -Name $name -Force -ErrorAction SilentlyContinue
        Set-Service -Name $name -StartupType Disabled -ErrorAction SilentlyContinue
    }
}
function Get-ServiceEnabled([string]$name) {
    $s = Get-CimInstance Win32_Service -Filter "Name='$name'" -ErrorAction SilentlyContinue
    if (-not $s) { return $null }
    return ($s.StartMode -ne 'Disabled')
}

# =====================================================================
#  АВТОЗАГРУЗКА
# =====================================================================
$StartupSources = @(
    @{ Name='Пользователь'; Run='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'; Approved='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' }
    @{ Name='Система';      Run='HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'; Approved='HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' }
    @{ Name='Система (32)'; Run='HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'; Approved='HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32' }
)
$StartupFolder = [Environment]::GetFolderPath('Startup')
$StartupFolderApproved = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
function Get-ApprovedState([string]$key, [string]$name) { try { $b = (Get-ItemProperty -Path $key -Name $name -ErrorAction Stop).$name; if ($b -and $b[0] -eq 3) { return $false } } catch {}; return $true }
function Set-ApprovedState([string]$key, [string]$name, [bool]$enabled) {
    if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
    $first = if ($enabled) { 2 } else { 3 }
    Set-ItemProperty -Path $key -Name $name -Value ([byte[]](@($first) + @(0,0,0,0,0,0,0,0,0,0,0))) -Type Binary
}
function Get-StartupEntries {
    $list = @()
    foreach ($src in $StartupSources) {
        if (-not (Test-Path $src.Run)) { continue }
        foreach ($p in (Get-ItemProperty -Path $src.Run).PSObject.Properties) { if ($p.Name -like 'PS*') { continue }; $list += [pscustomobject]@{ Name=$p.Name; Command=[string]$p.Value; Source=$src.Name; Approved=$src.Approved; Enabled=(Get-ApprovedState $src.Approved $p.Name) } }
    }
    if (Test-Path $StartupFolder) { foreach ($f in (Get-ChildItem -Path $StartupFolder -File -ErrorAction SilentlyContinue | Where-Object Name -ne 'desktop.ini')) { $list += [pscustomobject]@{ Name=$f.Name; Command=$f.FullName; Source='Папка автозагрузки'; Approved=$StartupFolderApproved; Enabled=(Get-ApprovedState $StartupFolderApproved $f.Name) } } }
    return $list
}

# =====================================================================
#  РЕЕСТР. Только безопасные категории: списки недавних файлов, кэши оболочки и записи,
#  которые ссылаются на несуществующие файлы. Перед изменением каждая ветка экспортируется
#  в .reg в папку ProgramData\Sweep\RegBackup, кнопка «Вернуть» импортирует её обратно.
# =====================================================================
$RegBackupDir = Join-Path $Root 'RegBackup'
New-Item -ItemType Directory -Path $RegBackupDir -Force | Out-Null

$RegCategories = @(
    @{ Id='mru';     Name='Списки недавних документов и команд'; Hint='RecentDocs, RunMRU, история диалогов «Открыть» и «Сохранить»'
       Keys=@('HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs',
              'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU',
              'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU',
              'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU',
              'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths'); Mode='clear' }
    @{ Id='muicache'; Name='Кэш названий программ (MuiCache)'; Hint='Названия давно удалённых программ, Windows пересоздаёт при необходимости'
       Keys=@('HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache'); Mode='clear' }
    @{ Id='apppaths'; Name='Пути к удалённым программам (App Paths)'; Hint='Записи, у которых исполняемый файл уже не существует'
       Keys=@('HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths', 'HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths'); Mode='dead' }
    @{ Id='deadrun'; Name='Автозагрузка несуществующих программ'; Hint='Записи Run, чей файл удалён с диска'
       Keys=@('HKCU\Software\Microsoft\Windows\CurrentVersion\Run', 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'); Mode='deadvalues' }
)
function Get-RegPsPath([string]$k) { return ($k -replace '^HKCU\\', 'HKCU:\' -replace '^HKLM\\', 'HKLM:\') }
function Get-ExePathFromCommand([string]$cmd) {
    if (-not $cmd) { return $null }
    $c = [Environment]::ExpandEnvironmentVariables($cmd.Trim())
    if ($c.StartsWith('"')) { $end = $c.IndexOf('"', 1); if ($end -gt 0) { return $c.Substring(1, $end - 1) } }
    $m = [regex]::Match($c, '^(.*?\.(exe|cmd|bat|com))', 'IgnoreCase'); if ($m.Success) { return $m.Groups[1].Value }
    return $c.Split(' ')[0]
}
# Возвращает список найденных элементов: @{ Key; Value; Label }
function Find-RegItems($cat) {
    $items = @()
    foreach ($k in $cat.Keys) {
        $ps = Get-RegPsPath $k
        if (-not (Test-Path $ps)) { continue }
        switch ($cat.Mode) {
            'clear' {
                $n = 0
                $n += @(Get-ChildItem -Path $ps -ErrorAction SilentlyContinue).Count
                $n += @((Get-ItemProperty -Path $ps -ErrorAction SilentlyContinue).PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' }).Count
                if ($n -gt 0) { $items += @{ Key=$k; Value=$null; Label="$k ($n зап.)" } }
            }
            'dead' {
                foreach ($sub in (Get-ChildItem -Path $ps -ErrorAction SilentlyContinue)) {
                    $exe = (Get-ItemProperty -Path $sub.PSPath -ErrorAction SilentlyContinue).'(default)'
                    $path = Get-ExePathFromCommand $exe
                    if ($path -and -not (Test-Path -LiteralPath $path)) { $items += @{ Key="$k\$($sub.PSChildName)"; Value=$null; Label="$($sub.PSChildName) → $path" } }
                }
            }
            'deadvalues' {
                foreach ($p in (Get-ItemProperty -Path $ps -ErrorAction SilentlyContinue).PSObject.Properties) {
                    if ($p.Name -like 'PS*') { continue }
                    $path = Get-ExePathFromCommand ([string]$p.Value)
                    if ($path -and -not (Test-Path -LiteralPath $path)) { $items += @{ Key=$k; Value=$p.Name; Label="$($p.Name) → $path" } }
                }
            }
        }
    }
    return $items
}
function Backup-RegKey([string]$key, [string]$session) {
    $file = Join-Path $RegBackupDir ("{0}_{1}.reg" -f $session, (($key -replace '[\\:]', '_') -replace '[^\w_\.]', ''))
    $safe = $file.Substring(0, [math]::Min($file.Length, 240))
    & reg.exe export $key $safe /y 2>&1 | Out-Null
    return $safe
}
function Clean-RegCategory($cat, [string]$session) {
    $done = 0
    $items = Find-RegItems $cat
    $backedUp = @{}
    foreach ($it in $items) {
        $rootKey = if ($cat.Mode -eq 'dead') { Split-Path $it.Key -Parent } else { $it.Key }
        if (-not $backedUp.ContainsKey($rootKey)) { Backup-RegKey $rootKey $session | Out-Null; $backedUp[$rootKey] = $true }
        try {
            $ps = Get-RegPsPath $it.Key
            if ($cat.Mode -eq 'clear') {
                Get-ChildItem -Path $ps -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                foreach ($p in (Get-ItemProperty -Path $ps -ErrorAction SilentlyContinue).PSObject.Properties) { if ($p.Name -notlike 'PS*') { Remove-ItemProperty -Path $ps -Name $p.Name -ErrorAction SilentlyContinue } }
            } elseif ($cat.Mode -eq 'dead') { Remove-Item -Path $ps -Recurse -Force -ErrorAction Stop }
            else { Remove-ItemProperty -Path $ps -Name $it.Value -ErrorAction Stop }
            $done++
        } catch { Write-Log "Реестр: не удалось $($it.Key): $($_.Exception.Message)" }
    }
    return $done
}
function Get-RegBackupSessions {
    $groups = Get-ChildItem -Path $RegBackupDir -Filter '*.reg' -ErrorAction SilentlyContinue | Group-Object { $_.Name.Substring(0, 15) } | Sort-Object Name -Descending
    $list = @()
    foreach ($g in $groups) { $date = $g.Name; try { $date = [datetime]::ParseExact($g.Name, 'yyyyMMdd_HHmmss', $null).ToString('d MMMM yyyy, HH:mm') } catch {}; $list += [pscustomobject]@{ Session=$g.Name; Date=$date; Count=$g.Count } }
    return $list
}
function Restore-RegSession([string]$session) {
    $n = 0
    foreach ($f in (Get-ChildItem -Path $RegBackupDir -Filter "$session*.reg" -ErrorAction SilentlyContinue)) { & reg.exe import $f.FullName 2>&1 | Out-Null; $n++; Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue }
    return $n
}


# =====================================================================
#  РЕЖИМ -auto: тихая очистка по расписанию, без окна
# =====================================================================
if ($args -contains '-auto') {
    try {
        $session = Get-Date -Format 'yyyyMMdd_HHmmss'; $freed = [long]0
        Write-Log "Автоочистка по расписанию, сеанс $session"
        foreach ($c in $Categories) { if ($c.Default -and $c.Id -ne 'bin') { $freed += Move-ToQuarantine $c $session } }
        # Карантин старше 30 дней удаляется окончательно, чтобы не копился
        Get-ChildItem -Path $Quarantine -Directory -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Автоочистка: освобождено $(Format-Size $freed)"
    } catch { Write-Log "Автоочистка: ошибка $($_.Exception.Message)" }
    exit
}
# =====================================================================
#  ИНТЕРФЕЙС
# =====================================================================
[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Sweep" Width="1080" Height="720" MinWidth="900" MinHeight="600"
        WindowStartupLocation="CenterScreen" Background="{DynamicResource WinBg}" FontFamily="Segoe UI" FontSize="13"
        Foreground="{DynamicResource TextMain}" UseLayoutRounding="True" TextOptions.TextFormattingMode="Display">
  <Window.Resources>
    <SolidColorBrush x:Key="WinBg" Color="#0D0B1A"/>
    <SolidColorBrush x:Key="SideBg" Color="#110E24"/>
    <SolidColorBrush x:Key="CardBg" Color="#181433"/>
    <SolidColorBrush x:Key="CardBorder" Color="#262052"/>
    <SolidColorBrush x:Key="CardHover" Color="#1E1940"/>
    <SolidColorBrush x:Key="TextMain" Color="#EDE9FE"/>
    <SolidColorBrush x:Key="TextMuted" Color="#8B86B0"/>
    <SolidColorBrush x:Key="Accent" Color="#8B5CF6"/>
    <SolidColorBrush x:Key="AccentSoft" Color="#2A1F5E"/>
    <SolidColorBrush x:Key="SoftBtn" Color="#221C47"/>
    <SolidColorBrush x:Key="StatusBg" Color="#0A0816"/>
    <SolidColorBrush x:Key="Good" Color="#34D399"/>
    <SolidColorBrush x:Key="Warn" Color="#FBBF24"/>
    <LinearGradientBrush x:Key="AccentGrad" StartPoint="0,0" EndPoint="1,1"><GradientStop Color="#7C3AED" Offset="0"/><GradientStop Color="#A78BFA" Offset="1"/></LinearGradientBrush>
    <LinearGradientBrush x:Key="HeroGrad" StartPoint="0,0" EndPoint="1,1"><GradientStop Color="#5B21B6" Offset="0"/><GradientStop Color="#7C3AED" Offset="0.55"/><GradientStop Color="#2563EB" Offset="1"/></LinearGradientBrush>

    <!-- Кнопки: лёгкое увеличение при наведении -->
    <Style x:Key="Btn" TargetType="Button">
      <Setter Property="Padding" Value="18,10"/><Setter Property="Margin" Value="0,0,10,0"/>
      <Setter Property="Foreground" Value="{DynamicResource TextMain}"/><Setter Property="Background" Value="{DynamicResource SoftBtn}"/>
      <Setter Property="BorderThickness" Value="0"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="FontSize" Value="13"/><Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template"><Setter.Value>
        <ControlTemplate TargetType="Button">
          <Border x:Name="B" Background="{TemplateBinding Background}" CornerRadius="12" Padding="{TemplateBinding Padding}" RenderTransformOrigin="0.5,0.5">
            <Border.RenderTransform><ScaleTransform ScaleX="1" ScaleY="1"/></Border.RenderTransform>
            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
          </Border>
          <ControlTemplate.Triggers>
            <Trigger Property="IsEnabled" Value="False"><Setter TargetName="B" Property="Opacity" Value="0.35"/></Trigger>
            <Trigger Property="IsMouseOver" Value="True">
              <Trigger.EnterActions><BeginStoryboard><Storyboard>
                <DoubleAnimation Storyboard.TargetName="B" Storyboard.TargetProperty="RenderTransform.ScaleX" To="1.04" Duration="0:0:0.12"/>
                <DoubleAnimation Storyboard.TargetName="B" Storyboard.TargetProperty="RenderTransform.ScaleY" To="1.04" Duration="0:0:0.12"/>
              </Storyboard></BeginStoryboard></Trigger.EnterActions>
              <Trigger.ExitActions><BeginStoryboard><Storyboard>
                <DoubleAnimation Storyboard.TargetName="B" Storyboard.TargetProperty="RenderTransform.ScaleX" To="1" Duration="0:0:0.15"/>
                <DoubleAnimation Storyboard.TargetName="B" Storyboard.TargetProperty="RenderTransform.ScaleY" To="1" Duration="0:0:0.15"/>
              </Storyboard></BeginStoryboard></Trigger.ExitActions>
            </Trigger>
          </ControlTemplate.Triggers>
        </ControlTemplate>
      </Setter.Value></Setter>
    </Style>
    <Style x:Key="BtnMain" TargetType="Button" BasedOn="{StaticResource Btn}"><Setter Property="Background" Value="{StaticResource AccentGrad}"/><Setter Property="Foreground" Value="White"/><Setter Property="Padding" Value="26,12"/><Setter Property="FontSize" Value="14"/></Style>
    <Style x:Key="BtnGood" TargetType="Button" BasedOn="{StaticResource Btn}"><Setter Property="Background" Value="{DynamicResource Good}"/><Setter Property="Foreground" Value="#052E16"/></Style>

    <!-- Боковое меню -->
    <Style x:Key="Nav" TargetType="RadioButton">
      <Setter Property="Foreground" Value="{DynamicResource TextMuted}"/><Setter Property="Cursor" Value="Hand"/><Setter Property="Margin" Value="12,1"/>
      <Setter Property="Template"><Setter.Value>
        <ControlTemplate TargetType="RadioButton">
          <Border x:Name="B" Background="Transparent" CornerRadius="12" Padding="14,9">
            <Grid>
              <Grid.ColumnDefinitions><ColumnDefinition Width="28"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
              <TextBlock x:Name="I" Text="{TemplateBinding Tag}" FontFamily="Segoe MDL2 Assets" FontSize="16" VerticalAlignment="Center" Foreground="{TemplateBinding Foreground}"/>
              <ContentPresenter Grid.Column="1" VerticalAlignment="Center" TextBlock.FontSize="14" TextBlock.FontWeight="SemiBold"/>
            </Grid>
          </Border>
          <ControlTemplate.Triggers>
            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="B" Property="Background" Value="{DynamicResource CardHover}"/><Setter Property="Foreground" Value="{DynamicResource TextMain}"/></Trigger>
            <Trigger Property="IsChecked" Value="True"><Setter TargetName="B" Property="Background" Value="{DynamicResource AccentSoft}"/><Setter Property="Foreground" Value="{DynamicResource TextMain}"/><Setter TargetName="I" Property="Foreground" Value="#A78BFA"/></Trigger>
          </ControlTemplate.Triggers>
        </ControlTemplate>
      </Setter.Value></Setter>
    </Style>

    <Style x:Key="Card" TargetType="Border"><Setter Property="Background" Value="{DynamicResource CardBg}"/><Setter Property="CornerRadius" Value="18"/><Setter Property="Padding" Value="22"/><Setter Property="Margin" Value="0,0,0,14"/><Setter Property="BorderBrush" Value="{DynamicResource CardBorder}"/><Setter Property="BorderThickness" Value="1"/></Style>

    <!-- Переключатели как в современных приложениях -->
    <Style TargetType="CheckBox">
      <Setter Property="Margin" Value="0,6"/><Setter Property="Cursor" Value="Hand"/><Setter Property="Foreground" Value="{DynamicResource TextMain}"/>
      <Setter Property="Template"><Setter.Value>
        <ControlTemplate TargetType="CheckBox">
          <Border x:Name="Row" Background="Transparent" CornerRadius="12" Padding="10,8">
            <Grid>
              <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
              <ContentPresenter VerticalAlignment="Center"/>
              <Border x:Name="Track" Grid.Column="1" Width="44" Height="24" CornerRadius="12" Background="#2F2A5A" VerticalAlignment="Center" Margin="16,0,0,0">
                <Ellipse x:Name="Knob" Width="18" Height="18" Fill="#CBD5E1" HorizontalAlignment="Left" Margin="3,0,0,0" RenderTransformOrigin="0.5,0.5">
                  <Ellipse.RenderTransform><TranslateTransform X="0"/></Ellipse.RenderTransform>
                </Ellipse>
              </Border>
            </Grid>
          </Border>
          <ControlTemplate.Triggers>
            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="Row" Property="Background" Value="{DynamicResource CardHover}"/></Trigger>
            <Trigger Property="IsChecked" Value="True">
              <Setter TargetName="Track" Property="Background" Value="{StaticResource AccentGrad}"/><Setter TargetName="Knob" Property="Fill" Value="White"/>
              <Trigger.EnterActions><BeginStoryboard><Storyboard><DoubleAnimation Storyboard.TargetName="Knob" Storyboard.TargetProperty="RenderTransform.X" To="20" Duration="0:0:0.15"/></Storyboard></BeginStoryboard></Trigger.EnterActions>
              <Trigger.ExitActions><BeginStoryboard><Storyboard><DoubleAnimation Storyboard.TargetName="Knob" Storyboard.TargetProperty="RenderTransform.X" To="0" Duration="0:0:0.15"/></Storyboard></BeginStoryboard></Trigger.ExitActions>
            </Trigger>
          </ControlTemplate.Triggers>
        </ControlTemplate>
      </Setter.Value></Setter>
    </Style>
    <Style TargetType="ScrollViewer"><Setter Property="VerticalScrollBarVisibility" Value="Auto"/></Style>
    <Style TargetType="ProgressBar"><Setter Property="Height" Value="4"/><Setter Property="Foreground" Value="#A78BFA"/><Setter Property="Background" Value="Transparent"/><Setter Property="BorderThickness" Value="0"/></Style>
  </Window.Resources>

  <Grid>
    <Grid.ColumnDefinitions><ColumnDefinition Width="236"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>

    <!-- Боковая панель -->
    <Border Grid.Column="0" Background="{DynamicResource SideBg}">
      <Grid>
        <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
        <StackPanel Orientation="Horizontal" Margin="24,26,24,22">
          <Border Width="40" Height="40" CornerRadius="12" Background="{StaticResource AccentGrad}"><TextBlock Text="&#xE74D;" FontFamily="Segoe MDL2 Assets" FontSize="18" Foreground="White" HorizontalAlignment="Center" VerticalAlignment="Center"/></Border>
          <StackPanel Margin="12,0,0,0" VerticalAlignment="Center"><TextBlock Text="Sweep" FontSize="20" FontWeight="Bold"/><TextBlock Text="версия 0.8" FontSize="11" Foreground="{DynamicResource TextMuted}"/></StackPanel>
        </StackPanel>
        <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Hidden"><StackPanel>
          <RadioButton x:Name="NavHome"    Style="{StaticResource Nav}" Tag="&#xE80F;" Content="Обзор" IsChecked="True"/>
          <RadioButton x:Name="NavClean"   Style="{StaticResource Nav}" Tag="&#xE74D;" Content="Мусор"/>
          <RadioButton x:Name="NavPrivacy" Style="{StaticResource Nav}" Tag="&#xE72E;" Content="Приватность"/>
          <RadioButton x:Name="NavReg"     Style="{StaticResource Nav}" Tag="&#xE8A5;" Content="Реестр"/>
          <RadioButton x:Name="NavSvc"     Style="{StaticResource Nav}" Tag="&#xE90F;" Content="Службы"/>
          <RadioButton x:Name="NavStartup" Style="{StaticResource Nav}" Tag="&#xE7E8;" Content="Автозагрузка"/>
          <RadioButton x:Name="NavBoost"   Style="{StaticResource Nav}" Tag="&#xE945;" Content="Ускорение"/>
          <RadioButton x:Name="NavDisk"    Style="{StaticResource Nav}" Tag="&#xEDA2;" Content="Диски"/>
          <RadioButton x:Name="NavSys"     Style="{StaticResource Nav}" Tag="&#xE7F4;" Content="Система"/>
          <RadioButton x:Name="NavApps"    Style="{StaticResource Nav}" Tag="&#xE71D;" Content="Приложения"/>
          <RadioButton x:Name="NavQ"       Style="{StaticResource Nav}" Tag="&#xE8B7;" Content="Карантин"/>
        </StackPanel></ScrollViewer>
        <StackPanel Grid.Row="2" Margin="16,8,16,16">
          <Button x:Name="BtnUpdateApp" Content="Обновить" Style="{StaticResource BtnMain}" Margin="0,0,0,8" HorizontalAlignment="Stretch" Visibility="Collapsed"/>
          <Grid>
            <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
            <Button x:Name="BtnTheme" Content="Светлая тема" Style="{StaticResource Btn}" Margin="0,0,6,0" HorizontalAlignment="Stretch" Padding="10,9" FontSize="12"/>
            <Button x:Name="BtnLang" Grid.Column="1" Content="EN" Style="{StaticResource Btn}" Margin="0,0,6,0" Padding="10,9" FontSize="12" ToolTip="Язык: English"/>
            <Button x:Name="BtnCheckUpdate" Grid.Column="2" Content="&#xE895;" FontFamily="Segoe MDL2 Assets" Style="{StaticResource Btn}" Margin="0" Padding="12,9" ToolTip="Проверить обновления"/>
          </Grid>
          <TextBlock Text="Не выходит в интернет. Обновления только по вашему нажатию." FontSize="10" Foreground="{DynamicResource TextMuted}" Margin="2,8,0,0" TextWrapping="Wrap"/>
        </StackPanel>
      </Grid>
    </Border>

    <!-- Контент -->
    <Grid Grid.Column="1">
      <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>

      <!-- Шапка -->
      <Border Grid.Row="0" Margin="28,24,28,0" CornerRadius="20" Padding="26,22" Background="{StaticResource HeroGrad}">
        <Grid>
          <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
          <StackPanel VerticalAlignment="Center">
            <TextBlock x:Name="HeadTitle" Text="Мусор" FontSize="26" FontWeight="Bold" Foreground="White"/>
            <TextBlock x:Name="HeadSub" Text="Ничего не удаляется безвозвратно: всё попадает в карантин" FontSize="13" Foreground="#DDD6FE" Margin="0,2,0,0"/>
          </StackPanel>
          <Border Grid.Column="1" Background="#26FFFFFF" CornerRadius="16" Padding="20,12" VerticalAlignment="Center">
            <StackPanel><TextBlock x:Name="BigLabel" Text="МОЖНО ОСВОБОДИТЬ" Foreground="#DDD6FE" FontSize="10" FontWeight="SemiBold"/><TextBlock x:Name="BigTotal" Text="…" Foreground="White" FontSize="32" FontWeight="Bold"/></StackPanel>
          </Border>
        </Grid>
      </Border>
      <ProgressBar x:Name="Busy" Grid.Row="0" VerticalAlignment="Bottom" Margin="54,0,54,-2" IsIndeterminate="True" Visibility="Collapsed"/>

      <!-- Секции -->
      <Grid Grid.Row="1" x:Name="Sections" Margin="28,18,28,0" RenderTransformOrigin="0.5,0.5">
        <Grid.RenderTransform><TranslateTransform x:Name="SectionShift" Y="0"/></Grid.RenderTransform>

        <Grid x:Name="SecHome">
          <ScrollViewer><StackPanel>
            <Border Style="{StaticResource Card}"><Grid>
              <Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
              <Grid Width="104" Height="104" Margin="0,0,22,0">
                <Ellipse Stroke="{DynamicResource CardBorder}" StrokeThickness="9" Width="96" Height="96"/>
                <Ellipse x:Name="HealthRing" Stroke="#A78BFA" StrokeThickness="9" Width="96" Height="96" StrokeDashCap="Round" StrokeDashArray="0 100" RenderTransformOrigin="0.5,0.5"><Ellipse.RenderTransform><RotateTransform Angle="-90"/></Ellipse.RenderTransform></Ellipse>
                <StackPanel VerticalAlignment="Center" HorizontalAlignment="Center"><TextBlock x:Name="HealthText" Text="…" FontSize="26" FontWeight="Bold" HorizontalAlignment="Center"/><TextBlock Text="из 100" FontSize="10" Foreground="{DynamicResource TextMuted}" HorizontalAlignment="Center" Margin="0,-4,0,0"/></StackPanel>
              </Grid>
              <StackPanel Grid.Column="1" VerticalAlignment="Center">
                <TextBlock x:Name="HealthTitle" Text="Индекс здоровья" FontWeight="Bold" FontSize="17"/>
                <TextBlock x:Name="HealthHint" Text="Считается по мусору, автозагрузке, свободному месту и настройкам приватности." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,0"/>
                <StackPanel x:Name="HealthTips" Margin="0,8,0,0"/>
              </StackPanel>
            </Grid></Border>
            <UniformGrid Columns="4" Margin="0,0,0,2">
              <Border Style="{StaticResource Card}" Margin="0,0,14,14"><StackPanel><TextBlock Text="МУСОР" FontSize="10" FontWeight="SemiBold" Foreground="{DynamicResource TextMuted}"/><TextBlock x:Name="TileJunk" Text="…" FontSize="26" FontWeight="Bold" Margin="0,4,0,0"/><TextBlock Text="можно освободить" FontSize="12" Foreground="{DynamicResource TextMuted}"/></StackPanel></Border>
              <Border Style="{StaticResource Card}" Margin="0,0,14,14"><StackPanel><TextBlock Text="ДИСК C:" FontSize="10" FontWeight="SemiBold" Foreground="{DynamicResource TextMuted}"/><TextBlock x:Name="TileDisk" Text="…" FontSize="26" FontWeight="Bold" Margin="0,4,0,0"/><TextBlock x:Name="TileDiskSub" Text="свободно" FontSize="12" Foreground="{DynamicResource TextMuted}"/></StackPanel></Border>
              <Border Style="{StaticResource Card}" Margin="0,0,14,14"><StackPanel><TextBlock Text="ПАМЯТЬ" FontSize="10" FontWeight="SemiBold" Foreground="{DynamicResource TextMuted}"/><TextBlock x:Name="TileMem" Text="…" FontSize="26" FontWeight="Bold" Margin="0,4,0,0"/><TextBlock x:Name="TileMemSub" Text="свободно" FontSize="12" Foreground="{DynamicResource TextMuted}"/></StackPanel></Border>
              <Border Style="{StaticResource Card}" Margin="0,0,0,14"><StackPanel><TextBlock Text="АВТОЗАГРУЗКА" FontSize="10" FontWeight="SemiBold" Foreground="{DynamicResource TextMuted}"/><TextBlock x:Name="TileStartup" Text="…" FontSize="26" FontWeight="Bold" Margin="0,4,0,0"/><TextBlock Text="программ запускается с Windows" FontSize="12" Foreground="{DynamicResource TextMuted}" TextWrapping="Wrap"/></StackPanel></Border>
            </UniformGrid>
            <Border Style="{StaticResource Card}"><Grid>
              <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
              <StackPanel VerticalAlignment="Center">
                <TextBlock Text="Быстрая очистка" FontWeight="Bold" FontSize="17"/>
                <TextBlock Text="Уберёт временные файлы, кэши и отчёты об ошибках с настройками по умолчанию. Корзина и куки не трогаются. Всё попадает в карантин." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,0"/>
              </StackPanel>
              <Button x:Name="BtnQuick" Grid.Column="1" Content="Очистить сейчас" Style="{StaticResource BtnMain}" Margin="20,0,0,0" VerticalAlignment="Center"/>
            </Grid></Border>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Как это работает" FontWeight="Bold" FontSize="15" Margin="0,0,0,6"/>
              <TextBlock Text="• Файлы не удаляются, а переносятся в карантин. Кнопка «Вернуть» ставит их на место." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,2"/>
              <TextBlock Text="• Настройки приватности и службы включаются обратно тем же переключателем." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,2"/>
              <TextBlock Text="• Перед чисткой реестра каждая ветка сохраняется в файл .reg." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,2"/>
              <TextBlock Text="• Программа не выходит в интернет и не собирает данные." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,2"/>
            </StackPanel></Border>
          </StackPanel></ScrollViewer>
        </Grid>

        <Grid x:Name="SecClean" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel x:Name="CatPanel"/></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnClean" Content="Очистить" Style="{StaticResource BtnMain}" IsEnabled="False"/><Button x:Name="BtnScan" Content="Проверить заново" Style="{StaticResource Btn}"/></StackPanel>
        </Grid>

        <Grid x:Name="SecPrivacy" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Переключатель включён, значит слежка отключена. Любой пункт можно вернуть к стандартной настройке. Полностью подействует после перезагрузки." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="10,0,10,8"/>
            <StackPanel x:Name="PrivPanel"/>
          </StackPanel></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnPrivAll" Content="Отключить всю слежку" Style="{StaticResource BtnMain}"/></StackPanel>
        </Grid>

        <Grid x:Name="SecReg" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><StackPanel>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Только безопасные разделы: списки недавних файлов, кэши оболочки и записи, которые ссылаются на удалённые программы. Перед изменением каждая ветка сохраняется в файл .reg, и её можно вернуть одной кнопкой." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="10,0,10,8"/>
              <StackPanel x:Name="RegPanel"/>
            </StackPanel></Border>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Резервные копии реестра" FontWeight="Bold" FontSize="15" Margin="0,0,0,6"/>
              <StackPanel x:Name="RegBackupPanel"/>
            </StackPanel></Border>
          </StackPanel></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnRegClean" Content="Очистить реестр" Style="{StaticResource BtnMain}" IsEnabled="False"/><Button x:Name="BtnRegScan" Content="Проверить" Style="{StaticResource Btn}"/></StackPanel>
        </Grid>

        <Grid x:Name="SecSvc" Visibility="Collapsed">
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Переключатель включён, значит служба работает. Выключите, чтобы освободить ресурсы. Исходная настройка запоминается, всё обратимо." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="10,0,10,8"/>
            <StackPanel x:Name="SvcPanel"/>
          </StackPanel></Border></ScrollViewer>
        </Grid>

        <Grid x:Name="SecStartup" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Выключите переключатель, и программа перестанет запускаться вместе с Windows. Ничего не удаляется." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="10,0,10,8"/>
            <StackPanel x:Name="StartupPanel"/>
          </StackPanel></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnStartupRefresh" Content="Обновить список" Style="{StaticResource Btn}"/></StackPanel>
        </Grid>

        <Grid x:Name="SecBoost" Visibility="Collapsed">
          <ScrollViewer><StackPanel>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Освободить оперативную память" FontWeight="Bold" FontSize="15"/>
              <TextBlock Text="Просит все программы отдать память, которую они держат про запас." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,12"/>
              <StackPanel Orientation="Horizontal"><Button x:Name="BtnMem" Content="Освободить" Style="{StaticResource BtnMain}"/><TextBlock x:Name="MemText" VerticalAlignment="Center" Foreground="{DynamicResource TextMuted}"/></StackPanel>
            </StackPanel></Border>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Оптимизировать диски" FontWeight="Bold" FontSize="15"/>
              <TextBlock Text="TRIM для SSD, дефрагментация для HDD. Windows сама определяет тип диска. Может занять несколько минут." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,12"/>
              <StackPanel Orientation="Horizontal"><Button x:Name="BtnDisk" Content="Оптимизировать" Style="{StaticResource BtnMain}"/><TextBlock x:Name="DiskText" VerticalAlignment="Center" Foreground="{DynamicResource TextMuted}"/></StackPanel>
            </StackPanel></Border>
            <Border Style="{StaticResource Card}"><Grid>
              <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
              <StackPanel>
                <TextBlock Text="Автоочистка по расписанию" FontWeight="Bold" FontSize="15"/>
                <TextBlock Text="Раз в неделю Sweep сам уберёт временные файлы и кэши с настройками по умолчанию, без окон и вопросов. Всё, как обычно, попадает в карантин." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,0"/>
                <TextBlock x:Name="SchedText" Text="" FontSize="12" Foreground="{DynamicResource TextMuted}" Margin="0,6,0,0"/>
              </StackPanel>
              <CheckBox x:Name="SchedBox" Grid.Column="1" Content="" VerticalAlignment="Center" Margin="10,0,0,0"/>
            </Grid></Border>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Обновления Windows" FontWeight="Bold" FontSize="15"/>
              <TextBlock Text="Открывает окно обновлений. Обновления закрывают дыры в безопасности и часто исправляют тормоза." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,4,0,12"/>
              <StackPanel Orientation="Horizontal"><Button x:Name="BtnUpdate" Content="Открыть обновления" Style="{StaticResource Btn}"/></StackPanel>
            </StackPanel></Border>
          </StackPanel></ScrollViewer>
        </Grid>

        <Grid x:Name="SecDisk" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><StackPanel>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock Text="Выберите диск, и Sweep найдёт на нём самые крупные файлы. Системные папки Windows и Program Files не проверяются. Отмеченные файлы переносятся в карантин, откуда их можно вернуть." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,0,0,10"/>
              <StackPanel x:Name="DiskPanel"/>
            </StackPanel></Border>
            <Border Style="{StaticResource Card}"><StackPanel>
              <TextBlock x:Name="BigFilesTitle" Text="Крупные файлы" FontWeight="Bold" FontSize="15" Margin="0,0,0,6"/>
              <StackPanel x:Name="BigFilesPanel"><TextBlock Text="Выберите диск и нажмите «Найти крупные файлы»." Foreground="{DynamicResource TextMuted}"/></StackPanel>
            </StackPanel></Border>
          </StackPanel></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14">
            <Button x:Name="BtnBigScan" Content="Найти крупные файлы" Style="{StaticResource BtnMain}"/>
            <Button x:Name="BtnBigClean" Content="Отмеченные в карантин" Style="{StaticResource Btn}" IsEnabled="False"/>
            <Button x:Name="BtnDiskOpen" Content="Открыть в Проводнике" Style="{StaticResource Btn}"/>
          </StackPanel>
        </Grid>

        <Grid x:Name="SecSys" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Сведения о компьютере. Собираются только по вашему нажатию и никуда не отправляются." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,0,0,10"/>
            <StackPanel x:Name="SysPanel"/>
          </StackPanel></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnSysInfo" Content="Собрать сведения" Style="{StaticResource BtnMain}"/><Button x:Name="BtnSysCopy" Content="Скопировать" Style="{StaticResource Btn}" IsEnabled="False"/></StackPanel>
        </Grid>

        <Grid x:Name="SecApps" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Предустановленные приложения Microsoft, которые редко кому нужны. Удаление освобождает место и убирает лишнее из меню Пуск. Любое из них можно бесплатно вернуть из Microsoft Store." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="10,0,10,8"/>
            <StackPanel x:Name="AppsPanel"><TextBlock Text="Нажмите «Проверить», чтобы увидеть установленные." Foreground="{DynamicResource TextMuted}" Margin="10,0"/></StackPanel>
          </StackPanel></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14">
            <Button x:Name="BtnAppsRemove" Content="Удалить отмеченные" Style="{StaticResource BtnMain}" IsEnabled="False"/>
            <Button x:Name="BtnAppsScan" Content="Проверить" Style="{StaticResource Btn}"/>
            <Button x:Name="BtnAppsStore" Content="Открыть Microsoft Store" Style="{StaticResource Btn}"/>
          </StackPanel>
        </Grid>

        <Grid x:Name="SecQ" Visibility="Collapsed">
          <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
          <ScrollViewer><Border Style="{StaticResource Card}"><StackPanel>
            <TextBlock Text="Всё, что убрал Sweep, лежит здесь. Нажмите «Вернуть», и файлы встанут на свои места. Место освобождается окончательно после удаления карантина." TextWrapping="Wrap" Foreground="{DynamicResource TextMuted}" Margin="0,0,0,10"/>
            <StackPanel x:Name="QPanel"/>
          </StackPanel></Border></ScrollViewer>
          <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,4,0,14"><Button x:Name="BtnQRefresh" Content="Обновить" Style="{StaticResource Btn}"/><Button x:Name="BtnQPurge" Content="Удалить весь карантин навсегда" Style="{StaticResource Btn}"/></StackPanel>
        </Grid>
      </Grid>

      <Border Grid.Row="2" Background="{DynamicResource StatusBg}" Padding="28,12"><TextBlock x:Name="StatusText" Text="Проверяю, что можно освободить…" Foreground="{DynamicResource TextMuted}" TextWrapping="Wrap"/></Border>
    </Grid>
  </Grid>
</Window>
"@

$Window = [Windows.Markup.XamlReader]::Load((New-Object System.Xml.XmlNodeReader $xaml))
function Translate-Tree($node) {
    if ($node -is [System.Windows.Controls.TextBlock]) { if ($node.Text) { $node.Text = T $node.Text } }
    elseif ($node -is [System.Windows.Controls.ContentControl] -and $node.Content -is [string]) { $node.Content = T $node.Content }
    if ($node -is [System.Windows.FrameworkElement] -and $node.ToolTip -is [string]) { $node.ToolTip = T $node.ToolTip }
    if ($node -is [System.Windows.DependencyObject]) { foreach ($ch in [System.Windows.LogicalTreeHelper]::GetChildren($node)) { if ($ch -is [System.Windows.DependencyObject]) { Translate-Tree $ch } } }
}
if ($script:Lang -eq 'en') { Translate-Tree $Window }
$ui = @{}
foreach ($n in 'HeadTitle','HeadSub','BigLabel','BigTotal','Busy','Sections','SectionShift','NavHome','SecHome','BtnUpdateApp','BtnCheckUpdate','BtnLang','HealthRing','HealthText','HealthTitle','HealthHint','HealthTips','NavApps','SecApps','AppsPanel','BtnAppsRemove','BtnAppsScan','BtnAppsStore','SchedText','SchedBox','NavDisk','SecDisk','DiskPanel','BigFilesTitle','BigFilesPanel','BtnBigScan','BtnBigClean','BtnDiskOpen','TileJunk','TileDisk','TileDiskSub','TileMem','TileMemSub','TileStartup','BtnQuick',
              'NavClean','NavPrivacy','NavReg','NavSvc','NavStartup','NavBoost','NavSys','NavQ',
              'SecClean','SecPrivacy','SecReg','SecSvc','SecStartup','SecBoost','SecSys','SecQ',
              'CatPanel','BtnClean','BtnScan','PrivPanel','BtnPrivAll','RegPanel','RegBackupPanel','BtnRegClean','BtnRegScan','SvcPanel','StartupPanel','BtnStartupRefresh',
              'BtnMem','MemText','BtnDisk','DiskText','BtnUpdate','SysPanel','BtnSysInfo','BtnSysCopy','QPanel','BtnQRefresh','BtnQPurge','StatusText','BtnTheme') { $ui[$n] = $Window.FindName($n) }

function Set-Status([string]$text) { $ui.StatusText.Text = (T $text); $Window.Dispatcher.Invoke([action]{}, [Windows.Threading.DispatcherPriority]::Render) }
$Window.Dispatcher.add_UnhandledException({
    param($sender, $e)
    $e.Handled = $true
    $msg = $e.Exception.Message; if ($e.Exception.InnerException) { $msg = $e.Exception.InnerException.Message }
    Write-Log "Ошибка: $msg"
    try { $ui.StatusText.Text = "Ошибка: $msg (записано в журнал)"; $ui.Busy.Visibility = 'Collapsed' } catch {}
})
function Set-Busy([bool]$on) { $ui.Busy.Visibility = $(if ($on) { 'Visible' } else { 'Collapsed' }) }
function New-Text([string]$text, [string]$color = 'TextMain', [int]$size = 13, [bool]$bold = $false) {
    $t = New-Object System.Windows.Controls.TextBlock; $t.Text = (T $text); $t.FontSize = $size; $t.TextWrapping = 'Wrap'
    if ($color -in 'TextMain','TextMuted','Good','Warn') { $t.SetResourceReference([System.Windows.Controls.TextBlock]::ForegroundProperty, $color) } else { $t.Foreground = $color }
    if ($bold) { $t.FontWeight = 'SemiBold' }
    return $t
}
function New-CheckRow([string]$title, [string]$hint, [bool]$checked, $tag) {
    $cb = New-Object System.Windows.Controls.CheckBox; $cb.IsChecked = $checked; $cb.Tag = $tag
    $sp = New-Object System.Windows.Controls.StackPanel
    $t1 = New-Text $title 'TextMain' 14 $true; $sp.Children.Add($t1) | Out-Null
    if ($hint) { $sp.Children.Add((New-Text $hint 'TextMuted' 12)) | Out-Null }
    $cb.Content = $sp
    return @{ Box=$cb; Title=$t1 }
}

# ----- Навигация с анимацией -----
$Sections = @{ NavHome=@{ Sec='SecHome'; Title='Обзор'; Sub='Состояние компьютера одним взглядом'; Big='МОЖНО ОСВОБОДИТЬ' }
               NavClean=@{ Sec='SecClean'; Title='Мусор'; Sub='Ничего не удаляется безвозвратно: всё попадает в карантин'; Big='МОЖНО ОСВОБОДИТЬ' }
               NavPrivacy=@{ Sec='SecPrivacy'; Title='Приватность'; Sub='Телеметрия, реклама и сбор данных под вашим контролем'; Big='ОТКЛЮЧЕНО' }
               NavReg=@{ Sec='SecReg'; Title='Реестр'; Sub='Безопасная чистка с резервной копией каждой ветки'; Big='НАЙДЕНО ЗАПИСЕЙ' }
               NavSvc=@{ Sec='SecSvc'; Title='Службы'; Sub='Выключайте то, что вам не нужно, и возвращайте одним движением'; Big='ВЫКЛЮЧЕНО' }
               NavStartup=@{ Sec='SecStartup'; Title='Автозагрузка'; Sub='Что запускается вместе с Windows'; Big='ОТКЛЮЧЕНО' }
               NavBoost=@{ Sec='SecBoost'; Title='Ускорение'; Sub='Память, диски и обновления'; Big='СВОБОДНО ПАМЯТИ' }
               NavDisk=@{ Sec='SecDisk'; Title='Диски'; Sub='Что занимает место на каждом диске'; Big='СВОБОДНО' }
               NavSys=@{ Sec='SecSys'; Title='Система'; Sub='Железо и Windows на одном экране'; Big='КОМПЬЮТЕР' }
               NavApps=@{ Sec='SecApps'; Title='Приложения'; Sub='Предустановленный мусор Windows'; Big='НАЙДЕНО' }
               NavQ=@{ Sec='SecQ'; Title='Карантин'; Sub='Всё, что убрано, можно вернуть'; Big='В КАРАНТИНЕ' } }
$FadeIn = New-Object System.Windows.Media.Animation.Storyboard
$fa = New-Object System.Windows.Media.Animation.DoubleAnimation(0.0, 1.0, [TimeSpan]::FromMilliseconds(260)); [System.Windows.Media.Animation.Storyboard]::SetTarget($fa, $ui.Sections); [System.Windows.Media.Animation.Storyboard]::SetTargetProperty($fa, (New-Object System.Windows.PropertyPath('Opacity')))
$sa = New-Object System.Windows.Media.Animation.DoubleAnimation(18.0, 0.0, [TimeSpan]::FromMilliseconds(260)); $sa.EasingFunction = New-Object System.Windows.Media.Animation.CubicEase; [System.Windows.Media.Animation.Storyboard]::SetTarget($sa, $ui.SectionShift); [System.Windows.Media.Animation.Storyboard]::SetTargetProperty($sa, (New-Object System.Windows.PropertyPath('Y')))
$FadeIn.Children.Add($fa) | Out-Null; $FadeIn.Children.Add($sa) | Out-Null
function Show-Section([string]$nav) {
    $d = $Sections[$nav]
    foreach ($k in $Sections.Keys) { $ui[$Sections[$k].Sec].Visibility = 'Collapsed' }
    $ui[$d.Sec].Visibility = 'Visible'
    $ui.HeadTitle.Text = (T $d.Title); $ui.HeadSub.Text = (T $d.Sub); $ui.BigLabel.Text = (T $d.Big)
    Update-BigNumber $nav
    $FadeIn.Begin($Window, $true)
}
foreach ($k in $Sections.Keys) { $ui[$k].Add_Checked({ Show-Section $this.Name }) }

# Анимация числа в шапке
$script:bigTarget = ''; $script:bigFrom = 0; $script:bigTo = 0; $script:bigStep = 0
$BigTimer = New-Object System.Windows.Threading.DispatcherTimer; $BigTimer.Interval = [TimeSpan]::FromMilliseconds(16)
$BigTimer.Add_Tick({
    $script:bigStep++
    $t = [math]::Min(1.0, $script:bigStep / 28.0); $e = 1 - [math]::Pow(1 - $t, 3)
    $ui.BigTotal.Text = Format-Size ([long]($script:bigFrom + ($script:bigTo - $script:bigFrom) * $e))
    if ($t -ge 1) { $BigTimer.Stop() }
})
function Set-BigSize([long]$bytes) { $script:bigFrom = 0; $script:bigTo = $bytes; $script:bigStep = 0; $BigTimer.Start() }
function Update-BigNumber([string]$nav) {
    $BigTimer.Stop()
    switch ($nav) {
        'NavHome'    { Set-BigSize (Get-CheckedTotal); Update-Tiles; Update-Health }
        'NavClean'   { Set-BigSize (Get-CheckedTotal) }
        'NavPrivacy' { $n = @($PrivBoxes.Values | Where-Object { $_.IsChecked }).Count; $ui.BigTotal.Text = ((T '{0} из {1}') -f $n, $Privacy.Count) }
        'NavReg'     { $ui.BigTotal.Text = $(if ($script:regFound -ge 0) { "$($script:regFound)" } else { '…' }) }
        'NavSvc'     { $n = @($SvcBoxes | Where-Object { -not $_.IsChecked }).Count; $ui.BigTotal.Text = ((T '{0} из {1}') -f $n, $SvcBoxes.Count) }
        'NavStartup' { $n = @($ui.StartupPanel.Children | Where-Object { $_ -is [System.Windows.Controls.CheckBox] -and -not $_.IsChecked }).Count; $ui.BigTotal.Text = "$n" }
        'NavBoost'   { $ui.BigTotal.Text = Format-Size ([long]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1KB)) }
        'NavDisk'    { if (-not $ui.DiskPanel.Children.Count) { Load-Disks }; $v = Get-SelectedVolume; if ($v) { $ui.BigTotal.Text = Format-Size ([long]$v.SizeRemaining) } }
        'NavSys'     { $ui.BigTotal.Text = $env:COMPUTERNAME }
        'NavApps'    { $ui.BigTotal.Text = $(if ($script:appsFound -ge 0) { "$($script:appsFound)" } else { '…' }) }
        'NavQ'       { $sz = [long]0; foreach ($q in (Get-QuarantineSessions)) { $sz += $q.Size }; $ui.BigTotal.Text = Format-Size $sz }
    }
}


function Update-Tiles {
    try {
        $ui.TileJunk.Text = Format-Size (Get-CheckedTotal)
        $sys = Get-Volume -DriveLetter ($env:SystemDrive.TrimEnd(':')) -ErrorAction SilentlyContinue
        if ($sys) { $ui.TileDisk.Text = Format-Size ([long]$sys.SizeRemaining); $ui.TileDiskSub.Text = ((T 'свободно из {0}') -f (Format-Size ([long]$sys.Size))) }
        $os = Get-CimInstance Win32_OperatingSystem
        $ui.TileMem.Text = Format-Size ([long]($os.FreePhysicalMemory * 1KB)); $ui.TileMemSub.Text = ((T 'свободно из {0}') -f (Format-Size ([long]($os.TotalVisibleMemorySize * 1KB))))
        $ui.TileStartup.Text = "$(@($ui.StartupPanel.Children | Where-Object { $_ -is [System.Windows.Controls.CheckBox] -and $_.IsChecked }).Count)"
    } catch { Write-Log "Плитки: $($_.Exception.Message)" }
}

# ----- Мусор -----
$CatBoxes = @{}; $CatSizes = @{}
foreach ($c in $Categories) {
    $row = New-CheckRow $c.Name $c.Hint $c.Default $c.Id
    $row.Box.Add_Click({ Set-BigSize (Get-CheckedTotal) })
    $ui.CatPanel.Children.Add($row.Box) | Out-Null
    $CatBoxes[$c.Id] = $row
}
function Get-CheckedTotal { $t = [long]0; foreach ($c in $Categories) { if ($CatBoxes[$c.Id].Box.IsChecked -and $CatSizes.ContainsKey($c.Id)) { $t += $CatSizes[$c.Id] } }; return $t }
function Start-Scan {
    $ui.BtnScan.IsEnabled = $false; $ui.BtnClean.IsEnabled = $false; Set-Busy $true
    foreach ($c in $Categories) {
        Set-Status "Проверяю: $($c.Name)…"
        $size = if ($c.Id -eq 'bin') { Get-RecycleBinSize } else { Get-CatSize $c }
        $CatSizes[$c.Id] = $size; $CatBoxes[$c.Id].Title.Text = "$(T $c.Name)    $(Format-Size $size)"
    }
    Set-BigSize (Get-CheckedTotal); Set-Busy $false; Update-Tiles; Update-Health
    Set-Status 'Проверка закончена. Отметьте, что убрать, и нажмите «Очистить». Всё, кроме корзины, попадёт в карантин.'
    $ui.BtnScan.IsEnabled = $true; $ui.BtnClean.IsEnabled = $true
}
$ui.BtnScan.Add_Click({ Start-Scan })
$ui.BtnQuick.Add_Click({
    foreach ($c in $Categories) { $CatBoxes[$c.Id].Box.IsChecked = $c.Default }
    if (-not $CatSizes.Count) { Start-Scan }
    $ui.BtnQuick.IsEnabled = $false
    $ui.BtnClean.RaiseEvent((New-Object System.Windows.RoutedEventArgs([System.Windows.Controls.Button]::ClickEvent)))
    Update-Tiles; $ui.BtnQuick.IsEnabled = $true
})
$ui.BtnClean.Add_Click({
    $ui.BtnClean.IsEnabled = $false; $ui.BtnScan.IsEnabled = $false; Set-Busy $true
    $session = Get-Date -Format 'yyyyMMdd_HHmmss'; $freed = [long]0; $wuStopped = $false
    Write-Log "Очистка, сеанс $session"
    foreach ($c in $Categories) {
        if (-not $CatBoxes[$c.Id].Box.IsChecked) { continue }
        Set-Status "Убираю: $($c.Name)…"
        switch ($c.Id) {
            'bin' { $before = Get-RecycleBinSize; try { Clear-RecycleBin -Force -ErrorAction SilentlyContinue } catch {}; $freed += $before }
            'wu'  { try { Stop-Service wuauserv -Force -ErrorAction SilentlyContinue; $wuStopped = $true } catch {}; $freed += Move-ToQuarantine $c $session }
            default { $freed += Move-ToQuarantine $c $session }
        }
        $CatSizes[$c.Id] = [long]0; $CatBoxes[$c.Id].Title.Text = (T $c.Name)
    }
    if ($wuStopped) { try { Start-Service wuauserv -ErrorAction SilentlyContinue } catch {} }
    Set-BigSize 0; Set-Busy $false; Write-Log "Освобождено $(Format-Size $freed)"
    Set-Status "Готово. Убрано: $(Format-Size $freed). Файлы лежат в карантине, их можно вернуть в разделе «Карантин». Занятые программами файлы пропущены."
    Load-Quarantine; Update-Tiles; Update-Health; $ui.BtnScan.IsEnabled = $true
})

# ----- Приватность -----
$PrivBoxes = @{}
$lastGroup = ''
foreach ($p in ($Privacy | Sort-Object { @('Сбор данных','Реклама и подсказки','Помощники Microsoft').IndexOf($_.Group) })) {
    if ($p.Group -ne $lastGroup) { $h = New-Text (T $p.Group).ToUpper() 'TextMuted' 10 $true; $h.Margin = '10,14,0,2'; $ui.PrivPanel.Children.Add($h) | Out-Null; $lastGroup = $p.Group }
    $row = New-CheckRow $p.Name $p.Hint (Get-PrivacyState $p) $p.Id
    $row.Box.Add_Click({
        $item = $Privacy | Where-Object { $_.Id -eq $this.Tag }
        try { Set-Privacy $item ([bool]$this.IsChecked); $state = if ($this.IsChecked) { 'отключено' } else { 'включено обратно' }; Write-Log "Приватность: $($item.Name) $state"; Set-Status ((T "{0}: $state.") -f (T $item.Name)) }
        catch { Set-Status "Не удалось изменить «$($item.Name)»: $($_.Exception.Message)" }
        Update-BigNumber 'NavPrivacy'
    })
    $ui.PrivPanel.Children.Add($row.Box) | Out-Null; $PrivBoxes[$p.Id] = $row.Box
}
$ui.BtnPrivAll.Add_Click({
    Set-Busy $true
    foreach ($p in $Privacy) { Set-Status "Отключаю: $($p.Name)…"; try { Set-Privacy $p $true; $PrivBoxes[$p.Id].IsChecked = $true } catch {} }
    Set-Busy $false; Write-Log 'Приватность: отключено всё'; Update-BigNumber 'NavPrivacy'
    Set-Status 'Вся слежка отключена. Подействует полностью после перезагрузки.'
})

# ----- Реестр -----
$script:regFound = -1
$RegBoxes = @{}
foreach ($c in $RegCategories) {
    $row = New-CheckRow $c.Name $c.Hint $true $c.Id
    $ui.RegPanel.Children.Add($row.Box) | Out-Null; $RegBoxes[$c.Id] = $row
}
function Load-RegBackups {
    $ui.RegBackupPanel.Children.Clear()
    $sessions = Get-RegBackupSessions
    if (-not $sessions -or $sessions.Count -eq 0) { $ui.RegBackupPanel.Children.Add((New-Text 'Резервных копий пока нет.' 'TextMuted')) | Out-Null; return }
    foreach ($s in $sessions) {
        $g = New-Object System.Windows.Controls.Grid; $g.Margin = '0,6'
        $c1 = New-Object System.Windows.Controls.ColumnDefinition; $c1.Width = '*'; $c2 = New-Object System.Windows.Controls.ColumnDefinition; $c2.Width = 'Auto'
        $g.ColumnDefinitions.Add($c1); $g.ColumnDefinitions.Add($c2)
        $info = New-Text ((T 'Чистка реестра {0}   файлов: {1}') -f $s.Date, $s.Count) 'TextMain' 14 $true; $info.VerticalAlignment = 'Center'
        $btn = New-Object System.Windows.Controls.Button; $btn.Content = (T 'Вернуть'); $btn.Style = $Window.FindResource('BtnGood'); $btn.Tag = $s.Session; $btn.Margin = '0'
        $btn.Add_Click({ Set-Status 'Возвращаю записи реестра…'; $n = Restore-RegSession $this.Tag; Write-Log "Реестр: восстановлено файлов $n"; Set-Status "Восстановлено веток: $n."; Load-RegBackups })
        [System.Windows.Controls.Grid]::SetColumn($info, 0); [System.Windows.Controls.Grid]::SetColumn($btn, 1)
        $g.Children.Add($info) | Out-Null; $g.Children.Add($btn) | Out-Null
        $ui.RegBackupPanel.Children.Add($g) | Out-Null
    }
}
$ui.BtnRegScan.Add_Click({
    Set-Busy $true; $total = 0
    foreach ($c in $RegCategories) {
        Set-Status "Проверяю реестр: $($c.Name)…"
        $n = @(Find-RegItems $c).Count; $total += $n
        $RegBoxes[$c.Id].Title.Text = "$(T $c.Name)    $n"
    }
    $script:regFound = $total; Update-BigNumber 'NavReg'; Set-Busy $false
    $ui.BtnRegClean.IsEnabled = ($total -gt 0)
    Set-Status $(if ($total -gt 0) { "Найдено записей: $total. Перед очисткой каждая ветка будет сохранена в .reg." } else { 'Лишних записей не найдено.' })
})
$ui.BtnRegClean.Add_Click({
    $ui.BtnRegClean.IsEnabled = $false; Set-Busy $true
    $session = Get-Date -Format 'yyyyMMdd_HHmmss'; $done = 0
    foreach ($c in $RegCategories) {
        if (-not $RegBoxes[$c.Id].Box.IsChecked) { continue }
        Set-Status "Сохраняю копию и чищу: $($c.Name)…"
        $done += Clean-RegCategory $c $session
        $RegBoxes[$c.Id].Title.Text = (T $c.Name)
    }
    $script:regFound = 0; Update-BigNumber 'NavReg'; Set-Busy $false; Write-Log "Реестр: удалено записей $done, сеанс $session"
    Set-Status "Готово. Удалено записей: $done. Резервная копия сохранена, её можно вернуть ниже."
    Load-RegBackups
})
Load-RegBackups

# ----- Службы -----
$SvcBoxes = @()
foreach ($s in $ServicesList) {
    $state = Get-ServiceEnabled $s.Name
    if ($null -eq $state) { continue }
    $row = New-CheckRow $s.Title $s.Hint $state $s.Name
    $row.Box.Add_Click({
        $name = $this.Tag
        try { Set-ServiceState $name ([bool]$this.IsChecked); $state = if ($this.IsChecked) { 'включена' } else { 'выключена' }; Write-Log "Служба $name $state"; Set-Status "Служба «$name» $state." }
        catch { Set-Status "Не удалось изменить службу: $($_.Exception.Message)" }
        Update-BigNumber 'NavSvc'
    })
    $ui.SvcPanel.Children.Add($row.Box) | Out-Null; $SvcBoxes += $row.Box
}

# ----- Автозагрузка -----
function Load-Startup {
    $ui.StartupPanel.Children.Clear()
    $entries = Get-StartupEntries
    if (-not $entries -or $entries.Count -eq 0) { $ui.StartupPanel.Children.Add((New-Text 'В автозагрузке ничего нет.')) | Out-Null; return }
    foreach ($e in $entries) {
        $row = New-CheckRow "$($e.Name)   ($(T $e.Source))" $e.Command $e.Enabled $e
        $row.Box.Add_Click({
            $entry = $this.Tag
            try { Set-ApprovedState $entry.Approved $entry.Name ([bool]$this.IsChecked); $state = if ($this.IsChecked) { 'включена' } else { 'отключена' }; Write-Log "Автозагрузка «$($entry.Name)» $state"; Set-Status "Автозагрузка «$($entry.Name)» $state. Подействует после перезагрузки." }
            catch { Set-Status "Не удалось изменить «$($entry.Name)»: $($_.Exception.Message)" }
            Update-BigNumber 'NavStartup'
        })
        $ui.StartupPanel.Children.Add($row.Box) | Out-Null
    }
}
$ui.BtnStartupRefresh.Add_Click({ Load-Startup })

# ----- Ускорение -----
$ui.BtnMem.Add_Click({
    $before = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1KB
    Set-Busy $true; Set-Status 'Освобождаю память…'
    foreach ($p in Get-Process) { try { [Sweep.Mem]::EmptyWorkingSet($p.Handle) | Out-Null } catch {} }
    Start-Sleep -Milliseconds 800
    $after = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1KB
    $ui.MemText.Text = ((T 'Свободно сейчас: {0}') -f (Format-Size $after)); Set-Busy $false; Update-BigNumber 'NavBoost'
    Set-Status "Память освобождена. Прибавилось: $(Format-Size ([math]::Max(0, $after - $before)))."
})
$ui.BtnDisk.Add_Click({
    $ui.BtnDisk.IsEnabled = $false; Set-Busy $true
    foreach ($v in (Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' -and $_.FileSystem -eq 'NTFS' })) {
        Set-Status "Оптимизирую диск $($v.DriveLetter): …"
        try { Optimize-Volume -DriveLetter $v.DriveLetter -ErrorAction Stop } catch { Write-Log "Диск $($v.DriveLetter): $($_.Exception.Message)" }
    }
    $ui.DiskText.Text = (T 'Готово'); Set-Busy $false; Set-Status 'Диски оптимизированы.'; $ui.BtnDisk.IsEnabled = $true
})
$ui.BtnUpdate.Add_Click({ Start-Process 'ms-settings:windowsupdate' })

# ----- Тема -----
$Themes = @{
    Dark  = @{ WinBg='#0D0B1A'; SideBg='#110E24'; CardBg='#181433'; CardBorder='#262052'; CardHover='#1E1940'; TextMain='#EDE9FE'; TextMuted='#8B86B0'; AccentSoft='#2A1F5E'; SoftBtn='#221C47'; StatusBg='#0A0816' }
    Light = @{ WinBg='#F5F3FF'; SideBg='#EDE9FE'; CardBg='#FFFFFF'; CardBorder='#DDD6FE'; CardHover='#F3F0FF'; TextMain='#1E1B3A'; TextMuted='#6B6790'; AccentSoft='#DDD6FE'; SoftBtn='#E4DEFA'; StatusBg='#1E1B3A' }
}
$script:theme = 'Dark'
$BrushConv = New-Object System.Windows.Media.BrushConverter
function Apply-Theme([string]$name) {
    try {
        $script:theme = $name
        foreach ($k in $Themes[$name].Keys) {
            $brush = $BrushConv.ConvertFromString($Themes[$name][$k]); $brush.Freeze()
            $Window.Resources[$k] = $brush
        }
        $ui.BtnTheme.Content = T $(if ($name -eq 'Dark') { 'Светлая тема' } else { 'Тёмная тема' })
        Save-Setting 'theme' $name
    } catch { Write-Log "Тема: $($_.Exception.Message)"; Set-Status "Не удалось переключить тему: $($_.Exception.Message)" }
}
try { if ((Get-Settings).theme -eq 'Light') { Apply-Theme 'Light' } } catch {}
$ui.BtnTheme.Content = T $(if ($script:theme -eq 'Dark') { 'Светлая тема' } else { 'Тёмная тема' })
$ui.BtnTheme.Add_Click({ if ($script:theme -eq 'Dark') { Apply-Theme 'Light' } else { Apply-Theme 'Dark' } })
$ui.BtnLang.Content = $(if ($script:Lang -eq 'en') { 'RU' } else { 'EN' })
$ui.BtnLang.Add_Click({
    Save-Setting 'lang' $(if ($script:Lang -eq 'en') { 'ru' } else { 'en' })
    Set-Status (T 'Перезапуск для смены языка…')
    $self = if ($PSCommandPath) { $PSCommandPath } else { [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName }
    if ($self -like '*.ps1') { Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$self`"" } else { Start-Process $self }
    $Window.Close()
})

# ----- Диски -----
$script:selectedDrive = $env:SystemDrive.TrimEnd(':')
$script:bigBoxes = @()
function Get-SelectedVolume { return (Get-Volume -DriveLetter $script:selectedDrive -ErrorAction SilentlyContinue) }
function Load-Disks {
    $ui.DiskPanel.Children.Clear()
    foreach ($v in (Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' -and $_.Size -gt 0 } | Sort-Object DriveLetter)) {
        $rb = New-Object System.Windows.Controls.RadioButton; $rb.GroupName = 'disks'; $rb.Tag = [string]$v.DriveLetter; $rb.Cursor = 'Hand'; $rb.Margin = '0,6'
        $rb.IsChecked = ($v.DriveLetter -eq $script:selectedDrive)
        $sp = New-Object System.Windows.Controls.StackPanel; $sp.Margin = '8,0,0,0'
        $label = if ($v.FileSystemLabel) { "$($v.FileSystemLabel) ($($v.DriveLetter):)" } else { (T 'Диск {0}:') -f $v.DriveLetter }
        $sp.Children.Add((New-Text $label 'TextMain' 14 $true)) | Out-Null
        $used = [long]($v.Size - $v.SizeRemaining); $pct = [math]::Round($used * 100 / $v.Size)
        $bar = New-Object System.Windows.Controls.Border; $bar.Height = 8; $bar.CornerRadius = '4'; $bar.Background = '#2F2A5A'; $bar.Margin = '0,6,0,4'; $bar.Width = 420; $bar.HorizontalAlignment = 'Left'
        $fill = New-Object System.Windows.Controls.Border; $fill.CornerRadius = '4'; $fill.HorizontalAlignment = 'Left'; $fill.Width = [math]::Max(4, 420 * $pct / 100)
        $fill.Background = $(if ($pct -ge 90) { '#EF4444' } elseif ($pct -ge 75) { '#FBBF24' } else { $Window.FindResource('AccentGrad') })
        $bar.Child = $fill; $sp.Children.Add($bar) | Out-Null
        $sp.Children.Add((New-Text ((T 'занято {0} из {1}  ·  свободно {2}  ·  {3}%') -f (Format-Size $used), (Format-Size ([long]$v.Size)), (Format-Size ([long]$v.SizeRemaining)), $pct) 'TextMuted' 12)) | Out-Null
        $rb.Content = $sp
        $rb.Add_Checked({ $script:selectedDrive = [string]$this.Tag; Update-BigNumber 'NavDisk'; $ui.BigFilesTitle.Text = ((T 'Крупные файлы на диске {0}:') -f $this.Tag) })
        $ui.DiskPanel.Children.Add($rb) | Out-Null
    }
}
$ui.BtnBigScan.Add_Click({
    $ui.BtnBigScan.IsEnabled = $false; $ui.BtnBigClean.IsEnabled = $false; Set-Busy $true
    $root = "$($script:selectedDrive):\"
    Set-Status "Ищу крупные файлы на диске $($script:selectedDrive): … На большом диске это может занять минуту."
    $skip = @("$env:WINDIR", "$env:ProgramFiles", "${env:ProgramFiles(x86)}", "$env:ProgramData", "$root`$Recycle.Bin", "${root}System Volume Information") | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\').ToLowerInvariant() }
    $files = Get-ChildItem -Path $root -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object {
        $d = $_.DirectoryName.ToLowerInvariant(); $ok = $true
        foreach ($sk in $skip) { if ($d -eq $sk -or $d.StartsWith($sk + '\')) { $ok = $false; break } }
        $ok -and $_.Length -gt 50MB -and $_.Directory.FullName -ne $root
    } | Sort-Object Length -Descending | Select-Object -First 30
    $ui.BigFilesPanel.Children.Clear(); $script:bigBoxes = @()
    if (-not $files) { $ui.BigFilesPanel.Children.Add((New-Text 'Файлов крупнее 50 МБ вне системных папок не найдено.' 'TextMuted')) | Out-Null }
    foreach ($f in $files) {
        $row = New-CheckRow "$($f.Name)    $(Format-Size $f.Length)" $f.DirectoryName $false $f.FullName
        $row.Box.Add_Click({ $ui.BtnBigClean.IsEnabled = (@($script:bigBoxes | Where-Object { $_.IsChecked }).Count -gt 0) })
        $ui.BigFilesPanel.Children.Add($row.Box) | Out-Null; $script:bigBoxes += $row.Box
    }
    Set-Busy $false; $ui.BtnBigScan.IsEnabled = $true
    Set-Status "Найдено крупных файлов: $(@($files).Count). Отметьте ненужные и нажмите «Отмеченные в карантин». Видео, архивы и образы дисков часто оказываются именно здесь."
})
$ui.BtnBigClean.Add_Click({
    $picked = @($script:bigBoxes | Where-Object { $_.IsChecked })
    if (-not $picked.Count) { return }
    $session = Get-Date -Format 'yyyyMMdd_HHmmss'
    $dest = Join-Path $Quarantine "$session\bigfiles"; New-Item -ItemType Directory -Path $dest -Force | Out-Null
    $manifest = Join-Path $Quarantine "$session\manifest.txt"; $n = 0; $freed = [long]0
    foreach ($cb in $picked) {
        $src = [string]$cb.Tag; $n++
        try { $size = (Get-Item -LiteralPath $src).Length; $target = Join-Path $dest ("{0:D3}_{1}" -f $n, (Split-Path $src -Leaf)); Move-Item -LiteralPath $src -Destination $target -Force -ErrorAction Stop; Add-Content -Path $manifest -Value "$target|$src" -Encoding UTF8; $freed += $size; $ui.BigFilesPanel.Children.Remove($cb) } catch { Write-Log "Крупный файл занят: $src" }
    }
    $script:bigBoxes = @($script:bigBoxes | Where-Object { -not $_.IsChecked }); $ui.BtnBigClean.IsEnabled = $false
    Write-Log "Крупные файлы в карантин: $(Format-Size $freed)"; Load-Quarantine; Load-Disks; Update-BigNumber 'NavDisk'
    Set-Status "В карантин перенесено: $(Format-Size $freed). Вернуть можно в разделе «Карантин»."
})
$ui.BtnDiskOpen.Add_Click({ Start-Process explorer.exe "$($script:selectedDrive):\" })

# ----- Индекс здоровья -----
function Update-Health {
    try {
        $score = 100; $tips = @()
        $junk = Get-CheckedTotal
        if ($junk -gt 5GB) { $score -= 25; $tips += 'Много мусора: запустите очистку' } elseif ($junk -gt 1GB) { $score -= 12; $tips += 'Есть что почистить' } elseif ($junk -gt 300MB) { $score -= 5 }
        $st = @($ui.StartupPanel.Children | Where-Object { $_ -is [System.Windows.Controls.CheckBox] -and $_.IsChecked }).Count
        if ($st -gt 12) { $score -= 20; $tips += "Автозагрузка перегружена: $st программ" } elseif ($st -gt 7) { $score -= 10; $tips += "В автозагрузке $st программ, часть можно выключить" }
        $sys = Get-Volume -DriveLetter ($env:SystemDrive.TrimEnd(':')) -ErrorAction SilentlyContinue
        if ($sys -and $sys.Size -gt 0) { $free = $sys.SizeRemaining / $sys.Size; if ($free -lt 0.07) { $score -= 25; $tips += 'На системном диске почти нет места' } elseif ($free -lt 0.15) { $score -= 12; $tips += 'На системном диске мало места' } }
        $priv = @($PrivBoxes.Values | Where-Object { $_.IsChecked }).Count
        if ($priv -lt 3) { $score -= 15; $tips += 'Слежка и реклама Windows включены' } elseif ($priv -lt 8) { $score -= 6; $tips += 'Часть телеметрии ещё включена' }
        $os = Get-CimInstance Win32_OperatingSystem; $up = (Get-Date) - $os.LastBootUpTime
        if ($up.TotalDays -gt 14) { $score -= 8; $tips += "Компьютер не перезагружался $([int]$up.TotalDays) дней" }
        $score = [math]::Max(5, [math]::Min(100, $score))
        $ui.HealthText.Text = "$score"
        $circ = [math]::PI * 96 / 9
        $ui.HealthRing.StrokeDashArray = New-Object System.Windows.Media.DoubleCollection(@([double]($circ * $score / 100), [double]999))
        $ui.HealthRing.Stroke = $(if ($score -ge 80) { '#34D399' } elseif ($score -ge 55) { '#FBBF24' } else { '#F87171' })
        $ui.HealthTitle.Text = T $(if ($score -ge 80) { 'Компьютер в хорошей форме' } elseif ($score -ge 55) { 'Есть что улучшить' } else { 'Компьютеру нужна забота' })
        $ui.HealthTips.Children.Clear()
        foreach ($t in ($tips | Select-Object -First 3)) { $ui.HealthTips.Children.Add((New-Text ('• ' + (T $t)) 'TextMain' 12)) | Out-Null }
        if (-not $tips) { $ui.HealthTips.Children.Add((New-Text '• Всё в порядке, так держать' 'Good' 12)) | Out-Null }
    } catch { Write-Log "Здоровье: $($_.Exception.Message)" }
}

# ----- Приложения (предустановленный мусор) -----
$BloatApps = @(
    @{ Id='Microsoft.XboxApp'; Name='Xbox'; Hint='Игровой клиент Xbox' }
    @{ Id='Microsoft.GamingApp'; Name='Xbox (новое приложение)'; Hint='Магазин игр Xbox' }
    @{ Id='Microsoft.XboxGamingOverlay'; Name='Xbox Game Bar'; Hint='Оверлей для записи игр. Если не играете, не нужен' }
    @{ Id='Microsoft.ZuneMusic'; Name='Media Player / Музыка Groove'; Hint='Проигрыватель Microsoft' }
    @{ Id='Microsoft.ZuneVideo'; Name='Кино и ТВ'; Hint='Видеопроигрыватель и магазин фильмов' }
    @{ Id='Microsoft.BingNews'; Name='Новости'; Hint='Лента новостей Microsoft' }
    @{ Id='Microsoft.BingWeather'; Name='Погода'; Hint='Погода от MSN' }
    @{ Id='Microsoft.BingSearch'; Name='Поиск Bing'; Hint='Веб-поиск в меню Пуск' }
    @{ Id='Microsoft.GetHelp'; Name='Техническая поддержка'; Hint='Чат с поддержкой Microsoft' }
    @{ Id='Microsoft.Getstarted'; Name='Советы'; Hint='Приложение «Начало работы»' }
    @{ Id='Microsoft.MicrosoftSolitaireCollection'; Name='Solitaire Collection'; Hint='Пасьянсы с рекламой' }
    @{ Id='Microsoft.People'; Name='Люди'; Hint='Контакты Microsoft' }
    @{ Id='Microsoft.MicrosoftOfficeHub'; Name='Office Hub'; Hint='Реклама подписки Microsoft 365' }
    @{ Id='Microsoft.SkypeApp'; Name='Skype'; Hint='Мессенджер' }
    @{ Id='Microsoft.WindowsFeedbackHub'; Name='Центр отзывов'; Hint='Отправка отзывов в Microsoft' }
    @{ Id='Microsoft.Microsoft3DViewer'; Name='3D Viewer'; Hint='Просмотр 3D-моделей' }
    @{ Id='Microsoft.MixedReality.Portal'; Name='Портал смешанной реальности'; Hint='Нужен только для VR-шлема' }
    @{ Id='Microsoft.WindowsMaps'; Name='Карты'; Hint='Офлайн-карты Windows' }
    @{ Id='Microsoft.549981C3F5F10'; Name='Кортана'; Hint='Голосовой помощник' }
    @{ Id='Clipchamp.Clipchamp'; Name='Clipchamp'; Hint='Видеоредактор с подпиской' }
    @{ Id='Microsoft.Todos'; Name='Microsoft To Do'; Hint='Список задач' }
    @{ Id='MicrosoftTeams'; Name='Teams (личный)'; Hint='Чат Teams для дома' }
    @{ Id='MSTeams'; Name='Teams'; Hint='Чат Teams' }
    @{ Id='Microsoft.PowerAutomateDesktop'; Name='Power Automate'; Hint='Автоматизация для бизнеса' }
    @{ Id='Microsoft.Copilot'; Name='Copilot'; Hint='Приложение помощника Microsoft' }
    @{ Id='Microsoft.OutlookForWindows'; Name='Outlook (новый)'; Hint='Почтовый клиент с рекламой' }
    @{ Id='Microsoft.MicrosoftJournal'; Name='Journal'; Hint='Рукописные заметки' }
    @{ Id='Microsoft.Whiteboard'; Name='Whiteboard'; Hint='Доска для рисования' }
    @{ Id='king.com.CandyCrushSaga'; Name='Candy Crush Saga'; Hint='Игра' }
    @{ Id='king.com.CandyCrushSodaSaga'; Name='Candy Crush Soda'; Hint='Игра' }
    @{ Id='SpotifyAB.SpotifyMusic'; Name='Spotify (предустановка)'; Hint='Рекламная предустановка' }
    @{ Id='Disney.37853FC22B2CE'; Name='Disney+'; Hint='Рекламная предустановка' }
    @{ Id='BytedancePte.Ltd.TikTok'; Name='TikTok'; Hint='Рекламная предустановка' }
    @{ Id='Facebook.InstagramBeta'; Name='Instagram'; Hint='Рекламная предустановка' }
    @{ Id='AmazonVideo.PrimeVideo'; Name='Prime Video'; Hint='Рекламная предустановка' }
)
$script:appsFound = -1; $script:appBoxes = @()
$ui.BtnAppsScan.Add_Click({
    Set-Busy $true; Set-Status 'Проверяю установленные приложения…'
    $ui.AppsPanel.Children.Clear(); $script:appBoxes = @()
    $installed = Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name -Unique
    $n = 0
    foreach ($a in $BloatApps) {
        if ($installed -notcontains $a.Id) { continue }
        $n++
        $row = New-CheckRow $a.Name $a.Hint $false $a.Id
        $row.Box.Add_Click({ $ui.BtnAppsRemove.IsEnabled = (@($script:appBoxes | Where-Object { $_.IsChecked }).Count -gt 0) })
        $ui.AppsPanel.Children.Add($row.Box) | Out-Null; $script:appBoxes += $row.Box
    }
    if ($n -eq 0) { $ui.AppsPanel.Children.Add((New-Text 'Лишних предустановленных приложений не найдено.' 'TextMuted')) | Out-Null }
    $script:appsFound = $n; Update-BigNumber 'NavApps'; Set-Busy $false
    Set-Status "Найдено предустановленных приложений: $n. Отметьте ненужные и нажмите «Удалить отмеченные»."
})
$ui.BtnAppsRemove.Add_Click({
    $picked = @($script:appBoxes | Where-Object { $_.IsChecked }); if (-not $picked.Count) { return }
    $ui.BtnAppsRemove.IsEnabled = $false; Set-Busy $true; $done = 0
    foreach ($cb in $picked) {
        $id = [string]$cb.Tag; Set-Status "Удаляю $id…"
        try {
            Get-AppxPackage -Name $id -AllUsers -ErrorAction SilentlyContinue | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
            Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq $id } | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Out-Null
            $ui.AppsPanel.Children.Remove($cb); $done++; Write-Log "Удалено приложение $id"
        } catch { Write-Log "Приложение $id не удалилось: $($_.Exception.Message)" }
    }
    $script:appBoxes = @($script:appBoxes | Where-Object { -not $_.IsChecked }); $script:appsFound = $script:appBoxes.Count; Update-BigNumber 'NavApps'; Set-Busy $false
    Set-Status "Удалено приложений: $done. Вернуть любое можно из Microsoft Store."
})
$ui.BtnAppsStore.Add_Click({ Start-Process 'ms-windows-store://home' })

# ----- Автоочистка по расписанию -----
$TaskName = 'Sweep Auto Clean'
function Get-SelfPath { if ($PSCommandPath) { return $PSCommandPath }; return [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName }
function Update-SchedText {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($t) { $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue; $next = if ($info -and $info.NextRunTime) { $info.NextRunTime.ToString('d MMMM, HH:mm') } else { (T 'скоро') }; $ui.SchedText.Text = ((T 'Включено. Следующий запуск: {0}') -f $next); $ui.SchedBox.IsChecked = $true }
    else { $ui.SchedText.Text = (T 'Выключено'); $ui.SchedBox.IsChecked = $false }
}
$ui.SchedBox.Add_Click({
    try {
        if ($ui.SchedBox.IsChecked) {
            $self = Get-SelfPath
            if ($self -like '*.ps1') { $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$self`" -auto" }
            else { $action = New-ScheduledTaskAction -Execute $self -Argument '-auto' }
            $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 12:00
            $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfIdle:$false -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
            Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User $env:USERNAME -Force | Out-Null
            Write-Log 'Расписание включено'; Set-Status 'Автоочистка включена: каждое воскресенье в 12:00, или при первом включении компьютера после этого.'
        } else {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Log 'Расписание выключено'; Set-Status 'Автоочистка выключена.'
        }
    } catch { Set-Status "Не удалось изменить расписание: $($_.Exception.Message)" }
    Update-SchedText
})
Update-SchedText

# ----- Система -----
$script:sysReport = ''
function Add-SysRow([string]$label, [string]$value) {
    if (-not $value) { $value = (T 'нет данных') }
    $g = New-Object System.Windows.Controls.Grid; $g.Margin = '0,5'
    $c1 = New-Object System.Windows.Controls.ColumnDefinition; $c1.Width = '200'; $c2 = New-Object System.Windows.Controls.ColumnDefinition; $c2.Width = '*'
    $g.ColumnDefinitions.Add($c1); $g.ColumnDefinitions.Add($c2)
    $l = New-Text (T $label) 'TextMuted' 13; $v = New-Object System.Windows.Controls.TextBlock; $v.Text = $value; $v.FontSize = 13; $v.FontWeight = 'SemiBold'; $v.TextWrapping = 'Wrap'; $v.SetResourceReference([System.Windows.Controls.TextBlock]::ForegroundProperty, 'TextMain')
    [System.Windows.Controls.Grid]::SetColumn($l, 0); [System.Windows.Controls.Grid]::SetColumn($v, 1)
    $g.Children.Add($l) | Out-Null; $g.Children.Add($v) | Out-Null
    $ui.SysPanel.Children.Add($g) | Out-Null
    $script:sysReport += "{0}: {1}`r`n" -f (T $label), $value
}
function Add-SysHeader([string]$text) { $t = New-Text $text 'TextMain' 15 $true; $t.Margin = '0,14,0,4'; $ui.SysPanel.Children.Add($t) | Out-Null; $script:sysReport += "`r`n[$text]`r`n" }
function Get-Temperatures {
    $out = @()
    try { foreach ($z in (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop)) { $c = [math]::Round(($z.CurrentTemperature / 10) - 273.15, 1); if ($c -gt 0 -and $c -lt 130) { $out += "$c °C" } } } catch {}
    if ($out.Count -gt 0) { return ($out -join ', ') }
    return (T 'недоступно без драйвера (датчики не отдаёт Windows)')
}
$ui.BtnSysInfo.Add_Click({
    $ui.BtnSysInfo.IsEnabled = $false; $ui.SysPanel.Children.Clear(); $script:sysReport = ''; Set-Busy $true
    Set-Status 'Собираю сведения о системе…'
    try {
        $os = Get-CimInstance Win32_OperatingSystem; $cs = Get-CimInstance Win32_ComputerSystem
        Add-SysHeader 'Система'
        Add-SysRow 'Windows' "$($os.Caption) $($os.Version) (сборка $($os.BuildNumber))"
        Add-SysRow 'Компьютер' "$($cs.Manufacturer) $($cs.Model)"
        $up = (Get-Date) - $os.LastBootUpTime; Add-SysRow 'Работает без перезагрузки' ((T '{0} д {1} ч {2} мин') -f $up.Days, $up.Hours, $up.Minutes)
        Add-SysHeader 'Процессор'
        foreach ($cpu in (Get-CimInstance Win32_Processor)) { Add-SysRow 'Модель' $cpu.Name.Trim(); Add-SysRow 'Ядра / потоки' "$($cpu.NumberOfCores) / $($cpu.NumberOfLogicalProcessors)"; Add-SysRow 'Частота' "$($cpu.MaxClockSpeed) МГц"; Add-SysRow 'Загрузка сейчас' "$($cpu.LoadPercentage) %" }
        Add-SysHeader 'Видеокарта'
        foreach ($gpu in (Get-CimInstance Win32_VideoController)) { Add-SysRow 'Модель' $gpu.Name; if ($gpu.AdapterRAM -gt 0) { Add-SysRow 'Видеопамять' (Format-Size ([long]$gpu.AdapterRAM)) }; Add-SysRow 'Драйвер' ((T '{0} от {1}') -f $gpu.DriverVersion, $gpu.DriverDate.ToString('d')) }
        Add-SysHeader 'Материнская плата'
        $mb = Get-CimInstance Win32_BaseBoard; Add-SysRow 'Модель' "$($mb.Manufacturer) $($mb.Product)"
        $bios = Get-CimInstance Win32_BIOS; Add-SysRow 'BIOS' ((T '{0} от {1}') -f $bios.SMBIOSBIOSVersion, $bios.ReleaseDate.ToString('d'))
        Add-SysHeader 'Оперативная память'
        $mods = Get-CimInstance Win32_PhysicalMemory; $total = ($mods | Measure-Object -Property Capacity -Sum).Sum
        Add-SysRow 'Всего' ((T '{0} ({1} план.)') -f (Format-Size ([long]$total)), $mods.Count)
        foreach ($m in $mods) { Add-SysRow ((T 'Планка {0}') -f $m.DeviceLocator) ("{0}, {1} МГц, {2}" -f (Format-Size ([long]$m.Capacity)), $m.Speed, $m.Manufacturer) }
        Add-SysRow 'Свободно сейчас' (Format-Size ([long]($os.FreePhysicalMemory * 1KB)))
        Add-SysHeader 'Диски'
        foreach ($d in (Get-PhysicalDisk -ErrorAction SilentlyContinue)) { Add-SysRow $d.FriendlyName ("{0}, {1}, {2}" -f (Format-Size ([long]$d.Size)), $d.MediaType, $d.BusType) }
        foreach ($v in (Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' })) { Add-SysRow ((T 'Диск {0}:') -f $v.DriveLetter) ((T 'свободно {0} из {1}') -f (Format-Size ([long]$v.SizeRemaining)), (Format-Size ([long]$v.Size))) }
        Add-SysHeader 'Температура'
        Add-SysRow 'Датчики' (Get-Temperatures)
        $ui.BtnSysCopy.IsEnabled = $true
        Set-Status 'Сведения собраны. Кнопка «Скопировать» положит их в буфер обмена текстом.'
    } catch { Set-Status "Не удалось собрать часть сведений: $($_.Exception.Message)" }
    Set-Busy $false; $ui.BtnSysInfo.IsEnabled = $true
})
$ui.BtnSysCopy.Add_Click({ try { [System.Windows.Clipboard]::SetText($script:sysReport); Set-Status 'Скопировано в буфер обмена.' } catch { Set-Status 'Не удалось скопировать.' } })

# ----- Карантин -----
function Load-Quarantine {
    $ui.QPanel.Children.Clear()
    $sessions = Get-QuarantineSessions
    if (-not $sessions -or $sessions.Count -eq 0) { $ui.QPanel.Children.Add((New-Text 'Карантин пуст.' 'TextMuted')) | Out-Null; return }
    foreach ($s in $sessions) {
        $row = New-Object System.Windows.Controls.Grid; $row.Margin = '0,6'
        $c1 = New-Object System.Windows.Controls.ColumnDefinition; $c1.Width = '*'; $c2 = New-Object System.Windows.Controls.ColumnDefinition; $c2.Width = 'Auto'
        $row.ColumnDefinitions.Add($c1); $row.ColumnDefinitions.Add($c2)
        $info = New-Text ((T 'Очистка {0}   {1}') -f $s.Date, (Format-Size $s.Size)) 'TextMain' 14 $true; $info.VerticalAlignment = 'Center'
        $btn = New-Object System.Windows.Controls.Button; $btn.Content = (T 'Вернуть'); $btn.Style = $Window.FindResource('BtnGood'); $btn.Tag = $s.Path; $btn.Margin = '0'
        $btn.Add_Click({ Set-Status 'Возвращаю файлы на место…'; $n = Restore-Session $this.Tag; Write-Log "Возвращено объектов: $n"; Set-Status "Возвращено объектов: $n."; Load-Quarantine; Update-BigNumber 'NavQ' })
        [System.Windows.Controls.Grid]::SetColumn($info, 0); [System.Windows.Controls.Grid]::SetColumn($btn, 1)
        $row.Children.Add($info) | Out-Null; $row.Children.Add($btn) | Out-Null
        $ui.QPanel.Children.Add($row) | Out-Null
    }
}
$ui.BtnQRefresh.Add_Click({ Load-Quarantine; Update-BigNumber 'NavQ' })
$ui.BtnQPurge.Add_Click({
    if ($ui.BtnQPurge.Content -ne (T 'Точно удалить? Нажмите ещё раз')) { $ui.BtnQPurge.Content = (T 'Точно удалить? Нажмите ещё раз'); return }
    Set-Status 'Удаляю карантин…'
    Get-ChildItem -Path $Quarantine -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $ui.BtnQPurge.Content = (T 'Удалить весь карантин навсегда'); Write-Log 'Карантин удалён'
    Set-Status 'Карантин очищен, место освобождено окончательно.'; Load-Quarantine; Update-BigNumber 'NavQ'
})

# =====================================================================
#  ОБНОВЛЕНИЯ через GitHub Releases. Репозиторий указывается в $UpdateRepo (например 'ivanov/sweep').
#  Проверка идёт в фоне отдельным процессом, окно не замирает. Ничего, кроме номера версии, не отправляется.
# =====================================================================
$AppVersion = '0.8'
$UpdateRepo = 'pabloescobarbl-ops/sweep'
$UpdateDir  = Join-Path $env:TEMP 'Sweep-update'
New-Item -ItemType Directory -Path $UpdateDir -Force | Out-Null
$script:updateInfo = $null
function Start-UpdateCheck {
    if (-not $UpdateRepo) { return }
    $status = Join-Path $UpdateDir 'check.json'; if (Test-Path $status) { Remove-Item $status -Force -ErrorAction SilentlyContinue }
    $job = @"
`$ProgressPreference = 'SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
  `$rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/$UpdateRepo/releases/latest' -Headers @{ 'User-Agent' = 'Sweep/$AppVersion' } -TimeoutSec 20
  `$asset = `$rel.assets | Where-Object { `$_.name -like 'Sweep-Setup-*.exe' } | Select-Object -First 1
  @{ tag = `$rel.tag_name; url = `$asset.browser_download_url; notes = [string]`$rel.body } | ConvertTo-Json | Set-Content -Path '$status' -Encoding UTF8
} catch { @{ error = `$_.Exception.Message } | ConvertTo-Json | Set-Content -Path '$status' -Encoding UTF8 }
"@
    $jobFile = Join-Path $UpdateDir 'check.ps1'; Set-Content -Path $jobFile -Value $job -Encoding UTF8
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$jobFile`"" -WindowStyle Hidden
    $script:updateWatch = $true
}
function Compare-Version([string]$a, [string]$b) { try { return ([version]($a -replace '[^\d\.]', '')).CompareTo([version]($b -replace '[^\d\.]', '')) } catch { return 0 } }
function Read-UpdateStatus {
    $status = Join-Path $UpdateDir 'check.json'
    if (-not (Test-Path $status)) { return }
    $script:updateWatch = $false
    try { $info = Get-Content $status -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return }
    if ($info.error) { Set-Status "Проверка обновлений: $($info.error)"; return }
    if ((Compare-Version $info.tag $AppVersion) -gt 0 -and $info.url) {
        $script:updateInfo = $info
        $ui.BtnUpdateApp.Content = ((T 'Обновить до {0}') -f $info.tag); $ui.BtnUpdateApp.Visibility = 'Visible'
        Set-Status "Доступна новая версия $($info.tag). Нажмите «Обновить до $($info.tag)»."
    } else { Set-Status "У вас последняя версия ($AppVersion)." }
}
$UpdateTimer = New-Object System.Windows.Threading.DispatcherTimer; $UpdateTimer.Interval = [TimeSpan]::FromSeconds(2)
$UpdateTimer.Add_Tick({ if ($script:updateWatch) { Read-UpdateStatus } })
$UpdateTimer.Start()
$ui.BtnCheckUpdate.Add_Click({ if (-not $UpdateRepo) { Set-Status 'Репозиторий обновлений не указан.'; return }; Set-Status 'Проверяю обновления…'; Start-UpdateCheck })
$ui.BtnUpdateApp.Add_Click({
    if (-not $script:updateInfo) { return }
    $ui.BtnUpdateApp.IsEnabled = $false; Set-Status "Скачиваю $($script:updateInfo.tag)…"
    try {
        $ProgressPreference = 'SilentlyContinue'
        $file = Join-Path $UpdateDir ([IO.Path]::GetFileName($script:updateInfo.url))
        Invoke-WebRequest -Uri $script:updateInfo.url -OutFile $file -UseBasicParsing -TimeoutSec 300
        UPDATE_SweepLY
    } catch { Set-Status "Не удалось обновить: $($_.Exception.Message)"; $ui.BtnUpdateApp.IsEnabled = $true }
})

$Window.Add_Loaded({ Load-Startup; Load-Quarantine; Load-Disks; Start-Scan; Update-Tiles })
$Window.ShowDialog() | Out-Null
