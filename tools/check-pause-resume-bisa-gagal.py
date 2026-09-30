#!/usr/bin/env python3
"""Buktikan logika check-pause-resume.py bisa GAGAL.

Sebuah pemeriksaan yang tidak bisa gagal tidak membuktikan apa pun - dan yang
paling berbahaya adalah pemeriksaan yang lulus sambil tidak memeriksa apa-apa,
karena ia memberi rasa aman yang salah.

Yang diuji di sini adalah bagian yang menentukan lulus/gagal: pembacaan baris
log aplikasi. Baris-baris itu berbentuk:

    Playback updated (\\.\DISPLAY1, \\.\DISPLAY2, \\.\DISPLAY3): paused [\\.\DISPLAY1]
    Playback updated (\\.\DISPLAY2): paused [] resumed [\\.\DISPLAY3]
    Playback timing \\.\DISPLAY3 resume-frame:7 rs=4 paused=false
    Seamless loop handoff completed on \\.\DISPLAY3 -> D:\\...mp4

Perhatikan baris pertama: DISPLAY3 disebut di bagian depan, tetapi yang dijeda
hanya DISPLAY1. Pencocokan yang mencari nama layar di SELURUH baris akan
menganggap DISPLAY3 dijeda juga - dan pemeriksaan yang membaca begitu bisa lulus
atau gagal karena alasan yang salah. Itu pernah terjadi di sini, dan itulah
sebabnya kasus ini diuji secara khusus di bawah.

Pemakaian:
  python tools/check-pause-resume-bisa-gagal.py
"""
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

AKAR = Path(__file__).resolve().parent


def muat():
    """Muat check-pause-resume.py sebagai modul (namanya mengandung tanda hubung)."""
    jalur = AKAR / 'check-pause-resume.py'
    spec = importlib.util.spec_from_file_location('cpr', jalur)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print()
    print('  ══ bisakah logika check-pause-resume GAGAL? ══')
    print()

    cpr = muat()
    masalah = []

    def periksa(nama, dapat, harus):
        tanda = '✓' if dapat == harus else '✗'
        print('  %s %-52s %s' % (tanda, nama, dapat))
        if dapat != harus:
            masalah.append('%s: dapat %s, harus %s' % (nama, dapat, harus))

    # ── 1. yang dijeda hanya yang ADA DI DALAM kurung ──────────────────────
    b = ('2026-09-30 21:00:21.967 [18696] Playback updated '
         '(\\\\\.\\DISPLAY1, \\\\.\\DISPLAY2, \\\\.\\DISPLAY3): '
         'paused [\\\\.\\DISPLAY1] resumed []')

    periksa('DISPLAY1 dijeda (ada di dalam kurung)',
            cpr.di_dalam(b, 'paused', 'DISPLAY1'), True)
    periksa('DISPLAY2 TIDAK dijeda (hanya disebut di depan)',
            cpr.di_dalam(b, 'paused', 'DISPLAY2'), False)
    periksa('DISPLAY3 TIDAK dijeda (hanya disebut di depan)',
            cpr.di_dalam(b, 'paused', 'DISPLAY3'), False)
    periksa('DISPLAY1 tidak dilanjutkan',
            cpr.di_dalam(b, 'resumed', 'DISPLAY1'), False)

    # ── 2. yang dilanjutkan ────────────────────────────────────────────────
    b2 = ('2026-09-30 21:04:37.411 [18696] Playback updated (\\\\.\\DISPLAY2): '
          'paused [] resumed [\\\\.\\DISPLAY3]')

    periksa('DISPLAY3 dilanjutkan', cpr.di_dalam(b2, 'resumed', 'DISPLAY3'), True)
    periksa('DISPLAY2 tidak dilanjutkan', cpr.di_dalam(b2, 'resumed', 'DISPLAY2'), False)
    periksa('DISPLAY3 tidak dijeda', cpr.di_dalam(b2, 'paused', 'DISPLAY3'), False)

    # ── 3. dua layar sekaligus ─────────────────────────────────────────────
    b3 = ('2026-09-30 21:00:21.967 [18696] Playback updated '
          '(\\\\.\\DISPLAY1, \\\\.\\DISPLAY2, \\\\.\\DISPLAY3): '
          'paused [\\\\.\\DISPLAY2, \\\\.\\DISPLAY3] resumed []')

    periksa('DISPLAY2 dijeda', cpr.di_dalam(b3, 'paused', 'DISPLAY2'), True)
    periksa('DISPLAY3 dijeda', cpr.di_dalam(b3, 'paused', 'DISPLAY3'), True)
    periksa('DISPLAY1 tidak dijeda', cpr.di_dalam(b3, 'paused', 'DISPLAY1'), False)

    # ── 4. daftar kosong ───────────────────────────────────────────────────
    b4 = ('2026-09-30 21:04:35.141 [18696] Playback updated '
          '(\\\\.\\DISPLAY1, \\\\.\\DISPLAY2): paused [] resumed []')

    periksa('daftar kosong: tidak ada yang dijeda',
            cpr.di_dalam(b4, 'paused', 'DISPLAY1'), False)

    # ── 5. pencarian frame dan putaran ─────────────────────────────────────
    #
    # Ini diuji lewat baca_log() yang membaca berkas sungguhan, jadi yang
    # diperiksa adalah fungsinya dengan data nyata. Kalau berkasnya tidak ada,
    # bagian ini dilewati dengan jujur.
    if cpr.LOG.exists():
        sejak = datetime.now() - timedelta(days=3650)
        ada_frame = cpr.cari_frame(sejak, 'DISPLAY3')
        periksa('cari_frame menemukan baris frame',
                ada_frame is not None, True)
        if ada_frame:
            import re
            m = re.search(r'resume-frame:(\d+)', ada_frame[1])
            periksa('angkanya terbaca', m is not None, True)

        ada_putaran = cpr.cari_putaran(sejak, 'DISPLAY3')
        periksa('cari_putaran menemukan putaran selesai',
                len(ada_putaran) > 0, True)

        # Layar yang tidak pernah ada tidak boleh dianggap punya jejak.
        periksa('layar karangan tidak punya jejak',
                cpr.cari_frame(sejak, 'DISPLAY99') is None, True)
    else:
        print('  - log tidak ada, bagian frame/putaran dilewati')

    print()
    if masalah:
        print('  ✗ %d masalah:' % len(masalah))
        for m in masalah:
            print('      %s' % m)
        return 1
    print('  ✓ logika bisa gagal, dan membaca yang dijeda dengan benar.')
    print('    (Kasus DISPLAY2/DISPLAY3 yang hanya disebut di depan itu nyata:')
    print('     pencocokan yang salah pernah membuat uji ini lulus/gagal')
    print('     karena alasan yang tidak ada hubungannya dengan wallpaper.)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
