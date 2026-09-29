#!/usr/bin/env python3
"""Tangkap layar panel QR di halaman beli, dengan kode QR asli dari iPaymu.

Tujuannya memeriksa tampilannya, bukan hanya keberadaan elemennya. Angka bisa
benar sementara tampilannya rusak - QR yang terpotong, teks yang tumpang
tindih, tombol yang keluar dari kartu.

Pemakaian:
  python tools/shoot-snap.py
"""
import http.server
import json
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8809
OUT = ROOT / 'build' / 'snap-shots'
NAMA = '_uji-shoot.html'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Minta QR sungguhan supaya tangkapan layarnya memperlihatkan yang benar-
    # benar dilihat pembeli, bukan contoh buatan.
    try:
        req = urllib.request.Request(
            'https://lumawall.xinet.id/api/checkout/',
            data=json.dumps({
                'nama': 'Tangkap Layar',
                'email': 'tangkapan@lumawall.invalid',
                'wa': '081234567890',
            }).encode(),
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        print('  ! gagal meminta QR: %s' % e)
        return 1

    if not d.get('ok'):
        print('  ! server menolak: %s' % (d.get('error') or d))
        return 1

    print('  pesanan: %s  total: Rp%s' % (d.get('order'), d.get('total')))

    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    kartu = teks[awal:akhir] if awal != -1 and akhir != -1 else ''

    halaman = '''<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>Tangkapan panel QR</title>
<link rel="stylesheet" href="/assets/css/fonts.ad37d8582b.css">
<link rel="stylesheet" href="/assets/css/style.322b8497e4.css">
<link rel="stylesheet" href="/assets/css/buy.css">
<style>
  body { margin:0; padding:32px 24px; background:#0b0b0e; }
  .wrap { max-width:1100px; margin:0 auto; }
</style>
</head><body><div class="wrap">%s</div>
<script>
(function(){
  var asli = window.fetch;
  window.fetch = function(u,o){
    u = String(u);
    if (u.indexOf('/api/checkout') === 0)
      return Promise.resolve(new Response(%s,{status:200,headers:{'Content-Type':'application/json'}}));
    if (u.indexOf('/api/status-pembayaran') === 0)
      return Promise.resolve(new Response('{"ok":true,"paid":false}',{status:200,headers:{'Content-Type':'application/json'}}));
    return asli.apply(this,arguments);
  };
})();
</script>
<script src="/assets/js/buy.js"></script>
<script>
document.getElementById('f-nama').value='Tangkap Layar';
document.getElementById('f-email').value='tangkapan@lumawall.invalid';
document.getElementById('f-wa').value='081234567890';
document.getElementById('buy-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
</script></body></html>''' % (kartu, json.dumps(json.dumps(d)))

    (SITE / NAMA).write_text(halaman, encoding='utf-8')

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    lebar_daftar = [('desktop', 1200, 1400), ('mobile', 390, 1500)]
    hasil = []

    try:
        for nama, lebar, tinggi in lebar_daftar:
            keluar = OUT / ('snap-%s.png' % nama)
            # Chrome menulis ke berkas dengan --screenshot; tunggu sampai QR
            # muncul dulu lewat --virtual-time-budget yang cukup panjang.
            r = subprocess.run(
                [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                 '--no-default-browser-check', '--hide-scrollbars',
                 '--user-data-dir=%s' % (ROOT / 'build' / ('_chrome_shoot_' + nama)),
                 '--window-size=%d,%d' % (lebar, tinggi),
                 '--virtual-time-budget=25000',
                 '--screenshot=%s' % keluar,
                 'http://127.0.0.1:%d/%s' % (PORT, NAMA)],
                capture_output=True, timeout=200, text=True,
            )
            if keluar.exists():
                kb = keluar.stat().st_size // 1024
                print('  \u2713 %-8s %4dpx  %4d KB  %s' % (nama, lebar, kb, keluar))
                hasil.append(keluar)
            else:
                print('  \u2717 %-8s gagal: %s' % (nama, (r.stderr or '')[:200]))
    finally:
        f = SITE / NAMA
        if f.exists():
            f.unlink()
        httpd.shutdown()

    print()
    print('  %d tangkapan layar di %s' % (len(hasil), OUT))
    return 0 if hasil else 1


if __name__ == '__main__':
    sys.exit(main())
