"""Measure what LumaWall costs while it is doing nothing, and fail if it is too much.

Why this exists
---------------
The app was measured at 7-9% of a CPU core while idle: no wallpaper change, no window
open, nothing happening. That is a live wallpaper engine - it should be close to free
when it is not decoding.

The cause was the pause scan. Every two seconds the app walked every top-level window
TWICE - once for "is a window covering this monitor" and once for "is a maximized window
covering this monitor" - and for each window it called, in this order:

    IsWindowVisible, IsIconic, IsZoomed
    IsCloaked                  <- a synchronous DWM round-trip, per window
    GetWindowThreadProcessId
    IsShellDesktopWindow, IsOverlayWindow, IsNonAppWindow
    GetWindowRect              <- marshals a RECT back, per window

On a desktop with ~80 top-level windows that is over a thousand cross-process calls per
tick, half of them answering questions about windows that were never going to cover
anything. It also wrote two log lines per tick - a file write on the UI thread - because
the dedupe set was rebuilt on every scan.

The fix, all of it measured below rather than assumed:
  * one pass instead of two, with the cheap attribute tests first and the DWM round-trip
    only for windows that already fill a monitor by rectangle;
  * the covering-window log line is deduped across scans, not per scan.

A checker is required because this is invisible: nothing looks wrong, the wallpapers
animate, and the only symptom is that the machine feels slow. Without a number attached
it creeps back.

Usage: python tools/check-idle-cpu.py [--seconds 30] [--limit 3.0]
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

LOG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'


def luma_pids():
    """Every running LumaWall process id."""
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-Process LumaWall -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
        capture_output=True, text=True)
    return [int(x) for x in out.stdout.split() if x.strip().isdigit()]


def cpu_seconds(pid):
    """Total CPU seconds this process has used, or None if it is gone."""
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "(Get-Process -Id %d -ErrorAction SilentlyContinue).CPU" % pid],
        capture_output=True, text=True)
    text = out.stdout.strip().replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def working_set(pid):
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "[int]((Get-Process -Id %d -ErrorAction SilentlyContinue).WorkingSet64/1MB)" % pid],
        capture_output=True, text=True)
    try:
        return int(out.stdout.strip())
    except ValueError:
        return 0


def log_stats():
    """(covering-window lines, total lines) since the log was last truncated."""
    if not LOG.exists():
        return None
    text = LOG.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()
    return sum(1 for ln in lines if 'Covering window' in ln), len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=30.0,
                    help='how long to sample (default 30)')
    ap.add_argument('--limit', type=float, default=3.0,
                    help='fail above this percentage of one core (default 3.0)')
    args = ap.parse_args()

    pids = luma_pids()
    if not pids:
        print('  LumaWall is not running, so there is nothing to measure')
        print('  start it and run this again - a skipped check is not a pass')
        return 1
    if len(pids) > 1:
        print('  FAIL %d LumaWall processes are running at once' % len(pids))
        for pid in pids:
            print('    pid %d  %d MB' % (pid, working_set(pid)))
        print('  one process is the design; the extras are stale and are also burning CPU')
        return 1

    pid = pids[0]
    print('  LumaWall pid %d' % pid)

    before = cpu_seconds(pid)
    if before is None:
        print('  FAIL could not read the CPU time of pid %d' % pid)
        return 1
    log_before = log_stats()
    t0 = time.time()

    # Sample without touching the machine: no clicks, no window changes. The point is to
    # measure what the app costs when the user is doing something else.
    time.sleep(args.seconds)

    after = cpu_seconds(pid)
    elapsed = time.time() - t0
    if after is None:
        print('  FAIL the process exited during the measurement')
        return 1

    used = after - before
    percent = 100.0 * used / elapsed
    ram = working_set(pid)
    log_after = log_stats()

    print('  sampled %.0f s: %.2f CPU seconds -> %.1f%% of one core'
          % (elapsed, used, percent))
    print('  working set: %d MB' % ram)

    if log_before and log_after:
        new_covering = log_after[0] - log_before[0]
        new_lines = log_after[1] - log_before[1]
        print('  new log lines: %d  (of which "Covering window": %d)'
              % (new_lines, new_covering))
        # The scan runs every 2 seconds. One line per covering window per handle is
        # expected; a line every tick is the bug this replaced.
        ticks = elapsed / 2.0
        if new_covering > max(4, ticks):
            print('  FAIL the covering-window log is written every tick again')
            print('       %d lines in %.0f s is roughly one per scan' % (new_covering, elapsed))
            return 1

    failures = []
    if percent > args.limit:
        failures.append('idle CPU is %.1f%%, above the %.1f%% limit' % (percent, args.limit))
    if ram > 420:
        failures.append('working set is %d MB' % ram)

    print()
    if failures:
        for f in failures:
            print('  FAIL %s' % f)
        print()
        print('  This is the cost of doing nothing. The usual cause is the pause scan:')
        print('  it runs every 2 s over every window, so a per-window call that can be')
        print('  skipped or reordered shows up here multiplied by the window count.')
        return 1

    print('  PASS idle cost: %.1f%% of one core (limit %.1f%%), %d MB'
          % (percent, args.limit, ram))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
