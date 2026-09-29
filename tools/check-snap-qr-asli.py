#!/usr/bin/env python3
"""Uji panel QR dengan kode QR ASLI dari iPaymu.

Versi sebelumnya memakai QR palsu 1x1, yang hanya membuktikan tata letaknya
bekerja. Uji ini memakai kode QR sungguhan dari server produksi, sehingga
sekaligus membuktikan bahwa data URL yang dikirim server benar-benar bisa
ditampilkan peramban pada ukuran yang bisa dipindai.

Kalau salah satu mata rantai putus - iPaymu mengubah bentuk balasannya, server
gagal mengekstrak data URL-nya, atau peramban menolak data URL sepanjang ini -
uji ini yang akan menangkapnya.

Pemakaian:
  python tools/check-snap-qr-asli.py
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
PORT = 8808
NAMA_UJI = '_uji-qr-asli.html'


def minta_qr_asli():
    """Buat pesanan sungguhan dan ambil data URL QR-nya."""
    muatan = json.dumps({
        'nama': 'Uji QR Asli',
        'email': 'uji-qr-asli@lumawall.invalid',
        'wa': '081234567890',
    }).encode()

    req = urllib.request.Request(
        'https://lumawall.xinet.id/api/checkout/',
        data=muatan, method='POST',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    print()
    print('  \u2550\u2550 panel QR dengan kode QR asli dari iPaymu \u2550\u2550')
    print()

    # ── 1. minta QR sungguhan ────────────────────────────────────────────────
    try:
        d = minta_qr_asli()
    except Exception as e:
        print('  \u2717 gagal meminta QR: %s' % e)
        return 1

    if not d.get('ok'):
        print('  \u2717 server menolak: %s' % (d.get('error') or d))
        return 1

    qr = d.get('qrImage') or ''
    print('  pesanan    : %s' % d.get('order'))
    print('  total      : Rp%s' % d.get('total'))
    print('  bentuk QR  : %s' % ('data URL' if qr.startswith('data:image/') else qr[:60]))
    print('  panjang QR : %d karakter' % len(qr))

    if not qr.startswith('data:image/'):
        print()
        print('  \u2717 GAGAL: server belum mengembalikan data URL.')
        print('    Data URL diperlukan karena alamat QrImage dari iPaymu berisi')
        print('    HTML, bukan gambar, dan peramban tidak bisa menampilkannya')
        print('    lewat atribut src.')
        return 1

    # ── 2. tampilkan di peramban ─────────────────────────────────────────────
    kartu = ''
    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    if awal != -1 and akhir != -1:
        kartu = teks[awal:akhir]

    halaman = '''<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>memuat</title>
<link rel="stylesheet" href="/assets/css/buy.css">
<style>body{margin:0;padding:24px;background:#0b0b0e;color:#eee;font-family:system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto}</style>
</head><body><div class="wrap">%s</div>
<script>
(function(){
  var asli = window.fetch;
  window.fetch = function(u, o){
    u = String(u);
    if (u.indexOf('/api/checkout') === 0) {
      return Promise.resolve(new Response(%s,
        {status:200, headers:{'Content-Type':'application/json'}}));
    }
    if (u.indexOf('/api/status-pembayaran') === 0) {
      return Promise.resolve(new Response('{"ok":true,"paid":false}',
        {status:200, headers:{'Content-Type':'application/json'}}));
    }
    return asli.apply(this, arguments);
  };
})();
</script>
<script src="/assets/js/buy.js"></script>
<script>
(function(){
  var hasil = { langkah: [], error: null };
  function catat(n, ok, ket){ hasil.langkah.push({nama:n, ok:!!ok, keterangan:String(ket||'')}); }

  try {
    document.getElementById('f-nama').value = 'Uji QR Asli';
    document.getElementById('f-email').value = 'uji-qr-asli@lumawall.invalid';
    document.getElementById('f-wa').value = '081234567890';
    document.getElementById('buy-form').dispatchEvent(
      new Event('submit', {bubbles:true, cancelable:true}));
  } catch(e){ hasil.error = String(e); }

  var n = 0;
  var t = setInterval(function(){
    n += 1;
    var img = document.getElementById('qr-img');
    var qrCard = document.getElementById('qr-card');
    var tampil = qrCard && !qrCard.hidden;
    var terlihat = img && !img.hidden && img.naturalWidth > 0 && img.naturalHeight > 0;

    if (tampil && terlihat) {
      clearInterval(t);
      catat('kartu QR tampil', tampil);
      // Yang menentukan: ukuran NYATA. QR yang tidak bisa dipindai karena
      // terlalu kecil sama saja dengan tidak ada.
      catat('QR terlihat dengan ukuran nyata', terlihat,
            img.naturalWidth + 'x' + img.naturalHeight);
      catat('QR cukup besar untuk dipindai', img.naturalWidth >= 200,
            img.naturalWidth + 'px (minimum 200)');
      var kotak = img.getBoundingClientRect();
      catat('QR punya ukuran di layar', kotak.width >= 200 && kotak.height >= 200,
            Math.round(kotak.width) + 'x' + Math.round(kotak.height) + ' px');
      catat('sumber berupa data URL',
            String(img.getAttribute('src')||'').indexOf('data:image/') === 0);
      catat('total tampil',
            (document.getElementById('qr-total')||{}).textContent,
            (document.getElementById('qr-total')||{}).textContent);
      catat('kode pesanan tampil',
            (document.getElementById('qr-order')||{}).textContent,
            (document.getElementById('qr-order')||{}).textContent);
      hasil.percobaan = n;
      document.title = 'HASIL' + JSON.stringify(hasil);
      return;
    }
    if (n >= 60) {
      clearInterval(t);
      catat('kartu QR tampil', tampil);
      catat('QR terlihat dengan ukuran nyata', terlihat);
      hasil.percobaan = n;
      document.title = 'HASIL' + JSON.stringify(hasil);
    }
  }, 250);
})();
</script></body></html>''' % (kartu, json.dumps(json.dumps(d)))

    (SITE / NAMA_UJI).write_text(halaman, encoding='utf-8')

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    try:
        r = subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
             '--no-default-browser-check', '--hide-scrollbars',
             '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_qrasli'),
             '--window-size=1200,1500', '--virtual-time-budget=25000',
             '--dump-dom', 'http://127.0.0.1:%d/%s' % (PORT, NAMA_UJI)],
            capture_output=True, timeout=200, text=True,
        )
    except subprocess.TimeoutExpired:
        print('  \u2717 Chrome tidak selesai dalam batas waktu')
        return 1
    finally:
        f = SITE / NAMA_UJI
        if f.exists():
            f.unlink()
        httpd.shutdown()

    dom = r.stdout or ''
    i = dom.find('HASIL')
    if i == -1:
        print('  \u2717 tidak ada hasil dari halaman')
        return 1
    end = dom.find('</title>', i)
    raw = dom[i + 5:end if end != -1 else None]
    for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'),
                 ('&gt;', '>'), ('&#39;', "'")):
        raw = raw.replace(a, b)

    try:
        hasil = json.loads(raw)
    except Exception as e:
        print('  \u2717 hasil tidak terbaca:', e)
        return 1

    print()
    gagal = 0
    for l in hasil.get('langkah', []):
        if not l['ok']:
            gagal += 1
        print('  %s %-34s %s' % ('\u2713' if l['ok'] else '\u2717', l['nama'], l['keterangan']))

    if hasil.get('error'):
        print('  ! %s' % hasil['error'])
        gagal += 1

    print()
    if gagal:
        print('  %d masalah.' % gagal)
        return 1
    print('  QR asli dari iPaymu tampil di halaman pada ukuran yang bisa dipindai.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
