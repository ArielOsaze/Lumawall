# repair-install.ps1 - puts the shortcuts and registry back on the real install.
#
# Why this is needed:
#
# The installer was run once with /VERYSILENT and /DIR pointed at a temporary folder,
# to prove by hash that the installer contains the fixed binary. The proof was sound
# but the side effect was not: an Inno Setup installer with the same AppId rewrites
# the Start Menu group, the uninstall entry and the Run key to point wherever it just
# installed. That folder was then deleted, so every shortcut became a dead reference
# and the app looked like it had disappeared - while its files were sitting untouched
# in the real install directory.
#
# This re-runs the installer with the default directory, which is what it would have
# done the first time. Inno Setup is idempotent: it overwrites the files with the same
# ones, rewrites the shortcuts and the registry entry to the correct paths, and
# preserves the user's settings because those live in %LOCALAPPDATA%\LumaWall and are
# not part of the install.
#
# The lesson, recorded because this cost the user their Start Menu entry: never run a
# real installer with a redirected /DIR just to inspect it. Extract it instead - the
# payload of an Inno Setup installer can be unpacked without running it - or copy the
# files out of an existing install.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/repair-install.ps1

$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$setup = Join-Path $root 'site\assets\downloads\LumaWall-Setup-4.0.1.exe'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\LumaWall'

Write-Host ''
Write-Host '  repairing the LumaWall install'
Write-Host '  ' + ('-' * 58)

if (-not (Test-Path $setup)) {
    Write-Host ('  installer not found at ' + $setup)
    exit 1
}

Write-Host ('  installer : ' + $setup)
Write-Host ('  target    : ' + $installDir + '  (the default, not a redirect)')

# Stop the app first: the installer has CloseApplications set, and a running instance
# would either block the file writes or be killed mid-frame.
$running = Get-Process LumaWall -ErrorAction SilentlyContinue
if ($running) {
    Write-Host ('  stopping the running app (pid ' + $running.Id + ')')
    Stop-Process -Id $running.Id -Force
    Start-Sleep -Seconds 2
}

Write-Host '  running the installer silently ...'
$proc = Start-Process -FilePath $setup `
    -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' `
    -PassThru -Wait
Write-Host ('  installer exit code: ' + $proc.ExitCode)

if ($proc.ExitCode -ne 0) {
    Write-Host '  the installer reported a failure; nothing else was changed'
    exit 1
}

Start-Sleep -Seconds 2

# ── verify ───────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '  verifying'

$exe = Join-Path $installDir 'LumaWall.exe'
if (Test-Path $exe) {
    $f = Get-Item $exe
    Write-Host ('    app        OK  ' + $f.Length + ' bytes')
} else {
    Write-Host '    app        MISSING'
    exit 1
}

$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\LumaWall'
if (Test-Path $startMenu) {
    $lnks = Get-ChildItem $startMenu -Filter '*.lnk' -ErrorAction SilentlyContinue
    Write-Host ('    Start Menu OK  ' + $lnks.Count + ' shortcut(s)')
    $shell = New-Object -ComObject WScript.Shell
    foreach ($lnk in $lnks) {
        $target = $shell.CreateShortcut($lnk.FullName).TargetPath
        $alive = if (Test-Path $target) { 'resolves' } else { 'BROKEN' }
        Write-Host ('      ' + $lnk.BaseName.PadRight(18) + $alive)
    }
} else {
    Write-Host '    Start Menu MISSING'
}

$uninstall = Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like '*LumaWall*' } | Select-Object -First 1
if ($uninstall) {
    $loc = $uninstall.InstallLocation
    $alive = if ($loc -and (Test-Path $loc)) { 'OK' } else { 'BROKEN' }
    Write-Host ('    uninstall  ' + $alive + '  -> ' + $loc)
} else {
    Write-Host '    uninstall  MISSING'
}

$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
if ($run -and $run.LumaWall) {
    $path = $run.LumaWall.Trim('"').Split('"')[0]
    $alive = if (Test-Path $path) { 'OK' } else { 'BROKEN' }
    Write-Host ('    startup    ' + $alive + '  -> ' + $path)
} else {
    Write-Host '    startup    not set (the user had it on; the installer task adds it)'
}

Write-Host ''
