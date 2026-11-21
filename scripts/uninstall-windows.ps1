# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# uninstall-windows.ps1 - removes what scripts\install-windows.ps1 created.

<#
.SYNOPSIS
    Removes what scripts\install-windows.ps1 created.
.DESCRIPTION
    The articles you saved are never touched. The log file and the settings are kept unless you ask for them to be
    deleted.
.PARAMETER RemoveGtk
    Also delete the GTK runtime the installer downloaded (%LOCALAPPDATA%\karamws\gtk).
.PARAMETER RemoveData
    Also delete the log file and the settings of KaramWS (%LOCALAPPDATA%\karamws, %APPDATA%\karamws). The articles
    you saved are in the folder you chose, not here. Cannot be undone.
.PARAMETER Force
    Do not ask for confirmation before -RemoveData deletes anything.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\uninstall-windows.ps1 -RemoveGtk -RemoveData
#>
[CmdletBinding()]
param(
    [switch]$RemoveGtk,
    [switch]$RemoveData,
    [switch]$Force
)

Set-StrictMode -Version 2.0

# This script is for Windows only; say so clearly instead of failing on a missing %LOCALAPPDATA%.
if ($env:OS -ne 'Windows_NT') {
    Write-Host ('ERR This script is for Windows. On Linux use scripts/install-debian.sh or ' +
                'scripts/install-arch.sh.') -ForegroundColor Red
    exit 1
}
$ErrorActionPreference = 'Stop'

$AppId       = 'io.github.AbuKaram01.KaramWS'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataRoot    = Join-Path $env:LOCALAPPDATA 'karamws'
$ConfigRoot  = Join-Path $env:APPDATA 'karamws'

function Info($Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Remove-IfPresent([string]$Path) {
    if (Test-Path $Path) { Remove-Item $Path -Recurse -Force; Info "Removed $Path" }
}

if ($RemoveData -and -not $Force) {
    $answer = Read-Host ('This deletes the log file and the settings of KaramWS (not the articles you saved). ' +
                         'Type YES to continue')
    if ($answer -ne 'YES') { Write-Host 'Nothing was deleted.'; exit 1 }
}

Remove-IfPresent (Join-Path ([Environment]::GetFolderPath('Programs')) 'KaramWS.lnk')
Remove-IfPresent (Join-Path $ProjectRoot '.venv')
# The Chromium the installer carried or downloaded, and the one in a checkout; it is not your data.
Remove-IfPresent (Join-Path $ProjectRoot 'browsers')
# The GTK runtime the installer carried (the note beside it says it was prepared by the build, not by you).
$carriedGtk = Join-Path $ProjectRoot 'gtk'
if (Test-Path (Join-Path $carriedGtk 'gvsbuild-release.txt')) { Remove-IfPresent $carriedGtk }
Remove-IfPresent "HKCU:\Software\Classes\AppUserModelId\$AppId"
[Environment]::SetEnvironmentVariable('KARAMWS_GTK_DIR', $null, 'User')

if ($RemoveGtk) { Remove-IfPresent (Join-Path $DataRoot 'gtk') }
if ($RemoveData) {
    Remove-IfPresent $ConfigRoot
    Get-ChildItem $DataRoot -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne 'gtk' -or $RemoveGtk } |
        ForEach-Object { Remove-IfPresent $_.FullName }
    if ((Test-Path $DataRoot) -and -not (Get-ChildItem $DataRoot -Force)) { Remove-Item $DataRoot -Force }
}

Write-Host 'Done.'
if (-not $RemoveData) { Write-Host "Your data is still in $DataRoot and $ConfigRoot (use -RemoveData to delete it)." }
