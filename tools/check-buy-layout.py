#!/usr/bin/env python3
"""Ukur luapan tata letak halaman pembelian di beberapa lebar layar.

Menebak penyebab luapan dari kode CSS tidak berhasil: yang terlihat di tangkapan
layar mobile adalah teks terpotong di kanan, dan penyebabnya tidak kelihatan
dari membaca aturan CSS satu per satu. Skrip ini bertanya langsung ke peramban:
elemen mana yang lebih lebar dari layar, dan berapa piksel lebihnya.

Cara kerja: berkas probe ditulis ke dalam folder situs (supaya satu asal dengan
halaman yang diperiksa), lalu Chrome dijalankan dengan --dump-dom dan hasilnya
dibaca dari judul dokumen. Tidak perlu DevTools Protocol atau pustaka tambahan.

Pemakaian:
  python tools/check-buy-layout.py
  python tools/check-buy-layout.py --page /beli/ --width 360
"""
import argparse
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
PORT = 8796
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PROFILE = ROOT / 'build' / '_chrome_layout'
PROBE_NAME = '_layout-probe.html'

# Lebar yang diuji. 360 px adalah ponsel paling sempit yang masih umum; kalau
# halaman muat di sana, ia muat di semua yang lebih lebar.
WIDTHS = [360, 390, 420, 768, 1024, 1440]

PAGES = [
    '/beli/',
    '/en/buy/',
    '/sukses/?order=LW-ABCDEF',
    '/en/success/?order=LW-ABCDEF',
]

# Fungsi ini menerima objek window sebagai argumen, bukan memakai `window`
# global. Alasannya penting: skrip ini berjalan di halaman PEMBUNGKUS, jadi
# `window` di dalamnya menunjuk ke halaman pembungkus - bukan ke halaman yang
# sedang diukur. Versi pertama memakai `window.innerWidth` dan karena itu
# selalu melaporkan lebar jendela Chrome (500px), bukan lebar iframe yang
# diuji. Hasilnya uji "mobile" tidak pernah benar-benar menguji mobile.
PROBE_JS = r'''
function probe(w) {
  var doc = w.document;
  var de = doc.documentElement;
  var vw = w.innerWidth;
  var out = { viewport: vw, docWidth: de.scrollWidth, overflowing: [], clipped: [] };

  var all = doc.querySelectorAll('body *');
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      var parentOverflows = false;
      var p = el.parentElement;
      while (p && p !== doc.body) {
        var pr = p.getBoundingClientRect();
        if (pr.right > vw + 1 || pr.left < -1) { parentOverflows = true; break; }
        p = p.parentElement;
      }
      if (!parentOverflows && out.overflowing.length < 10) {
        out.overflowing.push({
          tag: el.tagName.toLowerCase(),
          cls: (typeof el.className === 'string') ? el.className.split(/\s+/).slice(0, 3).join('.') : '',
          text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 46),
          left: Math.round(r.left), right: Math.round(r.right),
          width: Math.round(r.width), over: Math.round(r.right - vw)
        });
      }
    }
  }

  var texty = doc.querySelectorAll('h1, h2, h3, p, span, b, a, code, summary, td');
  for (var j = 0; j < texty.length; j++) {
    var t = texty[j];
    if (t.children.length > 0) continue;
    if (t.scrollWidth > t.clientWidth + 2 && t.clientWidth > 0 && out.clipped.length < 10) {
      out.clipped.push({
        tag: t.tagName.toLowerCase(),
        text: (t.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40),
        scrollW: t.scrollWidth, clientW: t.clientWidth
      });
    }
  }
  return out;
}
'''


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def write_probe(target_path, width):
    """Tulis pembungkus yang memuat halaman lalu menaruh hasil probe di judul.

    Lebar iframe di-set eksplisit, bukan 100vw. Alasannya: `--window-size` di
    Chrome headless TIDAK selalu menghasilkan viewport selebar itu - terukur
    500px untuk permintaan 360px - sehingga halaman di dalam iframe melihat
    lebar yang salah dan uji luapan jadi mengukur hal yang keliru. Menetapkan
    lebar langsung membuat viewport di dalam iframe persis seperti yang diminta.
    """
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>html,body{margin:0;padding:0;overflow:hidden}'
        'iframe{border:0;width:%dpx;height:100vh;display:block}</style></head><body>'
        '<iframe id="f" src="%s"></iframe>'
        '<script>\n%s\n'
        'window.addEventListener("load", function () {\n'
        '  setTimeout(function () {\n'
        '    try {\n'
        '      var w = document.getElementById("f").contentWindow;\n'
        '      var res = probe(w);\n'
        '      document.title = "RESULT" + JSON.stringify(res);\n'
        '    } catch (e) {\n'
        '      document.title = "RESULT" + JSON.stringify({ error: String(e) });\n'
        '    }\n'
        '  }, 1800);\n'
        '});\n'
        '</script></body></html>' % (width, target_path, PROBE_JS)
    )
    (SITE / PROBE_NAME).write_text(html, encoding='utf-8')


def run_probe(width, height=900):
    cmd = [
        CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--hide-scrollbars',
        '--user-data-dir=%s' % PROFILE,
        '--window-size=%d,%d' % (width, height),
        '--virtual-time-budget=8000',
        '--dump-dom',
        'http://127.0.0.1:%d/%s' % (PORT, PROBE_NAME),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=120, text=True)
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}

    dom = out.stdout or ''
    idx = dom.find('RESULT')
    if idx == -1:
        return {'error': 'tidak ada hasil (panjang DOM %d)' % len(dom)}
    end = dom.find('</title>', idx)
    raw = dom[idx + 6:end if end != -1 else None]
    for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&#39;', "'")):
        raw = raw.replace(a, b)
    try:
        return json.loads(raw)
    except Exception as e:
        return {'error': 'JSON tidak terbaca: %s' % e, 'raw': raw[:160]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', help='hanya periksa satu halaman')
    ap.add_argument('--width', type=int, help='hanya periksa satu lebar')
    args = ap.parse_args()

    if not Path(CHROME).exists():
        print('  Chrome tidak ditemukan di %s' % CHROME)
        return 1

    pages = [args.page] if args.page else PAGES
    widths = [args.width] if args.width else WIDTHS

    httpd = serve()
    time.sleep(1)

    masalah = 0
    total = 0

    try:
        for url in pages:
            print('  \u2550\u2550 %s \u2550\u2550' % url)
            for w in widths:
                total += 1
                write_probe(url, w)
                r = run_probe(w)

                if 'error' in r:
                    print('     %4dpx  ! %s' % (w, r['error']))
                    masalah += 1
                    continue

                over = r.get('overflowing') or []
                clip = r.get('clipped') or []
                doc = r.get('docWidth', 0)

                if not over and not clip and doc <= w + 1:
                    print('     %4dpx  \u2713 bersih (doc %dpx)' % (w, doc))
                    continue

                masalah += 1
                print('     %4dpx  \u2717 doc %dpx' % (w, doc))
                for o in over[:6]:
                    print('             meluber %+dpx  <%s class="%s"> %s'
                          % (o['over'], o['tag'], o['cls'], o['text'][:36]))
                for c in clip[:6]:
                    print('             terpotong     %s (%dpx > %dpx) %s'
                          % (c['tag'], c['scrollW'], c['clientW'], c['text'][:32]))
            print()
    finally:
        # Berkas probe tidak boleh tertinggal di folder situs: ia akan ikut
        # ter-deploy dan muncul sebagai halaman kosong yang bisa diakses siapa pun.
        probe_file = SITE / PROBE_NAME
        if probe_file.exists():
            probe_file.unlink()
        httpd.shutdown()

    print()
    if masalah:
        print('  %d dari %d kombinasi punya masalah tata letak.' % (masalah, total))
        return 1
    print('  semua %d kombinasi bersih.' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
