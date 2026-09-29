#!/usr/bin/env python3
"""Ukur apakah panel QR meluber keluar layar di beberapa lebar.

Tangkapan layar memperlihatkan teks yang terpotong di 390px, tetapi tangkapan
layar pernah menipu di proyek ini: `--window-size` tidak selalu menjadi lebar
viewport yang sebenarnya, dan teks yang "terpotong" di gambar ternyata utuh di
halaman.

Karena itu yang diukur di sini adalah angka, bukan gambar: lebar dokumen
dibandingkan lebar viewport, dan setiap elemen diperiksa apakah kotaknya keluar
dari batas layar. Meluber atau tidak meluber terlihat dari angkanya.

Pemakaian:
  python tools/check-snap-layout.py
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
PORT = 8810
NAMA = '_uji-layout.html'

# Lebar yang diuji, dari yang tersempit sampai yang terlebar. 320px adalah
# batas bawah yang masih dipakai ponsel; kalau di situ tidak meluber, lebar
# yang lebih besar juga tidak.
LEBAR = [320, 360, 390, 414, 768, 1200]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


# Lebar viewport diukur lewat iframe, bukan --window-size.
#
# Chrome punya lebar jendela minimum sekitar 500px: meminta 320px tetap
# menghasilkan viewport 500px, jadi pengukuran "mobile" yang memakai
# --window-size sebenarnya mengukur lebar desktop - dan hasilnya selalu bersih.
# Itu pernah terjadi di proyek ini, dan sempat membuat teks yang terpotong di
# ponsel dianggap artefak tangkapan layar.
#
# Iframe lebarnya bisa disetel bebas, dan karena halaman ujinya seasal,
# isinya bisa diperiksa langsung dari halaman pembungkus.
PROBE = r'''
function ukur(w) {
  var d = w.document.documentElement;
  var hasil = {
    viewport: w.innerWidth,
    dokumen: d.scrollWidth,
    meluber: d.scrollWidth > w.innerWidth + 1,
    elemen: []
  };

  // Elemen yang keluar dari batas kanan layar. Diperiksa per elemen supaya
  // yang meluber bisa disebutkan namanya, bukan hanya diketahui ada.
  var semua = w.document.querySelectorAll('#qr-card *, #done-card *');
  for (var i = 0; i < semua.length; i++) {
    var el = semua[i];
    var r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > w.innerWidth + 1) {
      hasil.elemen.push({
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
        kelas: String(el.className || '').slice(0, 40),
        kanan: Math.round(r.right),
        lebar: Math.round(r.width),
        teks: String(el.textContent || '').trim().slice(0, 50)
      });
    }
  }
  return hasil;
}
'''


def halaman(d):
    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    kartu = teks[awal:akhir] if awal != -1 and akhir != -1 else ''

    return '''<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>memuat</title>
<link rel="stylesheet" href="/assets/css/style.322b8497e4.css">
<link rel="stylesheet" href="/assets/css/buy.css">
<style>body{margin:0;background:#0b0b0e}.wrap{padding:16px}</style>
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
document.getElementById('f-nama').value='Uji Layout';
document.getElementById('f-email').value='uji-layout@lumawall.invalid';
document.getElementById('buy-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
</script>
</body></html>''' % (kartu, json.dumps(json.dumps(d)))


def halaman_pembungkus(lebar):
    """Halaman pembungkus: satu iframe selebar yang diminta, plus pengukur."""
    return '''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>memuat</title></head><body style="margin:0">
<iframe id="f" src="/%s" style="width:%dpx;height:1600px;border:0"></iframe>
<script>%s</script>
<script>
window.addEventListener('load', function () {
  setTimeout(function () {
    try {
      var w = document.getElementById('f').contentWindow;
      document.title = 'UKUR' + JSON.stringify(ukur(w));
    } catch (e) {
      document.title = 'UKUR' + JSON.stringify({ error: String(e) });
    }
  }, 3000);
});
</script></body></html>''' % (NAMA, lebar, PROBE)


def main():
    # QR palsu: uji ini tentang tata letak, bukan tentang iPaymu, jadi tidak
    # perlu memanggil server produksi berkali-kali untuk enam lebar berbeda.
    qr = ('data:image/png;base64,'
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/'
          'q842iQAAAABJRU5ErkJggg==')
    d = {
        'ok': True, 'order': 'LW-LAYOUT', 'amount': 10000,
        'total': 10249, 'fee': 249, 'qrImage': qr, 'channel': 'QRIS',
        'expiredAt': '2026-10-01 00:41:22',
    }

    (SITE / NAMA).write_text(halaman(d), encoding='utf-8')
    pembungkus = SITE / '_uji-pembungkus.html'

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    print()
    print('  \u2550\u2550 tata letak panel QR per lebar \u2550\u2550')
    print()

    gagal = 0
    try:
        for lebar in LEBAR:
            pembungkus.write_text(halaman_pembungkus(lebar), encoding='utf-8')
            try:
                r = subprocess.run(
                    [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                     '--no-default-browser-check', '--hide-scrollbars',
                     '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_layout'),
                     '--window-size=1400,1700',
                     '--virtual-time-budget=20000', '--dump-dom',
                     'http://127.0.0.1:%d/_uji-pembungkus.html' % PORT],
                    capture_output=True, timeout=120, text=True,
                )
            except subprocess.TimeoutExpired:
                print('  \u2717 %4dpx  timeout' % lebar)
                gagal += 1
                continue

            dom = r.stdout or ''
            i = dom.find('UKUR')
            if i == -1:
                print('  \u2717 %4dpx  tidak ada hasil' % lebar)
                gagal += 1
                continue

            end = dom.find('</title>', i)
            raw = dom[i + 4:end if end != -1 else None]
            for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'),
                         ('&gt;', '>'), ('&#39;', "'")):
                raw = raw.replace(a, b)

            try:
                h = json.loads(raw)
            except Exception as e:
                print('  \u2717 %4dpx  hasil tidak terbaca: %s' % (lebar, e))
                gagal += 1
                continue

            if h['meluber']:
                print('  \u2717 %4dpx  viewport %d, dokumen %d - MELUBER %dpx'
                      % (lebar, h['viewport'], h['dokumen'], h['dokumen'] - h['viewport']))
                for el in h['elemen'][:6]:
                    print('       %s#%s.%s  kanan=%d lebar=%d  "%s"'
                          % (el['tag'], el['id'], el['kelas'], el['kanan'],
                             el['lebar'], el['teks']))
                gagal += 1
            else:
                print('  \u2713 %4dpx  viewport %d = dokumen %d'
                      % (lebar, h['viewport'], h['dokumen']))
    finally:
        for f in (SITE / NAMA, SITE / '_uji-pembungkus.html'):
            if f.exists():
                f.unlink()
        httpd.shutdown()

    print()
    if gagal:
        print('  %d lebar bermasalah.' % gagal)
        return 1
    print('  tidak ada yang meluber di semua lebar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
