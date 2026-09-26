"""check-memory-plan.py — is the memory work intact, and are the traps still avoided?

Why this exists:

Every item in the memory plan is invisible when it breaks:

  * A browser argument deleted during a refactor changes no test, no build, no
    screenshot - it just quietly stops saving memory.
  * The one thing in this whole area that must NEVER come back is the working-set
    trim. It broke the wallpapers twice, and both times the log looked healthy:
    "5/5 process(es) trimmed" while every screen was black. It is a cheap change to
    re-add and an expensive one to diagnose, so it is pinned here by name along with
    the measurements that condemned it.

This is a source check. The runtime proof is tools/check-wallpaper-alive.ps1, which
reports whether the videos are actually decoding.

Usage:
    python tools/check-memory-plan.py
"""

import os
import re
import sys

PROGRAM = 'LumaWall/Program.cs'
TRIM = 'LumaWall/MemoryTrim.cs'
WINDOW = 'LumaWall/MainWindow.cs'

# Every browser argument the memory plan depends on, with why it is there. Removing
# any of these is a silent regression, so each one is named rather than counted.
REQUIRED_ARGUMENTS = {
    '--disable-back-forward-cache':
        'a wallpaper never navigates back, so a frozen page snapshot per history '
        'step is pure waste',
    '--js-flags=--scavenger_max_new_space_capacity_mb=8':
        'caps the V8 young generation; documented by WebView2 as a memory reducer',
    '--disk-cache-size=33554432':
        'a deterministic ceiling on the disk cache',
    '--skia-font-cache-limit-mb=8':
        'a deterministic ceiling on the font cache',
    '--skia-resource-cache-limit-mb=16':
        'a deterministic ceiling on the resource cache',
}

# Arguments that must NOT be present, each with the reason it was rejected. These
# are the tempting ones - every one of them looks like an easy win.
FORBIDDEN_ARGUMENTS = {
    '--process-per-site':
        'collapses every display onto ONE renderer, so a single crash takes down '
        'every monitor - and it is what let a trim reach a renderer still playing',
    '--renderer-process-limit=1':
        'the same coupling as --process-per-site, stated explicitly',
    '--enable-low-end-device-mode':
        'can silently change raster and decode quality, which the user ruled out',
    '--disable-accelerated-video-decode':
        'software decode costs RAM AND runs in a lower-privilege process',
    '--disable-gpu-memory-buffer-video-frames':
        'removes the zero-copy GPU path, creating the copies we are avoiding',
    '--msWebView2SimulateMemoryPressureWhenInactive':
        'never fires for a wallpaper: the window stays visible even when covered, '
        'so WebView2 never considers it inactive. The CDP call replaces it.',
}

# The API calls the plan is built on. Each must appear somewhere in the app.
REQUIRED_CALLS = [
    ('Memory.simulatePressureNotification',
     'the browser-side purge, fired when the app knows the wallpaper stopped'),
    ('Memory.forciblyPurgeJavaScriptMemory',
     'drops stale JS heap on a paused wallpaper'),
    ('MemoryUsageTargetLevel',
     'the documented per-WebView memory target'),
]

# The working-set trim and the two Win32 calls it needs. These must NOT be present.
# Both attempts at trimming killed the video decoders - see the note in MemoryTrim.cs
# - and the second attempt's log looked perfect while every screen was black.
FORBIDDEN_CALLS = [
    ('EmptyWorkingSet',
     'trims a working set; measured to kill video decode, and the decoder did not '
     'come back when the wallpaper resumed'),
    ('SetProcessWorkingSetSize',
     'the same operation; same measurement, same result'),
]


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def main():
    problems = []
    notes = []

    print()
    print('  memory plan: is the surviving work in place, and the traps avoided?')
    print()

    for path in (PROGRAM, TRIM, WINDOW):
        if not os.path.exists(path):
            print('  missing %s' % path)
            return 1

    program = read(PROGRAM)
    trim = read(TRIM)

    # ── 1. the browser arguments ─────────────────────────────────────────────
    #
    # Read from the argument array specifically, not the whole file: several of these
    # names appear in the comments explaining why they are absent, and a whole-file
    # search would find the explanation and call it a present argument.
    match = re.search(r'string arguments = string\.Join\([^;]*?\}\s*\);', program, re.S)
    if not match:
        problems.append('%s: could not find the browser argument list' % PROGRAM)
        argument_text = ''
    else:
        argument_text = match.group(0)

    for argument, why in sorted(REQUIRED_ARGUMENTS.items()):
        if '"%s"' % argument in argument_text:
            print('    present  %s' % argument)
        else:
            problems.append('browser argument missing: %s (%s)' % (argument, why))
            print('    MISSING  %s' % argument)

    for argument, why in sorted(FORBIDDEN_ARGUMENTS.items()):
        if '"%s"' % argument in argument_text:
            problems.append('browser argument must not ship: %s (%s)' % (argument, why))
            print('    SHIPPED  %s  <-- should not be here' % argument)

    # ── 2. the API calls that are kept ───────────────────────────────────────
    print()
    combined = program + trim
    for call, why in REQUIRED_CALLS:
        if call in combined:
            print('    present  %s' % call)
        else:
            problems.append('API call missing: %s (%s)' % (call, why))
            print('    MISSING  %s' % call)

    # ── 3. the calls that must stay gone ─────────────────────────────────────
    #
    # Matched as a DECLARATION, not as a call or a bare word. The names appear
    # legitimately in two places that must not trip this: the comment in MemoryTrim.cs
    # that explains why the trim was removed, and the checker's own forbidden list.
    # Matching a bare name flagged the explanation, and a checker that reports the
    # documentation as the fault is one people learn to ignore.
    print()
    for call, why in FORBIDDEN_CALLS:
        # A P/Invoke declaration is the thing that makes the function callable:
        # `[DllImport("...")] ... extern bool EmptyWorkingSet(...)`. Comments never
        # match this, because they contain no `extern` on the same construct.
        declared = re.search(
            r'\[DllImport[^\]]*\]\s*(?:private|internal|public)?\s*static\s*extern\s+[\w\.<>\[\]]+\s+%s\b' % call,
            trim + program)
        if declared:
            problems.append('the working-set trim is back: %s (%s)' % (call, why))
            print('    PRESENT  %s  <-- this is what broke the wallpapers' % call)
        else:
            print('    absent   %s' % call)

    # ── 4. the gates on what remains ─────────────────────────────────────────
    #
    # The safety property of the surviving memory work is that it never runs while a
    # wallpaper is playing. Each gate is checked by name, because the failure mode is
    # a gate that quietly stops being consulted.
    print()
    gates = [
        (r'public void MaintainPausedMemory\(\)[\s\S]{0,500}?if \(!playbackPaused \|\| staticMode\) return;',
         'MaintainPausedMemory refuses to run for a playing wallpaper'),
        (r'private void PurgeJavaScriptMemory\(\)[\s\S]{0,400}?if \(!playbackPaused\) return;',
         'PurgeJavaScriptMemory is gated on the paused state'),
        (r'private void RequestMemoryPressure\(\)[\s\S]{0,400}?if \(staticMode\) return;',
         'RequestMemoryPressure has its own guard'),
    ]

    for pattern, description in gates:
        if re.search(pattern, program):
            print('    held     %s' % description)
        else:
            problems.append('gate not found: %s' % description)
            print('    BROKEN   %s' % description)

    # ── 5. the honest reporting ──────────────────────────────────────────────
    #
    # The UI must show commit as well as working set. Two numbers, because a single
    # one can be read as a saving that is not there.
    print()
    if 'CollectMemory' in program and 'telemetryRamDetail' in read(WINDOW):
        print('    present  the panel reports the whole group and the commit figure')
    else:
        notes.append('the performance panel does not report the browser group and '
                     'commit; a memory figure would then be misleading')

    # ── report ───────────────────────────────────────────────────────────────
    print()
    if notes:
        for note in notes:
            print('  note: %s' % note)
        print()

    if problems:
        print('  %d problem(s):' % len(problems))
        for problem in problems:
            print('    · %s' % problem)
        print()
        return 1

    print('  the surviving work is in place and the traps are absent')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
