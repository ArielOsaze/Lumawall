# reset-install-location.ps1 - forgets the redirected install so the default is used.
#
# Why this is needed:
#
# Inno Setup remembers where an app was last installed and offers that path as the
# default on the next run. The verification run had redirected /DIR to a temporary
# folder, so every later run - including the silent repair - reinstalled to that same
# temporary folder, recreating it. The result was two installs: the real one the user
# had, and the temporary one the installer kept choosing.
#
# Clearing the remembered location is the fix. The installer then falls back to its
# DefaultDirName, which is the real location.
#
# What is removed, and what is deliberately kept:
#
#   removed  - the remembered install directory (Inno's own bookkeeping)
#   removed  - the uninstall entry, which points at the temporary folder
#   removed  - the Run key, which points at the temporary folder
#   removed  - the temporary folder itself
#   kept     - %LOCALAPPDATA%\LumaWall (config, wallpapers, logs, WebView2 data)
#   kept     - the real install directory and its files
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/reset-install-location.ps1

$ErrorActionPreference = 'Continue'

$verifyDir = 'C:\Users\ariel\Documents\Codex\2026-09-20\bik\_verify-install'

Write-Host ''
Write-Host '  forgetting the redirected install location'
Write-Host '  ' + ('-' * 58)

# ── 1. Inno's remembered directory ───────────────────────────────────────────
#
# The AppId comes from installer/LumaWall.iss: {{6CC7BEB4-4F78-4BA8-A109-C23DB7598C51}
# Note the doubled brace - Inno escapes a literal brace by doubling it, so the real
# registry key name has a single leading brace.
$appId = '{6CC7BEB4-4F78-4BA8-A109-C23DB7598C51}_is1'
foreach ($root in @('HKCU', 'HKLM')) {
    $path = "${root}:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$appId"
    if (Test-Path $path) {
        $loc = (Get-ItemProperty $path -ErrorAction SilentlyContinue).InstallLocation
        Write-Host ('  found remembered install at: ' + $loc)
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host '  removed the uninstall entry (it will be recreated on the next install)'
    }
}

# ── 2. the Run key, if it points at the temporary folder ─────────────────────
$runPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$run = Get-ItemProperty $runPath -ErrorAction SilentlyContinue
if ($run -and $run.LumaWall -and $run.LumaWall -like "*$verifyDir*") {
    Remove-ItemProperty $runPath -Name 'LumaWall' -Force -ErrorAction SilentlyContinue
    Write-Host '  removed the startup entry that pointed at the temporary folder'
}

# ── 3. the Start Menu group ──────────────────────────────────────────────────
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\LumaWall'
if (Test-Path $startMenu) {
    Remove-Item $startMenu -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host '  removed the Start Menu group (recreated on the next install)'
}

# ── 4. the temporary folder ──────────────────────────────────────────────────
if (Test-Path $verifyDir) {
    Remove-Item $verifyDir -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $verifyDir) {
        Write-Host ('  could not remove ' + $verifyDir + ' (a file may be in use)')
    } else {
        Write-Host '  removed the temporary install folder'
    }
} else {
    Write-Host '  the temporary folder is already gone'
}

Write-Host ''
Write-Host '  kept: the real install and %LOCALAPPDATA%\LumaWall (your settings)'
Write-Host ''
