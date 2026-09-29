#!/usr/bin/env python3
"""Tangkap halaman beli dan sukses supaya bisa diperiksa dengan mata.

Halaman yang terlihat benar di kode bisa tetap rusak saat dirender: font yang
tidak termuat, kartu yang tumpang tindih, tombol yang tidak terlihat. Karena itu
halaman diperiksa sebagai gambar, bukan sebagai HTML.

Halaman disajikan lewat server lokal sederhana supaya jalur relatif
(../assets/...) ikut berfungsi seperti di situs sungguhan.

Pemakaian:
  python tools/shoot-buy-pages.py
"""
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
OUT = ROOT / 'build' / 'buy-shots'
PORT = 8795

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

PAGES = [
    ('beli', '/beli/', 1440, 900),
    ('sukses', '/sukses/?order=LW-ABCDEF', 1440, 900),
    ('beli-mobile', '/beli/', 420, 900),
    ('beli-en', '/en/buy/', 1440, 900),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def main():
    if not Path(CHROME).exists():
        print('  Chrome tidak ditemukan di %s' % CHROME)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    httpd = serve()
    time.sleep(1)

    print('  server lokal: http://127.0.0.1:%d' % PORT)
    print()

    hasil = []
    for nama, path, w, h in PAGES:
        out = OUT / ('%s.png' % nama)
        url = 'http://127.0.0.1:%d%s' % (PORT, path)
        cmd = [
            CHROME,
            '--headless=new',
            '--disable-gpu',
            '--hide-scrollbars',
            '--no-first-run',
            '--no-default-browser-check',
            '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_shoot'),
            '--window-size=%d,%d' % (w, h),
            '--screenshot=%s' % out,
            '--virtual-time-budget=6000',
            url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            print('  ! %s: timeout' % nama)
            hasil.append((nama, False))
            continue

        if out.exists() and out.stat().st_size > 5000:
            kb = out.stat().st_size / 1024
            print('  \u2713 %-14s %5.0f KB  %s' % (nama, kb, out.relative_to(ROOT)))
            hasil.append((nama, True))
        else:
            ukuran = out.stat().st_size if out.exists() else 0
            print('  \u2717 %-14s gagal (%d byte)' % (nama, ukuran))
            hasil.append((nama, False))

    httpd.shutdown()

    gagal = [h for h in hasil if not h[1]]
    print()
    if gagal:
        print('  %d halaman gagal ditangkap' % len(gagal))
        return 1
    print('  semua %d halaman tertangkap di build/buy-shots/' % len(hasil))
    return 0


if __name__ == '__main__':
    sys.exit(main())
