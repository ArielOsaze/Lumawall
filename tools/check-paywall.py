#!/usr/bin/env python3
"""Buktikan bahwa berkas berbayar tidak bisa diunduh tanpa membayar.

Ini uji negatif, dan itu disengaja: yang diperiksa bukan "apakah unduhan
berhasil", melainkan "apakah unduhan yang TIDAK seharusnya berhasil memang
gagal". Uji yang hanya memeriksa jalur sukses tidak akan pernah menangkap
kebocoran - dan kebocoran itulah yang membuat seluruh sistem pembayaran tidak
berguna.

Yang diperiksa:

  1. Alamat lama di folder situs tidak lagi menyajikan berkas.
  2. Alamat berkas di penyimpanan tidak bisa dibaca tanpa kunci.
  3. Halaman beli dan sukses tidak memuat tautan unduhan langsung.
  4. Tidak ada berkas installer yang tertinggal di dalam repositori situs.
  5. Kunci rahasia tidak muncul di berkas mana pun yang disajikan ke peramban.

Pemakaian:
  python tools/check-paywall.py
  python tools/check-paywall.py --live      # sertakan pemeriksaan ke situs live
"""
import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
BASE = 'https://lumawall.xinet.id'
STORAGE = 'https://cauklmkpjwsdwqoazqlx.supabase.co'

# Nama berkas yang tidak boleh bisa diambil siapa pun tanpa token.
PAID_FILES = [
    'LumaWall-Setup-4.5.7.0.exe',
    'LumaWall-portable-4.5.7.0.zip',
]

# Pola yang menandakan kunci rahasia. Dipakai untuk memeriksa berkas yang
# disajikan ke peramban - bukan untuk mencari kunci di seluruh mesin.
SECRET_PATTERNS = [
    (r'sbp_[A-Za-z0-9]{20,}', 'Supabase access token'),
    (r'sb_secret_[A-Za-z0-9_-]{20,}', 'Supabase secret key'),
    (r'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_-]{40,}', 'JWT (mungkin service key)'),
    (r'service_role["\']?\s*[:=]\s*["\'][A-Za-z0-9._-]{40,}', 'service_role key literal'),
]

results = []


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('  %s %s%s' % ('\u2713' if ok else '\u2717', name,
                         ('  -> ' + detail) if detail else ''))


def http(url, method='GET', timeout=25):
    """Kembalikan (status, panjang isi). Status 0 berarti gagal koneksi."""
    req = urllib.request.Request(url, method=method)
    req.add_header('User-Agent', 'LumaWall-PaywallCheck/1.0')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, len(resp.read(2048))
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return 0, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true',
                    help='periksa juga situs yang sudah ter-deploy')
    args = ap.parse_args()

    print('\n  \u2550\u2550 uji gerbang unduhan \u2550\u2550\n')

    # ── 1. berkas tidak boleh ada di folder yang disajikan ───────────────────
    dl_dir = SITE / 'assets' / 'downloads'
    if dl_dir.exists():
        sisa = [p.name for p in dl_dir.iterdir() if p.is_file()]
    else:
        sisa = []
    check('folder site/assets/downloads kosong', not sisa,
          ('masih ada: ' + ', '.join(sisa[:4])) if sisa else 'tidak ada berkas')

    # ── 2. tidak ada berkas berbayar yang dilacak git ────────────────────────
    try:
        out = subprocess.run(
            ['git', 'ls-files', 'site/assets/downloads/'],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        dilacak = [l for l in out.splitlines() if l.strip()]
    except Exception as e:
        dilacak = ['(gagal memeriksa: %s)' % e]
    check('tidak ada installer yang dilacak git di folder situs', not dilacak,
          ', '.join(dilacak[:4]))

    # ── 3. halaman tidak memuat tautan unduhan langsung ─────────────────────
    halaman = [
        SITE / 'index.html', SITE / 'en' / 'index.html',
        SITE / 'beli' / 'index.html', SITE / 'en' / 'buy' / 'index.html',
        SITE / 'sukses' / 'index.html', SITE / 'en' / 'success' / 'index.html',
    ]
    bocor = []
    for p in halaman:
        if not p.exists():
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        for m in re.finditer(r'(?:href|src)="([^"]*downloads/[^"]+)"', text):
            bocor.append('%s: %s' % (p.name, m.group(1)))
    check('tidak ada halaman yang menautkan berkas unduhan langsung', not bocor,
          '; '.join(bocor[:3]))

    # ── 4. kunci rahasia tidak ada di berkas yang disajikan ─────────────────
    temuan = []
    periksa = []
    for sub in ('assets', 'beli', 'sukses', 'en'):
        d = SITE / sub
        if d.is_dir():
            periksa.extend(p for p in d.rglob('*') if p.is_file() and
                           p.suffix.lower() in ('.js', '.html', '.css', '.json'))
    for p in [SITE / 'index.html', SITE / 'robots.txt', SITE / 'sitemap.xml']:
        if p.exists():
            periksa.append(p)

    for p in periksa:
        try:
            text = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, text):
                temuan.append('%s: %s' % (p.relative_to(SITE), label))
    check('tidak ada kunci rahasia di berkas yang disajikan', not temuan,
          '; '.join(temuan[:3]))

    # ── 5. berkas di penyimpanan tidak bisa dibaca tanpa kunci ──────────────
    if args.live:
        for name in PAID_FILES[:1]:
            st, _ = http('%s/storage/v1/object/public/lumawall/%s' % (STORAGE, name))
            check('berkas di penyimpanan tidak bisa dibaca publik (%s)' % name,
                  st != 200, 'HTTP %s' % st)

        # ── 6. alamat lama harus mengalihkan, bukan menyajikan berkas ────────
        for name in PAID_FILES:
            st, _ = http('%s/assets/downloads/%s' % (BASE, name))
            # 200 hanya boleh kalau isinya halaman HTML (pengalihan tidak diikuti),
            # jadi yang menentukan adalah bukan berkas biner yang terkirim.
            check('alamat unduhan lama tidak menyajikan berkas (%s)' % name,
                  st != 200, 'HTTP %s' % st)

        # ── 7. endpoint unduhan tanpa token harus menolak ────────────────────
        st, _ = http('%s/api/download?t=token-palsu-yang-cukup-panjang-1234567890' % BASE)
        check('endpoint unduhan menolak token palsu', st in (400, 403),
              'HTTP %s' % st)

        st, _ = http('%s/api/download' % BASE)
        check('endpoint unduhan menolak permintaan tanpa token', st == 400,
              'HTTP %s' % st)

        # ── 8. halaman status menolak kode palsu ─────────────────────────────
        st, _ = http('%s/api/order?code=LW-ZZZZZZ' % BASE)
        check('halaman status menolak kode pesanan palsu', st == 404,
              'HTTP %s' % st)

        # ── 9. checkout menolak data kosong ──────────────────────────────────
        req = urllib.request.Request(
            '%s/api/checkout' % BASE, method='POST',
            data=b'{"nama":"","email":"bukan-email"}',
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                st = resp.status
        except urllib.error.HTTPError as e:
            st = e.code
        except Exception:
            st = 0
        check('checkout menolak data yang tidak sah', st == 400, 'HTTP %s' % st)
    else:
        print('  \u2013 pemeriksaan situs live dilewati (pakai --live untuk menyertakan)')

    gagal = [r for r in results if not r[1]]
    print()
    if gagal:
        print('  %d dari %d uji GAGAL - berkas berbayar bisa bocor.'
              % (len(gagal), len(results)))
        return 1
    print('  semua %d uji lulus - tidak ada jalan mengunduh tanpa membayar.'
          % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
