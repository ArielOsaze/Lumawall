# probe-trim-access.ps1 - why does OpenProcess fail on the WebView2 processes?
#
# Why this exists:
#
# The memory measurement showed a 43 MB working-set drop when a wallpaper paused, but
# the app's log said "Memory trimmed for paused wallpaper: 0/5 process(es)" - so the
# drop came from the browser-side purge, not from the Win32 trim. A trim that reports
# 0 successes and is counted as a win is exactly the kind of claim this project has
# been trying to avoid, so the next question is whether the trim can be made to work
# or whether it should be removed.
#
# The likely cause is that Chromium sets a restrictive security descriptor on its own
# processes: a sandboxed renderer is deliberately hard for another process to open,
# and the browser process protects itself the same way. This probe confirms it by
# asking for the access rights the trim needs and printing the Win32 error.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/probe-trim-access.ps1

$ErrorActionPreference = 'Stop'

Add-Type -Namespace Probe -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern IntPtr OpenProcess(int desiredAccess, bool inheritHandle, int processId);

[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool CloseHandle(IntPtr handle);

[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool SetProcessWorkingSetSize(IntPtr process, IntPtr min, IntPtr max);

// psapi.dll, not kernel32.dll. The first version of the app declared this in
// kernel32, which threw EntryPointNotFoundException at call time and - because it
// shared a try block with SetProcessWorkingSetSize - stopped the trim from ever
// running while still reporting success to the caller.
[DllImport("psapi.dll", SetLastError = true)]
public static extern bool EmptyWorkingSet(IntPtr process);
'@

$PROCESS_SET_QUOTA = 0x0100
$PROCESS_QUERY_INFORMATION = 0x0400
$PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

function Try-Access {
    param([int]$TargetPid, [int]$Access, [string]$Name)

    $handle = [Probe.Native]::OpenProcess($Access, $false, $TargetPid)
    if ($handle -eq [IntPtr]::Zero) {
        $err = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        # 5 is ERROR_ACCESS_DENIED - the process is there but refuses the handle.
        return [pscustomobject]@{
            Pid = $TargetPid; Name = $Name; Access = ('0x{0:X}' -f $Access)
            Opened = $false; Error = $err; Trimmed = $false
        }
    }

    $trimmed = [Probe.Native]::EmptyWorkingSet($handle)
    if (-not $trimmed) {
        $trimmed = [Probe.Native]::SetProcessWorkingSetSize($handle, [IntPtr](-1), [IntPtr](-1))
    }
    [Probe.Native]::CloseHandle($handle) | Out-Null

    return [pscustomobject]@{
        Pid = $TargetPid; Name = $Name; Access = ('0x{0:X}' -f $Access)
        Opened = $true; Error = 0; Trimmed = $trimmed
    }
}

Write-Host ''
Write-Host '  probing access to the LumaWall WebView2 processes'
Write-Host ''

$targets = @()
$targets += Get-CimInstance Win32_Process -Filter "Name='LumaWall.exe'" -ErrorAction SilentlyContinue
$targets += Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*LumaWall*' }

if (-not $targets -or $targets.Count -eq 0) {
    Write-Host '  LumaWall is not running; start it first'
    Write-Host ''
    exit 1
}

# Computed here rather than inline: PowerShell parses `-bor` inside an array literal
# as a method call on the array, not as a bitwise-or of the two integers.
$accessA = $PROCESS_SET_QUOTA -bor $PROCESS_QUERY_INFORMATION
$accessB = $PROCESS_QUERY_LIMITED_INFORMATION -bor $PROCESS_SET_QUOTA
$accessModes = @($accessA, $accessB)

Write-Host ('  {0,-9} {1,-34} {2,-8} {3,-7} {4}' -f 'pid', 'process', 'access', 'opened', 'trimmed')
Write-Host ('  {0,-9} {1,-34} {2,-8} {3,-7} {4}' -f '--------', '-------------------------------', '------', '------', '-------')

foreach ($t in $targets) {
    # The process kind is in the command line for the browser group and in the name
    # for the host, and knowing which one refuses is the whole point of the probe.
    $kind = $t.Name
    if ($t.CommandLine -match '--type=(\w+)') { $kind = $Matches[1] }

    foreach ($access in $accessModes) {
        $r = Try-Access -TargetPid $t.ProcessId -Access $access -Name $kind
        Write-Host ('  {0,-9} {1,-34} {2,-8} {3,-7} {4}' -f $r.Pid, $r.Name, $r.Access, $r.Opened, $r.Trimmed)
        if (-not $r.Opened) {
            $meaning = switch ($r.Error) {
                5 { 'ACCESS_DENIED - the process refuses the handle' }
                87 { 'INVALID_PARAMETER' }
                default { "Win32 error $($r.Error)" }
            }
            Write-Host ('  {0,-9} {1,-34} {2}' -f '', '', $meaning)
        }
    }
}

Write-Host ''
Write-Host '  Reading: if the renderer and gpu rows show ACCESS_DENIED and the browser'
Write-Host '  row opens, the trim can only ever work on the browser process. If every'
Write-Host '  row is denied, the Win32 trim is not a usable mechanism for this app and'
Write-Host '  the browser-side purge is what actually releases memory.'
Write-Host ''
