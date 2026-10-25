# Сборка Sweep.exe из Sweep.ps1. Запускать на Windows: правой кнопкой -> «Выполнить с помощью PowerShell»,
# или в PowerShell: Set-ExecutionPolicy -Scope Process Bypass; .\build-exe.ps1
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-Location $PSScriptRoot
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host 'Ставлю модуль ps2exe (один раз, из галереи PowerShell)…'
    try { Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser | Out-Null } catch {}
    Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction SilentlyContinue
    Install-Module ps2exe -Scope CurrentUser -Force -AllowClobber
}
Import-Module ps2exe
Invoke-ps2exe -inputFile '.\Sweep.ps1' -outputFile '.\Sweep.exe' -iconFile '.\sweep.ico' `
    -noConsole -STA -requireAdmin -x64 `
    -title 'Sweep' -description 'Чистка, приватность и ускорение Windows' -company 'Sweep' -product 'Sweep' -version "0.7.0.0" -copyright 'MIT'
Write-Host ''
Write-Host 'Готово: Sweep.exe лежит рядом с этим файлом.' -ForegroundColor Green
Write-Host 'Теперь можно собрать установщик: build-setup.bat (нужен Inno Setup).'
