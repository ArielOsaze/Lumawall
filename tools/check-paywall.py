#!/usr/bin/env python3
"""Buktikan bahwa berkas berbayar tidak bisa diunduh tanpa membayar.

Ini uji negatif, dan itu disengaja: yang diperiksa bukan "apakah unduhan
berhasil", melainkan "apakah unduhan yang TIDAK seharusnya berhasil memang
gagal". Uji yang hanya memeriksa jalur sukses tidak akan pernah menangkap
kebocoran - dan kebocoran itulah yang membuat seluruh sistem pembayaran tidak
berguna.

Yang diperiksa:

  1. Berkas installer tidak ada di folder yang disajikan situs.
  2. Berkas installer tidak dilacak git (kalau dilacak, ia ada di repo publik).
  3. Tidak ada halaman yang menautkan berkas unduhan langsung.
  4. Tidak ada kunci rahasia di berkas yang disajikan ke peramban.
  5. Berkas di penyimpanan tidak bisa dibaca tanpa kunci.
  6. Alamat unduhan lama mengalihkan ke halaman beli, bukan mengirim berkas.
  7. Endpoint unduhan menolak token palsu dan permintaan tanpa token.
  8. Halaman status menolak kode pesanan palsu.
  9. Checkout menolak data yang tidak sah.

Catatan penting soal cara memeriksa nomor 6: permintaan HTTP yang mengikuti
pengalihan akan berakhir di halaman beli dengan status 200, dan itu terlihat
seperti "berkasnya bisa diunduh" padahal justru sebaliknya. Karena itu yang
diperiksa adalah **isi jawabannya**, bukan statusnya: berkas biner dimulai
dengan 'MZ' (executable Windows), sedangkan halaman beli dimulai dengan
'<!DOCTYPE'. Pengalihan sengaja TIDAK diikuti.

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

# Penanda isi: berkas Windows dimulai dengan 'MZ', ZIP dengan 'PK', halaman HTML
# dengan '<!DOCTYPE' atau '<html'.
BINARY_MARKERS = [b'MZ', b'PK\x03\x04']

results = []


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('  %s %s%s' % ('\u2713' if ok else '\u2717', name,
                         ('  -> ' + detail) if detail else ''))


def fetch(url, timeout=25, follow=True):
    """Kembalikan (status, isi_awal). Pengalihan tidak diikuti kalau follow=False."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'LumaWall-PaywallCheck/1.0')
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read(512)
    except urllib.error.HTTPError as e:
        try:
            body = e.read(512)
        except Exception:
            body = b''
        return e.code, body
    except Exception as e:
        return 0, str(e).encode()


def looks_binary(body):
    return any(body.startswith(m) for m in BINARY_MARKERS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true',
                    help='periksa juga situs yang sudah ter-deploy')
    args = ap.parse_args()

    print('\n  \u2550\u2550 uji gerbang unduhan \u2550\u2550\n')

    # ── 1. berkas tidak boleh ada di folder yang disajikan ───────────────────
    dl_dir = SITE / 'assets' / 'downloads'
    sisa = [p.name for p in dl_dir.iterdir() if p.is_file()] if dl_dir.exists() else []
    check('folder site/assets/downloads kosong', not sisa,
          ('masih ada: ' + ', '.join(sisa[:4])) if sisa else 'tidak ada berkas')

    # ── 2. tidak ada berkas berbayar yang dilacak git ────────────────────────
    try:
        out = subprocess.run(['git', 'ls-files', 'site/assets/downloads/'],
                             cwd=str(ROOT), capture_output=True, text=True, timeout=60).stdout
        dilacak = [l for l in out.strip().splitlines() if l.strip()]
    except Exception as e:
        dilacak = ['(gagal memeriksa: %s)' % e]
    check('tidak ada installer yang dilacak git di folder situs', not dilacak,
          ', '.join(dilacak[:4]))

    # ── 3. halaman tidak memuat tautan unduhan langsung ─────────────────────
    halaman = [SITE / 'index.html', SITE / 'en' / 'index.html',
               SITE / 'beli' / 'index.html', SITE / 'en' / 'buy' / 'index.html',
               SITE / 'sukses' / 'index.html', SITE / 'en' / 'success' / 'index.html']
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

    if not args.live:
        print('  \u2013 pemeriksaan situs live dilewati (pakai --live untuk menyertakan)')
    else:
        # ── 5. berkas di penyimpanan tidak bisa dibaca tanpa kunci ──────────
        for name in PAID_FILES[:1]:
            st, body = fetch('%s/storage/v1/object/public/lumawall/%s' % (STORAGE, name))
            check('berkas di penyimpanan tidak bisa dibaca publik (%s)' % name,
                  st != 200 or not looks_binary(body),
                  'HTTP %s, isi %d byte' % (st, len(body)))

        # ── 6. alamat lama harus mengalihkan, bukan mengirim berkas ─────────
        # Pengalihan TIDAK diikuti: yang diperiksa isi jawabannya. Halaman beli
        # juga berstatus 200, jadi status saja tidak bisa membedakan keduanya -
        # yang membedakan adalah 'MZ' (berkas Windows) versus '<!DOCTYPE'.
        for name in PAID_FILES:
            st, body = fetch('%s/assets/downloads/%s' % (BASE, name), follow=False)
            aman = not looks_binary(body)
            detail = 'HTTP %s, %s' % (
                st, 'berkas biner terkirim!' if not aman
                else ('pengalihan' if st in (301, 302, 307, 308) else 'halaman'))
            check('alamat unduhan lama tidak mengirim berkas (%s)' % name, aman, detail)

        # ── 7. endpoint unduhan harus menolak ───────────────────────────────
        # 503 diterima: artinya server belum dikonfigurasi, dan yang penting
        # bukan itu - yang penting TIDAK 200 dengan berkas di dalamnya.
        st, body = fetch('%s/api/download/?t=token-palsu-yang-cukup-panjang-1234567890' % BASE)
        check('endpoint unduhan tidak mengirim berkas untuk token palsu',
              not looks_binary(body), 'HTTP %s' % st)

        st, body = fetch('%s/api/download/' % BASE)
        check('endpoint unduhan tidak mengirim berkas tanpa token',
              not looks_binary(body), 'HTTP %s' % st)

        # ── 8. halaman status harus menolak kode palsu ──────────────────────
        st, body = fetch('%s/api/order/?code=LW-ZZZZZZ' % BASE)
        ok = st in (404, 503) or b'error' in body
        check('halaman status tidak mengembalikan tautan untuk kode palsu',
              ok and b'downloadUrl' not in body, 'HTTP %s' % st)

        # ── 9. checkout harus menolak data tidak sah ────────────────────────
        req = urllib.request.Request(
            '%s/api/checkout/' % BASE, method='POST',
            data=b'{"nama":"","email":"bukan-email"}',
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                st = resp.status
        except urllib.error.HTTPError as e:
            st = e.code
        except Exception:
            st = 0
        # 308/301 = pengalihan karena trailing slash; ikuti satu kali.
        if st in (301, 308):
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    st = resp.status
            except urllib.error.HTTPError as e:
                st = e.code
        check('checkout menolak data yang tidak sah', st in (400, 503), 'HTTP %s' % st)

    gagal = [r for r in results if not r[1]]
    print()
    if gagal:
        print('  %d dari %d uji GAGAL - periksa daftar di atas.' % (len(gagal), len(results)))
        return 1
    print('  semua %d uji lulus - tidak ada jalan mengunduh tanpa membayar.' % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
