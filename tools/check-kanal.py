#!/usr/bin/env python3
"""Ukur nilai yang benar-benar tampil di pemilih cara bayar dan panel pembayaran.

Ditulis karena pemeriksaan lewat tangkapan layar tidak bisa dipercaya untuk
angka. Pada uji ini, pembacaan tangkapan layar melaporkan "Harga barang
Rp12.000" dan kode pesanan "INV-BCCK2FM" - dua nilai yang tidak ada di halaman
mana pun di proyek ini. Angka yang salah lebih berbahaya daripada tidak ada
angka, karena angkanya terlihat meyakinkan.

Yang diukur di sini dibaca dari DOM setelah halaman selesai bekerja: nilai
sebenarnya yang dilihat pembeli, bukan perkiraan dari gambar.

Pemakaian:
  python tools/check-kanal.py
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
PORT = 8812
NAMA = '_uji-kanal.html'
PEMBUNGKUS = '_uji-kanal-bungkus.html'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def minta(kanal, percobaan=3):
    """Buat pesanan sungguhan, dengan percobaan ulang.

    Transaksi yang gagal tidak menagih apa pun, jadi mencoba lagi aman - dan
    tanpa ini checker melaporkan gangguan jaringan sesaat sebagai kegagalan.
    """
    terakhir = None
    for i in range(percobaan):
        try:
            req = urllib.request.Request(
                'https://lumawall.xinet.id/api/checkout/',
                data=json.dumps({
                    'nama': 'Uji Kanal', 'email': 'uji-kanal@lumawall.invalid',
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
            time.sleep(3)
    raise RuntimeError('%s: %s' % (kanal, terakhir))


PROBE = r'''
function ukur(w) {
  var d = w.document;
  var out = {};

  function teks(id) {
    var el = d.getElementById(id);
    return el ? String(el.textContent || '').trim() : null;
  }
  function tampil(id) {
    var el = d.getElementById(id);
    if (!el) return null;
    var cs = w.getComputedStyle(el);
    return cs.display !== 'none' && !el.hidden;
  }

  // Pemilih cara bayar.
  out.kanalAda = !!d.getElementById('kanal-grid');
  out.jumlahKanal = d.querySelectorAll('.kanal').length;
  out.kanalAktif = (d.querySelector('.kanal.aktif') || {}).getAttribute
    ? d.querySelector('.kanal.aktif').getAttribute('data-kanal') : null;

  // Rincian total.
  out.harga = teks('total-bayar') !== null ? null : null;
  out.rincian = {};
  var baris = d.querySelectorAll('.buy-total-baris');
  for (var i = 0; i < baris.length; i++) {
    var label = baris[i].querySelector('span');
    var nilai = baris[i].querySelector('b');
    if (label && nilai) {
      out.rincian[label.textContent.trim().split('\n')[0].trim()] = nilai.textContent.trim();
    }
  }

  // Panel pembayaran.
  out.qrPanelTampil = tampil('qr-panel');
  out.vaPanelTampil = tampil('va-panel');
  out.qrCardTampil = tampil('qr-card');
  out.qrJudul = teks('qr-judul');
  out.qrTotal = teks('qr-total');
  out.vaNomor = teks('va-nomor');
  out.vaBank = teks('va-bank');
  out.vaJumlah = teks('va-jumlah');
  out.qrOrder = teks('qr-order');
  out.qrExpired = teks('qr-expired');
  out.status = teks('qr-status-text');

  var img = d.getElementById('qr-img');
  out.qrTerlihat = img ? (!img.hidden && img.naturalWidth > 0) : false;
  out.qrUkuran = img ? (img.naturalWidth + 'x' + img.naturalHeight) : null;
  out.qrSumber = img ? String(img.getAttribute('src') || '').slice(0, 11) : null;

  return out;
}
'''


def halaman(d, aksi):
    teks = (SITE / 'beli' / 'index.html').read_text(encoding='utf-8')
    awal = teks.find('<div class="buy-card" id="form-card">')
    akhir = teks.find('</section>', awal)
    kartu = teks[awal:akhir] if awal != -1 and akhir != -1 else ''

    return '''<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>memuat</title>
<link rel="stylesheet" href="/assets/css/buy.css">
<style>body{margin:0;padding:20px;background:#0b0b0e}
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
document.getElementById('f-nama').value='Uji Kanal';
document.getElementById('f-email').value='uji@lumawall.invalid';
document.getElementById('f-wa').value='081234567890';
setTimeout(function(){ %s }, 500);
</script></body></html>''' % (kartu, json.dumps(json.dumps(d)), aksi)


def jalankan(html, nama):
    (SITE / NAMA).write_text(html, encoding='utf-8')
    (SITE / PEMBUNGKUS).write_text(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>memuat</title></head>'
        '<body style="margin:0"><iframe id="f" src="/%s" '
        'style="width:900px;height:1600px;border:0"></iframe>'
        '<script>%s</script>'
        '<script>window.addEventListener("load",function(){setTimeout(function(){'
        'try{var w=document.getElementById("f").contentWindow;'
        'document.title="UKUR"+JSON.stringify(ukur(w));}'
        'catch(e){document.title="UKUR"+JSON.stringify({error:String(e)});}},4000);});'
        '</script></body></html>' % (NAMA, PROBE),
        encoding='utf-8',
    )
    try:
        r = subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
             '--no-default-browser-check', '--hide-scrollbars',
             '--user-data-dir=%s' % (ROOT / 'build' / '_chrome_kanalchk'),
             '--window-size=940,1650', '--virtual-time-budget=25000', '--dump-dom',
             'http://127.0.0.1:%d/%s' % (PORT, PEMBUNGKUS)],
            capture_output=True, timeout=200, text=True,
        )
    except subprocess.TimeoutExpired:
        return None

    dom = r.stdout or ''
    i = dom.find('UKUR')
    if i == -1:
        return None
    end = dom.find('</title>', i)
    raw = dom[i + 4:end if end != -1 else None]
    for a, b in (('&quot;', '"'), ('&amp;', '&'), ('&lt;', '<'),
                 ('&gt;', '>'), ('&#39;', "'")):
        raw = raw.replace(a, b)
    try:
        return json.loads(raw)
    except Exception:
        return None


def main():
    print()
    print('  \u2550\u2550 nilai yang benar-benar tampil \u2550\u2550')
    print()

    try:
        qris = minta('qris')
        bca = minta('bca')
    except Exception as e:
        print('  \u2717 gagal membuat pesanan: %s' % e)
        return 1

    print('  pesanan QRIS : %s  total %s' % (qris.get('order'), qris.get('total')))
    print('  pesanan BCA  : %s  total %s' % (bca.get('order'), bca.get('total')))
    print()

    handler = lambda *a, **k: Quiet(*a, directory=str(SITE), **k)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(1)

    gagal = 0
    try:
        # ── 1. QRIS ─────────────────────────────────────────────────────────
        print('  \u2500\u2500 QRIS \u2500\u2500')
        h = jalankan(halaman(qris, """
          document.getElementById('buy-form').dispatchEvent(
            new Event('submit',{bubbles:true,cancelable:true}));
        """), 'qris')
        if not h:
            print('     \u2717 tidak ada hasil')
            gagal += 1
        else:
            cek = [
                ('pemilih cara bayar ada', h.get('kanalAda') is True, ''),
                ('dua pilihan', h.get('jumlahKanal') == 2, str(h.get('jumlahKanal'))),
                ('QRIS terpilih', h.get('kanalAktif') == 'qris', str(h.get('kanalAktif'))),
                ('panel QR tampil', h.get('qrPanelTampil') is True, ''),
                ('panel VA tersembunyi', h.get('vaPanelTampil') is False, ''),
                ('gambar QR terlihat', h.get('qrTerlihat') is True, str(h.get('qrUkuran'))),
                ('sumber data URL', h.get('qrSumber') == 'data:image/', str(h.get('qrSumber'))),
                ('judul benar', h.get('qrJudul') == 'Bayar dengan QRIS', str(h.get('qrJudul'))),
                ('kode pesanan benar', h.get('qrOrder') == qris.get('order'), str(h.get('qrOrder'))),
            ]
            for nama, ok, ket in cek:
                if not ok: gagal += 1
                print('     %s %-28s %s' % ('\u2713' if ok else '\u2717', nama, ket))
            print('     total tampil : %s (server: Rp%s)'
                  % (h.get('qrTotal'), '{:,}'.format(qris.get('total')).replace(',', '.')))
            print('     rincian      : %s' % json.dumps(h.get('rincian', {}), ensure_ascii=False))
        print()

        # ── 2. Transfer BCA ─────────────────────────────────────────────────
        print('  \u2500\u2500 Transfer BCA \u2500\u2500')
        h = jalankan(halaman(bca, """
          document.querySelector('[data-kanal="bca"]').click();
          document.getElementById('buy-form').dispatchEvent(
            new Event('submit',{bubbles:true,cancelable:true}));
        """), 'bca')
        if not h:
            print('     \u2717 tidak ada hasil')
            gagal += 1
        else:
            nomor = h.get('vaNomor') or ''
            cek = [
                ('panel VA tampil', h.get('vaPanelTampil') is True, ''),
                ('panel QR tersembunyi', h.get('qrPanelTampil') is False, ''),
                ('judul menyebut bank', 'BCA' in (h.get('qrJudul') or ''), str(h.get('qrJudul'))),
                ('nomor VA ada', bool(nomor) and nomor != '\u2014', nomor),
                ('nomor VA berupa digit', nomor.isdigit() if nomor else False,
                 '%d digit' % len(nomor)),
                ('bank disebut', 'BCA' in (h.get('vaBank') or ''), str(h.get('vaBank'))),
                ('jumlah transfer ada', bool(h.get('vaJumlah')), str(h.get('vaJumlah'))),
                ('kode pesanan benar', h.get('qrOrder') == bca.get('order'), str(h.get('qrOrder'))),
            ]
            for nama, ok, ket in cek:
                if not ok: gagal += 1
                print('     %s %-28s %s' % ('\u2713' if ok else '\u2717', nama, ket))
            print('     total tampil : %s (server: Rp%s)'
                  % (h.get('qrTotal'), '{:,}'.format(bca.get('total')).replace(',', '.')))
            print('     rincian      : %s' % json.dumps(h.get('rincian', {}), ensure_ascii=False))
    finally:
        for f in (SITE / NAMA, SITE / PEMBUNGKUS):
            if f.exists():
                f.unlink()
        httpd.shutdown()

    print()
    if gagal:
        print('  %d masalah.' % gagal)
        return 1
    print('  semua lulus: pemilih cara bayar bekerja, dan panelnya menampilkan')
    print('  nilai yang sama dengan yang dikembalikan server.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
