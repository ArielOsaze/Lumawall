#!/usr/bin/env python3
"""Cari elemen mana yang menentukan lebar dokumen (diagnostik).

check-buy-layout.py melaporkan "doc 500px" di viewport 360px tetapi tidak
menemukan elemen yang meluber - artinya elemen penyebabnya meluber lewat cara
yang tidak tertangkap pemeriksaan `right > vw`. Skrip ini melaporkan elemen
terlebar secara langsung, diurutkan, supaya penyebabnya kelihatan.

Pemakaian:
  python tools/diag-buy-width.py --page /beli/ --width 360
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
PORT = 8797
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PROFILE = ROOT / 'build' / '_chrome_diag'
PROBE_NAME = '_width-diag.html'

# Menerima objek window sebagai argumen, bukan memakai `window` global: skrip
# ini berjalan di halaman pembungkus, jadi `window` menunjuk ke halaman
# pembungkus - bukan ke halaman di dalam iframe yang sedang diukur.
JS = r'''
function probe(w) {
  var doc = w.document;
  var vw = w.innerWidth;
  var out = { viewport: vw, docWidth: doc.documentElement.scrollWidth,
              bodyWidth: doc.body.scrollWidth, widest: [] };
  var all = doc.querySelectorAll('*');
  var list = [];
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var r = el.getBoundingClientRect();
    if (r.width <= vw + 1) continue;
    list.push({
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string') ? el.className.split(/\s+/).slice(0, 4).join('.') : '',
      id: el.id || '',
      width: Math.round(r.width),
      right: Math.round(r.right),
      scrollW: el.scrollWidth,
      clientW: el.clientWidth,
      cssWidth: w.getComputedStyle(el).width,
      cssMinWidth: w.getComputedStyle(el).minWidth,
      cssWhiteSpace: w.getComputedStyle(el).whiteSpace,
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 44)
    });
  }
  list.sort(function (a, b) { return b.width - a.width; });
  out.widest = list.slice(0, 15);
  return out;
}
'''


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default='/beli/')
    ap.add_argument('--width', type=int, default=360)
    args = ap.parse_args()

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    # Lebar iframe di-set eksplisit: `--window-size` di Chrome headless tidak
    # selalu menghasilkan viewport selebar itu (terukur 500px untuk permintaan
    # 360px), sehingga halaman di dalam iframe melihat lebar yang salah.
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>html,body{margin:0;padding:0;overflow:hidden}'
        'iframe{border:0;width:%dpx;height:100vh;display:block}</style></head><body>'
        '<iframe id="f" src="%s"></iframe><script>\n%s\n'
        'window.addEventListener("load", function(){ setTimeout(function(){'
        'try{var w=document.getElementById("f").contentWindow;'
        'document.title="RESULT"+JSON.stringify(probe(w));}'
        'catch(e){document.title="RESULT"+JSON.stringify({error:String(e)});}},1800);});\n'
        '</script></body></html>' % (args.width, args.page, JS)
    )
    probe_file = SITE / PROBE_NAME
    probe_file.write_text(html, encoding='utf-8')

    cmd = [
        CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--hide-scrollbars',
        '--user-data-dir=%s' % PROFILE,
        '--window-size=%d,900' % args.width,
        '--virtual-time-budget=8000', '--dump-dom',
        'http://127.0.0.1:%d/%s' % (PORT, PROBE_NAME),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=120, text=True)
    finally:
        if probe_file.exists():
            probe_file.unlink()
        httpd.shutdown()

    dom = out.stdout or ''
    idx = dom.find('RESULT')
    if idx == -1:
        print('  ! tidak ada hasil (DOM %d byte)' % len(dom))
        return 1
    end = dom.find('</title>', idx)
    raw = dom[idx + 6:end if end != -1 else None]
    for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&#39;', "'")):
        raw = raw.replace(a, b)

    try:
        r = json.loads(raw)
    except Exception as e:
        print('  ! JSON tidak terbaca: %s' % e)
        print('    %s' % raw[:300])
        return 1

    print('  halaman   : %s @ %dpx' % (args.page, r['viewport']))
    print('  lebar doc : %dpx' % r['docWidth'])
    print('  lebar body: %dpx' % r['bodyWidth'])
    print()
    if not r['widest']:
        print('  tidak ada elemen yang lebih lebar dari viewport.')
        print('  (kalau doc tetap lebih lebar, penyebabnya margin/padding negatif)')
        return 0

    print('  elemen terlebar:')
    for e in r['widest']:
        print('     %5dpx  <%s%s%s>  width=%s min-width=%s ws=%s'
              % (e['width'], e['tag'],
                 ('#' + e['id']) if e['id'] else '',
                 ('.' + e['cls']) if e['cls'] else '',
                 e['cssWidth'], e['cssMinWidth'], e['cssWhiteSpace']))
        if e['text']:
            print('             "%s"' % e['text'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
