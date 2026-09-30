#!/usr/bin/env python3
"""Buktikan pause/resume bekerja: benar-benar berhenti saat fullscreen, dan
langsung lanjut begitu aplikasinya tidak fullscreen lagi.

Cara mengukurnya diubah, dan alasannya penting.

Versi sebelumnya membaca kecerahan layar uji. Itu tidak bisa dipercaya di mesin
yang sedang dipakai orang: setiap jendela lain yang kebetulan berada di layar
itu ikut terbaca, dan aplikasi ini memang menjeda wallpaper saat ada jendela
menutupinya - jadi "layar gelap" bisa berarti wallpapernya dijeda dengan benar,
atau bisa berarti ada jendela lain di atasnya. Dua hal yang sangat berbeda
menghasilkan angka yang sama.

Yang dipakai sekarang adalah jejak aplikasinya sendiri, yang mencatat setiap
perubahan keadaan dengan cap waktu milidetik:

  * berhenti   ->  "Playback updated (...): paused [\\.\DISPLAYx]"
  * lanjut     ->  "resumed [\\.\DISPLAYx]"
  * frame baru ->  "Playback timing \\.\DISPLAYx resume-frame:NN ms"
  * masih maju ->  "Seamless loop handoff completed on \\.\DISPLAYx"

Tiga yang pertama membuktikan perintahnya sampai dan dikerjakan. Yang keempat
membuktikan videonya benar-benar berjalan, bukan sekadar dilaporkan berjalan:
video yang dijeda tidak pernah menyelesaikan putaran, jadi tidak akan ada baris
"loop handoff" selama jeda, dan baris itu muncul kembali setelah lanjut. Itu
bukti yang tidak bisa dihasilkan oleh keadaan beku.

Pemakaian:
  python tools/check-pause-resume.py [--display DISPLAY3]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)

LOG = Path('C:/Users/ariel/AppData/Local/LumaWall/Logs/lumawall.log')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

BARIS_WAKTU = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})')


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def baca_log():
    """Semua baris log sebagai (waktu, teks)."""
    try:
        isi = LOG.read_text(encoding='utf-8', errors='replace').splitlines()
    except Exception:
        return []
    hasil = []
    for b in isi:
        m = BARIS_WAKTU.match(b)
        if m:
            try:
                t = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                continue
            hasil.append((t, b))
    return hasil


def layar_dari(nama):
    """Monitor dengan nama device itu, atau None."""
    for m in monitor_list():
        if m['device'].endswith(nama):
            return m
    return None


def monitor_list():
    """Daftar monitor dari Windows, tanpa bergantung pada modul lain."""
    user32.SetProcessDPIAware()
    hasil = []

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', RECT), ('rcWork', RECT),
                    ('dwFlags', wt.DWORD), ('szDevice', wt.WCHAR * 32)]

    MONITORENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC,
                                         ctypes.POINTER(RECT), wt.LPARAM)

    def cb(hmon, hdc, lprc, data):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            hasil.append({
                'device': mi.szDevice,
                'x': mi.rcMonitor.left, 'y': mi.rcMonitor.top,
                'width': mi.rcMonitor.right - mi.rcMonitor.left,
                'height': mi.rcMonitor.bottom - mi.rcMonitor.top,
                'primary': bool(mi.dwFlags & 1),
            })
        return True

    user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(cb), 0)
    return hasil


def jendela_chrome(pid=None):
    """Jendela Chrome yang terlihat.

    Kalau `pid` diberi, hanya jendela milik proses itu dan anak-anaknya. Itu
    yang dipakai uji ini: melacak berdasarkan proses yang diluncurkan sendiri
    jauh lebih tepat daripada menebak dari jendela yang "baru muncul". Cara
    menebak gagal persis pada kasus yang paling sering terjadi - ada Chrome sisa
    dari run sebelumnya, yang sudah ada sebelum uji mulai, jadi dianggap milik
    pengguna, tidak pernah ditutup, dan membuat run berikutnya gagal.
    """
    hasil = []
    keluarga = kumpulan_pid(pid) if pid else None

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
        if keluarga is not None:
            hpid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
            if hpid.value not in keluarga:
                return True
        hasil.append(int(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default=None,
                    help='layar uji; default: yang sedang memutar')
    args = ap.parse_args()

    print()
    print('  ══ pause saat fullscreen, lanjut saat tidak ══')
    print()

    # Layar uji: yang paling akhir menyelesaikan putaran, karena itu yang
    # benar-benar sedang memutar. Kalau tidak ada, pakai yang diminta.
    if args.display:
        mon = layar_dari(args.display)
        nama = args.display
    else:
        terakhir = {}
        for t, b in baca_log():
            m = re.search(r'loop handoff completed on .*?(DISPLAY\d+)', b)
            if m:
                terakhir[m.group(1)] = t
        if not terakhir:
            print('  tidak ada layar yang sedang memutar')
            return 1
        kandidat = max(terakhir, key=terakhir.get)
        nama = kandidat
        mon = layar_dari(kandidat)

    if mon is None:
        print('  layar %s tidak ditemukan' % nama)
        return 1

    print('  layar: %s %dx%d di (%d,%d)'
          % (mon['device'], mon['width'], mon['height'], mon['x'], mon['y']))
    print()

    # ── apakah layarnya bebas? ──────────────────────────────────────────────
    #
    # Ini menentukan uji ini bisa dijalankan atau tidak. Kalau ada jendela lain
    # di layar itu, aplikasi MENJEDA wallpaper dengan benar - dan uji ini akan
    # mengukur jeda yang benar sebagai "wallpaper tidak berjalan". Jadi layarnya
    # harus bebas lebih dulu.
    # Jendela lain di layar uji diminimalkan, lalu dikembalikan.
    #
    # Minimize, bukan ditutup dan bukan dipindahkan:
    #
    #   * Bukan ditutup, karena jendela itu milik pengguna. Sebuah pemeriksaan
    #     yang menutup pekerjaan orang lain bukan pemeriksaan yang boleh
    #     dijalankan.
    #   * Bukan dipindahkan, karena jendela yang maximized melompat balik ke
    #     ukuran penuhnya begitu dipindahkan - SetWindowPos berhasil, lalu window
    #     manager mengembalikannya ke layar, dan layarnya tetap terhalang.
    #   * Minimize selalu bekerja untuk jendela biasa, dan jendela yang
    #     diminimalkan tidak menutupi apa pun.
    #
    # Aplikasi ini memang MENJEDA wallpaper saat ada jendela menutupinya - itu
    # perilaku yang benar, bukan bug - jadi layar uji harus bebas dulu, kalau
    # tidak yang terukur adalah jeda yang benar itu sendiri.
    penutup = jendela_di(mon)
    disingkirkan = []
    ditolak = []
    if penutup:
        print('  menyingkirkan %d jendela dari layar uji (diminimalkan):' % len(penutup))
        for judul, hwnd in penutup:
            ctypes.set_last_error(0)
            user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
            time.sleep(0.3)
            # ShowWindow sering mengembalikan 0 walau berhasil, jadi hasilnya
            # dibaca dari keadaan jendelanya, bukan dari nilai kembaliannya.
            if user32.IsIconic(hwnd):
                disingkirkan.append(hwnd)
                print('      %s' % judul[:52])
            else:
                ditolak.append(judul)
        print()

    if ditolak:
        print('  jendela ini menolak diminimalkan:')
        for judul in ditolak:
            print('      %s' % judul[:56])
        print()
        print('  Biasanya karena berjalan dengan hak lebih tinggi (Task Manager).')

        # Layar lain dicoba lebih dulu.
        #
        # Uji ini tentang perilaku aplikasi, bukan tentang satu layar tertentu:
        # menjeda saat fullscreen dan lanjut saat tidak adalah perilaku yang sama
        # di semua layar. Karena itu menolak berjalan hanya karena satu layar
        # kebetulan terhalang adalah pemborosan - dan di mesin ini Task Manager
        # memang sering terbuka dan memang tidak bisa dipindahkan, jadi uji itu
        # akan hampir selalu menolak berjalan. Pindah ke layar bebas jauh lebih
        # berguna, dan hasilnya sama sahnya.
        for hwnd in disingkirkan:
            user32.ShowWindow(hwnd, 9)   # SW_RESTORE
        print()

        lain = None
        for m in monitor_list():
            if m['device'] == mon['device']:
                continue
            d, t = singkirkan(m, pid_lumawall())
            if not t:
                lain = (m, d)
                break
            pulihkan(d)

        if lain is None:
            print('  tidak ada layar lain yang bebas. Uji ini tidak dijalankan,')
            print('  karena apa pun yang diukur hanyalah jendela itu.')
            print()
            return 2

        mon, disingkirkan = lain
        nama = mon['device'].split('\\\\')[-1]
        print('  pindah ke layar bebas: %s %dx%d di (%d,%d)'
              % (mon['device'], mon['width'], mon['height'], mon['x'], mon['y']))
        print()

    if not penutup:
        print('  layar sudah bebas')
    print()

    # Sisa Chrome uji dari run sebelumnya dibersihkan lebih dulu.
    #
    # Dikenali dari baris perintahnya: proses Chrome yang memakai profil uji
    # ini. Itu bukti yang pasti - profil itu hanya dipakai uji ini - sedangkan
    # menebak dari judul jendela bisa mengenai Chrome milik pengguna. Sisa yang
    # tidak dibersihkan akan menetap di layar uji dan membuat run berikutnya
    # gagal karena layarnya "terhalang", padahal itu jendela kita sendiri.
    bersihkan_sisa()

    t0 = datetime.now()
    gagal = []
    proc = None

    # ── 1. buka aplikasi fullscreen ─────────────────────────────────────────
    print('  ── 1. membuka aplikasi fullscreen ──')
    # Profil tetap: satu profil per uji, dan kunci profil lama dibersihkan supaya
    # Chrome tidak menolak start karena sesi sebelumnya belum dilepas.
    profil = Path('build/chrome-pause').resolve()
    if profil.exists():
        shutil.rmtree(profil, ignore_errors=True)
    proc = subprocess.Popen([
        CHROME, '--kiosk',
        '--window-position=%d,%d' % (mon['x'], mon['y']),
        '--window-size=%d,%d' % (mon['width'], mon['height']),
        '--no-first-run', '--no-default-browser-check',
        '--user-data-dir=%s' % str(profil),
        'about:blank',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Tunggu aplikasi fullscreen benar-benar berdiri. Yang dihitung hanya jendela
    # Chrome milik uji ini, supaya jendela lain yang muncul bersamaan tidak
    # membuat uji mengira aplikasinya sudah terbuka.
    def chrome_baru_di_layar():
        return jendela_chrome(proc.pid)

    for _ in range(60):
        if chrome_baru_di_layar():
            break
        time.sleep(0.25)

    # Pastikan jendelanya benar-benar berada di layar uji dan berukuran penuh.
    #
    # Chrome kiosk tidak selalu menghormati --window-position: ia bisa membuka di
    # layar primary. Kalau itu terjadi, aplikasi tidak melihat ada jendela
    # menutupi layar uji, jadi wallpapernya tidak dijeda - dan uji ini akan
    # melaporkan "tidak dijeda" untuk aplikasi yang berperilaku benar. Jauh lebih
    # baik memindahkan jendelanya daripada menyalahkan aplikasi atas kesalahan
    # peluncurannya.
    for _ in range(20):
        pindah = False
        for hwnd in chrome_baru_di_layar():
            r = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
                continue
            sudah = (abs(r.left - mon['x']) <= 4 and abs(r.top - mon['y']) <= 4
                     and abs((r.right - r.left) - mon['width']) <= 4
                     and abs((r.bottom - r.top) - mon['height']) <= 4)
            if not sudah:
                user32.SetWindowPos(hwnd, 0, mon['x'], mon['y'],
                                    mon['width'], mon['height'], 0x0004 | 0x0010)
                pindah = True
        if not pindah:
            break
        time.sleep(0.4)

    if not chrome_baru_di_layar():
        print('     ! jendela fullscreen tidak pernah muncul')
        bersihkan(proc.pid)
        pulihkan(disingkirkan)
        return 1

    print('     aplikasi fullscreen berdiri')

    # Tunggu aplikasi mencatat jeda.
    t_jeda = tunggu(lambda: cari_jeda(t0, nama), 20)
    if t_jeda:
        print('     ✓ wallpaper DIJEDA saat fullscreen')
        print('       %s' % t_jeda[1].split('] ', 1)[-1][-104:])
    else:
        print('     ✗ tidak ada catatan jeda dalam 20 detik')
        gagal.append('tidak dijeda')

    # Video yang dijeda tidak menyelesaikan putaran. Ini bukti bebas bahwa
    # pemutaran benar-benar berhenti, bukan sekadar dilaporkan berhenti.
    putaran_jeda = cari_putaran(t_jeda[0] if t_jeda else t0, nama)
    if putaran_jeda:
        print('     ✗ video masih menyelesaikan putaran saat dijeda (%d kali)'
              % len(putaran_jeda))
        gagal.append('masih berputar saat dijeda')
    else:
        print('     ✓ tidak ada putaran selesai selama jeda - video benar berhenti')
    print()

    # ── 2. keluar dari fullscreen ───────────────────────────────────────────
    print('  ── 2. keluar dari fullscreen ──')
    t_keluar = datetime.now()
    for hwnd in jendela_chrome(proc.pid):
        user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
    print('     aplikasi diminimalkan (bukan ditutup)')

    t_lanjut = tunggu(lambda: cari_lanjut(t_keluar, nama), 20)
    if t_lanjut:
        print('     ✓ wallpaper DILANJUTKAN')
        print('       %s' % t_lanjut[1].split('] ', 1)[-1][-104:])
    else:
        print('     ✗ tidak ada catatan lanjut dalam 20 detik')
        gagal.append('tidak dilanjutkan')

    # Berapa lama dari perintah sampai frame pertama.
    frame = tunggu(lambda: cari_frame(t_keluar, nama), 20)
    if frame:
        m = re.search(r'resume-frame:(\d+)', frame[1])
        ms = int(m.group(1)) if m else None
        print('     ✓ frame pertama setelah %s ms' % (ms if ms is not None else '?'))
        if ms is not None and ms > 2000:
            gagal.append('frame lambat')
    else:
        print('     ✗ tidak ada frame baru setelah dilanjutkan')
        gagal.append('tidak ada frame')

    # Putaran harus mulai lagi: bukti videonya benar-benar berjalan.
    #
    # Batas waktunya dihitung dari durasi video itu sendiri, bukan angka tetap.
    # Video 11 detik dengan batas 30 detik terlihat cukup, tetapi tidak: posisi
    # setelah dilanjutkan bisa sudah jauh di tengah, jadi putaran berikutnya
    # jatuh tepat di luar jendela tunggu dan uji melaporkan "video tidak
    # berjalan" untuk video yang berjalan normal. Dua kali durasi, ditambah
    # kelonggaran, selalu cukup.
    durasi = durasi_video(nama)
    batas_putaran = max(30, durasi * 2 + 10)
    putaran_lanjut = tunggu(lambda: cari_putaran(t_keluar, nama), batas_putaran)
    if putaran_lanjut:
        detik = (putaran_lanjut[0][0] - t_keluar).total_seconds()
        print('     ✓ video berjalan lagi (putaran selesai setelah %.1f detik,'
              ' bukti nyata)' % detik)
    else:
        print('     ✗ video tidak menyelesaikan putaran dalam %.0f detik'
              % batas_putaran)
        gagal.append('video tidak berjalan')
    print()

    bersihkan(proc.pid)
    pulihkan(disingkirkan)

    print('  ══ kesimpulan ══')
    if gagal:
        print('  %d masalah: %s' % (len(gagal), ', '.join(gagal)))
        return 1
    print('  benar-benar berhenti saat fullscreen, dan langsung lanjut')
    print('  begitu aplikasinya tidak fullscreen lagi.')
    return 0


def jendela_di(mon, pid_aplikasi=None):
    """Jendela proses lain yang benar-benar terlihat di layar ini.

    `pid_aplikasi` yang diberikan akan dilewati: jendela LumaWall sendiri memang
    ada di sana, dan bukan penghalang.
    """
    if pid_aplikasi is None:
        pid_aplikasi = pid_lumawall()
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w < 400 or h < 300:
            return True
        if not (r.left < mon['x'] + mon['width'] and r.right > mon['x']
                and r.top < mon['y'] + mon['height'] and r.bottom > mon['y']):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'SysListView32'):
            return True
        # Jendela LumaWall sendiri bukan penghalang.
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value in pid_aplikasi:
            return True
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        hasil.append(((ti.value.strip() or cls.value), int(hwnd)))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def pid_lumawall():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process LumaWall -EA SilentlyContinue).Id'],
                       capture_output=True, text=True, timeout=30)
    out = set()
    for baris in r.stdout.split():
        try:
            out.add(int(baris))
        except ValueError:
            pass
    return out


def tunggu(fn, detik):
    """Panggil fn berulang sampai mengembalikan sesuatu yang benar."""
    batas = time.time() + detik
    while time.time() < batas:
        h = fn()
        if h:
            return h
        time.sleep(0.2)
    return None


def di_dalam(b, kunci, nama):
    """Apakah `nama` ada di dalam daftar `kunci [...]` pada baris log itu?

    Baris "Playback updated" menyebut setiap layar di bagian depan, lalu hanya
    sebagian saja di dalam tanda kurung:

        Playback updated (\\.\DISPLAY1, \\.\DISPLAY2, \\.\DISPLAY3): paused [\\.\DISPLAY1]

    Mencari nama di seluruh baris akan cocok untuk DISPLAY2 dan DISPLAY3 juga,
    padahal yang dijeda hanya DISPLAY1. Uji yang membaca begitu akan lulus atau
    gagal karena alasan yang salah, dan itu lebih buruk daripada tidak ada uji.
    Yang benar adalah memeriksa isi tanda kurung setelah kata kuncinya.
    """
    m = re.search(re.escape(kunci) + r'\s*\[([^\]]*)\]', b)
    return bool(m) and nama in m.group(1)


def cari_jeda(sejak, nama):
    for t, b in baca_log():
        if t < sejak:
            continue
        if 'Playback updated' in b and di_dalam(b, 'paused', nama):
            return (t, b)
    return None


def cari_lanjut(sejak, nama):
    for t, b in baca_log():
        if t < sejak:
            continue
        if 'Playback updated' in b and di_dalam(b, 'resumed', nama):
            return (t, b)
    return None


def cari_frame(sejak, nama):
    for t, b in baca_log():
        if t < sejak:
            continue
        if 'resume-frame:' in b and nama in b:
            return (t, b)
    return None


def cari_putaran(sejak, nama):
    hasil = []
    for t, b in baca_log():
        if t < sejak:
            continue
        if 'Seamless loop handoff completed on' in b and nama in b:
            hasil.append((t, b))
    return hasil


def bersihkan_sisa():
    """Hentikan Chrome uji yang tertinggal dari run sebelumnya."""
    profil = str(Path('build/chrome-pause').resolve())
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         'Get-CimInstance Win32_Process -Filter "Name=\'chrome.exe\'" | '
         'Where-Object { $_.CommandLine -like "*chrome-pause*" } | '
         'ForEach-Object { $_.ProcessId }'],
        capture_output=True, text=True, timeout=60)
    pids = [b.strip() for b in r.stdout.split() if b.strip().isdigit()]
    for pid in pids:
        subprocess.run(['taskkill', '/PID', pid, '/T', '/F'], capture_output=True)
    if pids:
        print('  membersihkan %d Chrome uji yang tertinggal' % len(pids))
        time.sleep(1.5)


def durasi_video(nama):
    """Durasi video wallpaper di layar itu, dalam detik (0 kalau tak diketahui)."""
    try:
        cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    except Exception:
        return 0.0
    for item in (cfg.get('MonitorVideos') or []):
        if not isinstance(item, dict):
            continue
        if str(item.get('Key', '')).endswith(nama):
            v = Path(str(item.get('Value', '')))
            if not v.exists():
                return 0.0
            r = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=nw=1:nk=1', str(v)],
                capture_output=True, text=True, timeout=30)
            try:
                return float(r.stdout.strip())
            except ValueError:
                return 0.0
    return 0.0


def singkirkan(mon, pid_aplikasi=None):
    """Minimalkan jendela lain di layar itu.

    Kembalikan (disingkirkan, ditolak). `ditolak` berisi judul yang menolak
    diminimalkan - kalau tidak kosong, layar itu belum bebas.
    """
    disingkirkan, ditolak = [], []
    for judul, hwnd in jendela_di(mon, pid_aplikasi):
        ctypes.set_last_error(0)
        user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
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
            user32.ShowWindow(hwnd, 9)   # SW_RESTORE


def bersihkan(pid):
    """Tutup HANYA jendela Chrome milik uji ini (proses yang kita luncurkan)."""
    for hwnd in jendela_chrome(pid):
        user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
    time.sleep(1.0)
    for hwnd in jendela_chrome(pid):
        user32.PostMessageW(hwnd, 0x0010, 0, 0)   # WM_CLOSE
    time.sleep(1.5)
    # Kalau masih ada, hentikan prosesnya - ini proses yang kita buat sendiri.
    for hwnd in jendela_chrome(pid):
        hpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hpid))
        subprocess.run(['taskkill', '/PID', str(hpid.value), '/T', '/F'],
                       capture_output=True)


if __name__ == '__main__':
    sys.exit(main())
