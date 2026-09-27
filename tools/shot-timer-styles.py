"""Photograph the real desktop timer, one style at a time, and save a sheet.

Why this exists
---------------
tools/render-timer-styles.py draws the styles with PIL by reproducing the layout rules. That
is a reasonable sketch and it cannot be trusted: it is a second implementation, so a style
that is wrong in DesktopTimer.cs and right in the sketch passes, and a style that exists only
in the app - the iOS lock-screen family - is not drawn at all.

This drives the real thing. It writes the style into the config, restarts the app, waits for
the widget, and captures the widget's own rectangle from the screen. What ends up in the sheet
is what the user sees.

The capture is of the widget's rectangle only, so the wallpaper behind it is whatever the user
has - which is the point: the widget has to be legible over a real wallpaper, not over a
neutral plate.

Usage: python tools/shot-timer-styles.py [style ...]
"""
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'config.json'
LOG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'
EXE = Path.home() / 'AppData' / 'Local' / 'Programs' / 'LumaWall' / 'LumaWall.exe'
BUILT = ROOT / 'LumaWall' / 'bin' / 'Release' / 'LumaWall.exe'
OUT = ROOT / 'build' / 'timer-styles-real.png'

ALL_STYLES = ['minimal', 'bold', 'glass', 'card', 'ring', 'analog',
              'ioslarge', 'ioslight', 'iosstack', 'iosdate']

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


def luma_pids():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-Process LumaWall -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"],
                         capture_output=True, text=True)
    return [int(x) for x in out.stdout.split() if x.strip().isdigit()]


def stop_app():
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-Process LumaWall -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True, text=True)
    time.sleep(2.5)


def start_app():
    exe = EXE if EXE.exists() else BUILT
    subprocess.run(['powershell', '-NoProfile', '-Command', "Start-Process '%s'" % exe],
                   capture_output=True, text=True)


def set_style(style):
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    cfg.setdefault('Timer', {})
    cfg['Timer']['Enabled'] = True
    cfg['Timer']['Style'] = style
    # A clock, so the same reading appears in every shot and the styles can be compared.
    cfg['Timer']['Mode'] = 'clock'
    cfg['Timer']['ShowDate'] = True
    cfg['Timer']['TwelveHour'] = False
    cfg['Timer']['Scale'] = 150
    cfg['Timer']['Position'] = 'middle-center'
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding='utf-8')


def timer_rect():
    """The widget's screen rectangle, or None."""
    pids = luma_pids()
    if not pids:
        return None
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in pids:
            return True
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        # The widget: small and not the main window.
        if 40 < w < 900 and 30 < h < 500:
            found.append((w * h, r))
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        return None
    found.sort(key=lambda t: -t[0])
    return found[0][1]


def capture(rect, path):
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom),
                         all_screens=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


def hide_app_window():
    """Minimise the main LumaWall window so it does not cover the widget.

    The widget sits at the desktop's level - below every application - which is the fix for
    "gabole menimpa apps yg dibuka". So the app's OWN window covers it too. Capturing
    without hiding the window photographs the app, not the timer.
    """
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "$p = Get-Process LumaWall -ErrorAction SilentlyContinue | "
                    "Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1; "
                    "if ($p) { (New-Object -ComObject WScript.Shell).AppActivate($p.Id) | Out-Null; "
                    "Start-Sleep -Milliseconds 300; "
                    "(New-Object -ComObject WScript.Shell).SendKeys('% n') }"],
                   capture_output=True, text=True)
    time.sleep(1.2)


def main():
    styles = sys.argv[1:] or ALL_STYLES
    shots = []
    failed = []

    for style in styles:
        print('  %-10s' % style, end=' ')
        set_style(style)
        stop_app()
        if LOG.exists():
            LOG.unlink()
        start_app()

        # Wait for the widget to exist and be painted.
        rect = None
        deadline = time.time() + 30
        while time.time() < deadline:
            time.sleep(1.2)
            rect = timer_rect()
            if rect is not None and (rect.right - rect.left) > 40:
                break
        if rect is None:
            print('NO WIDGET')
            failed.append(style)
            continue

        # Get the app window out of the way, then let the widget repaint.
        hide_app_window()
        time.sleep(1.6)

        path = ROOT / 'build' / ('timer-%s.png' % style)
        img = capture(rect, path)

        # Measure what was captured rather than trusting a look: a widget draws opaque
        # glyphs on transparent pixels, so the rectangle must contain a wide range of
        # luminance. A flat capture means the wallpaper or a window was photographed.
        import numpy as np
        a = np.asarray(img.convert('RGB'))
        lum = a.mean(axis=2)
        spread = float(np.percentile(lum, 97) - np.percentile(lum, 3))
        bright = float((lum > 200).mean() * 100)
        shots.append((style, img, spread, bright))
        print('%dx%d  spread %5.1f  bright %4.1f%%' % (img.width, img.height, spread, bright))
        if spread < 40:
            failed.append('%s (flat capture, spread %.0f)' % (style, spread))

    stop_app()

    if not shots:
        print()
        print('  FAIL no style produced a widget - nothing to compare')
        return 1

    # One sheet, on a mid-grey plate so a transparent style is visible against something.
    cell_w = max(i.width for _, i, _, _ in shots) + 30
    cell_h = max(i.height for _, i, _, _ in shots) + 34
    cols = min(3, len(shots))
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new('RGB', (cell_w * cols, cell_h * rows), (74, 78, 86))
    draw = ImageDraw.Draw(sheet)
    for i, (style, img, spread, bright) in enumerate(shots):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        sheet.paste(img, (x + 15, y + 8), img if img.mode == 'RGBA' else None)
        draw.text((x + 15, y + cell_h - 22),
                  '%s   spread %.0f  bright %.0f%%' % (style, spread, bright),
                  fill=(240, 240, 240))
    sheet.save(OUT)
    print()
    print('  wrote %s  (%d styles)' % (OUT, len(shots)))

    if failed:
        print()
        print('  FAIL these styles did not draw: %s' % ', '.join(failed))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
