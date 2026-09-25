"""measure-explorer-recovery.py — times the recovery after Explorer restarts.

The page claims recovery happens "in under 4 seconds". The mechanism is real - the
app watches the desktop host handle and rebuilds its wallpaper windows - but the
figure was never measured, and an Explorer restart is exactly the kind of event
where a guessed number is wrong.

This restarts Explorer and stamps the wall clock at the moment the shell is back,
then reads the app's own log for the moment each wallpaper window attaches. The
difference is the recovery time.

Explorer restarts on its own, so this is safe: the shell comes back with the
taskbar and the desktop.

Run:  python tools/measure-explorer-recovery.py
"""

import datetime
import os
import re
import subprocess
import sys
import time

LOG = os.path.expandvars(r'%LOCALAPPDATA%\LumaWall\Logs\lumawall.log')


def main():
    if not os.path.exists(LOG):
        print('  no log at %s' % LOG)
        return 1

    before = os.path.getsize(LOG)
    print('  restarting Explorer...')

    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Stop-Process -Name explorer -Force'],
                   capture_output=True, text=True)

    # Wait for the shell to come back, and record exactly when it did. This is the
    # start of the interval the user experiences as "the desktop is broken".
    deadline = time.time() + 60
    shell_back = None
    while time.time() < deadline:
        q = subprocess.run(['powershell', '-NoProfile', '-Command',
                            '(Get-Process explorer -ErrorAction SilentlyContinue | Measure-Object).Count'],
                           capture_output=True, text=True)
        if q.stdout.strip() not in ('', '0'):
            shell_back = datetime.datetime.now()
            break
        time.sleep(0.05)

    if shell_back is None:
        print('  explorer never came back')
        return 1

    print('  shell is back at %s' % shell_back.strftime('%H:%M:%S.%f')[:-3])

    # Wait for the app to notice and rebuild.
    time.sleep(6)

    with open(LOG, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(before)
        added = f.read()

    # Every wallpaper window that attached, with its timestamp.
    attaches = re.findall(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Desktop host attached',
                          added, re.M)
    if not attaches:
        print('  no attach lines after the restart - the app did not rebuild')
        return 1

    def parse(ts):
        return datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')

    first = parse(attaches[0])
    last = parse(attaches[-1])

    print('  %d wallpaper window(s) rebuilt' % len(attaches))
    print()
    print('    first attach : %s   (+%.0f ms after the shell returned)'
          % (first.strftime('%H:%M:%S.%f')[:-3], (first - shell_back).total_seconds() * 1000))
    print('    last attach  : %s   (+%.0f ms after the shell returned)'
          % (last.strftime('%H:%M:%S.%f')[:-3], (last - shell_back).total_seconds() * 1000))
    print('    spread       : %.0f ms across %d monitors'
          % ((last - first).total_seconds() * 1000, len(attaches)))
    print()

    total_ms = (last - shell_back).total_seconds() * 1000
    print('  recovery: %.0f ms from the shell returning to the last wallpaper' % total_ms)
    print()
    print('  the page claims "under 4 seconds"')
    if total_ms < 4000:
        print('  measured %.0f ms - the claim holds' % total_ms)
        return 0
    print('  measured %.0f ms - the claim is WRONG and must be changed' % total_ms)
    return 1


if __name__ == '__main__':
    sys.exit(main())
