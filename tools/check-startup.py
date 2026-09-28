"""Check that LumaWall is ready quickly, and that the first frames are not late.

Why this exists
---------------
The report was "pas pertama buka lumawall setelah smua di close lumayan ngelag" - the
first launch after everything has been closed feels slow.

It was: the log showed a 2.9-second gap between the first renderer being ready and the
first wallpaper being attached. The cause was PrepareDesktopOnce() sending message 0x052C
to Progman on every start. That message makes Explorer tear down its desktop layout and
build a new WorkerW, and it was sent twice with a one second timeout each.

It is only needed when no WorkerW exists yet. When Explorer has been running - the normal
case, including a restart of the app - the existing WorkerW can be reused, and the
message can be skipped entirely.

This measures the two things that make startup feel slow:
  * how long from process start to the first wallpaper being committed;
  * whether any single step took longer than it should, which points at what to fix.

It restarts the app itself, so the number is a real cold start rather than a warm page
cache. That costs a few seconds of wallpaper decoding; there is no other way to measure
it honestly.

Usage: python tools/check-startup.py [--limit 4.0]
"""
import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'
EXE = Path.home() / 'AppData' / 'Local' / 'Programs' / 'LumaWall' / 'LumaWall.exe'


def stop():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-Process LumaWall -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True, text=True)
    time.sleep(3)


def start():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Start-Process '%s'" % EXE], capture_output=True, text=True)


def timeline():
    """[(seconds from first line, message)] for the newest process in the log."""
    if not LOG.exists():
        return []
    lines = LOG.read_text(encoding='utf-8', errors='replace').splitlines()
    pids = []
    for ln in lines:
        m = re.search(r'\[(\d+)\]', ln)
        if m and (not pids or pids[-1] != m.group(1)):
            pids.append(m.group(1))
    if not pids:
        return []
    newest = pids[-1]
    ts = []
    for ln in lines:
        if '[%s]' % newest not in ln:
            continue
        m = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) \[\d+\] (.*)', ln)
        if m:
            ts.append((m.group(1), m.group(2)))
    if not ts:
        return []
    fmt = '%Y-%m-%d %H:%M:%S.%f'
    t0 = datetime.strptime(ts[0][0], fmt)
    return [((datetime.strptime(t, fmt) - t0).total_seconds(), msg) for t, msg in ts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=float, default=4.0,
                    help='fail if the first wallpaper takes longer than this (default 4s)')
    ap.add_argument('--no-restart', action='store_true',
                    help='measure the run already in the log instead of restarting')
    args = ap.parse_args()

    if not EXE.exists():
        print('  FAIL LumaWall is not installed at %s' % EXE)
        return 1

    if not args.no_restart:
        print('  restarting LumaWall for a cold start')
        stop()
        if LOG.exists():
            LOG.unlink()
        start()
        # Wait for the log to show the last display committed, or give up.
        deadline = time.time() + 60
        while time.time() < deadline:
            time.sleep(1.5)
            events = timeline()
            if sum(1 for _, m in events if 'without blank frame' in m) >= 3:
                break

    events = timeline()
    if not events:
        print('  FAIL no log lines for the running process')
        return 1

    ready = [s for s, m in events if 'renderer ready' in m]
    swaps = [s for s, m in events if 'without blank frame' in m]
    prepared = [s for s, m in events if 'Desktop prepared for wallpaper' in m]
    reused = [s for s, m in events if 'Desktop already prepared' in m]

    print()
    if ready:
        print('  first renderer ready : %.2fs' % ready[0])
    if swaps:
        print('  first wallpaper up   : %.2fs' % swaps[0])
        print('  all displays up      : %.2fs' % swaps[-1])
    if prepared:
        print('  0x052C was SENT at %.2fs (Explorer had no WorkerW)' % prepared[0])
    if reused:
        print('  0x052C was SKIPPED at %.2fs (existing WorkerW reused)' % reused[0])

    # Split the time into "loading the app" and "the app starting up", because they have
    # different causes and only one of them is the app's to fix.
    #
    # The first gap in the log - from the first line the process writes to the next one -
    # covers the CLR loading, WPF initialising and the window being constructed. Measured:
    # 0.21s on a warm start, but 1.8s for the first start after a build, when the
    # antivirus scans the new executable. Treating that as an app step made this check
    # fail right after every release with a message blaming 0x052C, which had in fact
    # been skipped - a false failure that hid the real number.
    #
    # So the app's own work is taken from its own stopwatch ("MainWindow built in N ms"),
    # and the process boot is reported separately with its own generous limit.
    boot_gap = events[1][0] - events[0][0] if len(events) > 1 else 0.0
    built = None
    for seconds, message in events:
        m = re.search(r'MainWindow built in (\d+) ms', message)
        if m:
            built = int(m.group(1)) / 1000.0
            break
    if built is None:
        # An older build without the instrumentation: fall back to the gap, and say so.
        built = boot_gap
        print('  window built         : unknown (this build does not log it)')
    else:
        print('  window built         : %.2fs of the %.2fs before the first step'
              % (built, boot_gap))
        print('  process boot         : %.2fs (CLR, WPF, and the first-run scan)'
              % max(0.0, boot_gap - built))

    # The largest gap between consecutive steps after the window exists: a single slow
    # step is what makes startup feel slow, and naming it is what makes it actionable.
    #
    # The boot gap is excluded here and judged separately, for the reason above.
    worst_gap, worst_msg = 0.0, ''
    for i in range(2, len(events)):
        gap = events[i][0] - events[i - 1][0]
        if gap > worst_gap:
            worst_gap, worst_msg = gap, events[i][1]

    print()
    print('  largest step after the window: %.2fs before "%s"'
          % (worst_gap, worst_msg[:60]))

    if not swaps:
        print()
        print('  FAIL no wallpaper was committed - the app did not finish starting')
        return 1

    first = swaps[0]
    failures = []
    if first > args.limit:
        failures.append('the first wallpaper took %.2fs (limit %.1fs)' % (first, args.limit))
    # 0.6s is generous for constructing the shell: measured 0.20-0.34s. It is separate
    # from the process boot so that a slow antivirus scan cannot fail it.
    if built > 0.6:
        failures.append('building the window took %.2fs (limit 0.6s)' % built)
    if worst_gap > 1.5:
        failures.append('a single step took %.2fs - "%s"' % (worst_gap, worst_msg[:60]))

    if failures:
        print()
        for f in failures:
            print('  FAIL %s' % f)
        print()
        print('  The usual causes, in order of how often they turned out to be it:')
        print('   * 0x052C sent when it did not need to be - that message rebuilds the')
        print('     shell desktop WorkerW and costs about 3 seconds; it must be skipped')
        print('     whenever a WorkerW already exists;')
        print('   * the catalogue being parsed on the UI thread instead of off it;')
        print('   * a page being rebuilt before the wallpapers are restored.')
        return 1

    print()
    print('  PASS first wallpaper up in %.2fs (limit %.1fs), window built in %.2fs,'
          % (first, args.limit, built))
    print('       largest step after the window %.2fs' % worst_gap)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
