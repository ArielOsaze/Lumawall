#!/usr/bin/env python3
"""Chrome untuk keperluan uji: diluncurkan, dilacak, dan dibersihkan dengan aman.

Aturan yang mengikat modul ini, dan alasannya:

  * TIDAK ADA jendela yang ditutup kecuali yang dibuat oleh uji itu sendiri.
    Sebuah pemeriksaan yang menutup pekerjaan orang lain bukan pemeriksaan yang
    boleh dijalankan, jadi identitas jendela uji harus dibuktikan, bukan
    ditebak.

  * Jendela uji dibuktikan lewat PROFIL yang dipakai prosesnya. Profil uji hanya
    dipakai uji, jadi proses Chrome yang memakai profil itu pasti milik uji.
    Membandingkan "jendela yang baru muncul" tidak cukup: Chrome sisa dari run
    sebelumnya sudah ada sebelum uji mulai, jadi ia dianggap milik pengguna,
    tidak pernah dibersihkan, dan menetap di layar uji sampai run berikutnya
    gagal karena layarnya "terhalang".

  * Jendela pengguna yang menghalangi layar uji DIMINIMALKAN, bukan ditutup dan
    bukan dipindahkan. Ditutup berarti menghancurkan pekerjaan orang; dipindahkan
    tidak bertahan untuk jendela yang maximized (window manager mengembalikannya
    ke layar). Minimize selalu bekerja dan cukup dengan satu klik untuk kembali.

  * Kalau sebuah jendela menolak diminimalkan (berjalan dengan hak lebih tinggi,
    seperti Task Manager), uji berhenti dan mengatakannya. Mengukur layar yang
    masih terhalang menghasilkan vonis palsu tentang aplikasinya.
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import time
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)

SW_MINIMIZE = 6
SW_RESTORE = 9
WM_CLOSE = 0x0010

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def profil_uji(nama):
    """Folder profil Chrome untuk uji bernama `nama`."""
    # Relatif terhadap berkas ini, bukan direktori kerja: profil uji harus
    # selalu di tempat yang sama, supaya pembersihan sisa (yang mencari
    # 'build/chrome-*' di baris perintah) menemukannya.
    return Path(__file__).resolve().parent.parent / 'build' / ('chrome-' + nama)


def bersihkan_sisa(nama):
    """Hentikan Chrome uji yang tertinggal dari run sebelumnya.

    Dikenali dari baris perintahnya yang menyebut folder profil uji ini. Itu
    bukti yang pasti, bukan tebakan dari judul jendela - dan judul jendela bisa
    mengenai Chrome milik pengguna.
    """
    penanda = profil_uji(nama).name
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
         "Where-Object { $_.CommandLine -like '*%s*' } | "
         "ForEach-Object { $_.ProcessId }" % penanda],
        capture_output=True, text=True, timeout=60)
    pids = [b.strip() for b in r.stdout.split() if b.strip().isdigit()]
    for pid in pids:
        subprocess.run(['taskkill', '/PID', pid, '/T', '/F'], capture_output=True)
    if pids:
        time.sleep(1.5)
    return len(pids)


def kumpulan_pid(akar):
    """PID `akar` beserta seluruh keturunannya."""
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         'Get-CimInstance Win32_Process | '
         'Select-Object ProcessId,ParentProcessId | '
         'ForEach-Object { "$($_.ProcessId) $($_.ParentProcessId)" }'],
        capture_output=True, text=True, timeout=60)
    anak = {}
    for baris in r.stdout.splitlines():
        bagian = baris.split()
        if len(bagian) == 2 and bagian[0].isdigit() and bagian[1].isdigit():
            anak.setdefault(int(bagian[1]), []).append(int(bagian[0]))
    hasil, tumpukan = set(), [akar]
    while tumpukan:
        p = tumpukan.pop()
        if p in hasil:
            continue
        hasil.add(p)
        tumpukan.extend(anak.get(p, []))
    return hasil


def jendela_chrome(pid):
    """Jendela Chrome yang terlihat, hanya milik proses `pid` dan keturunannya."""
    hasil = []
    keluarga = kumpulan_pid(pid)

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
        hpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
        if hpid.value not in keluarga:
            return True
        hasil.append(int(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def buka(nama, x, y, lebar, tinggi, kiosk=True):
    """Luncurkan Chrome uji dan kembalikan prosesnya.

    Profil lama dihapus lebih dulu: Chrome menolak start dengan profil yang
    masih terkunci oleh sesi sebelumnya, dan kegagalan itu tampak seperti
    "jendela tidak pernah muncul" - gejala yang menyesatkan.
    """
    import shutil
    bersihkan_sisa(nama)
    profil = profil_uji(nama)
    if profil.exists():
        shutil.rmtree(profil, ignore_errors=True)
    arg = [
        CHROME,
        '--window-position=%d,%d' % (x, y),
        '--window-size=%d,%d' % (lebar, tinggi),
        '--no-first-run', '--no-default-browser-check',
        '--disable-session-crashed-bubble',
        '--user-data-dir=%s' % str(profil),
    ]
    if kiosk:
        arg.insert(1, '--kiosk')
    arg.append('about:blank')
    return subprocess.Popen(arg, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def tunggu_jendela(proc, detik=15):
    """Tunggu jendela Chrome uji benar-benar berdiri."""
    batas = time.time() + detik
    while time.time() < batas:
        j = jendela_chrome(proc.pid)
        if j:
            return j
        time.sleep(0.25)
    return []


def tutup(proc):
    """Tutup HANYA jendela milik proses ini, dan hanya setelah diminimalkan.

    Minimize dulu supaya Windows keluar dari mode fullscreen sebelum jendelanya
    hilang - persis seperti pengguna meninggalkan aplikasi fullscreen.
    """
    if proc is None:
        return
    for hwnd in jendela_chrome(proc.pid):
        user32.ShowWindow(hwnd, SW_MINIMIZE)
    time.sleep(1.0)
    for hwnd in jendela_chrome(proc.pid):
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    # Kalau masih ada, hentikan prosesnya - ini proses yang kita buat sendiri,
    # jadi tidak ada pekerjaan pengguna yang hilang.
    time.sleep(1.5)
    for hwnd in jendela_chrome(proc.pid):
        hpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
        subprocess.run(['taskkill', '/PID', str(hpid.value), '/T', '/F'],
                       capture_output=True)


def jendela_asing(monitor, pid_aplikasi=None):
    """Jendela proses lain yang terlihat di layar ini, sebagai (judul, hwnd, w, h)."""
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        # Jendela yang diminimalkan tidak menutupi apa pun.
        if user32.IsIconic(hwnd):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w < 400 or h < 300:
            return True
        if not (r.left < monitor['x'] + monitor['width'] and r.right > monitor['x']
                and r.top < monitor['y'] + monitor['height'] and r.bottom > monitor['y']):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'SysListView32'):
            return True
        if pid_aplikasi is not None:
            hpid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
            if hpid.value in pid_aplikasi:
                return True
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        hasil.append(((ti.value.strip() or cls.value), int(hwnd), w, h))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def singkirkan(monitor, pid_aplikasi=None):
    """Minimalkan jendela lain di layar uji.

    Kembalikan (disingkirkan, ditolak). `ditolak` berisi judul jendela yang
    menolak diminimalkan; kalau tidak kosong, layar uji belum bebas dan uji
    sebaiknya tidak dijalankan.
    """
    disingkirkan, ditolak = [], []
    for judul, hwnd, w, h in jendela_asing(monitor, pid_aplikasi):
        ctypes.set_last_error(0)
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        time.sleep(0.3)
        # ShowWindow sering mengembalikan 0 walau berhasil, jadi hasilnya dibaca
        # dari keadaan jendelanya.
        if user32.IsIconic(hwnd):
            disingkirkan.append(hwnd)
        else:
            ditolak.append(judul)
    return disingkirkan, ditolak


def pulihkan(daftar):
    """Kembalikan jendela pengguna yang tadi diminimalkan."""
    for hwnd in daftar:
        if user32.IsWindow(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

def jendela_uji(penanda):
    """Jendela Chrome yang prosesnya memakai profil uji `penanda`.

    Dilacak lewat PROFIL, bukan lewat PID proses yang kita luncurkan, dan
    alasannya penting: Chrome dengan profil baru sering me-restart dirinya
    sendiri. Proses yang kita luncurkan mati, jendelanya milik proses baru, dan
    pelacakan lewat PID tidak menemukan apa pun.

    Akibatnya pernah sangat menyesatkan: minimize tidak pernah dikirim, jadi
    jendela uji tetap menutupi layar, aplikasi tetap menjeda wallpaper (itu
    perilaku yang BENAR), dan pemeriksaan melaporkan "tidak dilanjutkan" -
    menyalahkan aplikasi atas jendela yang tidak pernah dipindahkan.
    """
    # Satu panggilan PowerShell untuk semua Chrome: PID + baris perintahnya.
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
         "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"],
        capture_output=True, text=True, timeout=90)
    keluarga = set()
    for baris in r.stdout.splitlines():
        if '\t' not in baris:
            continue
        pid_teks, cmd = baris.split('\t', 1)
        if penanda in cmd and pid_teks.strip().isdigit():
            keluarga.add(int(pid_teks.strip()))

    if not keluarga:
        return []

    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.startswith('Chrome_WidgetWin_1'):
            return True
        r2 = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r2)):
            return True
        if (r2.right - r2.left) < 400 or (r2.bottom - r2.top) < 300:
            return True
        hpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
        if hpid.value not in keluarga:
            return True
        hasil.append(int(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return hasil
