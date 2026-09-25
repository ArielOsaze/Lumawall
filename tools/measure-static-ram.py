"""measure-static-ram.py — measures what a static wallpaper actually saves.

The page and the video both claim that a still image "saves about 130 MB of RAM
per monitor" because it is rendered directly instead of through WebView2. The
architectural half of that is true - SetImage() paints a BitmapImage, while a
video goes through a WebView2 surface. The figure was never measured.

This measures it: the whole process tree (LumaWall plus every WebView2 child) with
three videos playing, then with one monitor switched to a still and the app
restarted, so the difference is one monitor's worth.

The config is restored afterwards even if the measurement fails.

Run:  python tools/measure-static-ram.py
"""

import json
import os
import shutil
import subprocess
import sys
import time

CFG = os.path.expandvars(r'%LOCALAPPDATA%\LumaWall\config.json')
BAK = CFG + '.ram-measure-backup'
EXE = os.path.expandvars(r'%LOCALAPPDATA%\Programs\LumaWall\LumaWall.exe')
WALLPAPERS = os.path.expandvars(r'%LOCALAPPDATA%\LumaWall\Wallpapers')


def tree_ram():
    """Total working set of LumaWall and every WebView2 process beneath it."""
    ps = r'''
$luma = Get-Process LumaWall -ErrorAction SilentlyContinue
$total = 0
$count = 0
foreach ($p in $luma) { $total += $p.WorkingSet64; $count++ }

# WebView2 children: find them by walking the process tree from LumaWall.
$all = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name
$roots = @($luma.Id)
$seen = @{}
$queue = [System.Collections.Queue]::new()
foreach ($r in $roots) { $queue.Enqueue($r) }
while ($queue.Count -gt 0) {
    $cur = $queue.Dequeue()
    foreach ($proc in $all) {
        if ($proc.ParentProcessId -eq $cur -and -not $seen[$proc.ProcessId]) {
            $seen[$proc.ProcessId] = $true
            $queue.Enqueue($proc.ProcessId)
            $pp = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
            if ($pp) { $total += $pp.WorkingSet64; $count++ }
        }
    }
}
"{0} {1}" -f $count, [math]::Round($total/1MB)
'''
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True)
    parts = r.stdout.strip().split()
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


def stop_app():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Get-Process LumaWall -ErrorAction SilentlyContinue | Stop-Process -Force'],
                   capture_output=True)
    time.sleep(3)


def start_app():
    subprocess.Popen([EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wallpapers need a moment to attach and start decoding.
    time.sleep(18)


def sample(label, seconds=10):
    """Average the tree RAM over a few seconds; a single reading is noisy."""
    vals = []
    counts = []
    for _ in range(4):
        c, mb = tree_ram()
        counts.append(c)
        vals.append(mb)
        time.sleep(seconds / 4)
    avg = sum(vals) / len(vals)
    print('    %-28s %3d processes, %4d MB' % (label, max(counts), avg))
    return avg


def main():
    if not os.path.exists(CFG):
        print('  no config at %s' % CFG)
        return 1

    shutil.copy2(CFG, BAK)
    print('  backed up config to %s' % os.path.basename(BAK))

    try:
        # ── with three videos ────────────────────────────────────────────────
        print()
        print('  three videos:')
        stop_app()
        start_app()
        with_video = sample('LumaWall + WebView2')

        # ── one monitor switched to a still ──────────────────────────────────
        d = json.load(open(CFG, encoding='utf-8'))
        monitors = d.get('MonitorVideos', [])
        if not monitors:
            print('  no monitor assignments; cannot run the comparison')
            return 1

        # Make a still from the video that is on the first monitor, so the
        # artwork is the same and only the renderer changes.
        first = monitors[0]['Value']
        still = os.path.join(WALLPAPERS, '_ram-measure-still.png')
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '3', '-i', first,
                            '-frames:v', '1', still], capture_output=True, text=True)
        if not os.path.exists(still):
            print('  could not extract a still: %s' % r.stderr[:200])
            return 1

        print()
        print('  monitor %s -> still image' % monitors[0]['Key'])
        monitors[0]['Value'] = still
        d['MonitorVideos'] = monitors
        json.dump(d, open(CFG, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

        print()
        print('  two videos and one still:')
        stop_app()
        start_app()
        with_still = sample('LumaWall + WebView2')

        delta = with_video - with_still
        print()
        print('  three videos : %4d MB' % with_video)
        print('  one still    : %4d MB' % with_still)
        print('  difference   : %4d MB for one monitor' % delta)
        print()
        if delta > 0:
            print('  The claim in the page and the video says 130 MB per monitor.')
            print('  Measured here: %d MB.' % delta)
        else:
            print('  No saving measured. The claim should be removed, not reworded.')

        os.remove(still)
        return 0
    finally:
        # Put the config back and restart, whatever happened.
        shutil.copy2(BAK, CFG)
        os.remove(BAK)
        stop_app()
        start_app()
        print()
        print('  config restored, app restarted')


if __name__ == '__main__':
    sys.exit(main())
