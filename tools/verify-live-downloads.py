"""verify-live-downloads.py — are the downloads on the site the builds we just made?

Why this exists:

A stale installer is the worst kind of bug this project has: the fix is real, the
commit is pushed, and the person who downloads the app still gets the broken build.
It happened - the site served a 25 September installer for a day after the wallpaper
bug was fixed, because nothing compared the live file to the local one.

Byte comparison is not enough on its own, because a download can be re-encoded in
transit. So this checks the size, the Content-Encoding, and the SHA-256 of what
actually arrives.

Usage:
    python tools/verify-live-downloads.py
"""

import hashlib
import os
import sys
import urllib.error
import urllib.request

BASE = 'https://lumawall.xinet.id/assets/downloads/'
LOCAL_DIR = os.path.join('site', 'assets', 'downloads')

FILES = [
    'LumaWall-Setup-4.0.1.exe',
    'LumaWall_4.0.1.0_x64.msix',
    'LumaWall-portable-4.0.1.zip',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    problems = []
    print()
    print('  are the live downloads the builds we made?')
    print()

    for name in FILES:
        local_path = os.path.join(LOCAL_DIR, name)
        if not os.path.exists(local_path):
            problems.append('%s is not in %s' % (name, LOCAL_DIR))
            print('    %-32s MISSING LOCALLY' % name)
            continue

        with open(local_path, 'rb') as handle:
            local = handle.read()

        try:
            request = urllib.request.Request(BASE + name, headers={'User-Agent': 'LumaWall verify'})
            with urllib.request.urlopen(request, timeout=180) as response:
                live = response.read()
                encoding = response.headers.get('Content-Encoding') or 'none'
        except urllib.error.HTTPError as e:
            problems.append('%s returned HTTP %s' % (name, e.code))
            print('    %-32s HTTP %s' % (name, e.code))
            continue
        except Exception as e:
            problems.append('%s could not be fetched: %s' % (name, e))
            print('    %-32s FETCH FAILED' % name)
            continue

        same = sha(live) == sha(local)
        # A transfer encoding would change the bytes without the file being stale, so
        # it is reported rather than treated as a mismatch.
        note = '' if same else '  <-- the live file is NOT the local file'
        print('    %-32s %10d bytes  encoding=%-8s  %s%s'
              % (name, len(local), encoding, 'IDENTICAL' if same else 'DIFFERENT', note))

        if not same:
            problems.append('%s differs: local %d bytes sha %s, live %d bytes sha %s'
                            % (name, len(local), sha(local)[:12], len(live), sha(live)[:12]))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for problem in problems:
            print('    · %s' % problem)
        print()
        print('  A stale download means the fix is committed but nobody can get it.')
        return 1

    print('  every download on the site is the build in the repository')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
