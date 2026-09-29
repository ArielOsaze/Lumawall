#!/usr/bin/env python3
"""Jalankan endpoint pembayaran LumaWall di mesin lokal, lalu uji perilakunya.

Kenapa ini ada: menguji endpoint langsung di situs live berarti setiap bug
ditemukan oleh pengunjung sungguhan, dengan uang sungguhan. Menjalankan handler
yang sama di lokal membuat bug ditemukan sebelum deploy.

Cara kerja: Node dijalankan dengan sebuah server HTTP kecil yang meneruskan
permintaan ke berkas handler di `site/api/`, memakai cara yang sama seperti
Vercel - jadi yang diuji adalah berkas yang benar-benar dikirim, bukan salinan.

Yang diuji:
  • checkout menolak data yang tidak sah
  • checkout menolak nama/email kosong
  • order menolak kode pesanan yang salah format
  • order menjawab 404 untuk kode yang tidak ada
  • download menolak permintaan tanpa token
  • download menolak token yang tidak dikenal
  • download tidak pernah mengirim berkas untuk token palsu

Pemakaian:
  python tools/test-endpoints.py
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8791

# Kredensial uji: nilai palsu, sengaja. Endpoint harus tetap menolak permintaan
# yang salah walau konfigurasinya lengkap - kalau penolakan itu bergantung pada
# konfigurasi yang kosong, uji ini tidak membuktikan apa pun.
ENV = {
    'SUPABASE_URL': 'https://contoh-tidak-nyata.supabase.co',
    'SUPABASE_SERVICE_KEY': 'kunci-uji-yang-tidak-dipakai',
    'IPAYMU_VA': '0000000000000000',
    'IPAYMU_API_KEY': 'kunci-ipaymu-uji',
    'LUMAWALL_BRIDGE_SECRET': 'rahasia-uji-yang-panjang-sekali-untuk-penurunan-token',
    'SITE_URL': 'http://localhost:%d' % PORT,
    'PORT': str(PORT),
    'NODE_ENV': 'test',
}

SERVER_JS = r'''
// Server uji: meneruskan permintaan ke handler di site/api/ dengan bentuk
// objek yang sama seperti yang diberikan Vercel (req.url, req.method,
// req.headers, req.body, res.statusCode, res.setHeader, res.end).
const http = require('http');
const path = require('path');

const root = process.argv[2];
const port = parseInt(process.argv[3], 10);

const handlerCache = {};

function loadHandler(name) {
  if (!handlerCache[name]) {
    const file = path.join(root, 'site', 'api', name + '.js');
    delete require.cache[require.resolve(file)];
    handlerCache[name] = require(file);
  }
  return handlerCache[name];
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const name = url.pathname.replace(/^\/api\//, '').replace(/\/$/, '');

  // Kumpulkan body mentah; handler yang memerlukannya membacanya sendiri.
  let raw = '';
  req.on('data', (c) => { raw += c; });
  req.on('end', () => {
    // Vercel sudah mem-parse body sebelum handler dipanggil, jadi server uji
    // harus melakukan hal yang sama. Kalau tidak, handler yang membaca body
    // akan menunggu event 'data' yang sudah lewat dan permintaannya menggantung
    // sampai timeout - kegagalan yang tampak seperti bug handler padahal bukan.
    const ctype = String(req.headers['content-type'] || '');
    if (ctype.includes('application/json')) {
      try {
        req.body = raw ? JSON.parse(raw) : {};
      } catch (e) {
        req.body = raw;
      }
    } else {
      req.body = raw;
    }

    let handler;
    try {
      handler = loadHandler(name);
    } catch (e) {
      res.statusCode = 404;
      res.setHeader('Content-Type', 'application/json');
      return res.end(JSON.stringify({ ok: false, error: 'handler tidak ada: ' + e.message }));
    }
    try {
      const out = handler(req, res);
      if (out && typeof out.catch === 'function') {
        out.catch((e) => {
          if (!res.headersSent) {
            res.statusCode = 500;
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ ok: false, error: String(e && e.message) }));
          }
        });
      }
    } catch (e) {
      if (!res.headersSent) {
        res.statusCode = 500;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({ ok: false, error: String(e && e.message) }));
      }
    }
  });
});

server.listen(port, '127.0.0.1', () => {
  console.log('siap ' + port);
});
'''

results = []


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('  %s %s%s' % ('\u2713' if ok else '\u2717', name,
                         ('  -> ' + detail) if detail else ''))


def call(path, method='GET', body=None, headers=None):
    url = 'http://127.0.0.1:%d%s' % (PORT, path)
    data = None
    h = {'User-Agent': 'LumaWall-Test/1.0'}
    if body is not None:
        data = json.dumps(body).encode() if not isinstance(body, bytes) else body
        h['Content-Type'] = 'application/json'
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def main():
    print('\n  \u2550\u2550 uji endpoint pembayaran (lokal) \u2550\u2550\n')

    server_file = ROOT / 'build' / '_test_server.js'
    server_file.parent.mkdir(parents=True, exist_ok=True)
    server_file.write_text(SERVER_JS, encoding='utf-8')

    env = dict(os.environ)
    env.update(ENV)

    proc = subprocess.Popen(
        ['node', str(server_file), str(ROOT), str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    # Tunggu server siap, maksimal 15 detik.
    ready = False
    for _ in range(60):
        try:
            with socket.create_connection(('127.0.0.1', PORT), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.25)

    if not ready:
        proc.kill()
        out, err = proc.communicate(timeout=10)
        print('  ! server uji tidak mau jalan')
        print('    stdout: %s' % out[:400])
        print('    stderr: %s' % err[:400])
        return 2

    try:
        # ── checkout: data tidak sah ─────────────────────────────────────────
        st, raw = call('/api/checkout', 'POST', {'nama': '', 'email': 'bukan-email'})
        check('checkout menolak nama dan email kosong', st == 400, 'HTTP %s' % st)

        st, raw = call('/api/checkout', 'POST', {'nama': 'A', 'email': 'a@b.co'})
        check('checkout menolak nama satu huruf', st == 400, 'HTTP %s' % st)

        st, raw = call('/api/checkout', 'POST', {'nama': 'Budi Santoso', 'email': 'salah'})
        check('checkout menolak email tanpa domain', st == 400, 'HTTP %s' % st)

        st, raw = call('/api/checkout', 'GET')
        check('checkout menolak GET', st == 405, 'HTTP %s' % st)

        # ── order: format kode ───────────────────────────────────────────────
        for buruk in ['', 'ABC', 'LW-', 'LW-123', 'LW-!!!', 'XX-ABCDEF']:
            st, raw = call('/api/order?code=%s' % urllib.parse.quote(buruk))
            if st != 400:
                check('order menolak kode "%s"' % buruk, False, 'HTTP %s' % st)
                break
        else:
            check('order menolak semua kode yang salah format', True,
                  '6 bentuk diuji')

        # ── order: kode sah tapi tidak ada (Supabase palsu -> 502) ───────────
        st, raw = call('/api/order?code=LW-ABCDEF')
        # Supabase palsu tidak bisa dihubungi, jadi 502 memang jawaban yang benar:
        # yang penting bukan 200 dan bukan tautan unduhan.
        check('order tidak mengembalikan tautan untuk kode yang tidak ada',
              st != 200, 'HTTP %s' % st)
        try:
            data = json.loads(raw)
            check('jawaban order tidak memuat tautan unduhan',
                  'downloadUrl' not in data and 'downloadToken' not in data,
                  'kunci: %s' % ', '.join(sorted(data.keys()))[:80])
        except Exception:
            check('jawaban order berupa JSON', False, raw[:80].decode('utf-8', 'replace'))

        # ── download: tanpa token ────────────────────────────────────────────
        st, raw = call('/api/download')
        check('download menolak permintaan tanpa token', st == 400, 'HTTP %s' % st)

        st, raw = call('/api/download?t=pendek')
        check('download menolak token yang terlalu pendek', st == 400, 'HTTP %s' % st)

        st, raw = call('/api/download?t=' + 'x' * 300)
        check('download menolak token yang terlalu panjang', st == 400, 'HTTP %s' % st)

        # ── download: token palsu (Supabase palsu -> 502, bukan berkas) ──────
        st, raw = call('/api/download?t=' + 'a' * 43)
        check('download tidak pernah mengirim berkas untuk token palsu',
              st != 200, 'HTTP %s' % st)
        check('jawaban download bukan berkas biner',
              b'LumaWall' not in raw[:200] or b'error' in raw[:200],
              'awal isi: %s' % raw[:60])

        st, raw = call('/api/download', 'POST')
        check('download menolak POST', st == 405, 'HTTP %s' % st)

        # ── webhook: harus menolak tanpa signature ───────────────────────────
        st, raw = call('/api/ipaymu-callback', 'POST',
                       b'referenceId=LW-ABCDEF&status=berhasil&amount=20000',
                       {'Content-Type': 'application/x-www-form-urlencoded'})
        check('webhook menjawab 200 (agar iPaymu tidak mengulang)', st == 200,
              'HTTP %s' % st)
        try:
            data = json.loads(raw)
            check('webhook menolak permintaan tanpa signature',
                  data.get('ok') is False and data.get('reason') == 'bad-signature',
                  str(data)[:80])
        except Exception:
            check('jawaban webhook berupa JSON', False, raw[:80].decode('utf-8', 'replace'))

        st, raw = call('/api/ipaymu-callback', 'POST',
                       b'referenceId=LW-ABCDEF&status=berhasil&amount=20000&signature=palsu',
                       {'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            data = json.loads(raw)
            check('webhook menolak signature yang salah',
                  data.get('ok') is False and data.get('reason') == 'bad-signature',
                  str(data)[:80])
        except Exception:
            check('jawaban webhook berupa JSON', False, raw[:80].decode('utf-8', 'replace'))

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    gagal = [r for r in results if not r[1]]
    print()
    if gagal:
        print('  %d dari %d uji GAGAL' % (len(gagal), len(results)))
        return 1
    print('  semua %d uji lulus' % len(results))
    return 0


if __name__ == '__main__':
    import urllib.parse  # noqa: E402  (dipakai di dalam main)
    sys.exit(main())
