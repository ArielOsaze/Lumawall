#!/usr/bin/env python3
"""Tangkap layar navbar dalam beberapa keadaan, untuk dilihat langsung.

Angka dan boolean tidak menunjukkan apakah sesuatu terlihat bagus. Skrip ini
mengambil gambar pada keadaan-keadaan yang penting, supaya hasilnya bisa
diperiksa dengan mata.

Pemakaian:
  python tools/shoot-navbar.py
"""
import functools
import http.server
import json
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9460
# Path absolut, dihitung dari letak berkas ini - bukan path relatif.
SITE = Path(__file__).resolve().parent.parent / 'site'
URL = 'http://127.0.0.1:8973/'
KELUARAN = Path('build/navbar')


def jalankan_server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(SITE.resolve()))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', 8973), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def target_ws():
    for _ in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=2) as r:
                for t in json.loads(r.read().decode()):
                    if t.get('type') == 'page' and t.get('webSocketDebuggerUrl'):
                        return t['webSocketDebuggerUrl']
        except Exception:
            pass
        time.sleep(0.5)
    return None


def kirim(ws, id_, method, params=None):
    ws.send(json.dumps({'id': id_, 'method': method, 'params': params or {}}))
    for _ in range(400):
        pesan = json.loads(ws.recv())
        if pesan.get('id') == id_:
            return pesan.get('result', {})
    return {}


def evaluasi(ws, ekspresi, id_=1):
    r = kirim(ws, id_, 'Runtime.evaluate',
              {'expression': ekspresi, 'returnByValue': True, 'awaitPromise': True})
    return r.get('result', {}).get('value')


def simpan(ws, jalur, id_):
    """Tangkap layar elemen navbar saja, dengan latar transparan."""
    hasil = kirim(ws, id_, 'Page.captureScreenshot',
                  {'format': 'png', 'captureBeyondViewport': False})
    import base64
    data = hasil.get('data')
    if not data:
        print('     ! gagal menangkap')
        return False
    jalur.parent.mkdir(parents=True, exist_ok=True)
    jalur.write_bytes(base64.b64decode(data))
    return True


def main():
    print()
    print('  ══ tangkap layar navbar ══')
    print()

    httpd = jalankan_server()
    proc = subprocess.Popen([
        CHROME, '--headless=new', '--remote-debugging-port=%d' % PORT,
        '--remote-allow-origins=*',
        '--window-size=1440,900', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--hide-scrollbars',
        '--user-data-dir=%s' % str(Path('build/chrome-shot').resolve()), URL,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        ws_url = target_ws()
        if not ws_url:
            print('  ! Chrome tidak bisa dihubungi')
            return 1

        import websocket  # type: ignore
        ws = websocket.create_connection(ws_url, timeout=20)
        kirim(ws, 100, 'Page.enable')
        time.sleep(2.5)

        # 1. bilah atas, diam
        if simpan(ws, KELUARAN / '1-bilah-atas.png', 11):
            print('     ✓ 1-bilah-atas.png')

        # 2. menu "Fitur" terbuka
        evaluasi(ws, "document.querySelectorAll('.nav-drop button')[0].click(); 'ok'")
        time.sleep(0.7)
        if simpan(ws, KELUARAN / '2-menu-fitur.png', 12):
            print('     ✓ 2-menu-fitur.png')

        # 3. menu "Galeri" terbuka
        evaluasi(ws, "document.querySelectorAll('.nav-drop button')[1].click(); 'ok'")
        time.sleep(0.7)
        if simpan(ws, KELUARAN / '3-menu-galeri.png', 13):
            print('     ✓ 3-menu-galeri.png')

        # 4. lebar 1024 - titik tersempit sebelum menu berganti
        evaluasi(ws, "document.querySelectorAll('.nav-drop button')[1].click(); 'ok'")
        kirim(ws, 101, 'Emulation.setDeviceMetricsOverride',
              {'width': 1024, 'height': 700, 'deviceScaleFactor': 1, 'mobile': False})
        time.sleep(1)
        if simpan(ws, KELUARAN / '4-lebar-1024.png', 14):
            print('     ✓ 4-lebar-1024.png')

        # 5. HP 390px - menu tertutup
        kirim(ws, 102, 'Emulation.setDeviceMetricsOverride',
              {'width': 390, 'height': 780, 'deviceScaleFactor': 2, 'mobile': True})
        time.sleep(1)
        if simpan(ws, KELUARAN / '5-hp-tertutup.png', 15):
            print('     ✓ 5-hp-tertutup.png')

        # 6. HP 390px - menu terbuka
        evaluasi(ws, "document.querySelector('.nav-burger').click(); 'ok'")
        time.sleep(0.8)
        if simpan(ws, KELUARAN / '6-hp-terbuka.png', 16):
            print('     ✓ 6-hp-terbuka.png')

        # 7. halaman EN
        kirim(ws, 103, 'Emulation.clearDeviceMetricsOverride')
        evaluasi(ws, "location.href = '/en/'; 'ok'")
        time.sleep(3.5)
        evaluasi(ws, "document.querySelectorAll('.nav-drop button')[1].click(); 'ok'")
        time.sleep(0.7)
        if simpan(ws, KELUARAN / '7-en-galeri.png', 17):
            print('     ✓ 7-en-galeri.png')

        ws.close()
        print()
        print('  gambar ada di: %s' % KELUARAN.resolve())
        return 0

    finally:
        proc.terminate()
        httpd.shutdown()


if __name__ == '__main__':
    sys.exit(main())
