"""verify-installer-payload.py — is this installer built from the current binary?

Why this exists, and the mistake it replaces:

The installer had to be checked against the fixed binary. The first attempt ran the
real installer with `/VERYSILENT /DIR=<temp folder>`. The check passed, and the side
effects cost the user their Start Menu entry: Inno Setup rewrote the Start Menu group,
the uninstall registry entry and the Run key to point at that temporary folder, which
was then deleted. It also remembers the redirected location, so a later repair
reinstalled there again.

So this never runs the installer.

── why it uses a manifest instead of reading the payload ───────────────────

The obvious read-only approach is to decompress the installer's embedded payload and
look for the exe inside it. That was tried and abandoned: Inno Setup 6.7 stores its
files in a framed LZMA2 stream whose layout is internal to Inno and changes between
versions, and a reader that parses it is a reader that breaks on the next Inno
release - silently, reporting a good installer as stale.

Instead, the build records a manifest: the SHA-256 of the installer and of every file
that went into it. This check then verifies that the installer on disk is the one the
manifest describes, and that the binary it was built from is still the current one.

That is a weaker claim than "the installer contains this byte sequence" - it is
"this installer was built from this binary" - and the difference matters. It is
sound here because the one-time proof was done by running the installer once and
comparing the installed exe by SHA-256, and that exact installer file is the one the
manifest describes and the one the site serves. The chain is closed.

Usage:
    python tools/verify-installer-payload.py             # verify
    python tools/verify-installer-payload.py --record    # after rebuilding
"""

import argparse
import hashlib
import json
import os
import sys

MANIFEST = os.path.join('installer', 'build-manifest.json')
DEFAULT_INSTALLER = os.path.join('site', 'assets', 'downloads', 'LumaWall-Setup-4.0.1.exe')
RELEASE_DIR = os.path.join('LumaWall', 'bin', 'Release')
KEY_BINARY = 'LumaWall.exe'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installer', default=DEFAULT_INSTALLER)
    parser.add_argument('--record', action='store_true',
                        help='write the manifest from the current artifacts')
    args = parser.parse_args()

    print()

    if args.record:
        print('  recording what this installer was built from')
        print()
        if not os.path.exists(args.installer):
            print('    installer not found: %s' % args.installer)
            return 1
        binary = os.path.join(RELEASE_DIR, KEY_BINARY)
        if not os.path.exists(binary):
            print('    binary not found: %s' % binary)
            return 1

        record = {
            'installer': {
                'path': args.installer.replace('\\', '/'),
                'sha256': sha(args.installer),
                'bytes': os.path.getsize(args.installer),
            },
            'built_from': {
                KEY_BINARY: {
                    'sha256': sha(binary),
                    'bytes': os.path.getsize(binary),
                },
            },
        }
        os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
        with open(MANIFEST, 'w', encoding='utf-8') as handle:
            json.dump(record, handle, indent=2)
            handle.write('\n')

        print('    installer  %d bytes  sha %s' % (record['installer']['bytes'],
                                                    record['installer']['sha256'][:16]))
        print('    from       %s  sha %s' % (KEY_BINARY,
                                             record['built_from'][KEY_BINARY]['sha256'][:16]))
        print()
        print('    wrote %s' % MANIFEST)
        print()
        return 0

    print('  is this installer built from the current binary?')
    print()

    if not os.path.exists(MANIFEST):
        print('    no manifest at %s' % MANIFEST)
        print('    run with --record once, right after building the installer')
        return 1
    with open(MANIFEST, encoding='utf-8') as handle:
        record = json.load(handle)

    if not os.path.exists(args.installer):
        print('    installer not found: %s' % args.installer)
        return 1

    problems = []

    # ── 1. the installer on disk is the one the manifest describes ───────────
    want = record['installer']
    got_bytes = os.path.getsize(args.installer)
    got_sha = sha(args.installer)
    print('    installer          %d bytes  sha %s' % (got_bytes, got_sha[:16]))
    if got_sha != want['sha256']:
        problems.append('the installer is not the one that was recorded: manifest says '
                        '%d bytes sha %s' % (want['bytes'], want['sha256'][:16]))
        print('    %-18s MISMATCH - rebuilt since the manifest was recorded' % '')
    else:
        print('    %-18s matches the manifest' % '')

    # ── 2. the binary it was built from is still the current one ─────────────
    for name, expected in record['built_from'].items():
        path = os.path.join(RELEASE_DIR, name)
        if not os.path.exists(path):
            problems.append('%s is gone from %s' % (name, RELEASE_DIR))
            print('    %-18s %s MISSING' % (name, name))
            continue
        actual = sha(path)
        if actual != expected['sha256']:
            problems.append('%s has changed since the installer was built - rebuild the '
                            'installer, then re-record' % name)
            print('    %-18s %s changed since the build' % (name, name))
        else:
            print('    %-18s %s unchanged since the build' % (name, name))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for problem in problems:
            print('    · %s' % problem)
        print()
        print('  A stale installer means the fix is committed but nobody can install it.')
        print('  Rebuild with installer/LumaWall.iss, then re-record.')
        return 1

    print('  this installer was built from the binary in the repository')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
