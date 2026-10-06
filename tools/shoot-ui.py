#!/usr/bin/env python3
"""Tangkap layar halaman Luma Studio dan Displays, untuk memeriksa kerapian UI.

Dipakai untuk melihat sendiri apa yang berantakan, bukan menebak dari kode.
Aman dijalankan saat pengguna bekerja: jendela aplikasi dipindahkan ke layar
uji lebih dulu, dan layar utama tidak disentuh.

Pemakaian:
  python tools/shoot-ui.py --halaman studio
  python tools/shoot-ui.py --halaman displays
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ukur_layar  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pid_lumawall():
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         '(Get-Process LumaWall -EA SilentlyContinue).Id'],
        capture_output=True, text=True, timeout=30)
    return set(int(x) for x in r.stdout.split() if x.strip().isdigit())


def jendela_app():
    """Jendela utama LumaWall, termasuk yang sedang tersembunyi.

    Jendela aplikasi bisa tidak terlihat karena sedang di tray - dan pencarian
    yang hanya menerima jendela terlihat akan melaporkan "aplikasinya tidak
    jalan" padahal ia jalan. Itu menyesatkan: yang salah cuma jendelanya
    tersembunyi, bukan aplikasinya berhenti.
    """
    pids = pid_lumawall()
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value not in pids:
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.startswith('HwndWrapper'):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w < 700 or h < 500:
            return True
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        hasil.append((int(hwnd), ti.value, r.left, r.top, w, h))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def pindah_ke_layar_uji(hwnd, monitor):
    """Pindahkan jendela aplikasi ke layar uji, tanpa menyentuh layar lain."""
    # Ukuran yang cukup untuk melihat seluruh halaman, tetapi tidak melebihi
    # layar uji.
    w = min(1500, monitor['width'] - 20)
    h = min(940, monitor['height'] - 20)
    x = monitor['x'] + (monitor['width'] - w) // 2
    y = monitor['y'] + (monitor['height'] - h) // 2
    user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0004 | 0x0010)
    time.sleep(0.6)


def klik_tombol_nav(monitor, label):
    """Klik tombol navigasi berdasarkan namanya, lewat UI Automation.

    Label disisipkan langsung ke dalam teks skrip, bukan diteruskan sebagai
    argumen: PowerShell menyambung argumen sesudah -Command ke dalam teks
    perintah, dan karena param() tidak lagi jadi pernyataan pertama, nilainya
    tidak sampai. Akibatnya pencarian selalu gagal dengan "TIDAK ADA" padahal
    tombolnya ada.
    """
    aman = label.replace("'", "''")
    ps = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)

# Tombol navigasi punya nama persis sama dengan labelnya. Pencarian memakai
# FindAll lalu dibandingkan di sini, karena FindFirst dengan NameProperty bisa
# mengenai tombol lain yang namanya mengandung label yang sama.
foreach ($b in $all) {
    if ($b.Current.Name -eq '__LABEL__' -and $b.Current.BoundingRectangle.Width -gt 0) {
        $r = $b.Current.BoundingRectangle
        if ($r.Left -lt __X__ -or $r.Left -gt (__X__ + __W__) -or $r.Top -lt __Y__ -or $r.Top -gt (__Y__ + __H__)) {
            Write-Output ("DI LUAR " + [int]$r.Left + "," + [int]$r.Top)
            exit 2
        }
        $p = New-Object System.Windows.Point(($r.Left + $r.Width / 2), ($r.Top + $r.Height / 2))
        [System.Windows.Forms.Cursor]::Position = $p
        Write-Output ("OK " + [int]$r.Left + "," + [int]$r.Top + " " + [int]$r.Width + "x" + [int]$r.Height)
        exit 0
    }
}
Write-Output "TIDAK ADA"
exit 1
'''
    ps = (ps.replace("__LABEL__", aman)
            .replace("__X__", str(int(monitor['x'])))
            .replace("__Y__", str(int(monitor['y'])))
            .replace("__W__", str(int(monitor['width'])))
            .replace("__H__", str(int(monitor['height']))))
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, timeout=90, errors='replace')
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--halaman', required=True,
                    choices=['studio', 'displays', 'koleksi', 'discover'])
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    mon = ukur_layar.pilih(args.display)
    if mon is None:
        print('  layar %s tidak ada' % args.display)
        return 1

    print()
    print('  ══ tangkap halaman %s ══' % args.halaman)
    print()

    j = jendela_app()
    if not j:
        print('  ! jendela LumaWall tidak ditemukan - jalankan aplikasinya dulu')
        return 1

    hwnd, judul, x, y, w, h = j[0]
    print('  jendela: %dx%d di (%d,%d)' % (w, h, x, y))

    # Ditampilkan dulu kalau sedang di tray. Tanpa ini jendelanya tidak
    # terlihat dan tangkapan layarnya kosong.
    SW_SHOW = 5
    SW_RESTORE = 9
    if not user32.IsWindowVisible(hwnd):
        print('  jendela sedang tersembunyi (tray) - ditampilkan')
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_SHOW)
        time.sleep(1.2)

    # Dipindahkan ke layar uji supaya layar utama tidak tersentuh.
    pindah_ke_layar_uji(hwnd, mon)
    j2 = jendela_app()
    if j2:
        hwnd, judul, x, y, w, h = j2[0]
        print('  dipindah: %dx%d di (%d,%d)' % (w, h, x, y))

    # Bawa ke depan.
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

    # Klik navigasi yang diminta.
    # Label sidebar mengikuti bahasa aplikasi: "Monitor" pada bahasa Indonesia,
    # "Displays" pada bahasa Inggris. Mencari satu label saja membuat alat ini
    # gagal di separuh konfigurasi - dan kegagalannya diam-diam, karena halaman
    # yang salah tetap tertangkap dan tampak wajar.
    kandidat = {'studio': ['Luma Studio'],
                'displays': ['Monitor', 'Displays'],
                'koleksi': ['Koleksi', 'Library'],
                'discover': ['Jelajahi', 'Discover']}[args.halaman]
    hasil = ''
    label = kandidat[0]
    for kandidat_label in kandidat:
        label = kandidat_label
        hasil = klik_tombol_nav(mon, kandidat_label)
        if hasil.startswith('OK'):
            break
    print('  navigasi "%s": %s' % (label, hasil))
    if hasil.startswith('OK'):
        import ctypes.wintypes as wt2
        # Klik di posisi yang dilaporkan.
        bagian = hasil.split()[1].split(',')
        px, py = int(bagian[0]), int(bagian[1])
        user32.SetCursorPos(px + 20, py + 10)
        time.sleep(0.2)
        user32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
        time.sleep(0.05)
        user32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
        time.sleep(1.5)

    # Tangkap jendelanya.
    j3 = jendela_app()
    if not j3:
        print('  ! jendela hilang')
        return 1
    hwnd, judul, x, y, w, h = sorted(j3, key=lambda t: -t[4] * t[5])[0]

    out = Path('build') / ('ui-%s.png' % args.halaman)
    out.parent.mkdir(parents=True, exist_ok=True)

    # CopyFromScreen dengan jendela diangkat sementara.
    #
    # PrintWindow sempat dicoba karena tahan tertutup, tetapi WebView2
    # mengembalikan gambar hitam di mesin ini - hasilnya 0% piksel terang, jadi
    # tidak bisa dipakai. CopyFromScreen menyalin apa yang terlihat, sehingga
    # jendela yang menutupi ikut tertangkap; itu diatasi dengan mengangkat
    # LumaWall ke paling depan hanya selama tangkapan, lalu mengembalikannya.
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.9)

    # Jendela bisa bergeser sedikit saat diangkat; ambil posisinya lagi supaya
    # potongannya tepat.
    j4 = jendela_app()
    if j4:
        hwnd2, _, x, y, w, h = sorted(j4, key=lambda t2: -t2[4] * t2[5])[0]
        if hwnd2 == hwnd:
            pass

    out = Path('build') / ('ui-%s.png' % args.halaman)
    out.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        "Add-Type -AssemblyName System.Drawing;"
        "$b = New-Object System.Drawing.Bitmap(%d,%d);"
        "$g = [System.Drawing.Graphics]::FromImage($b);"
        "$g.CopyFromScreen(%d,%d,0,0,(New-Object System.Drawing.Size(%d,%d)));"
        "$b.Save('%s');"
        "$g.Dispose(); $b.Dispose();" % (w, h, x, y, w, h,
                                          str(out.resolve()).replace('\\', '\\\\'))
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, text=True, timeout=60)

    # Dikembalikan, supaya tidak menutupi layar kerja pengguna.
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE)

    # Diperiksa: tangkapan yang seluruhnya hitam berarti jendelanya tidak
    # tertangkap, dan itu harus dilaporkan, bukan disimpan seolah berhasil.
    try:
        from PIL import Image
        im = Image.open(out).convert('L')
        kecil = list(im.resize((80, 50)).get_flattened_data())
        terang = sum(1 for v in kecil if v > 60)
        if terang < len(kecil) * 0.02:
            print('  ! tangkapan hampir seluruhnya hitam (%d/%d piksel terang)'
                  % (terang, len(kecil)))
            print('    jendela mungkin tidak tertangkap - periksa hasilnya')
    except Exception as e:
        print('  (pemeriksaan tangkapan dilewati: %s)' % str(e)[:40])

    if out.exists():
        print('  disimpan: %s  (%dx%d)' % (out, w, h))
        return 0
    print('  ! tangkapan gagal')
    return 1


if __name__ == '__main__':
    sys.exit(main())
