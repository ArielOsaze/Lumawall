#!/usr/bin/env python3
"""Uji navbar baru: dropdown, menu mobile, dan keyboard.

Navbar berubah dari enam tautan datar menjadi dua menu bertingkat. Yang paling
mudah rusak pada perubahan seperti ini adalah hal-hal yang tidak terlihat di
tangkapan layar: apakah menunya bisa dibuka dengan keyboard, apakah Escape
menutupnya, dan apakah menu mobile benar-benar bisa dipakai.

Yang diperiksa di sini:

  1. bilah atas tidak lagi penuh — jumlah tautan yang terlihat berkurang
  2. setiap dropdown membuka panelnya saat diklik
  3. Escape menutup dan mengembalikan fokus ke tombolnya
  4. mengklik di luar menutup menunya
  5. menu mobile muncul di lebar HP dan tautannya lengkap
  6. tidak ada yang meluber keluar layar pada lebar 360, 414, 768, 1024, 1440

Pemakaian:
  python tools/check-navbar.py
"""
import json
import subprocess
import sys
import time
import socketserver
import urllib.request
from pathlib import Path

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

# Chrome uji dibersihkan lewat modul bersama. Chrome yang tertinggal dari
# run sebelumnya memegang port debug dan kunci profil, jadi run berikutnya
# gagal terhubung - dan itu muncul sebagai "navbar tidak bisa diperiksa",
# gejala yang menyesatkan karena navbar-nya sendiri tidak pernah dilihat.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chrome_uji import bersihkan_sisa, kumpulan_pid  # noqa: E402
PORT = 9458
# Path absolut, dihitung dari letak berkas ini - bukan path relatif.
# Path relatif bergantung pada direktori kerja: dijalankan dari tempat lain,
# folder 'site' tidak ditemukan, server gagal, dan checker keluar sebelum
# memeriksa apa pun - yang terbaca sebagai 'semua rusak' atau 'tidak ada
# yang terdeteksi', dua-duanya menyesatkan.
SITE = Path(__file__).resolve().parent.parent / 'site'
URL = 'http://127.0.0.1:8971/'


class ServerDiam(socketserver.TCPServer):
    """Server yang tidak berteriak saat klien membatalkan unduhan.

    Chrome membatalkan unduhan berkas besar (video promo) begitu halaman selesai
    dimuat. http.server bawaan mencetak traceback penuh ke stderr untuk itu, dan
    traceback-nya menenggelamkan hasil pemeriksaan yang sebenarnya - sampai
    pernah terbaca sebagai kegagalan, padahal semua pemeriksaan lulus.

    Yang ditangani hanya pemutusan koneksi, yang memang kejadian normal. Kesalahan
    lain tetap dilewatkan.
    """

    def handle_error(self, request, client_address):
        import sys as _sys
        jenis = _sys.exc_info()[0]
        if jenis in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        super().handle_error(request, client_address)


def jalankan_server():
    """Sajikan folder site lewat http.server supaya path absolut bekerja."""
    import functools
    import http.server
    import socketserver
    import threading

    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(SITE.resolve()))
    httpd = ServerDiam(('127.0.0.1', 8971), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def chrome_buka(url, lebar, tinggi):
    """Buka Chrome headless dan kembalikan prosesnya."""
    return subprocess.Popen([
        CHROME,
        '--headless=new',
        '--remote-debugging-port=%d' % PORT,
        # Chrome rejects a WebSocket that does not come from a page it serves
        # unless the origin is allowed explicitly; without this the connection is
        # refused with 403 and nothing else in this check can run.
        '--remote-allow-origins=*',
        '--window-size=%d,%d' % (lebar, tinggi),
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--user-data-dir=%s' % str(Path('build/chrome-nav').resolve()),
        url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def target_ws():
    """Alamat WebSocket halaman aktif."""
    for _ in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT, timeout=2) as r:
                data = json.loads(r.read().decode())
            for t in data:
                if t.get('type') == 'page' and t.get('webSocketDebuggerUrl'):
                    return t['webSocketDebuggerUrl']
        except Exception:
            pass
        time.sleep(0.5)
    return None


def evaluasi(ws, ekspresi):
    """Jalankan JS di halaman lewat CDP dan kembalikan nilainya."""
    import websocket  # type: ignore

    ws.send(json.dumps({
        'id': 1, 'method': 'Runtime.evaluate',
        'params': {'expression': ekspresi, 'returnByValue': True, 'awaitPromise': True},
    }))
    for _ in range(200):
        pesan = json.loads(ws.recv())
        if pesan.get('id') == 1:
            if pesan.get('result', {}).get('exceptionDetails'):
                # Dikembalikan sebagai dict bertanda, bukan None: None juga
                # berarti "belum ada hasil", dan menyamakan keduanya membuat
                # halaman yang melempar error lolos sebagai "tidak ada masalah".
                pesan_error = pesan['result']['exceptionDetails'].get(
                    'exception', {}).get('description', 'error tidak diketahui')
                return {'__error__': pesan_error}
            hasil = pesan.get('result', {}).get('result', {})
            if 'value' in hasil:
                return hasil['value']
            return None
    return None


def main():
    print()
    print('  ══ uji navbar ══')
    print()

    httpd = jalankan_server()
    # Sisa run sebelumnya dibersihkan lebih dulu.
    bersihkan_sisa('nav')
    proc = chrome_buka(URL, 1440, 900)

    try:
        ws_url = target_ws()
        if not ws_url:
            print('  ! Chrome tidak bisa dihubungi')
            return 1

        import websocket  # type: ignore
        ws = websocket.create_connection(ws_url, timeout=20)
        time.sleep(2)

        gagal = []

        # ── 1. bilah atas tidak penuh ──────────────────────────────────────
        print('  ── 1. isi bilah atas ──')
        info = evaluasi(ws, """(() => {
          const bar = document.querySelector('.nav-links');
          if (!bar) return {error: 'nav-links tidak ada'};
          const links = bar.querySelectorAll(':scope > a');
          const drops = bar.querySelectorAll('.nav-drop');
          const terlihat = Array.from(bar.children).filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          return {
            tautanDatar: links.length,
            dropdown: drops.length,
            terlihat: terlihat.length,
            label: terlihat.map(el => (el.textContent || '').trim().slice(0, 20)),
          };
        })()""")
        if not info or info.get('error') or info.get('__error__'):
            sebab = (info or {}).get('__error__') or (info or {}).get('error') or 'tidak bisa dibaca'
            print('     ✗ %s' % sebab)
            gagal.append('bilah atas')
        else:
            print('     tautan datar: %d' % info['tautanDatar'])
            print('     dropdown    : %d' % info['dropdown'])
            print('     terlihat    : %d  %s' % (info['terlihat'], info['label']))
            # Dua hal diperiksa, dan keduanya perlu. Jumlah saja tidak cukup:
            # bilah atas yang hanya berisi FAQ juga "sedikit", dan itu justru
            # kerusakan yang lebih parah - seluruh bagian halaman menjadi tidak
            # bisa dicapai dari navigasi.
            if info['dropdown'] < 2:
                print('     ✗ hanya %d menu bertingkat, seharusnya 2' % info['dropdown'])
                gagal.append('menu bertingkat hilang')
            elif info['tautanDatar'] < 1:
                print('     ✗ tidak ada tautan langsung (FAQ hilang)')
                gagal.append('tautan FAQ hilang')
            elif info['terlihat'] <= 4:
                print('     ✓ bilah atas ringkas (maksimal 4 item)')
            else:
                print('     ✗ masih terlalu banyak item')
                gagal.append('bilah atas')
        print()

        # ── 2. dropdown membuka ────────────────────────────────────────────
        print('  ── 2. dropdown membuka saat diklik ──')
        hasil = evaluasi(ws, """(async () => {
          const out = [];
          for (const drop of document.querySelectorAll('.nav-drop')) {
            const btn = drop.querySelector('button');
            btn.click();
            await new Promise(r => setTimeout(r, 250));
            const panel = drop.querySelector('.nav-drop-panel');
            const cs = getComputedStyle(panel);
            out.push({
              label: (btn.textContent || '').trim(),
              buka: drop.classList.contains('open'),
              terlihat: cs.visibility === 'visible' && Number(cs.opacity) > 0.9,
              aria: btn.getAttribute('aria-expanded'),
              jumlahTautan: panel.querySelectorAll('a').length,
            });
            btn.click();
            await new Promise(r => setTimeout(r, 150));
          }
          return out;
        })()""")
        # Koleksi kosong adalah kegagalan, bukan alasan untuk melewati
        # pemeriksaan. Versi sebelumnya menulis `for d in (hasil or [])`, jadi
        # ketika dropdown-nya tidak ada sama sekali - justru kerusakan yang
        # paling parah - loop-nya berjalan nol kali dan pemeriksaan ini lulus
        # tanpa memeriksa apa pun.
        if isinstance(hasil, dict) and hasil.get('__error__'):
            print('     ✗ skrip gagal: %s' % hasil['__error__'])
            gagal.append('dropdown tidak terbaca')
            hasil = []
        if not hasil:
            print('     ✗ tidak ada dropdown di bilah atas')
            gagal.append('dropdown hilang')
        for d in hasil:
            # Isinya diperiksa, bukan hanya apakah panelnya terbuka. Menu yang
            # terbuka dengan rapi tetapi tidak berisi tujuan apa pun adalah
            # kerusakan yang lebih buruk daripada menu yang tidak terbuka:
            # pengunjung melihat sesuatu yang tampak berfungsi, mengkliknya, dan
            # tidak terjadi apa-apa.
            if d['jumlahTautan'] < 1:
                print('     ✗ "%s" terbuka tetapi kosong' % d['label'])
                gagal.append('menu kosong: ' + d['label'])
            elif d['buka'] and d['terlihat'] and d['aria'] == 'true':
                print('     ✓ "%s" membuka %d tautan' % (d['label'], d['jumlahTautan']))
            else:
                print('     ✗ "%s" tidak membuka dengan benar: %s' % (d['label'], d))
                gagal.append('dropdown ' + d['label'])
        print()

        # ── 3. Escape menutup ──────────────────────────────────────────────
        print('  ── 3. Escape menutup dan mengembalikan fokus ──')
        esc = evaluasi(ws, """(async () => {
          const drop = document.querySelector('.nav-drop');
          const btn = drop.querySelector('button');
          btn.click();
          await new Promise(r => setTimeout(r, 200));
          const sebelum = drop.classList.contains('open');
          btn.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
          await new Promise(r => setTimeout(r, 200));
          return {
            sebelum: sebelum,
            sesudah: drop.classList.contains('open'),
            fokusDiTombol: document.activeElement === btn,
            aria: btn.getAttribute('aria-expanded'),
          };
        })()""")
        if isinstance(esc, dict) and esc.get('__error__'):
            print('     ✗ skrip gagal: %s' % esc['__error__'])
            gagal.append('Escape tidak terbaca')
            esc = None
        if esc and esc['sebelum'] and not esc['sesudah'] and esc['aria'] == 'false':
            print('     ✓ Escape menutup menu')
            print('     %s fokus kembali ke tombol' % ('✓' if esc['fokusDiTombol'] else '✗'))
            if not esc['fokusDiTombol']:
                gagal.append('fokus Escape')
        else:
            print('     ✗ Escape tidak menutup: %s' % esc)
            gagal.append('Escape')
        print()

        # ── 4. klik di luar menutup ────────────────────────────────────────
        print('  ── 4. klik di luar menutup ──')
        luar = evaluasi(ws, """(async () => {
          const drop = document.querySelector('.nav-drop');
          drop.querySelector('button').click();
          await new Promise(r => setTimeout(r, 200));
          const sebelum = drop.classList.contains('open');
          document.body.click();
          await new Promise(r => setTimeout(r, 200));
          return {sebelum: sebelum, sesudah: drop.classList.contains('open')};
        })()""")
        if isinstance(luar, dict) and luar.get('__error__'):
            print('     ✗ skrip gagal: %s' % luar['__error__'])
            gagal.append('klik luar tidak terbaca')
            luar = None
        if luar and luar['sebelum'] and not luar['sesudah']:
            print('     ✓ klik di luar menutup menu')
        else:
            print('     ✗ klik di luar tidak menutup: %s' % luar)
            gagal.append('klik luar')
        print()

        # ── 5. tidak meluber di berbagai lebar ─────────────────────────────
        print('  ── 5. tidak meluber di berbagai lebar ──')
        for lebar in (360, 414, 768, 1024, 1440):
            subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Start-Sleep -Milliseconds 1'], capture_output=True)
            nilai = evaluasi(ws, """(() => {
              const d = document.documentElement;
              const nav = document.querySelector('.nav-in');
              const r = nav.getBoundingClientRect();
              return {
                scrollW: d.scrollWidth,
                clientW: d.clientWidth,
                navKanan: Math.round(r.right),
                navKiri: Math.round(r.left),
              };
            })()""")
            # Ukuran viewport diubah lewat CDP
            import websocket  # type: ignore
            ws.send(json.dumps({
                'id': 99, 'method': 'Emulation.setDeviceMetricsOverride',
                'params': {'width': lebar, 'height': 800, 'deviceScaleFactor': 1,
                           'mobile': lebar <= 760},
            }))
            ws.recv()
            time.sleep(0.6)
            nilai = evaluasi(ws, """(() => {
              const d = document.documentElement;
              const nav = document.querySelector('.nav-in');
              const r = nav.getBoundingClientRect();
              return {
                scrollW: d.scrollWidth,
                clientW: d.clientWidth,
                navKanan: Math.round(r.right),
                navKiri: Math.round(r.left),
                burgerTampil: getComputedStyle(document.querySelector('.nav-burger')).display !== 'none',
                tautanTampil: getComputedStyle(document.querySelector('.nav-links')).display !== 'none',
              };
            })()""")
            if not nilai:
                print('     ✗ %4dpx  tidak bisa diukur' % lebar)
                gagal.append('tidak terukur di %dpx' % lebar)
                continue

            meluber = nilai['scrollW'] > nilai['clientW'] + 1
            tanda = '✗' if meluber else '✓'
            print('     %s %4dpx  scrollW=%d clientW=%d  burger=%s tautan=%s'
                  % (tanda, lebar, nilai['scrollW'], nilai['clientW'],
                     nilai['burgerTampil'], nilai['tautanTampil']))
            if meluber:
                gagal.append('meluber di %dpx' % lebar)

            # Di bawah 760px menu bilah atas memang disembunyikan, jadi kalau
            # TIDAK ada jalan lain menuju bagian-bagian halaman, pengunjung HP
            # kehilangan seluruh navigasi. Itu pernah terjadi di sini.
            if lebar <= 760 and not nilai['burgerTampil']:
                print('       ✗ di %dpx tidak ada menu sama sekali' % lebar)
                gagal.append('tanpa menu di %dpx' % lebar)
        print()

        # ── 6. menu mobile lengkap ─────────────────────────────────────────
        print('  ── 6. menu mobile ──')
        ws.send(json.dumps({
            'id': 98, 'method': 'Emulation.setDeviceMetricsOverride',
            'params': {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True},
        }))
        ws.recv()
        time.sleep(0.8)
        mobil = evaluasi(ws, """(async () => {
          const burger = document.querySelector('.nav-burger');
          const menu = document.getElementById('nav-mobile');
          if (!burger || !menu) return {error: 'tidak ada'};
          const sebelum = menu.classList.contains('open');
          burger.click();
          await new Promise(r => setTimeout(r, 300));
          const cs = getComputedStyle(menu);
          const tautan = Array.from(menu.querySelectorAll('a')).map(a => a.getAttribute('href'));
          const r = menu.getBoundingClientRect();
          return {
            sebelum: sebelum,
            sesudah: menu.classList.contains('open'),
            display: cs.display,
            tautan: tautan,
            jumlah: tautan.length,
            tinggi: Math.round(r.height),
            aria: burger.getAttribute('aria-expanded'),
          };
        })()""")
        if isinstance(mobil, dict) and mobil.get('__error__'):
            print('     ✗ skrip gagal: %s' % mobil['__error__'])
            gagal.append('menu mobile tidak terbaca')
            mobil = None
        if mobil and mobil.get('jumlah', 0) < 5:
            print('     ✗ menu mobile hanya berisi %d tautan' % mobil.get('jumlah', 0))
            gagal.append('menu mobile tidak lengkap')
        elif mobil and mobil.get('sesudah') and mobil['display'] == 'flex':
            print('     ✓ menu mobile membuka (%d tautan)' % mobil['jumlah'])
            print('       %s' % ', '.join(mobil['tautan']))
        else:
            print('     ✗ menu mobile tidak membuka: %s' % mobil)
            gagal.append('menu mobile')
        print()

        ws.close()

        print('  ══ kesimpulan ══')
        if gagal:
            print('  %d masalah: %s' % (len(gagal), ', '.join(gagal)))
            return 1
        print('  semua pemeriksaan navbar lulus.')
        return 0

    finally:
        # Seluruh pohon proses dimatikan, bukan hanya induknya. Chrome
        # meninggalkan proses anak yang memegang port debug dan kunci
        # profil; kalau dibiarkan, run berikutnya gagal terhubung dan
        # hasilnya terbaca sebagai "navbar tidak bisa diperiksa".
        for pid in kumpulan_pid(proc.pid):
            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                           capture_output=True)
        httpd.shutdown()


if __name__ == '__main__':
    sys.exit(main())
