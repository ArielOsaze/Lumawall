#!/usr/bin/env python3
"""Tangkap layar halaman beli dengan pemilih cara bayar dan panel pembayaran.

Menguji dua keadaan yang paling penting:
  1. Formulir dengan QRIS terpilih (biaya Rp249)
  2. Formulir dengan Transfer Bank terpilih (daftar bank muncul, biaya berubah)
  3. Panel QR setelah pesanan dibuat
  4. Panel Virtual Account setelah pesanan dibuat

Pemakaian:
  python tools/shoot-kanal.py
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
PORT = 8811
OUT = ROOT / 'build' / 'kanal-shots'
NAMA = '_uji-kanal-shoot.html'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def minta(kanal, percobaan=3):
    """Buat pesanan sungguhan, dengan percobaan ulang.

    Percobaan ulang bukan kemalasan: iPaymu sesekali lambat atau menolak satu
    permintaan, dan itu terlihat dari sisi sini sebagai HTTP 502. Transaksi
    yang gagal tidak menagih apa pun, jadi mencoba lagi aman - dan tanpa ini
    checker melaporkan kegagalan yang sebenarnya hanya gangguan sesaat.
    """
    terakhir = None
    for i in range(percobaan):
        try:
            req = urllib.request.Request(
                'https://lumawall.xinet.id/api/checkout/',
                data=json.dumps({
                    'nama': 'Tangkap Kanal', 'email': 'kanal@lumawall.invalid',
                    'wa': '081234567890', 'kanal': kanal,
                }).encode(),
                method='POST', headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode())
            if d.get('ok'):
                return d
            terakhir = d.get('error') or str(d)
        except Exception as e:
            terakhir = str(e)
        if i < percobaan - 1:
            print('  ! %s percobaan %d gagal (%s), mencoba lagi'
                  % (kanal, i + 1, terakhir[:60]))
            time.sleep(3)
    raise RuntimeError('%s: %s' % (kanal, terakhir))


def halaman(d, aksi_js):
    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    kartu = teks[awal:akhir] if awal != -1 and akhir != -1 else ''

    return '''<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>Tangkapan</title>
<link rel="stylesheet" href="/assets/css/fonts.ad37d8582b.css">
<link rel="stylesheet" href="/assets/css/style.322b8497e4.css">
<link rel="stylesheet" href="/assets/css/buy.css">
<style>body{margin:0;padding:32px 24px;background:#0b0b0e}
.wrap{max-width:1100px;margin:0 auto}</style>
</head><body><div class="wrap">%s</div>
<script>
window.LumaWallHarga = 10000;
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
document.getElementById('f-nama').value='Budi Santoso';
document.getElementById('f-email').value='budi@example.com';
document.getElementById('f-wa').value='081234567890';
setTimeout(function(){ %s }, 400);
</script></body></html>''' % (kartu, json.dumps(json.dumps(d)), aksi_js)


def tangkap(nama, html, tinggi=1500):
    (SITE / NAMA).write_text(html, encoding='utf-8')
    keluar = OUT / ('%s.png' % nama)
    try:
        subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
             '--no-default-browser-check', '--hide-scrollbars',
             '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_kanal'),
             '--window-size=1200,%d' % tinggi, '--virtual-time-budget=20000',
             '--screenshot=%s' % keluar,
             'http://127.0.0.1:%d/%s' % (PORT, NAMA)],
            capture_output=True, timeout=180, text=True,
        )
    except subprocess.TimeoutExpired:
        print('  \u2717 %s: timeout' % nama)
        return False
    if keluar.exists():
        print('  \u2713 %-22s %4d KB  %s' % (nama, keluar.stat().st_size // 1024, keluar.name))
        return True
    print('  \u2717 %s: tidak ada berkas' % nama)
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Pesanan sungguhan untuk kedua kanal, supaya tangkapannya memperlihatkan
    # yang benar-benar dilihat pembeli.
    print()
    print('  \u2550\u2550 meminta pesanan sungguhan \u2550\u2550')
    try:
        qr = minta('qris')
        va = minta('bca')
    except Exception as e:
        print('  \u2717 gagal: %s' % e)
        return 1
    print('  QRIS : %s  total Rp%s' % (qr.get('order'), qr.get('total')))
    print('  BCA  : %s  total Rp%s' % (va.get('order'), va.get('total')))
    print()

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    print('  \u2550\u2550 tangkapan layar \u2550\u2550')
    hasil = []
    try:
        # Formulir: QRIS terpilih.
        hasil.append(tangkap('1-formulir-qris', halaman(qr, '')))

        # Formulir: Transfer Bank dipilih, daftar bank muncul, biaya berubah.
        hasil.append(tangkap('2-formulir-bank', halaman(va, """
          document.querySelector('[data-kanal="bca"]').click();
          document.querySelector('[data-bank="mandiri"]').click();
        """)))

        # Panel QR.
        hasil.append(tangkap('3-panel-qr', halaman(qr, """
          document.getElementById('buy-form').dispatchEvent(
            new Event('submit',{bubbles:true,cancelable:true}));
        """)))

        # Panel Virtual Account.
        hasil.append(tangkap('4-panel-va', halaman(va, """
          document.querySelector('[data-kanal="bca"]').click();
          document.getElementById('buy-form').dispatchEvent(
            new Event('submit',{bubbles:true,cancelable:true}));
        """)))
    finally:
        f = SITE / NAMA
        if f.exists():
            f.unlink()
        httpd.shutdown()

    print()
    berhasil = sum(1 for h in hasil if h)
    print('  %d dari %d tertangkap di %s' % (berhasil, len(hasil), OUT))
    return 0 if berhasil == len(hasil) else 1


if __name__ == '__main__':
    sys.exit(main())
