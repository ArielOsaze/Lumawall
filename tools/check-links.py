#!/usr/bin/env python3
"""Periksa setiap tautan internal di situs, cari yang menuju halaman tidak ada.

Tautan bahasa adalah yang paling mudah salah dan paling sulit terlihat:
keduanya terlihat benar di halaman mana pun, dan baru ketahuan rusak ketika ada
pengunjung yang menekannya. Situs ini punya delapan halaman dalam dua bahasa
dengan kedalaman berbeda, jadi "naik satu folder" berarti hal yang berbeda di
tiap halaman - dan itulah sumber kesalahannya.

Pemakaian:
  python tools/check-links.py
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
BASE = 'https://lumawall.xinet.id'

# Alamat luar tidak diperiksa: uji ini tentang struktur folder, bukan tentang
# apakah pihak ketiga sedang hidup.
def internal(target):
    if not target:
        return False
    if target.startswith(('http://', 'https://')):
        return target.startswith(BASE)
    return not target.startswith(('mailto:', 'tel:', '#', 'javascript:', 'data:'))


def ke_jalur(halaman, target):
    """Ubah target relatif/absolut jadi jalur berkas di dalam site/."""
    if target.startswith(BASE):
        target = target[len(BASE):] or '/'
    p = urlparse(target)
    jalur = unquote(p.path)
    if jalur.startswith('/'):
        hasil = SITE / jalur.lstrip('/')
    else:
        hasil = (halaman.parent / jalur).resolve()
    if p.path.endswith('/') or hasil.is_dir():
        hasil = hasil / 'index.html'
    return hasil


def main():
    print()
    print('  \u2550\u2550 memeriksa tautan internal \u2550\u2550')
    print()

    halaman = sorted(SITE.rglob('*.html'))
    rusak = []
    diperiksa = 0

    for hal in halaman:
        teks = hal.read_text(encoding='utf-8', errors='replace')
        relatif = hal.relative_to(SITE).as_posix()

        for m in re.finditer(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', teks):
            target = m.group(1).strip()
            if not internal(target):
                continue
            diperiksa += 1
            tujuan = ke_jalur(hal, target)
            if not tujuan.exists():
                rusak.append((relatif, target, str(tujuan.relative_to(SITE)) if SITE in tujuan.parents or tujuan.parent == SITE else str(tujuan)))

    print('  %d halaman, %d tautan internal diperiksa' % (len(halaman), diperiksa))
    print()

    if not rusak:
        print('  \u2713 semua tautan internal menuju berkas yang ada')
        return 0

    # Kelompokkan per halaman supaya mudah dibaca.
    sekarang = None
    for hal, target, tujuan in rusak:
        if hal != sekarang:
            print('  %s' % hal)
            sekarang = hal
        print('     \u2717 %-34s -> %s' % (target, tujuan))
    print()
    print('  %d tautan rusak.' % len(rusak))
    return 1


if __name__ == '__main__':
    sys.exit(main())
