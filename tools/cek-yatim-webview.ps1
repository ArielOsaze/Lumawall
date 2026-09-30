# Check whether orphaned WebView2 trees are still running and still decoding.
# An orphan is a browser process whose LumaWall parent no longer exists, but which
# keeps a renderer and a gpu-process alive - so it keeps decoding video nobody sees.
# Pure ASCII (PowerShell 5.1 reads BOM-less files as ANSI).

$lw = @(Get-Process LumaWall -ErrorAction SilentlyContinue)
$lwIds = @()
foreach ($p in $lw) { $lwIds += $p.Id }
Write-Output "LumaWall pids: $($lwIds -join ', ')"
Write-Output ""

# Every browser process belongs to a user-data-dir. The app's is WebView2\Shared.
# A browser process with that dir but no living LumaWall ancestor is an orphan.
$browsers = @()
Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | ForEach-Object {
    $cmd = $_.CommandLine
    if ($cmd -notmatch '--type=') {
        # This is a browser (root) process.
        $shared = $cmd -match 'WebView2'
        $browsers += [pscustomobject]@{
            Pid = [int]$_.ProcessId
            Ppid = [int]$_.ParentProcessId
            Shared = $shared
            Started = $_.CreationDate
        }
    }
}

Write-Output "--- root browser processes ---"
foreach ($b in $browsers) {
    $parent = Get-Process -Id $b.Ppid -ErrorAction SilentlyContinue
    $pname = 'GONE'
    if ($parent) { $pname = $parent.ProcessName }
    $isOurs = $false
    if ($lwIds -contains $b.Ppid) { $isOurs = $true }
    $tag = 'OTHER-APP'
    if ($b.Shared) {
        if ($isOurs) { $tag = 'LumaWall (live)' } else { $tag = 'LumaWall (ORPHAN)' }
    }
    Write-Output ("  pid={0,-7} parent={1,-7} {2,-14} {3}" -f $b.Pid, $b.Ppid, $pname, $tag)
}

Write-Output ""
Write-Output "--- decode work per root browser tree ---"
foreach ($b in $browsers) {
    if (-not $b.Shared) { continue }

    # Collect the whole tree: browser + its descendants.
    $tree = New-Object System.Collections.ArrayList
    [void]$tree.Add($b.Pid)
    $changed = $true
    while ($changed) {
        $changed = $false
        Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | ForEach-Object {
            $cpid = [int]$_.ProcessId
            $cppid = [int]$_.ParentProcessId
            if (($tree -contains $cppid) -and -not ($tree -contains $cpid)) {
                [void]$tree.Add($cpid)
                $changed = $true
            }
        }
    }

    $cpu1 = 0.0
    $ram = 0
    foreach ($t in $tree) {
        $pr = Get-Process -Id $t -ErrorAction SilentlyContinue
        if ($pr) { $cpu1 += $pr.CPU; $ram += $pr.WorkingSet64 }
    }
    Start-Sleep -Milliseconds 1200
    $cpu2 = 0.0
    foreach ($t in $tree) {
        $pr = Get-Process -Id $t -ErrorAction SilentlyContinue
        if ($pr) { $cpu2 += $pr.CPU }
    }

    $live = 'no'
    if ($lwIds -contains $b.Ppid) { $live = 'yes' }
    $used = $cpu2 - $cpu1
    $pct = [math]::Round(100.0 * $used / 1.2, 1)
    Write-Output ("  root pid={0,-7} live={1,-4} procs={2,-3} cpu={3,6:N1}%  ram={4,6:N0} MB" -f `
        $b.Pid, $live, $tree.Count, $pct, ($ram / 1MB))
}

Write-Output ""
Write-Output "--- video decode engine, by pid ---"
$s = (Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples
$rows = @()
foreach ($c in $s) {
    if ($c.InstanceName -notmatch 'engtype_videodecode') { continue }
    if ($c.CookedValue -le 0.1) { continue }
    $pidnya = 'x'
    if ($c.InstanceName -match 'pid_(\d+)') { $pidnya = $Matches[1] }
    $rows += [pscustomobject]@{ Pid = $pidnya; Pct = [math]::Round($c.CookedValue, 1) }
}
if ($rows.Count -eq 0) {
    Write-Output "  no video decode activity"
} else {
    foreach ($r in ($rows | Sort-Object -Property Pct -Descending)) {
        # Which tree does this pid belong to?
        $owner = 'unknown'
        foreach ($b in $browsers) {
            if (-not $b.Shared) { continue }
            $tree = New-Object System.Collections.ArrayList
            [void]$tree.Add($b.Pid)
            $changed = $true
            while ($changed) {
                $changed = $false
                Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | ForEach-Object {
                    $cpid = [int]$_.ProcessId
                    $cppid = [int]$_.ParentProcessId
                    if (($tree -contains $cppid) -and -not ($tree -contains $cpid)) {
                        [void]$tree.Add($cpid); $changed = $true
                    }
                }
            }
            if ($tree -contains [int]$r.Pid) {
                $live = 'no'
                if ($lwIds -contains $b.Ppid) { $live = 'yes' }
                $owner = "tree $($b.Pid) (live=$live)"
            }
        }
        Write-Output ("  pid={0,-7} {1,6:N1}%   {2}" -f $r.Pid, $r.Pct, $owner)
    }
}
