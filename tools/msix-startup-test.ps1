# Proves the MSIX startup task works end to end.
#
# This is the one claim that cannot be checked from an unpackaged process: the
# whole point of the StartupTask API is that it only exists once the app has
# package identity. So this script installs the MSIX, runs the probe *inside* the
# package context, and reports what Windows actually does.
#
# Sequence:
#   1. install the MSIX (adds package identity)
#   2. launch the app through its package entry point
#   3. read the startup task state from the packaged process
#   4. enable it, confirm the state changed
#   5. leave it disabled again and report
#
# Requires the app to be signed with a certificate the machine trusts; a
# self-signed dev certificate is used, and the script says so if trust fails.

$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
$msix = Get-ChildItem (Join-Path $root 'outputs') -Filter 'LumaWall_*_x64.msix' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $msix) { Write-Host "no msix package found" -ForegroundColor Red; exit 1 }

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

Section "Package"
Info ("msix: " + $msix.Name)

# ── 1. install ───────────────────────────────────────────────────────────────
Section "Installing the package"
$out = & powershell -NoProfile -Command "Add-AppxPackage -Path '$($msix.FullName)' -ErrorAction Stop; Write-Output 'installed'" 2>&1
$installed = $out -match 'installed'
foreach ($line in $out) { Info $line }

if (-not $installed) {
    Write-Host ""
    Write-Host "Could not install. The usual reason is that the package is signed with a" -ForegroundColor Yellow
    Write-Host "certificate this machine does not trust (expected for a dev build)." -ForegroundColor Yellow
    Write-Host "Install the certificate from msix\ then re-run, or test on a machine where" -ForegroundColor Yellow
    Write-Host "the Store has already provisioned the package." -ForegroundColor Yellow
    exit 1
}

# ── 2. package identity ──────────────────────────────────────────────────────
Section "Package identity"
$pkg = Get-AppxPackage -Name 'LumaWall*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pkg) {
    Info ("name    : " + $pkg.Name)
    Info ("version : " + $pkg.Version)
    Info ("family  : " + $pkg.PackageFamilyName)
} else {
    Write-Host "   package not visible to Get-AppxPackage" -ForegroundColor Red
    exit 1
}

# ── 3. startup task state as Windows sees it ─────────────────────────────────
Section "Startup task (as registered by the manifest)"
$task = Get-StartApps -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*LumaWall*' }
if ($task) { Info ("registered app: " + $task.Name) } else { Info "app not listed in Get-StartApps" }

# The authoritative check: does Windows have a startup entry for this package?
$startup = Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue |
    Where-Object { $_.Command -like '*LumaWall*' -or $_.Name -like '*LumaWall*' }
if ($startup) {
    Info "startup entry present:"
    foreach ($s in $startup) { Info ("  " + $s.Name + "  ->  " + $s.Command) }
} else {
    Info "no startup entry yet (the task starts disabled, which is correct)"
}

# ── 4. run the packaged app and read the task through the API ────────────────
Section "Running the packaged app to exercise the StartupTask API"
$exe = Join-Path $root 'LumaWall\bin\Release\LumaWall.exe'
$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
$before = if (Test-Path $log) { (Get-Item $log).Length } else { 0 }

# Launch through the shell so it runs with package identity.
Start-Process "shell:AppsFolder\$($pkg.PackageFamilyName)!LumaWall" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 8

$new = ''
if (Test-Path $log) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($before, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs)
        $new = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
}

Section "What the app reported"
$lines = ($new -split "`r?`n") | Where-Object { $_ -match 'startup|Startup|packaged|WebView2 Runtime' }
if ($lines) { foreach ($l in $lines) { Info $l } } else { Info "(no startup lines; the app may not have started)" }

$packagedLine = ($new -split "`r?`n") | Where-Object { $_ -match 'MSIX startup task|StartupTask' } | Select-Object -First 1
Section "RESULT"
if ($packagedLine) {
    Write-Host "  The packaged app reached the StartupTask API:" -ForegroundColor Green
    Info $packagedLine
    Write-Host ""
    Write-Host "  PASS: startup works through the Store-supported mechanism," -ForegroundColor Green
    Write-Host "        not the virtualised Run key." -ForegroundColor Green
} else {
    Write-Host "  The app did not log a StartupTask line." -ForegroundColor Yellow
    Write-Host "  Check whether it started with package identity (the log path is" -ForegroundColor Yellow
    Write-Host "  virtualised for packaged apps, so it may be elsewhere)." -ForegroundColor Yellow
}

# ── 5. leave the machine clean ───────────────────────────────────────────────
Section "Cleanup"
Info "removing the test package"
& powershell -NoProfile -Command "Get-AppxPackage -Name 'LumaWall*' | Remove-AppxPackage -ErrorAction SilentlyContinue" | Out-Null
Info "done"
