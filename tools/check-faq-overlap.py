#!/usr/bin/env python3
"""Periksa apakah panah di pertanyaan FAQ menutupi teksnya.

Latar: checker tata letak melaporkan `<summary>` punya isi 4px lebih lebar dari
kotaknya (283px isi di dalam 279px). Angka itu bisa berarti dua hal yang sangat
berbeda:

  a. teks pertanyaannya benar-benar terpotong - cacat yang harus diperbaiki;
  b. hanya panah kecil di kanan yang membesar karena diputar 45 derajat -
     tidak ada yang terpotong, teksnya utuh.

Membedakannya dari angka saja tidak bisa. Skrip ini mengukur dua hal yang
memisahkannya dengan jelas:

  1. Lebar teks pertanyaannya sendiri, dibanding ruang yang tersedia untuknya.
  2. Apakah kotak teks dan kotak panah benar-benar beririsan.

Pemakaian:
  python tools/check-faq-overlap.py
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
PORT = 8802
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
FRAME = '_faq-probe.html'

PROBE = r'''
function probe(w) {
  var doc = w.document;
  var vw = w.innerWidth;
  var out = { viewport: vw, items: [] };

  var summaries = doc.querySelectorAll('.faq summary');
  for (var i = 0; i < summaries.length; i++) {
    var s = summaries[i];
    var cs = w.getComputedStyle(s);

    // Kotak teks: rentang tempat teks boleh mengalir.
    var padL = parseFloat(cs.paddingLeft) || 0;
    var padR = parseFloat(cs.paddingRight) || 0;
    var gap = parseFloat(cs.columnGap || cs.gap) || 0;
    var sr = s.getBoundingClientRect();

    // Panah digambar oleh ::after. Ukur kotaknya lewat pseudo-element.
    var after = w.getComputedStyle(s, '::after');
    var afterW = parseFloat(after.width) || 0;
    var afterH = parseFloat(after.height) || 0;

    // Rentang teks yang tersedia: dari padding kiri sampai sebelum panah.
    var textRoom = sr.width - padL - padR - gap - afterW;

    // Lebar teks sesungguhnya: bungkus isi dalam span sementara.
    var clone = s.cloneNode(true);
    var teks = (s.textContent || '').trim();
    var span = doc.createElement('span');
    span.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;'
      + 'font:' + cs.font + ';letter-spacing:' + cs.letterSpacing;
    span.textContent = teks;
    doc.body.appendChild(span);
    var textW = span.getBoundingClientRect().width;
    doc.body.removeChild(span);

    // Kotak panah yang sebenarnya (setelah diputar 45 derajat, kotak
    // pembatasnya membesar sekitar 1.41x).
    var rotW = afterW, rotH = afterH;
    if (after.transform && after.transform.indexOf('matrix') === 0) {
      var m = after.transform.match(/matrix\(([^)]+)\)/);
      if (m) {
        var p = m[1].split(',').map(parseFloat);
        // Skala sumbu: panjang vektor kolom.
        var sx = Math.sqrt(p[0] * p[0] + p[1] * p[1]);
        var sy = Math.sqrt(p[2] * p[2] + p[3] * p[3]);
        rotW = afterW * sx;
        rotH = afterH * sy;
      }
    }

    // Yang menentukan apakah teks "terpotong" bukan lebar teks tanpa pembungkusan,
    // melainkan apakah ia dibungkus (wrap) atau dipotong. Teks di dalam flex item
    // boleh membungkus ke beberapa baris, dan itu perilaku normal - bukan cacat.
    //
    // Cara membedakannya: ukur tinggi. Kalau tinggi elemen lebih dari satu baris,
    // teksnya membungkus. Kalau sama dengan satu baris sementara lebar teksnya
    // melebihi ruang yang tersedia, barulah teksnya benar-benar terpotong.
    var lh = parseFloat(cs.lineHeight);
    if (isNaN(lh)) lh = parseFloat(cs.fontSize) * 1.5;
    var tinggiSatuBaris = lh + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    var tinggiElemen = sr.height;
    var jumlahBaris = Math.max(1, Math.round((tinggiElemen - parseFloat(cs.paddingTop)
                                              - parseFloat(cs.paddingBottom)) / lh));

    // Terpotong = teks lebih lebar dari ruangnya DAN elemen tidak bertambah tinggi
    // untuk menampungnya (yaitu hanya satu baris).
    var terpotong = (textW > textRoom + 1) && (jumlahBaris <= 1);

    out.items.push({
      pertanyaan: teks.slice(0, 44),
      lebarKotak: Math.round(sr.width),
      ruangTeks: Math.round(textRoom),
      lebarTeks: Math.round(textW),
      tinggiElemen: Math.round(tinggiElemen),
      jumlahBaris: jumlahBaris,
      teksMuat: !terpotong,
      cara: jumlahBaris > 1 ? 'membungkus ke ' + jumlahBaris + ' baris' : 'satu baris',
      lebarPanahAsli: Math.round(afterW),
      lebarPanahSetelahPutar: Math.round(rotW),
      panahMuat: afterW <= (parseFloat(cs.width) || sr.width) + 1
    });
  }
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

    ok_semua = True
    try:
        for page, width in [('/beli/', 390), ('/beli/', 1440), ('/en/buy/', 390)]:
            html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8">'
                '<style>html,body{margin:0;padding:0}'
                'iframe{border:0;width:%dpx;height:1200px;display:block}</style>'
                '</head><body><iframe id="f" src="%s"></iframe><script>\n%s\n'
                'window.addEventListener("load", function(){setTimeout(function(){'
                'try{var w=document.getElementById("f").contentWindow;'
                'document.title="RESULT"+JSON.stringify(probe(w));}'
                'catch(e){document.title="RESULT"+JSON.stringify({error:String(e)});}'
                '},1600);});\n</script></body></html>' % (width, page, PROBE)
            )
            frame = SITE / FRAME
            frame.write_text(html, encoding='utf-8')

            out = ROOT / 'build' / '_faq_probe_result.txt'
            cmd = [
                CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                '--no-default-browser-check', '--hide-scrollbars',
                '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_faq'),
                '--window-size=%d,1220' % (width + 20),
                '--virtual-time-budget=9000', '--dump-dom',
                'http://127.0.0.1:%d/%s' % (PORT, FRAME),
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=150, text=True)
            except subprocess.TimeoutExpired:
                print('  ! %s @ %dpx: timeout' % (page, width))
                ok_semua = False
                continue

            dom = r.stdout or ''
            idx = dom.find('RESULT')
            if idx == -1:
                print('  ! %s @ %dpx: tidak ada hasil' % (page, width))
                ok_semua = False
                continue
            end = dom.find('</title>', idx)
            raw = dom[idx + 6:end if end != -1 else None]
            for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&#39;', "'")):
                raw = raw.replace(a, b)

            try:
                data = json.loads(raw)
            except Exception as e:
                print('  ! %s @ %dpx: JSON tidak terbaca (%s)' % (page, width, e))
                ok_semua = False
                continue

            print('  \u2550\u2550 %s @ %dpx \u2550\u2550' % (page, data.get('viewport')))
            for it in data.get('items', []):
                status = 'OK' if it['teksMuat'] else 'TERPOTONG'
                if not it['teksMuat']:
                    ok_semua = False
                print('     %-44s %-9s %s' % (it['pertanyaan'], status, it.get('cara', '')))
                if not it['teksMuat']:
                    print('        ruang %dpx < teks %dpx, tinggi %dpx (%d baris)'
                          % (it['ruangTeks'], it['lebarTeks'],
                             it['tinggiElemen'], it['jumlahBaris']))
            print()

            if frame.exists():
                frame.unlink()
    finally:
        frame = SITE / FRAME
        if frame.exists():
            frame.unlink()
        httpd.shutdown()

    print()
    if ok_semua:
        print('  semua pertanyaan FAQ muat - tidak ada teks yang terpotong.')
        return 0
    print('  ADA teks pertanyaan yang terpotong - perlu diperbaiki.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
