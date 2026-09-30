#!/usr/bin/env python3
"""Ukur berapa lama wallpaper kembali setelah aplikasi fullscreen ditutup.

Dilaporkan: keluar dari aplikasi fullscreen meninggalkan layar hitam, dan
wallpaper tidak melanjutkan dirinya. Yang diukur di sini adalah berapa lama
layar tetap hitam setelah jendela fullscreen ditutup.

Jendela fullscreen-nya dibuat oleh skrip ini sendiri: jendela tanpa bingkai yang
menutupi seluruh layar. Itu cukup untuk membuat Windows masuk ke mode fullscreen
dan berhenti mengomposisi desktop, yang merupakan keadaan yang memicu bug ini.
Memakai game sungguhan tidak praktis untuk pemeriksaan otomatis, dan tidak perlu:
yang penting bagi DWM adalah ada jendela yang menutupi layar sepenuhnya.

Yang dicatat adalah kecerahan layar setiap 100 ms sejak jendela ditutup, supaya
lamanya hitam bisa disebut dalam angka, bukan kesan.

Pemakaian:
  python tools/check-fullscreen.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ukur_layar  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


CONFIG = Path('C:/Users/ariel/AppData/Local/LumaWall/config.json')

# Aplikasi fullscreen yang sungguhan.
#
# Versi pertama skrip ini memakai jendela borderless PowerShell, dan uji itu
# LULUS tanpa membuktikan apa pun: jendela borderless biasa tidak membuat DWM
# berhenti mengomposisi desktop, jadi keadaan yang dikeluhkan tidak pernah
# terjadi. Chrome dengan --start-fullscreen memasuki mode fullscreen yang
# sesungguhnya, yang memang menghentikan komposisi desktop - dan itulah yang
# harus diuji.
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
# --kiosk, not --start-fullscreen: the latter opens a normal window that merely
# fills the screen, and Windows does not treat it as a fullscreen app - so DWM
# keeps compositing the desktop and the state being tested never happens.
# --kiosk enters the real fullscreen mode. --window-position puts it on the
# display under test, because a new window otherwise opens on the primary one.
FULLSCREEN_ARGS = [
    '--kiosk',
    '--window-position={X},{Y}',
    '--window-size={W},{H}',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-features=Translate,MediaRouter',
    '--user-data-dir=%s',
    'about:blank',
]


def tulis_wallpaper(device, berkas):
    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    for item in (cfg.get('MonitorVideos') or []):
        if isinstance(item, dict) and item.get('Key') == device:
            item['Value'] = str(berkas)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')


def jendela_chrome():
    """Jendela Chrome yang sedang terbuka, sebagai (hwnd, judul).

    Dipakai untuk menutup Chrome milik uji ini saja, dan untuk memastikan ia
    benar-benar sudah tertutup sebelum hasilnya dibaca.
    """
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.startswith('Chrome_WidgetWin_1'):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        if (r.right - r.left) < 400 or (r.bottom - r.top) < 300:
            return True
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        hasil.append((int(hwnd), ti.value.strip() or '(tanpa judul)'))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def jendela_asing(monitor, min_lebar=400, min_tinggi=300):
    """Jendela milik proses LAIN yang menutupi layar yang diukur.

    Milik proses lain, bukan milik LumaWall: jendela wallpaper LumaWall memang
    harus ada di sana. Yang dicari adalah hal yang akan terbaca sebagai
    wallpaper padahal bukan.
    """
    pid_kita = ukur_layar.pid_aplikasi()
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid_kita:
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        lebar, tinggi = r.right - r.left, r.bottom - r.top
        if lebar < min_lebar or tinggi < min_tinggi:
            return True
        # Hanya yang benar-benar menutupi layar ini.
        if not (r.left < monitor['x'] + monitor['width'] and r.right > monitor['x']
                and r.top < monitor['y'] + monitor['height'] and r.bottom > monitor['y']):
            return True
        # Jendela desktop sendiri bukan penutup.
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'SysListView32'):
            return True
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        nama = ti.value.strip() or cls.value
        hasil.append((nama, int(hwnd), lebar, tinggi))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


class Pengukur(threading.Thread):
    """Kecerahan layar sesering mungkin, dengan cap waktu."""

    def __init__(self, monitor):
        super().__init__(daemon=True)
        self.monitor = monitor
        self.jalan = True
        self.contoh = []

    def run(self):
        while self.jalan:
            n = ukur_layar.baca(self.monitor)
            if n is not None:
                self.contoh.append((time.time(), n))
            time.sleep(0.05)

    def hentikan(self):
        self.jalan = False
        self.join(timeout=3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    monitor = ukur_layar.pilih(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ keluar dari fullscreen: berapa lama hitam? ══')
    print()
    print('  layar: %s %dx%d di (%d,%d)'
          % (monitor['device'], monitor['width'], monitor['height'],
             monitor['x'], monitor['y']))
    print()

    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    video = None
    for p in (cfg.get('Library') or []):
        s = str(p)
        if s.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')) and Path(s).exists():
            video = Path(s)
            break
    if video is None:
        print('  ! tidak ada video di library')
        return 1

    tulis_wallpaper(monitor['device'], video)
    ukur_layar.jalankan_app()

    if not ukur_layar.bersihkan_layar(monitor):
        print('  ! layar uji tidak bisa dibersihkan')
        return 1

    if ukur_layar.tunggu_tergambar(monitor) is None:
        print('  ! wallpaper tidak pernah tergambar')
        return 1
    time.sleep(3)

    # Jendela lain yang menutupi layar uji membuat seluruh pengukuran tidak sah.
    #
    # Ini bukan kemungkinan teoretis: Voicemeeter dan Settings terbuka di layar
    # uji selama pengembangan, dan hasilnya terbaca sebagai "wallpaper tetap
    # hitam" padahal wallpapernya berjalan normal di belakangnya. Pemeriksaan
    # yang menyalahkan hal yang salah lebih buruk daripada tidak ada
    # pemeriksaan, jadi ini diperiksa dan dilaporkan di muka.
    # Jendela lain yang menutupi layar uji diminimalkan - tidak ditutup, dan
    # tidak dipindah. Minimalkan adalah satu-satunya dari ketiganya yang bisa
    # dikembalikan persis seperti semula: jendela kembali ke posisi dan
    # ukurannya sendiri saat dipulihkan, dan selama uji ia benar-benar tidak
    # menghalangi.
    penutup = jendela_asing(monitor)
    dipulihkan = []
    if penutup:
        print('  menyingkirkan %d jendela dari layar uji (diminimalkan, bukan ditutup):' % len(penutup))
        for nama, hwnd, lebar, tinggi in penutup:
            print('       %-32s %dx%d' % (nama[:32], lebar, tinggi))
            user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
            dipulihkan.append(hwnd)
        time.sleep(1.5)
        print()

    awal = ukur_layar.baca(monitor)
    print('  wallpaper tergambar: %.1f' % awal)
    print()

    profil = Path('build/chrome-fullscreen').resolve()
    if profil.exists():
        shutil.rmtree(profil, ignore_errors=True)

    # Catat Chrome yang sudah terbuka sebelum uji ini berjalan.
    #
    # Tanpa ini, penutupan di akhir akan menutup SEMUA Chrome di mesin -
    # termasuk jendela kerja pengguna. Uji yang menghancurkan pekerjaan yang
    # tidak ada hubungannya bukan uji yang boleh dijalankan siapa pun.
    chrome_sebelum = set(h for h, _ in jendela_chrome())
    print('  Chrome yang sudah terbuka: %d jendela (tidak akan diganggu)' % len(chrome_sebelum))
    print()

    print('  ── membuka Chrome fullscreen ──')
    args = []
    for a in FULLSCREEN_ARGS:
        if '%s' in a:
            args.append(a % str(profil))
        else:
            args.append(a.replace('{X}', str(monitor['x']))
                         .replace('{Y}', str(monitor['y']))
                         .replace('{W}', str(monitor['width']))
                         .replace('{H}', str(monitor['height'])))
    proc = subprocess.Popen([CHROME] + args,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Beri waktu Chrome benar-benar masuk mode fullscreen. Kalau jendelanya
    # belum fullscreen saat diukur, yang diuji bukan apa-apa.
    time.sleep(7)

    saat_fullscreen = ukur_layar.baca(monitor)
    print('     kecerahan saat fullscreen: %.1f' % saat_fullscreen)
    if saat_fullscreen > 60:
        print('     ! Chrome mungkin belum fullscreen - hasilnya tidak sah')
    print()

    # Mulai mengukur TEPAT sebelum jendelanya ditutup.
    ukur = Pengukur(monitor)
    ukur.start()
    tanda = time.time()

    print('  ── keluar dari fullscreen ──')
    # Minimised, never closed.
    #
    # Two reasons, and the second is the important one:
    #
    #   1. Minimising IS the event being tested. A fullscreen window that is
    #      minimised takes Windows out of fullscreen-app mode exactly as closing
    #      it does, so the desktop composition comes back - which is what this
    #      whole check is about.
    #   2. Nothing on this machine is closed by a test. Earlier versions of this
    #      script closed windows to clear the screen, and that is not acceptable:
    #      a check that destroys the user's open work is not one that can be run.
    SW_MINIMIZE = 6

    def chrome_baru():
        """Jendela Chrome yang muncul setelah uji ini mulai - milik uji ini saja."""
        return [(h, j) for h, j in jendela_chrome() if h not in chrome_sebelum]

    dilempar = []
    for hwnd, judul in chrome_baru():
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        dilempar.append(judul)
    print('     %d jendela Chrome uji diminimalkan' % len(dilempar))

    # Tunggu sampai tidak ada lagi yang fullscreen. Yang diperiksa bukan
    # "jendelanya hilang" - jendelanya masih ada, hanya tidak lagi menutupi
    # layar - melainkan bahwa layarnya sudah bebas.
    batas = time.time() + 25
    while time.time() < batas:
        if not jendela_asing(monitor):
            break
        time.sleep(0.3)
    sisa = jendela_asing(monitor)
    if sisa:
        print('     ! masih ada %d jendela menutupi layar uji' % len(sisa))
        for nama, _h, l, t in sisa:
            print('       %s (%dx%d)' % (nama[:40], l, t))
        print('       hasil pengukuran tidak sah')
        ukur.hentikan()
        # Jendela yang tadi disingkirkan tetap dipulihkan sebelum berhenti.
        if dipulihkan:
            for hwnd in dipulihkan:
                if user32.IsWindow(hwnd):
                    user32.ShowWindow(hwnd, 9)   # SW_RESTORE
            print('     %d jendela dipulihkan' % len(dipulihkan))
        return 1
    print('     layar uji bebas')

    time.sleep(12)
    ukur.hentikan()

    print('     selesai')
    print()

    # Analisis: berapa lama layar tetap hitam setelah jendela ditutup?
    if not ukur.contoh:
        print('  ! tidak ada sampel')
        return 1

    setelah = [(t - tanda, n) for t, n in ukur.contoh if t >= tanda]
    if not setelah:
        print('  ! tidak ada sampel setelah penutupan')
        return 1

    # Hitam dianggap < 8 dari 255; itu batas yang sama yang dipakai pemeriksaan
    # lain, dan jauh di bawah video tergelap mana pun.
    hitam = [d for d, n in setelah if n < 8]
    pulih = next((d for d, n in setelah if n >= 30), None)
    akhir = statistics.mean(n for _, n in setelah[-10:])

    # Pulihkan jendela yang diminimalkan, apa pun hasil ujinya. Tanpa ini,
    # menjalankan pemeriksaan meninggalkan jendela pengguna terlipat di taskbar -
    # perubahan yang tidak diminta dan tidak terlihat sebabnya.
    if dipulihkan:
        SW_RESTORE = 9
        for hwnd in dipulihkan:
            if user32.IsWindow(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
        print('  ── memulihkan %d jendela ──' % len(dipulihkan))
        time.sleep(1.5)
        print()

    print('  ── hasil ──')
    print('     %d sampel selama %.1f detik' % (len(setelah), setelah[-1][0]))
    print('     kecerahan akhir: %.1f' % akhir)
    if hitam:
        print('     HITAM selama %.1f detik (%.1f s sampai %.1f s)'
              % (hitam[-1] - hitam[0] + 0.05, hitam[0], hitam[-1]))
    else:
        print('     tidak ada sampel hitam')
    if pulih is not None:
        print('     kembali terang setelah %.1f detik' % pulih)
    print()

    # Gambar jejaknya, supaya bisa dilihat apakah hitamnya satu blok atau
    # berkedip-kedip.
    print('     jejak (detik: kecerahan, satu baris per detik):')
    per_detik = {}
    for d, n in setelah:
        per_detik.setdefault(int(d), []).append(n)
    for detik in sorted(per_detik)[:14]:
        nilai = per_detik[detik]
        bar = '#' * int(statistics.mean(nilai) / 8)
        print('       %2ds  %6.1f  %s' % (detik, statistics.mean(nilai), bar))
    print()

    if hitam and (hitam[-1] - hitam[0]) > 1.5:
        print('  ✗ wallpaper tetap hitam %.1f detik setelah keluar fullscreen'
              % (hitam[-1] - hitam[0]))
        return 1
    if akhir < 30:
        print('  ✗ wallpaper tidak kembali menggambar (kecerahan akhir %.1f)' % akhir)
        return 1

    print('  ✓ wallpaper kembali dengan cepat setelah keluar fullscreen')
    return 0


if __name__ == '__main__':
    sys.exit(main())
