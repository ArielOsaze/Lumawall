#!/usr/bin/env python3
"""Uji Stop lalu Apply, sambil mengukur apakah ada jeda hitam.

Ini pengujian yang paling penting untuk keluhan yang dilaporkan, dan yang paling
sulit dilakukan dengan benar: "hitam" harus diukur, bukan diperkirakan dari
kode. Wallpaper bisa saja gelap secara alami, jadi yang dibedakan bukan
"hitam atau tidak" melainkan "kecerahan turun ke nyaris nol atau tidak".

Caranya: tombol Hentikan dan tombol Terapkan ditekan lewat UI Automation pada
jendela aplikasi yang sesungguhnya, sementara kecerahan layar dibaca berkala.
Yang dicari adalah penurunan tajam ke nyaris nol di antara kedua tekanan itu.

Pemakaian:
  python tools/check-stop-apply.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_screen  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pilih_monitor(nama):
    for m in test_screen.monitors():
        if nama in (m.get('device') or ''):
            return m
    return None


def baca_kecerahan(monitor):
    """Kecerahan rata-rata di lima titik layar, 0-255."""
    hdc = user32.GetDC(None)
    if not hdc:
        return None
    try:
        nilai = []
        for fx, fy in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
            x = monitor['x'] + int(monitor['width'] * fx)
            y = monitor['y'] + int(monitor['height'] * fy)
            w = gdi32.GetPixel(hdc, x, y)
            if w == 0xFFFFFFFF:
                continue
            r, g, b = w & 0xFF, (w >> 8) & 0xFF, (w >> 16) & 0xFF
            nilai.append(0.299 * r + 0.587 * g + 0.114 * b)
        return statistics.mean(nilai) if nilai else None
    finally:
        user32.ReleaseDC(None, hdc)


class Pengukur(threading.Thread):
    """Membaca kecerahan terus-menerus selama pengujian."""

    def __init__(self, monitor, jeda=0.15):
        super().__init__(daemon=True)
        self.monitor = monitor
        self.jeda = jeda
        self.jalan = True
        self.contoh = []

    def run(self):
        mulai = time.time()
        while self.jalan:
            n = baca_kecerahan(self.monitor)
            if n is not None:
                self.contoh.append((time.time() - mulai, n))
            time.sleep(self.jeda)

    def hentikan(self):
        self.jalan = False
        self.join(timeout=3)


def buka_halaman(judul_jendela, nama_halaman, waktu_tunggu=20):
    """Buka salah satu halaman lewat tombol navigasinya.

    Tombol Hentikan hanya ada di halaman Displays, jadi halaman itu harus dibuka
    lebih dulu. Ini juga membuat pengujiannya menempuh jalur yang sama dengan
    pengguna, bukan menyentuh fungsi internalnya langsung.
    """
    return klik_tombol(judul_jendela, nama_halaman, waktu_tunggu)


def klik_tombol(judul_jendela, nama_tombol, waktu_tunggu=20):
    """Tekan tombol di aplikasi lewat UI Automation.

    Mengembalikan True kalau tombolnya ditemukan dan ditekan. UI Automation
    dipakai, bukan klik koordinat: koordinat berubah kalau jendelanya dipindah
    atau ukurannya berubah, dan klik yang meleset akan terbaca sebagai
    "aplikasinya tidak merespons".
    """
    skrip = (
        "Add-Type -AssemblyName UIAutomationClient;"
        "$w = [System.Windows.Automation.AutomationElement]::RootElement;"
        "$cond = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, '%s');"
        "$win = $w.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond);"
        "if (-not $win) { Write-Output 'NO_WINDOW'; exit }"
        "$bcond = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, '%s');"
        "$btn = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $bcond);"
        "if (-not $btn) { Write-Output 'NO_BUTTON'; exit }"
        "$p = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern);"
        "$p.Invoke(); Write-Output 'OK'"
    ) % (judul_jendela, nama_tombol)

    r = subprocess.run(['powershell', '-NoProfile', '-Command', skrip],
                       capture_output=True, text=True, timeout=waktu_tunggu)
    keluaran = (r.stdout or '').strip()
    return keluaran == 'OK', keluaran


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    ap.add_argument('--judul', default='LumaWall')
    args = ap.parse_args()

    monitor = pilih_monitor(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ uji Stop lalu Apply di %s ══' % args.display)
    print()
    print('  layar: %s' % test_screen.describe(monitor))
    print()

    # Jendela aplikasi dipindahkan lebih dulu, dan kepindahannya diverifikasi.
    #
    # Jendela LumaWall sendiri bisa berdiri di atas layar yang diukur, sehingga
    # titik sampelnya jatuh di dalam jendela itu dan yang terbaca adalah warna
    # antarmuka aplikasi - terang, diam, dan selalu tampak benar. Itu membuat
    # pemeriksaan ini melaporkan "tidak ada jeda hitam" untuk keadaan apa pun.
    import ukur_layar
    if not ukur_layar.bersihkan_layar(monitor):
        print('  ! jendela aplikasi menutupi layar uji - pengukuran tidak sah')
        return 1

    # Kecerahan awal, sebagai pembanding. Kalau layarnya sudah gelap sejak awal,
    # penurunan berikutnya tidak bisa disimpulkan apa-apa.
    awal = baca_kecerahan(monitor)
    if awal is None:
        print('  ! tidak bisa membaca warna layar')
        return 1
    print('  kecerahan awal: %.1f / 255' % awal)
    if awal < 20:
        print('  ! layar sudah gelap sejak awal, uji ini tidak bisa menyimpulkan')
        return 1
    print()

    ukur = Pengukur(monitor)
    ukur.start()

    try:
        print('  ── membuka halaman Displays ──')
        ok, pesan = buka_halaman(args.judul, 'Displays')
        if not ok:
            for alternatif in ('Tampilan', 'Layar'):
                ok, pesan = buka_halaman(args.judul, alternatif)
                if ok:
                    break
        if not ok:
            print('     \u2717 halaman Displays tidak bisa dibuka (%s)' % pesan)
            return 1
        print('     \u2713 terbuka')
        time.sleep(2)
        print()

        print('  ── menekan Stop ──')
        # Tombolnya bernama "Stop" pada antarmuka Inggris dan "Hentikan" pada
        # antarmuka Indonesia. Bahasa bisa berubah, jadi keduanya dicari.
        ok, pesan = klik_tombol(args.judul, 'Hentikan')
        if not ok:
            for alternatif in ('Stop', 'Berhenti'):
                ok, pesan = klik_tombol(args.judul, alternatif)
                if ok:
                    break
        if not ok:
            print('     \u2717 tombol tidak ditemukan (%s)' % pesan)
            return 1
        print('     \u2713 ditekan')
        time.sleep(3)

        tengah = baca_kecerahan(monitor)
        print('     kecerahan setelah Hentikan: %.1f / 255' % tengah)
        if tengah < awal * 0.25:
            print('     \u2717 LAYAR JADI HITAM setelah Hentikan')
            print('       Frame terakhir seharusnya tetap terlihat.')
            return 1
        print('     \u2713 frame terakhir masih terlihat')
        print()

        print('  ── menekan Apply ──')
        ok, pesan = klik_tombol(args.judul, 'Terapkan')
        if not ok:
            for alternatif in ('Apply', 'Pasang'):
                ok, pesan = klik_tombol(args.judul, alternatif)
                if ok:
                    break
        if not ok:
            print('     \u2717 tombol tidak ditemukan (%s)' % pesan)
            return 1
        print('     \u2713 ditekan')
        time.sleep(8)
    finally:
        time.sleep(0.5)
        ukur.hentikan()

    # ── analisis ────────────────────────────────────────────────────────────
    print()
    print('  ── hasil pengukuran ──')
    if not ukur.contoh:
        print('     ! tidak ada sampel')
        return 1

    nol = [t for t, n in ukur.contoh if n < 8]
    print('     %d sampel selama %.1f detik' % (len(ukur.contoh), ukur.contoh[-1][0]))
    print('     kecerahan: min %.1f, rata-rata %.1f, maks %.1f'
          % (min(n for _, n in ukur.contoh),
             statistics.mean(n for _, n in ukur.contoh),
             max(n for _, n in ukur.contoh)))

    if nol:
        print()
        print('     \u2717 ADA %d sampel nyaris hitam (%.1f detik)' % (len(nol), nol[-1] - nol[0]))
        print('       Titik-titiknya: %s' % ', '.join('%.1fs' % t for t in nol[:10]))
        return 1

    print()
    print('  \u2713 tidak ada jeda hitam: kecerahan tidak pernah turun ke nyaris nol')
    return 0


if __name__ == '__main__':
    sys.exit(main())
