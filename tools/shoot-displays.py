#!/usr/bin/env python3
"""Tangkap layar halaman Displays, untuk dilihat langsung.

Pemakaian:
  python tools/shoot-displays.py
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def main():
    # Buka halaman Displays lewat UI.
    skrip = (
        "Add-Type -AssemblyName UIAutomationClient;"
        "$w = [System.Windows.Automation.AutomationElement]::RootElement;"
        "$c = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, 'LumaWall');"
        "$win = $w.FindFirst([System.Windows.Automation.TreeScope]::Children, $c);"
        "if (-not $win) { Write-Output 'NO_WINDOW'; exit }"
        "$b = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, 'Displays');"
        "$el = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $b);"
        "if ($el) { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); "
        "Write-Output 'OK' } else { Write-Output 'NO_BUTTON' }"
    )
    r = subprocess.run(['powershell', '-NoProfile', '-Command', skrip],
                       capture_output=True, text=True, timeout=60)
    print('  buka Displays: %s' % (r.stdout or '').strip())
    time.sleep(3)

    # Cari jendela utama LumaWall.
    keluaran = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "(Get-Process LumaWall -ErrorAction SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle } | Select-Object -First 1).Id"],
        capture_output=True, text=True, timeout=30).stdout
    pid = None
    for t in keluaran.split():
        if t.strip().isdigit():
            pid = int(t.strip())
            break
    if pid is None:
        print('  ! aplikasi tidak jalan')
        return 1

    jendela = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w > 900 and h > 600:
            jendela.append((int(hwnd), r.left, r.top, w, h))
        return True

    user32.EnumWindows(cb, 0)
    if not jendela:
        print('  ! jendela utama tidak ditemukan')
        return 1

    hwnd, x, y, w, h = sorted(jendela, key=lambda t: -t[3] * t[4])[0]
    print('  jendela: %dx%d di (%d,%d)' % (w, h, x, y))

    # Bawa ke depan supaya tidak tertutup jendela lain.
    user32.SetForegroundWindow(hwnd)
    time.sleep(1)

    keluar = Path('build/displays.png')
    keluar.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        "Add-Type -AssemblyName System.Drawing;"
        "$b = New-Object System.Drawing.Bitmap(%d,%d);"
        "$g = [System.Drawing.Graphics]::FromImage($b);"
        "$g.CopyFromScreen(%d,%d,0,0,(New-Object System.Drawing.Size(%d,%d)));"
        "$b.Save('%s');" % (w, h, x, y, w, h, str(keluar.resolve()).replace('\\', '\\\\'))
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, text=True, timeout=60)

    if keluar.exists():
        print('  disimpan: %s' % keluar)
        return 0
    print('  ! tangkapan layar gagal')
    return 1


if __name__ == '__main__':
    sys.exit(main())
