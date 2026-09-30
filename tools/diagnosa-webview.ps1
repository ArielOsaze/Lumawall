# Diagnose the WebView2 process tree and video handling.
# Pure ASCII: PowerShell 5.1 reads BOM-less files as ANSI and mangles anything else.

$all = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'")
Write-Output "total msedgewebview2 processes: $($all.Count)"
Write-Output ""

$byParent = @{}
foreach ($p in $all) {
    $ppid = [int]$p.ParentProcessId
    if (-not $byParent.ContainsKey($ppid)) { $byParent[$ppid] = New-Object System.Collections.ArrayList }
    $type = 'browser'
    if ($p.CommandLine -match '--type=([a-z0-9-]+)') { $type = $Matches[1] }
    [void]$byParent[$ppid].Add($type)
}

Write-Output "--- grouped by parent process ---"
foreach ($k in ($byParent.Keys | Sort-Object)) {
    $parent = Get-Process -Id $k -ErrorAction SilentlyContinue
    $pname = 'GONE'
    if ($parent) { $pname = $parent.ProcessName }
    $types = $byParent[$k]
    Write-Output ("parent {0,-7} {1,-16} children={2}" -f $k, $pname, $types.Count)
    Write-Output ("     types: {0}" -f ($types -join ', '))
}

Write-Output ""
Write-Output "--- LumaWall processes ---"
$lw = @(Get-Process LumaWall -ErrorAction SilentlyContinue)
foreach ($p in $lw) {
    $ram = [math]::Round($p.WorkingSet64 / 1MB)
    Write-Output ("  pid={0,-7} ram={1} MB  started={2}" -f $p.Id, $ram, $p.StartTime)
}
if ($lw.Count -eq 0) { Write-Output "  none running" }

Write-Output ""
Write-Output "--- RAM by process group ---"
$groups = @{}
foreach ($p in $all) {
    $cmd = $p.CommandLine
    $owner = 'unknown'
    foreach ($lwp in $lw) {
        if ($cmd -like "*$($lwp.Id)*") { $owner = "LumaWall pid=$($lwp.Id)" }
    }
    if ($owner -eq 'unknown') {
        # No explicit parent link in cmdline; use parent process name.
        $parent = Get-Process -Id ([int]$p.ParentProcessId) -ErrorAction SilentlyContinue
        if ($parent) { $owner = $parent.ProcessName }
    }
    if (-not $groups.ContainsKey($owner)) { $groups[$owner] = 0 }
    $groups[$owner] += $p.WorkingSet64
}
foreach ($k in ($groups.Keys | Sort-Object)) {
    Write-Output ("  {0,-24} {1,8:N0} MB" -f $k, ($groups[$k] / 1MB))
}

Write-Output ""
Write-Output "--- ffmpeg available to the app? ---"
$paths = @(
    "$env:LOCALAPPDATA\Programs\LumaWall\ffmpeg.exe",
    "$env:LOCALAPPDATA\Programs\LumaWall\tools\ffmpeg.exe",
    "$env:ProgramFiles\LumaWall\ffmpeg.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Output "  FOUND: $p" } else { Write-Output "  absent: $p" }
}
$onPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($onPath) { Write-Output "  on PATH: $($onPath.Source)" } else { Write-Output "  not on PATH" }

Write-Output ""
Write-Output "--- video cache folder ---"
$cache = "$env:LOCALAPPDATA\LumaWall\VideoCache"
if (Test-Path $cache) {
    $n = @(Get-ChildItem $cache -File).Count
    $sz = (Get-ChildItem $cache -File | Measure-Object -Property Length -Sum).Sum
    Write-Output ("  exists: {0} files, {1:N0} MB" -f $n, ($sz / 1MB))
} else {
    Write-Output "  does not exist yet"
}
