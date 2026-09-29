#!/usr/bin/env python3
"""Uji panel QR di halaman beli, dengan jawaban server yang dipalsukan.

Yang diuji: logika halaman, bukan jaringannya. Server sudah diuji terpisah
(QR asli dari iPaymu, data URL 450x450), jadi yang tersisa adalah pertanyaan
yang berbeda - apakah halaman benar-benar menampilkan QR itu kepada pembeli.

Bedanya penting dan bukan kehati-hatian berlebih. Sebuah <img> yang menunjuk
HTML alih-alih gambar tetap ada di HTML, tetap punya src, dan sebagian
pemeriksaan akan melaporkannya "berhasil dimuat" - tetapi tingginya nol dan
pembeli tidak melihat apa pun. Karena itu yang diperiksa di sini adalah lebar
dan tinggi gambar setelah dimuat.

Halaman uji ini memuat buy.css dan buy.js yang asli, dengan markup yang sama
seperti halaman beli, dan fetch yang di-stub supaya tidak ada permintaan
jaringan. Jadi yang diuji adalah berkas yang benar-benar dipakai pembeli.

Pemakaian:
  python tools/check-snap-payment.py
"""
import http.server
import json
import re
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 8807
NAMA_UJI = '_uji-snap.html'


def markup_beli():
    """Ambil bagian markup yang diuji, apa adanya dari halaman beli.

    Dibaca dari halaman aslinya, bukan disalin ke sini: markup yang disalin
    akan menyimpang dari yang asli, dan uji yang menguji salinan tidak
    membuktikan apa pun tentang halaman yang dipakai pembeli.
    """
    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')

    # Ketiga kartu, dari kartu formulir sampai kartu selesai.
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    if awal == -1 or akhir == -1:
        raise SystemExit('  ! markup kartu tidak ditemukan di site/beli/index.html')
    return teks[awal:akhir]


def halaman_uji():
    """Halaman uji: markup asli + stub fetch + buy.js asli."""
    kartu = markup_beli()

    # Jawaban server yang dipalsukan. Bentuknya persis seperti yang dikembalikan
    # /api/checkout: order, amount, total, fee, qrImage (data URL), channel,
    # expiredAt. Data URL-nya PNG 1x1 yang diperbesar CSS - cukup untuk menguji
    # apakah gambar punya ukuran nyata setelah dimuat.
    qr_palsu = (
        'data:image/png;base64,'
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/'
        'q842iQAAAABJRU5ErkJggg=='
    )

    return '''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>memuat</title>
<link rel="stylesheet" href="/assets/css/buy.css">
<style>
  /* Halaman uji tidak punya gaya global situs, jadi bagian yang diuji diberi
     ukuran yang masuk akal supaya tata letaknya terbaca. */
  body { margin: 0; padding: 24px; background: #0b0b0e; color: #eee;
         font-family: system-ui, sans-serif; }
  .wrap { max-width: 1100px; margin: 0 auto; }
</style>
</head>
<body>
<div class="wrap">
%s
</div>

<script>
/* Jawaban server dipalsukan. Hanya /api/checkout dan /api/status-pembayaran
   yang dijawab; permintaan lain diteruskan ke fetch asli supaya kesalahan
   tidak tersembunyi. */
(function () {
  var asli = window.fetch;
  window.fetch = function (url, opsi) {
    var u = String(url);
    if (u.indexOf('/api/checkout') === 0) {
      return Promise.resolve(new Response(JSON.stringify({
        ok: true,
        order: 'LW-UJI123',
        amount: 10000,
        total: 10249,
        fee: 249,
        qrImage: '%s',
        qrString: '00020101021226670016COM.NOBUBANK',
        channel: 'QRIS',
        expiredAt: '2026-10-01 00:06:22'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    if (u.indexOf('/api/status-pembayaran') === 0) {
      return Promise.resolve(new Response(JSON.stringify({
        ok: true, order: 'LW-UJI123', status: 'menunggu', paid: false
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    return asli.apply(this, arguments);
  };
})();
</script>
<script src="/assets/js/buy.js"></script>

<script>
(function () {
  var hasil = { langkah: [], error: null };
  function catat(nama, ok, keterangan) {
    hasil.langkah.push({ nama: nama, ok: !!ok, keterangan: String(keterangan || '') });
  }

  try {
    catat('formulir ada', !!document.getElementById('buy-form'));
    catat('kartu QR ada', !!document.getElementById('qr-card'));
    catat('kartu QR tersembunyi di awal',
          document.getElementById('qr-card') && document.getElementById('qr-card').hidden);
    catat('kartu selesai tersembunyi di awal',
          document.getElementById('done-card') && document.getElementById('done-card').hidden);

    document.getElementById('f-nama').value = 'Uji Panel';
    document.getElementById('f-email').value = 'uji-panel@lumawall.invalid';
    document.getElementById('f-wa').value = '081234567890';

    document.getElementById('buy-form').dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true })
    );
  } catch (e) { hasil.error = String(e); }

  var n = 0;
  var timer = setInterval(function () {
    n += 1;
    var qrCard = document.getElementById('qr-card');
    var img = document.getElementById('qr-img');
    var loading = document.getElementById('qr-loading');
    var formCard = document.getElementById('form-card');

    var qrTampil = qrCard && !qrCard.hidden;
    // Yang menentukan: ukuran NYATA gambar setelah dimuat.
    var imgTerlihat = img && !img.hidden && img.naturalWidth > 0 && img.naturalHeight > 0;

    if (qrTampil && (imgTerlihat || (loading && !loading.hidden && /gagal/i.test(loading.textContent || '')))) {
      clearInterval(timer);
      catat('kartu QR tampil', qrTampil);
      catat('formulir tersembunyi', formCard && formCard.hidden);
      catat('gambar QR terlihat', imgTerlihat,
            img ? img.naturalWidth + 'x' + img.naturalHeight : 'tidak ada');
      var src = img ? String(img.getAttribute('src') || '') : '';
      catat('sumber gambar berupa data URL', src.indexOf('data:image/') === 0,
            src.slice(0, 24));
      var total = document.getElementById('qr-total');
      catat('total tampil', total && total.textContent.trim(), total ? total.textContent.trim() : '');
      var order = document.getElementById('qr-order');
      catat('kode pesanan tampil', order && order.textContent.trim(), order ? order.textContent.trim() : '');
      var status = document.getElementById('qr-status-text');
      catat('status tampil', status && status.textContent.trim(), status ? status.textContent.trim() : '');
      var expired = document.getElementById('qr-expired');
      catat('waktu berlaku tampil', expired && expired.textContent.trim(), expired ? expired.textContent.trim() : '');
      hasil.percobaan = n;
      document.title = 'HASIL' + JSON.stringify(hasil);
      return;
    }

    if (n >= 40) {
      clearInterval(timer);
      catat('kartu QR tampil', qrTampil);
      catat('gambar QR terlihat', imgTerlihat);
      var a = document.getElementById('buy-alert');
      catat('peringatan halaman', a && !a.hidden, a ? (a.textContent || '').slice(0, 200) : '');
      hasil.percobaan = n;
      document.title = 'HASIL' + JSON.stringify(hasil);
    }
  }, 250);
})();
</script>
</body>
</html>''' % (kartu, qr_palsu)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not Path(CHROME).exists():
        print('  Chrome tidak ditemukan')
        return 1

    (SITE / NAMA_UJI).write_text(halaman_uji(), encoding='utf-8')

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    print()
    print('  \u2550\u2550 panel QR di halaman beli \u2550\u2550')
    print()

    try:
        r = subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
             '--no-default-browser-check', '--hide-scrollbars',
             '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_snap'),
             '--window-size=1200,1400', '--virtual-time-budget=20000',
             '--dump-dom', 'http://127.0.0.1:%d/%s' % (PORT, NAMA_UJI)],
            capture_output=True, timeout=200, text=True,
        )
    except subprocess.TimeoutExpired:
        print('  ! Chrome tidak selesai dalam batas waktu')
        return 1
    finally:
        f = SITE / NAMA_UJI
        if f.exists():
            f.unlink()
        httpd.shutdown()

    dom = r.stdout or ''
    i = dom.find('HASIL')
    if i == -1:
        print('  ! tidak ada hasil dari halaman')
        print('   ', (r.stderr or '')[:400])
        return 1

    end = dom.find('</title>', i)
    raw = dom[i + 5:end if end != -1 else None]
    for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'),
                 ('&gt;', '>'), ('&#39;', "'")):
        raw = raw.replace(a, b)

    try:
        d = json.loads(raw)
    except Exception as e:
        print('  ! hasil tidak terbaca:', e)
        print('   ', raw[:400])
        return 1

    gagal = 0
    for l in d.get('langkah', []):
        if not l['ok']:
            gagal += 1
        print('  %s %-32s %s' % ('\u2713' if l['ok'] else '\u2717', l['nama'], l['keterangan']))

    if d.get('error'):
        print('  ! kesalahan di halaman: %s' % d['error'])
        gagal += 1

    print()
    terlihat = [l for l in d.get('langkah', []) if l['nama'] == 'gambar QR terlihat']
    if terlihat and terlihat[0]['ok']:
        print('  QR terlihat, ukuran %s - pembeli bisa memindainya' % terlihat[0]['keterangan'])
    else:
        print('  \u2717 QR TIDAK terlihat - pembeli tidak punya cara membayar')
        gagal += 1

    if gagal:
        print()
        print('  %d masalah.' % gagal)
        return 1

    print()
    print('  semua lulus.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
