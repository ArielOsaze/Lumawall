"""check-memory-plan.py — is the memory work still intact?

Why this exists:

Every item in the memory plan is invisible when it breaks:

  * A browser argument deleted during a refactor changes no test, no build, no
    screenshot - it just quietly stops saving memory.
  * `MemoryTrim.TrimProcess` is called only while a wallpaper is paused, which is
    not the state any screenshot is taken in.
  * The gate that keeps trimming off a PLAYING wallpaper is the one thing in this
    whole area that must never be relaxed, and relaxing it looks like a one-line
    simplification.

So this reads the source and checks that each piece is present and each gate is
still closed. It is a source check, not a runtime one: the runtime proof is
tools/measure-memory.ps1, which needs a running app and a fullscreen cover.

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
    '--process-per-site':
        'keeps the multi-monitor case at one renderer instead of one per display',
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
    '--renderer-process-limit=1':
        'one renderer crash would take down every monitor\'s wallpaper',
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
    ('EmptyWorkingSet',
     'the working-set trim'),
    ('GetProcessInfos',
     'enumerates the browser group so the trim can reach it'),
]


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def main():
    problems = []
    notes = []

    print()
    print('  memory plan: is every optimisation still in place?')
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

    # ── 2. the API calls ─────────────────────────────────────────────────────
    print()
    combined = program + trim
    for call, why in REQUIRED_CALLS:
        if call in combined:
            print('    present  %s' % call)
        else:
            problems.append('API call missing: %s (%s)' % (call, why))
            print('    MISSING  %s' % call)

    # ── 3. the gates ─────────────────────────────────────────────────────────
    #
    # The safety property of this whole area is that nothing memory-related runs
    # while a wallpaper is playing. Each gate is checked by name, because the
    # failure mode is a gate that quietly stops being consulted.
    print()
    gates = [
        # TrimIfHidden must refuse to trim unless playback is paused.
        (r'public void TrimIfHidden\(\)[\s\S]{0,600}?if \(!playbackPaused\) return;',
         'TrimIfHidden refuses to trim a playing wallpaper'),
        # TrimNow must re-check on the worker: the user can resume in between.
        (r'private void TrimNow\([\s\S]{0,400}?if \(!playbackPaused\) return;',
         'TrimNow re-checks the pause state on the worker thread'),
        # MaintainPausedMemory must be gated too.
        (r'public void MaintainPausedMemory\(\)[\s\S]{0,300}?if \(!playbackPaused \|\| staticMode\) return;',
         'MaintainPausedMemory is gated on the paused state'),
        # The purge must not run on a playing wallpaper.
        (r'private void PurgeJavaScriptMemory\(\)[\s\S]{0,400}?if \(!playbackPaused\) return;',
         'PurgeJavaScriptMemory is gated on the paused state'),
        # The trim must run off the UI thread.
        (r'Task\.Run\(delegate \{ TrimNow\(',
         'the trim runs on a worker, not the UI thread'),
    ]

    for pattern, description in gates:
        if re.search(pattern, program):
            print('    held     %s' % description)
        else:
            problems.append('gate not found: %s' % description)
            print('    BROKEN   %s' % description)

    # ── 4. the empty-working-set declaration ─────────────────────────────────
    #
    # This was wrong once - declared in kernel32.dll, where the entry point does not
    # exist - and the resulting exception silently disabled the trim while the log
    # still reported a count. Checked by name so it cannot come back.
    print()
    if re.search(r'\[DllImport\("psapi\.dll"[^\)]*\)\]\s*private static extern bool EmptyWorkingSet', trim):
        print('    correct  EmptyWorkingSet is imported from psapi.dll')
    else:
        problems.append('EmptyWorkingSet must be imported from psapi.dll, not kernel32.dll '
                        '(the wrong DLL throws at call time and silently disables the trim)')
        print('    WRONG    EmptyWorkingSet is not imported from psapi.dll')

    # ── 5. the honest reporting ──────────────────────────────────────────────
    #
    # The UI must show commit as well as working set, or a trim looks like a release.
    print()
    if 'CollectMemory' in program and 'telemetryRamDetail' in read(WINDOW):
        print('    present  the panel reports the whole group and the commit figure')
    else:
        notes.append('the performance panel does not report the browser group and '
                     'commit; a working-set trim would then look like a real release')

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

    print('  every argument, call and gate is in place')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
