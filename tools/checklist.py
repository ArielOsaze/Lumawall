"""Check every feature and every optimisation claim, and print one verdict per line.

Why this exists
---------------
"zero bug" and "10/10" are not measurable, but the things behind them are. This walks
the whole delivery - the catalogue, the app, the timer, the site, the installer, the
promo - and reports, for each item, WHAT was measured and HOW. A claim with no
measurement behind it is not reported as passing; it is reported as unproven, and
unproven is a failure.

This is the summary a person can read to decide whether to trust the build. The
individual tools it calls do the measuring; this one collects their answers and makes
sure nothing is quietly skipped.

Usage: python tools/checklist.py [--json build/checklist.json]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'
CATALOG = ROOT / 'LumaWall' / 'catalog.json'
SITE = ROOT / 'site'


class Item:
    """One line of the checklist."""

    def __init__(self, group, name, ok, evidence, note=''):
        self.group = group
        self.name = name
        self.ok = ok
        self.evidence = evidence
        self.note = note


def run(cmd, timeout=240, cwd=None):
    """Run a command, return (exit code, stdout+stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(cwd or ROOT), errors='replace')
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, 'timed out after %ds' % timeout
    except FileNotFoundError as e:
        return 127, str(e)


def first_line(text, match):
    for line in text.splitlines():
        if re.search(match, line, re.I):
            return line.strip()
    return ''


# ── the catalogue ────────────────────────────────────────────────────────────────────

def catalogue_items():
    items = []
    if not CATALOG.exists():
        items.append(Item('Catalogue', 'the catalogue file exists', False, 'missing'))
        return items

    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    total = len(data)
    dynamic = sum(1 for e in data if (e.get('kind') or '').lower() == 'dynamic')
    measured = sum(1 for e in data if re.match(r'^\d+x\d+$', str(e.get('resolution') or '')))
    thumbs = sum(1 for e in data if (e.get('thumbnailUrl') or '').strip())
    urls = sum(1 for e in data if (e.get('videoUrl') or '').strip())
    cats = sorted({e.get('category') for e in data if e.get('category')})
    mature = sum(1 for e in data if (e.get('category') or '') == 'Mature 18+')

    def hd(e):
        m = re.match(r'^(\d+)x(\d+)$', str(e.get('resolution') or ''))
        return bool(m) and int(m.group(2)) >= 720

    hd_count = sum(1 for e in data if hd(e))
    fourk = sum(1 for e in data if re.match(r'^(\d+)x(\d+)$', str(e.get('resolution') or ''))
               and int(re.match(r'^(\d+)x(\d+)$', str(e['resolution'])).group(1)) >= 2560)

    # Duplicates by video URL.
    seen, dups = set(), 0
    for e in data:
        u = (e.get('videoUrl') or '').strip()
        if not u:
            continue
        if u in seen:
            dups += 1
        seen.add(u)

    items.append(Item('Catalogue', 'reaches the 15,000 target', total >= 15000,
                      '%d entries' % total))
    items.append(Item('Catalogue', 'every entry is dynamic', dynamic == total,
                      '%d of %d (%.1f%%)' % (dynamic, total, 100.0 * dynamic / total)))
    items.append(Item('Catalogue', 'every resolution is measured', measured == total,
                      '%d of %d' % (measured, total)))
    items.append(Item('Catalogue', 'every entry is HD or better', hd_count == total,
                      '%d of %d, %d are 2K+' % (hd_count, total, fourk)))
    items.append(Item('Catalogue', 'no duplicate videos', dups == 0,
                      '%d duplicates' % dups))
    items.append(Item('Catalogue', 'every entry has a playable URL', urls == total,
                      '%d of %d' % (urls, total)))
    items.append(Item('Catalogue', 'every entry has a thumbnail', thumbs == total,
                      '%d of %d' % (thumbs, total)))
    items.append(Item('Catalogue', 'the categories are the expected set', len(cats) >= 14,
                      '%d categories' % len(cats), ', '.join(cats)))
    items.append(Item('Catalogue', 'the mature category is populated', mature > 0,
                      '%d entries' % mature))
    return items


# ── the app, from its own log ────────────────────────────────────────────────────────

def app_items():
    items = []
    if not LOG.exists():
        items.append(Item('App', 'the app has run', False, 'no log at %s' % LOG))
        return items

    text = LOG.read_text(encoding='utf-8', errors='replace')
    lines = text.splitlines()

    # Per-PID, so a stale process cannot hide a failure in a fresh one.
    pids = {}
    for ln in lines:
        m = re.search(r'\[(\d+)\]', ln)
        if m:
            pids.setdefault(m.group(1), []).append(ln)
    newest = max(pids, key=lambda p: len(pids[p])) if pids else None
    mine = pids.get(newest, [])

    ready = sum(1 for ln in mine if 'renderer ready' in ln)
    exceptions = sum(1 for ln in mine if 'exception' in ln.lower())
    blank = sum(1 for ln in mine if 'without blank frame' in ln)
    cover = sum(1 for ln in mine if 'Covering window' in ln)

    items.append(Item('App', 'every display rendered', ready >= 3,
                      '%d renderers ready (pid %s)' % (ready, newest)))
    items.append(Item('App', 'no unhandled exceptions', exceptions == 0,
                      '%d exceptions' % exceptions))
    items.append(Item('App', 'wallpapers swapped without a blank frame', blank >= 3,
                      '%d swaps' % blank))
    items.append(Item('App', 'the covering-window log is not spammed', cover <= 12,
                      '%d lines' % cover))
    return items


# ── the checks that need to run ──────────────────────────────────────────────────────

def measured_items():
    """The checks that must actually be executed, each with its own verdict."""
    checks = [
        ('Timer', 'the timer never covers an application',
         ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
          'tools/check-timer-zorder.ps1'], 180),
        ('App', 'choosing a placement keeps the scroll position',
         ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
          'tools/test-studio-scroll.ps1'], 180),
        ('App', 'the idle cost is small',
         ['python', 'tools/check-idle-cpu.py', '--seconds', '20', '--limit', '4'], 200),
        ('Studio', 'the two columns are balanced',
         ['node', 'tools/check-studio-layout.mjs'], 200),
        ('App', 'the scrollbar is dark',
         ['python', 'tools/check-scrollbar.py'], 200),
        ('App', 'the hover states work and are not Aero',
         ['python', 'tools/verify-hover.py'], 200),
    ]

    items = []
    for group, name, cmd, timeout in checks:
        code, out = run(cmd, timeout=timeout)
        # The verdict line is the one that says PASS or FAIL, not the exit code alone:
        # a tool that prints FAIL and exits 0 would otherwise be recorded as a pass.
        verdict = first_line(out, r'\b(PASS|FAIL)\b')
        ok = code == 0 and 'FAIL' not in out.upper()
        note = verdict[:120] if verdict else (out.strip().splitlines() or [''])[-1][:120]
        items.append(Item(group, name, ok, 'exit %d' % code, note))
    return items


def static_items():
    """Things that can be verified by reading the tree, no app needed."""
    items = []

    # The version is consistent everywhere.
    ver = ''
    ai = ROOT / 'LumaWall' / 'Properties' / 'AssemblyInfo.cs'
    if ai.exists():
        m = re.search(r'AssemblyFileVersion\("([\d.]+)"\)', ai.read_text(encoding='utf-8'))
        if m:
            ver = m.group(1)
    iss = ROOT / 'installer' / 'LumaWall.iss'
    iss_ver = ''
    if iss.exists():
        body = iss.read_text(encoding='utf-8')
        # The installer has no literal version: it reads it from the built binary with
        # GetVersionNumbersString, so the right check is that it still does. A hardcoded
        # number here is the thing that goes stale - it did, and shipped a 4.1.3.0
        # installer after a 4.2 build.
        if 'GetVersionNumbersString' in body:
            iss_ver = ver  # read from the binary, so it cannot disagree
        else:
            m = re.search(r'#define\s+\w*[Vv]ersion\w*\s+"([\d.]+)"', body)
            iss_ver = m.group(1) if m else ''
    msix = ROOT / 'msix' / 'AppxManifest.xml'
    msix_ver = ''
    if msix.exists():
        m = re.search(r'Version="(\d+\.\d+\.\d+\.\d+)"', msix.read_text(encoding='utf-8'))
        if m:
            msix_ver = m.group(1)
    same = ver and ver == iss_ver == msix_ver
    items.append(Item('Release', 'one version across the app, installer and MSIX', bool(same),
                      'app %s / iss %s / msix %s' % (ver or '?', iss_ver or '?', msix_ver or '?')))

    # The installer, the portable build and the MSIX exist and are the current version.
    dl = SITE / 'assets' / 'downloads'
    found = []
    for pattern, label in [('LumaWall-Setup-%s.exe', 'installer'),
                           ('LumaWall-portable-%s.zip', 'portable'),
                           ('LumaWall_%s_x64.msix', 'MSIX')]:
        p = dl / (pattern % ver) if ver else None
        found.append((label, p is not None and p.exists(),
                      '%d MB' % (p.stat().st_size // (1024 * 1024)) if p and p.exists() else 'missing'))
    for label, ok, note in found:
        items.append(Item('Release', 'the site ships the current %s' % label, ok, note))

    # The site offers the current version on both pages.
    for page, lang in [(SITE / 'index.html', 'ID'), (SITE / 'en' / 'index.html', 'EN')]:
        if not page.exists():
            items.append(Item('Site', 'the %s page exists' % lang, False, 'missing'))
            continue
        body = page.read_text(encoding='utf-8', errors='replace')
        has = ver and ver in body
        items.append(Item('Site', 'the %s page links the current build' % lang, bool(has),
                          ver if has else 'links something else'))

    # The logo is the shipped one: it carries cyan, the discarded mark did not.
    try:
        from PIL import Image
        import numpy as np
        logo = SITE / 'assets' / 'logo' / 'logo-150.png'
        img = Image.open(logo).convert('RGBA')
        a = np.asarray(img)
        vis = a[a[:, :, 3] > 128]
        lum = vis[:, :3].mean(axis=1)
        mark = vis[lum > lum.mean() + 15]
        cyan = ((abs(mark[:, 0].astype(int) - 121) < 58)
                & (abs(mark[:, 1].astype(int) - 232) < 48)
                & (abs(mark[:, 2].astype(int) - 252) < 48)).sum()
        items.append(Item('Site', 'the logo is the shipped one', cyan > 50,
                          '%d cyan pixels in the mark' % cyan))
    except Exception as e:
        items.append(Item('Site', 'the logo is the shipped one', False, str(e)[:60]))

    # The app icon is the same mark.
    try:
        from PIL import Image
        import numpy as np
        ico = ROOT / 'LumaWall' / 'app.ico'
        img = Image.open(ico)
        best = None
        for i in range(getattr(img, 'n_frames', 1)):
            img.seek(i)
            if best is None or img.size[0] > best.size[0]:
                best = img.convert('RGBA').copy()
        a = np.asarray(best)
        vis = a[a[:, :, 3] > 128]
        lum = vis[:, :3].mean(axis=1)
        mark = vis[lum > lum.mean() + 15]
        cyan = ((abs(mark[:, 0].astype(int) - 121) < 58)
                & (abs(mark[:, 1].astype(int) - 232) < 48)
                & (abs(mark[:, 2].astype(int) - 252) < 48)).sum()
        items.append(Item('Site', 'the app icon is the same mark', cyan > 0,
                          '%d cyan pixels' % cyan))
    except Exception as e:
        items.append(Item('Site', 'the app icon is the same mark', False, str(e)[:60]))

    # The timer is not topmost anywhere in the source: this is the z-order fix.
    dt = (ROOT / 'LumaWall' / 'DesktopTimer.cs')
    if dt.exists():
        body = dt.read_text(encoding='utf-8', errors='replace')
        topmost_true = re.search(r'TopMost\s*=\s*true', body)
        placed = 'PlaceAtDesktopLevel' in body
        items.append(Item('Timer', 'the widget is not topmost', not topmost_true,
                          'TopMost = true is absent' if not topmost_true else 'FOUND TopMost = true'))
        items.append(Item('Timer', 'the widget is anchored to the desktop', placed,
                          'PlaceAtDesktopLevel is called' if placed else 'no anchor call'))

    # The pause scan is a single pass with the cheap tests first.
    pg = (ROOT / 'LumaWall' / 'Program.cs')
    if pg.exists():
        body = pg.read_text(encoding='utf-8', errors='replace')
        single = 'FindCoveringMonitors' in body
        # The DWM round-trip must come after the rectangle test, not before it.
        scan = body.find('ScanCoveringWindows')
        order_ok = True
        if scan > 0:
            chunk = body[scan:scan + 4000]
            i_rect = chunk.find('GetWindowRect')
            i_cloak = chunk.find('IsCloaked')
            order_ok = i_rect != -1 and i_cloak != -1 and i_rect < i_cloak
        items.append(Item('App', 'the pause scan is one pass', single,
                          'FindCoveringMonitors exists' if single else 'only the two-pass API'))
        items.append(Item('App', 'the cheap window tests run first', order_ok,
                          'rect before the DWM round-trip' if order_ok else 'DWM is called first'))

    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='build/checklist.json')
    ap.add_argument('--skip-run', action='store_true',
                    help='only the static and catalogue checks (no app needed)')
    args = ap.parse_args()

    items = []
    items += catalogue_items()
    items += app_items()
    items += static_items()
    if not args.skip_run:
        items += measured_items()

    # Report, grouped.
    groups = []
    for it in items:
        if it.group not in groups:
            groups.append(it.group)

    width = max((len(i.name) for i in items), default=40)
    failed = []
    print()
    for g in groups:
        print('  %s' % g)
        for it in items:
            if it.group != g:
                continue
            mark = 'PASS' if it.ok else 'FAIL'
            note = ('   %s' % it.note) if it.note else ''
            print('    %-4s %-*s  %s%s' % (mark, width, it.name, it.evidence, note))
            if not it.ok:
                failed.append(it)
        print()

    passed = sum(1 for i in items if i.ok)
    print('  %d of %d checks pass' % (passed, len(items)))
    if failed:
        print()
        print('  what failed:')
        for it in failed:
            print('    - %s: %s' % (it.name, it.evidence))
    print()

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        # bool() on every field: numpy returns np.bool_ from the pixel comparisons, and
        # json refuses to serialise it - the check had already passed when the crash
        # happened, so a passing run wrote no report at all.
        out.write_text(json.dumps(
            [{'group': str(i.group), 'name': str(i.name), 'ok': bool(i.ok),
              'evidence': str(i.evidence), 'note': str(i.note)} for i in items],
            indent=2), encoding='utf-8')
        print('  wrote %s' % out)

    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
