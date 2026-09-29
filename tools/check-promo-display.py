#!/usr/bin/env python3
"""Periksa apakah blok promo di halaman beli tampil sesuai tanggalnya.

Ada dua blok yang saling bertentangan di halaman beli:
  - blok "promo" (menjelaskan promo Rp10.000 sedang berjalan)
  - blok "setelah promo" (menjelaskan harga sudah Rp18.000)

Keduanya TIDAK boleh terlihat bersamaan. Ini pernah terjadi: `.store-hint {
display: flex }` menang atas `[hidden]` bawaan peramban, jadi blok yang
seharusnya tersembunyi tetap muncul dan halaman menyatakan dua hal yang
berlawanan sekaligus.

Uji ini memeriksa yang sebenarnya: elemen mana yang BENAR-BENAR terlihat
menurut peramban, bukan sekadar ada di HTML.

Pemakaian:
  python tools/check-promo-display.py
"""
import http.server
import json
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
PORT = 8804
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
FRAME = '_cek-promo.html'

PROBE = r'''
function probe(w) {
  var d = w.document;
  var out = {};

  function terlihat(el) {
    if (!el) return false;
    var cs = w.getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden' && !el.hidden;
  }

  // Blok promo vs blok setelah-promo. Dihitung sebagai daftar karena elemennya
  // lebih dari satu (badge, batang pengumuman, catatan harga).
  var promoOnly = d.querySelectorAll('[data-promo-only]');
  var afterPromo = d.querySelectorAll('[data-after-promo]');

  out.promoOnlyTotal = promoOnly.length;
  out.promoOnlyTerlihat = 0;
  promoOnly.forEach(function (e) { if (terlihat(e)) out.promoOnlyTerlihat++; });

  out.afterPromoTotal = afterPromo.length;
  out.afterPromoTerlihat = 0;
  afterPromo.forEach(function (e) { if (terlihat(e)) out.afterPromoTerlihat++; });

  // Harga yang benar-benar tampil ke pengunjung.
  out.harga = [];
  d.querySelectorAll('[data-price]').forEach(function (e) {
    if (terlihat(e)) out.harga.push(e.textContent.trim());
  });

  // Judul halaman juga menyebut harga, dan itu yang muncul di tab peramban.
  out.judul = d.title;

  return out;
}
'''


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not Path(CHROME).exists():
        print('  Chrome tidak ditemukan')
        return 1

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    gagal = 0
    try:
        for halaman in ('/beli/', '/en/buy/'):
            html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
                '<iframe id="f" src="%s" style="width:1200px;height:2400px;border:0"></iframe>'
                '<script>%s\n'
                'window.addEventListener("load", function () {\n'
                '  setTimeout(function () {\n'
                '    try { var w = document.getElementById("f").contentWindow;\n'
                '          document.title = "RESULT" + JSON.stringify(probe(w)); }\n'
                '    catch (e) { document.title = "RESULT" + JSON.stringify({error: String(e)}); }\n'
                '  }, 2500);\n'
                '});\n'
                '</script></body></html>' % (halaman, PROBE)
            )
            frame_file = SITE / FRAME
            frame_file.write_text(html, encoding='utf-8')

            try:
                r = subprocess.run(
                    [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                     '--no-default-browser-check', '--hide-scrollbars',
                     '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_promo'),
                     '--window-size=1220,2420',
                     '--virtual-time-budget=9000', '--dump-dom',
                     'http://127.0.0.1:%d/%s' % (PORT, FRAME)],
                    capture_output=True, timeout=180, text=True,
                )
            except subprocess.TimeoutExpired:
                print('  ! %s: timeout' % halaman)
                gagal += 1
                continue

            dom = r.stdout or ''
            i = dom.find('RESULT')
            if i == -1:
                print('  ! %s: tidak ada hasil' % halaman)
                gagal += 1
                continue
            end = dom.find('</title>', i)
            raw = dom[i + 6:end if end != -1 else None]
            for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'),
                         ('&gt;', '>'), ('&#39;', "'")):
                raw = raw.replace(a, b)

            try:
                d = json.loads(raw)
            except Exception as e:
                print('  ! %s: JSON tidak terbaca (%s)' % (halaman, e))
                gagal += 1
                continue

            print('  \u2550\u2550 %s \u2550\u2550' % halaman)
            print('     blok promo       : %d dari %d terlihat'
                  % (d['promoOnlyTerlihat'], d['promoOnlyTotal']))
            print('     blok setelah     : %d dari %d terlihat'
                  % (d['afterPromoTerlihat'], d['afterPromoTotal']))
            print('     harga tampil     : %s' % ', '.join(sorted(set(d['harga']))))
            print('     judul            : %s' % d['judul'][:70])

            # Inilah yang diperiksa: tidak boleh ada dua pernyataan yang
            # bertentangan tampil sekaligus.
            if d['promoOnlyTerlihat'] > 0 and d['afterPromoTerlihat'] > 0:
                print('     \u2717 GAGAL: blok promo dan blok setelah-promo '
                      'terlihat bersamaan - halaman menyatakan dua hal yang '
                      'berlawanan')
                gagal += 1
            elif d['promoOnlyTerlihat'] == 0 and d['afterPromoTerlihat'] == 0:
                print('     \u2717 GAGAL: keduanya tersembunyi - pengunjung tidak '
                      'tahu harganya yang mana')
                gagal += 1
            elif d['promoOnlyTerlihat'] > 0:
                print('     \u2713 benar: hanya blok promo yang tampil')
            else:
                print('     \u2713 benar: hanya blok setelah-promo yang tampil')

            # Harga yang tampil harus satu nilai saja. Dua nilai berbeda di
            # halaman yang sama berarti salah satu akan dianggap janji.
            unik = sorted(set(d['harga']))
            if len(unik) > 1:
                print('     \u2717 GAGAL: harga yang tampil tidak seragam: %s'
                      % ', '.join(unik))
                gagal += 1
            print()
    finally:
        f = SITE / FRAME
        if f.exists():
            f.unlink()
        httpd.shutdown()

    if gagal:
        print('  %d masalah ditemukan.' % gagal)
        return 1
    print('  semua halaman menampilkan promo secara konsisten.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
