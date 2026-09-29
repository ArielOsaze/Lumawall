#!/usr/bin/env python3
"""Ringkasan status: apa yang sudah terbukti, apa yang belum.

Menjalankan semua pemeriksaan yang tidak memerlukan kredensial, lalu
mencetak satu tabel ringkas. Tujuannya supaya "sudah selesai" selalu bisa
dibedakan dari "belum diuji", dan supaya tidak ada klaim tanpa bukti.

Pemakaian:
  python tools/status.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (nama, perintah, perlu_kredensial)
CHECKS = [
    ('gerbang unduhan', ['python', 'tools/check-paywall.py'], False),
    ('gerbang unduhan (live)', ['python', 'tools/check-paywall.py', '--live'], False),
    ('endpoint pembayaran', ['python', 'tools/test-endpoints.py'], False),
    ('halaman beli (2 bahasa)', ['python', 'tools/make_en_pages.py'], False),
    ('tata letak halaman beli', ['python', 'tools/check-buy-layout.py'], False),
    ('klaim token (SQL)', None, True),           # hanya lewat MCP
    ('kredensial iPaymu', None, True),           # butuh kunci produksi
    ('pembayaran sungguhan', None, True),        # butuh transaksi nyata
]


def run(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, '(timeout)'
    except FileNotFoundError as e:
        return 127, str(e)


def main():
    print()
    print('  \u2550\u2550 status LumaWall \u2550\u2550')
    print()

    lulus = 0
    gagal = 0
    belum = 0

    for nama, cmd, perlu_kred in CHECKS:
        if cmd is None:
            print('  \u2013  %-26s belum diuji (butuh kredensial / transaksi)' % nama)
            belum += 1
            continue

        code, out = run(cmd)

        # Ambil baris terakhir yang berarti sebagai ringkasan.
        baris = [l.strip() for l in out.splitlines() if l.strip()]
        ringkas = ''
        for l in reversed(baris):
            if 'lulus' in l or 'gagal' in l or 'masalah' in l or 'bersih' in l:
                ringkas = l.lstrip('\u2713\u2717\u2013 ').strip()
                break
        if not ringkas and baris:
            ringkas = baris[-1][:70]

        if code == 0:
            print('  \u2713  %-26s %s' % (nama, ringkas))
            lulus += 1
        else:
            print('  \u2717  %-26s %s' % (nama, ringkas or ('keluar dengan kode %d' % code)))
            gagal += 1

    print()
    print('  %d lulus, %d gagal, %d belum diuji' % (lulus, gagal, belum))
    print()
    if belum:
        print('  Yang belum diuji memerlukan hal yang tidak ada di mesin ini:')
        print('    \u2022 klaim token  : tabel Supabase proyek LumaWall (butuh migrasi)')
        print('    \u2022 iPaymu       : kunci produksi (sudah terverifikasi valid sebelumnya)')
        print('    \u2022 pembayaran   : satu transaksi nyata Rp20.000')
        print()
    return 1 if gagal else 0


if __name__ == '__main__':
    sys.exit(main())
