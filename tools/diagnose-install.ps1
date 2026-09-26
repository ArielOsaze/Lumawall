# diagnose-install.ps1 - where did the LumaWall installation go?
#
# Why this exists:
#
# The installer was run once with /VERYSILENT and /DIR pointed at a temporary folder,
# to prove the installer contains the fixed binary. That check was worth doing, but
# the side effects were not thought through: an Inno Setup installer with the same
# AppId updates the Start Menu shortcuts and the uninstall registry entry to point at
# wherever it just installed. The temporary folder was then deleted, so anything
# still pointing at it is now a dead reference - which looks exactly like "the app
# disappeared".
#
# So this looks in every place an installed app can be:
#
#   1. the install directory          (are the files still there?)
#   2. Start Menu shortcuts           (do they exist, and do they resolve?)
#   3. the desktop shortcut
#   4. the uninstall registry entry   (does it point at a folder that exists?)
#   5. the Run key                    (does start-with-Windows point at a real file?)
#   6. the running process
#
# and reports which of them are broken. It changes nothing.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/diagnose-install.ps1

$ErrorActionPreference = 'Continue'

$installDir = Join-Path $env:LOCALAPPDATA 'Programs\LumaWall'
$exe = Join-Path $installDir 'LumaWall.exe'

Write-Host ''
Write-Host '  where is LumaWall?'
Write-Host '  ' + ('-' * 58)

# ── 1. the install directory ─────────────────────────────────────────────────
Write-Host ''
Write-Host '  1. install directory'
Write-Host ('     ' + $installDir)
if (Test-Path $exe) {
    $f = Get-Item $exe
    Write-Host ('     FOUND  LumaWall.exe  ' + $f.Length + ' bytes  ' + $f.LastWriteTime)
    $count = (Get-ChildItem $installDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ('     ' + $count + ' files total')
} else {
    Write-Host '     NOT FOUND - the app is not installed here'
    if (Test-Path $installDir) {
        Write-Host '     (the folder exists but has no LumaWall.exe)'
        Get-ChildItem $installDir -ErrorAction SilentlyContinue |
            Select-Object -First 12 | ForEach-Object { Write-Host ('       ' + $_.Name) }
    } else {
        Write-Host '     (the folder does not exist at all)'
    }
}

# ── 2. Start Menu shortcuts ──────────────────────────────────────────────────
Write-Host ''
Write-Host '  2. Start Menu shortcuts'
$shortcutRoots = @(
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
    (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs')
)
$foundShortcut = $false
foreach ($root in $shortcutRoots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem $root -Recurse -Filter '*LumaWall*' -ErrorAction SilentlyContinue | ForEach-Object {
        $foundShortcut = $true
        $target = ''
        if ($_.Extension -eq '.lnk') {
            try {
                $shell = New-Object -ComObject WScript.Shell
                $target = $shell.CreateShortcut($_.FullName).TargetPath
            } catch { $target = '(unreadable)' }
        }
        $alive = if ($target -and (Test-Path $target)) { 'OK' } else { 'BROKEN' }
        Write-Host ('     ' + $alive.PadRight(7) + $_.FullName)
        if ($target) { Write-Host ('             -> ' + $target) }
    }
}
if (-not $foundShortcut) { Write-Host '     NONE FOUND' }

# ── 3. desktop shortcut ──────────────────────────────────────────────────────
Write-Host ''
Write-Host '  3. desktop shortcut'
$desktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'LumaWall.lnk'
if (Test-Path $desktopLnk) {
    try {
        $shell = New-Object -ComObject WScript.Shell
        $target = $shell.CreateShortcut($desktopLnk).TargetPath
        $alive = if (Test-Path $target) { 'OK' } else { 'BROKEN' }
        Write-Host ('     ' + $alive + '  -> ' + $target)
    } catch { Write-Host '     present but unreadable' }
} else {
    Write-Host '     none (the installer makes this optional)'
}

# ── 4. the uninstall registry entry ──────────────────────────────────────────
Write-Host ''
Write-Host '  4. uninstall registry entry'
$keys = @(
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$foundEntry = $false
foreach ($key in $keys) {
    Get-ItemProperty $key -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like '*LumaWall*' } |
        ForEach-Object {
            $foundEntry = $true
            Write-Host ('     ' + $_.DisplayName + '  v' + $_.DisplayVersion)
            Write-Host ('       install location : ' + $_.InstallLocation)
            Write-Host ('       uninstall string : ' + $_.UninstallString)
            $loc = $_.InstallLocation
            if ($loc) {
                if (Test-Path $loc) { Write-Host '       -> the location exists' }
                else { Write-Host '       -> BROKEN: that location does not exist' }
            }
        }
}
if (-not $foundEntry) { Write-Host '     NONE FOUND' }

# ── 5. start with Windows ────────────────────────────────────────────────────
Write-Host ''
Write-Host '  5. start with Windows (HKCU Run)'
$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
if ($run -and $run.LumaWall) {
    Write-Host ('     ' + $run.LumaWall)
    $path = $run.LumaWall.Trim('"').Split('"')[0]
    if (Test-Path $path) { Write-Host '     -> the target exists' }
    else { Write-Host '     -> BROKEN: that target does not exist' }
} else {
    Write-Host '     not set'
}

# ── 6. the running process ───────────────────────────────────────────────────
Write-Host ''
Write-Host '  6. running process'
$proc = Get-Process LumaWall -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host ('     running, pid ' + $proc.Id + '  from ' + $proc.Path)
} else {
    Write-Host '     not running'
}

Write-Host ''
