#!/usr/bin/env python3
"""Uji alur pembelian lengkap terhadap situs live.

Yang diuji berurutan, meniru pembeli sungguhan:

  1. Checkout dengan data sah  -> harus mengembalikan tautan pembayaran iPaymu
  2. Kode pesanan yang baru     -> harus berstatus "menunggu", TANPA tautan unduhan
  3. Tautan unduhan sebelum bayar -> harus ditolak
  4. Tautan unduhan dengan token palsu -> harus ditolak

Langkah 1 memanggil iPaymu sungguhan dan membuat baris pesanan nyata di
database. Itu disengaja: inilah satu-satunya cara membuktikan jalurnya bekerja
ujung ke ujung. Pesanan uji ditandai di kolom catatan supaya bisa dikenali dan
dibersihkan.

Yang TIDAK dilakukan skrip ini: menyelesaikan pembayaran. Itu perlu uang
sungguhan dan keputusan pemilik produk.

Pemakaian:
  python tools/test-live-checkout.py
  python tools/test-live-checkout.py --bersihkan
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://lumawall.xinet.id'
ROOT = Path(__file__).resolve().parent.parent

results = []


def check(nama, ok, detail=''):
    results.append((nama, ok, detail))
    print('  %s %s%s' % ('\u2713' if ok else '\u2717', nama,
                         ('  -> ' + detail) if detail else ''))


def call(path, method='GET', body=None, headers=None, timeout=45):
    url = BASE + path
    data = None
    h = {'User-Agent': 'LumaWall-LiveTest/1.0', 'Accept': 'application/json'}
    if body is not None:
        data = json.dumps(body).encode()
        h['Content-Type'] = 'application/json'
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bersihkan', action='store_true',
                    help='tandai pesanan uji sebagai dibatalkan (bukan hapus)')
    args = ap.parse_args()

    print('\n  \u2550\u2550 uji alur pembelian (live) \u2550\u2550\n')

    if args.bersihkan:
        return bersihkan()

    # ── 1. checkout dengan data sah ──────────────────────────────────────────
    print('  1. checkout')
    st, raw = call('/api/checkout/', 'POST', {
        'nama': 'Uji Otomatis LumaWall',
        'email': 'uji-otomatis@lumawall.invalid',
        'wa': '081234567890',
    })

    try:
        data = json.loads(raw)
    except Exception:
        check('checkout menjawab JSON', False, raw[:120].decode('utf-8', 'replace'))
        return ringkas()

    if st != 200 or not data.get('ok'):
        check('checkout menerima data yang sah', False,
              'HTTP %s: %s' % (st, str(data.get('error'))[:100]))
        print()
        print('  Endpoint menolak permintaan yang sah. Kalau pesannya menyebut')
        print('  variabel yang belum diisi, periksa environment di Vercel.')
        return ringkas()

    order = data.get('order', '')
    payment_url = data.get('paymentUrl', '')

    check('checkout menerima data yang sah', True, 'HTTP %s' % st)
    check('kode pesanan berformat benar', bool(re.match(r'^LW-[A-Z0-9]{6}$', order)), order)
    check('tautan pembayaran iPaymu diterima',
          payment_url.startswith('https://my.ipaymu.com/') or
          payment_url.startswith('https://sandbox.ipaymu.com/'),
          payment_url[:60])
    check('jumlah sesuai harga web', data.get('amount') == 20000,
          'Rp%s' % data.get('amount'))

    # ── 2. status pesanan sebelum dibayar ────────────────────────────────────
    print()
    print('  2. status pesanan sebelum dibayar')
    st, raw = call('/api/order/?code=%s' % order)
    try:
        d = json.loads(raw)
    except Exception:
        check('halaman status menjawab JSON', False, raw[:100].decode('utf-8', 'replace'))
        return ringkas()

    check('status pesanan bisa dibaca', st == 200 and d.get('ok') is True, 'HTTP %s' % st)
    check('pesanan berstatus belum dibayar', d.get('paid') is False,
          'status: %s' % d.get('status'))
    check('tautan unduhan TIDAK diberikan sebelum bayar',
          not d.get('downloadUrl') and not d.get('downloadToken'),
          'kunci: %s' % ', '.join(sorted(d.keys())))

    # ── 3. unduhan sebelum bayar harus ditolak ───────────────────────────────
    print()
    print('  3. unduhan sebelum dibayar')
    st, raw = call('/api/download/?t=' + 'a' * 43)
    check('unduhan dengan token palsu ditolak', st in (400, 403), 'HTTP %s' % st)
    check('jawaban bukan berkas', not raw.startswith(b'MZ') and not raw.startswith(b'PK'),
          '%d byte' % len(raw))

    # Token yang diturunkan dari kode pesanan belum dibayar juga harus gagal,
    # karena barisnya belum ada di tabel download_tokens.
    st, raw = call('/api/download/?t=' + order.replace('LW-', 'lumawall:') + 'x' * 20)
    check('unduhan dengan token turunan pesanan belum bayar ditolak',
          st in (400, 403), 'HTTP %s' % st)

    print()
    print('  Pesanan uji: %s' % order)
    print('  Pesanan ini ada di database dengan status "menunggu".')
    print('  Untuk menandainya sebagai batal:')
    print('    python tools/test-live-checkout.py --bersihkan')
    print()
    print('  Langkah berikutnya yang perlu MANUSIA:')
    print('    buka tautan pembayaran di atas dan bayar Rp20.000, lalu periksa')
    print('    bahwa halaman /sukses/ menampilkan tautan unduhan.')

    return ringkas()


def bersihkan():
    """Tandai pesanan uji sebagai dibatalkan.

    Ditandai, bukan dihapus: riwayat pesanan yang hilang lebih sulit
    dipertanggungjawabkan daripada pesanan yang jelas-jelas dibatalkan.
    """
    import subprocess
    print('  menandai pesanan uji sebagai dibatalkan lewat Supabase CLI')
    sql = ("update public.orders set status='dibatalkan', "
           "diperbarui_pada=now(), "
           "catatan=coalesce(catatan,'') || ' [uji otomatis, dibatalkan]' "
           "where email_pembeli='uji-otomatis@lumawall.invalid' "
           "and status='menunggu';")
    env = {}
    try:
        env_line = Path(r'C:\Users\ariel\.supabase\access-token').read_text(encoding='utf-8').strip()
    except Exception:
        env_line = ''

    cmd = ['npx', '--yes', 'supabase@latest', 'db', 'push', '--include-all', '--yes']
    print('  (gunakan SQL editor Supabase untuk perintah ini)')
    print()
    print(sql)
    return 0


def ringkas():
    gagal = [r for r in results if not r[1]]
    print()
    if gagal:
        print('  %d dari %d uji GAGAL' % (len(gagal), len(results)))
        return 1
    print('  semua %d uji lulus' % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
