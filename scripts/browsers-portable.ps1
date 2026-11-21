# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# browsers-portable.ps1 - the Chromium that Playwright drives, as a folder that can travel inside the installer.
#
# Playwright keeps the browsers it downloads in a folder that PLAYWRIGHT_BROWSERS_PATH names. Here that folder is
# the target, so the browser travels with the installer and the installed program finds it beside its virtual
# environment (src\karamws\core\paths.py): nothing is downloaded when KaramWS is installed. Nothing is installed on
# the computer and nothing is written outside the target folder and a temporary one.
#
# Dot-source this file to use its functions:
#
#     Get-PortableBrowsers -Target <folder> -Python <python.exe> -Wheelhouse <folder>
#     Test-BrowsersFolder  <folder>
#
# Playwright itself is taken from the wheelhouse that scripts\python-bundle.ps1 builds, so the browser is the very
# one that version of Playwright expects (each Playwright release is tied to one Chromium build).

# Why the last attempt to prepare the browsers failed ('' when it did not).
$script:BrowsersProblem = ''

<#
.SYNOPSIS
    Whether a folder holds the Chromium that Playwright launches (headless) and the full Chromium beside it.
#>
function Test-BrowsersFolder([string]$Folder) {
    if (-not $Folder -or -not (Test-Path -LiteralPath $Folder)) { return $false }
    return [bool](Get-ChildItem -LiteralPath $Folder -Directory -Filter 'chromium-*' -ErrorAction SilentlyContinue) -and
           [bool](Get-ChildItem -LiteralPath $Folder -Directory -Filter 'chromium_headless_shell-*' `
                  -ErrorAction SilentlyContinue)
}

<#
.SYNOPSIS
    Downloads Chromium into -Target, with the Playwright of the wheelhouse.
.OUTPUTS
    $true when -Target holds a complete Chromium, else $false (and $script:BrowsersProblem says why).
#>
function Get-PortableBrowsers {
    param(
        [Parameter(Mandatory)][string]$Target,
        [Parameter(Mandatory)][string]$Python,
        [Parameter(Mandatory)][string]$Wheelhouse
    )

    $script:BrowsersProblem = ''
    $work = Join-Path ([IO.Path]::GetTempPath()) ('playwright-' + [guid]::NewGuid().ToString('N'))
    $staging = $Target + '.partial'
    $savedBrowsersPath = $env:PLAYWRIGHT_BROWSERS_PATH
    $savedPythonPath = $env:PYTHONPATH
    try {
        if (-not (Test-Path -LiteralPath $Wheelhouse)) {
            throw "there is no wheelhouse at $Wheelhouse (Playwright comes from it)."
        }
        New-Item -ItemType Directory -Force -Path $work | Out-Null
        if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $staging | Out-Null

        Write-Host '==> Unpacking the wheelhouse''s Playwright into a temporary folder...' -ForegroundColor Cyan
        # Out-Host: what the commands print is shown, but must not become part of what this function returns.
        & $Python -m pip install --no-index --find-links $Wheelhouse --target $work --quiet playwright | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "pip could not install Playwright from the wheelhouse (exit code $LASTEXITCODE)." }

        Write-Host '==> Downloading Chromium for Playwright (this is the largest part of the installer)...' `
            -ForegroundColor Cyan
        $env:PLAYWRIGHT_BROWSERS_PATH = $staging
        $env:PYTHONPATH = $work
        & $Python -m playwright install chromium | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "'playwright install chromium' failed (exit code $LASTEXITCODE)." }
        if (-not (Test-BrowsersFolder $staging)) {
            throw "Chromium is not complete in $staging after the download."
        }

        if (Test-Path $Target) { Remove-Item $Target -Recurse -Force }
        Move-Item -LiteralPath $staging -Destination $Target
        $size = (Get-ChildItem -LiteralPath $Target -Recurse -File | Measure-Object -Property Length -Sum).Sum
        Write-Host ('OK  Chromium is in {0} ({1:N0} MB).' -f $Target, ($size / 1MB)) -ForegroundColor Green
        return $true
    } catch {
        $script:BrowsersProblem = "Chromium could not be prepared: $($_.Exception.Message)"
        Write-Host "!!  $script:BrowsersProblem" -ForegroundColor Yellow
        return $false
    } finally {
        $env:PLAYWRIGHT_BROWSERS_PATH = $savedBrowsersPath
        $env:PYTHONPATH = $savedPythonPath
        if (Test-Path $work) { Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue }
        if (Test-Path $staging) { Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
