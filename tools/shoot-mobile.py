#!/usr/bin/env python3
"""Tangkap halaman pembelian pada lebar ponsel yang benar.

`--window-size` di Chrome headless tidak selalu menghasilkan viewport selebar
itu: terukur 500px untuk permintaan 360px. Tangkapan layar karena itu tidak
menunjukkan apa yang akan dilihat pengguna ponsel, dan pemeriksaan sebelumnya
melaporkan "teks terpotong" yang sebenarnya hanya artefak.

Skrip ini memuat halaman di dalam iframe selebar yang diminta, sehingga
tangkapan layarnya benar-benar menunjukkan tata letak pada lebar itu.

Pemakaian:
  python tools/shoot-mobile.py
"""
import http.server
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
OUT = ROOT / 'build' / 'buy-shots'
PORT = 8798
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
WRAP = '_shot-frame.html'

SHOTS = [
    ('beli-360', '/beli/', 360, 1400),
    ('beli-390', '/beli/', 390, 1400),
    ('sukses-390', '/sukses/?order=LW-ABCDEF', 390, 1000),
    ('beli-en-390', '/en/buy/', 390, 1400),
    ('beli-tablet', '/beli/', 768, 1200),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not Path(CHROME).exists():
        print('  Chrome tidak ditemukan')
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    ok = 0
    try:
        for nama, path, w, h in SHOTS:
            # Tinggi iframe = tinggi isi, supaya seluruh halaman tertangkap
            # dalam satu gambar dan tidak terpotong di bagian bawah.
            html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<style>html,body{margin:0;padding:0;background:#080a0c}'
                'iframe{border:0;width:%dpx;height:%dpx;display:block}</style>'
                '</head><body><iframe src="%s"></iframe></body></html>'
                % (w, h, path)
            )
            wrap_file = SITE / WRAP
            wrap_file.write_text(html, encoding='utf-8')

            out = OUT / ('%s.png' % nama)
            cmd = [
                CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                '--no-first-run', '--no-default-browser-check',
                '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_shot2'),
                '--window-size=%d,%d' % (w + 20, h + 20),
                '--virtual-time-budget=7000',
                '--screenshot=%s' % out,
                'http://127.0.0.1:%d/%s' % (PORT, WRAP),
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                print('  ! %s: timeout' % nama)
                continue

            if out.exists() and out.stat().st_size > 4000:
                print('  \u2713 %-14s %4dpx  %5.0f KB' % (nama, w, out.stat().st_size / 1024))
                ok += 1
            else:
                print('  \u2717 %-14s gagal' % nama)
    finally:
        wrap_file = SITE / WRAP
        if wrap_file.exists():
            wrap_file.unlink()
        httpd.shutdown()

    print()
    print('  %d dari %d tertangkap di build/buy-shots/' % (ok, len(SHOTS)))
    return 0 if ok == len(SHOTS) else 1


if __name__ == '__main__':
    sys.exit(main())
