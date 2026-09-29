#!/usr/bin/env python3
"""Buktikan harga naik otomatis setelah 15 Oktober 2026.

Ini uji yang paling penting untuk fitur ini, dan yang paling mudah dilupakan:
semua orang menguji bahwa promo BERJALAN hari ini. Yang tidak diuji adalah
apakah promo benar-benar BERHENTI pada tanggalnya - dan justru itu yang gagal
diam-diam, karena tidak ada yang memperhatikan sampai ada pembeli membayar
Rp10.000 untuk produk yang seharusnya Rp18.000.

Cara menguji tanggal yang belum tiba tanpa menunggu: jam server dipalsukan.
Fungsi `currentPrice(now)` menerima waktu sebagai argumen justru supaya bisa
diuji begini - kalau ia membaca jam sendiri, satu-satunya cara mengujinya
adalah menunggu sampai Oktober.

Pemakaian:
  python tools/check-price-schedule.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Setiap kasus: (waktu uji dalam WIB, harga yang diharapkan, promo diharapkan,
# keterangan). Waktu di WIB (UTC+7) karena itulah zona pembeli.
KASUS = [
    ('2026-09-29T23:35:00+07:00', 10000, True, 'hari ini - promo berjalan'),
    ('2026-10-01T00:00:00+07:00', 10000, True, 'awal Oktober'),
    ('2026-10-15T00:00:00+07:00', 10000, True, 'pagi di hari terakhir promo'),
    ('2026-10-15T23:59:00+07:00', 10000, True, 'satu menit sebelum tengah malam'),
    ('2026-10-15T23:59:59+07:00', 10000, True, 'detik terakhir promo'),
    ('2026-10-16T00:00:00+07:00', 18000, False, 'TENGAH MALAM - harga harus naik'),
    ('2026-10-16T00:00:01+07:00', 18000, False, 'satu detik setelah promo'),
    ('2026-10-20T12:00:00+07:00', 18000, False, 'seminggu setelah promo'),
    ('2027-01-01T00:00:00+07:00', 18000, False, 'tahun berikutnya'),
]

# Batas waktu dalam UTC, untuk memastikan zona waktu tidak salah tafsir.
# 16 Oktober 00:00 WIB = 15 Oktober 17:00 UTC. Kalau kode memakai UTC
# apa adanya, promo akan berakhir 7 jam terlalu cepat - dan itu berarti
# pembeli di Indonesia masih melihat harga promo padahal sudah ditagih penuh.
KASUS_UTC = [
    ('2026-10-15T16:59:00+00:00', 10000, True, '15 Okt 23:59 WIB - masih promo'),
    ('2026-10-15T17:00:00+00:00', 18000, False, '16 Okt 00:00 WIB - sudah naik'),
]


def uji(kasus):
    """Jalankan currentPrice() di Node dengan waktu yang diberikan."""
    daftar = json.dumps([k[0] for k in kasus])
    skrip = (
        "const { currentPrice } = require('./site/api/_lib.js');"
        "const waktu = %s;"
        "const hasil = waktu.map(function (w) {"
        "  const h = currentPrice(new Date(w));"
        "  return { amount: h.amount, promo: h.promo };"
        "});"
        "console.log(JSON.stringify(hasil));" % daftar
    )
    r = subprocess.run(['node', '-e', skrip], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print('  ! gagal menjalankan Node:')
        print('   ', (r.stderr or '')[:300])
        return None
    try:
        return json.loads(r.stdout.strip())
    except Exception as e:
        print('  ! keluaran tidak terbaca:', e, r.stdout[:200])
        return None


def jalankan(nama, kasus):
    print('  \u2550\u2550 %s \u2550\u2550' % nama)
    hasil = uji(kasus)
    if hasil is None:
        return 1

    gagal = 0
    for (waktu, harga_harap, promo_harap, ket), h in zip(kasus, hasil):
        harga_ok = h['amount'] == harga_harap
        promo_ok = h['promo'] == promo_harap
        ok = harga_ok and promo_ok
        if not ok:
            gagal += 1
        tanda = '\u2713' if ok else '\u2717'
        print('     %s %-32s Rp%-7s promo=%-5s  %s'
              % (tanda, waktu[11:19] + ' ' + waktu[-6:],
                 '{:,}'.format(h['amount']).replace(',', '.'),
                 str(h['promo']), ket))
        if not ok:
            print('        diharapkan Rp%s promo=%s'
                  % ('{:,}'.format(harga_harap).replace(',', '.'), promo_harap))
    print()
    return gagal


def main():
    print()
    print('  \u2550\u2550 jadwal harga LumaWall \u2550\u2550')
    print()

    gagal = jalankan('waktu Indonesia (WIB)', KASUS)
    gagal += jalankan('dinyatakan dalam UTC', KASUS_UTC)

    if gagal:
        print('  %d kasus GAGAL - jadwal harganya salah.' % gagal)
        return 1

    print('  semua kasus lulus:')
    print('    \u2022 promo Rp10.000 berlaku sampai 15 Oktober 2026 pukul 23:59:59 WIB')
    print('    \u2022 harga naik ke Rp18.000 tepat pada 16 Oktober 2026 pukul 00:00 WIB')
    print('    \u2022 batasnya memakai jam Jakarta, bukan UTC')
    return 0


if __name__ == '__main__':
    sys.exit(main())
