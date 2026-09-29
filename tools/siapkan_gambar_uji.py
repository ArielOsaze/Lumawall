#!/usr/bin/env python3
"""Sediakan gambar uji untuk pemeriksaan wallpaper statis.

Pemeriksaan wallpaper statis butuh gambar yang warnanya diketahui, supaya bisa
dibedakan "wallpapernya benar-benar tampil" dari "layarnya kebetulan terang".
Gambar itu dulu dibuat manual, dan pemeriksaannya langsung gagal begitu gambar
itu dihapus - kegagalan yang tidak ada hubungannya dengan yang sedang diuji.

Sekarang gambar itu dibuat oleh modul ini, jadi pemeriksaan selalu bisa berjalan.

Warnanya sengaja dipilih agar tidak mungkin tertukar dengan apa pun: kuning
terang dengan persegi hijau, jauh dari warna desktop, tema gelap aplikasi, dan
warna wallpaper mana pun yang biasa dipakai.

Pemakaian:
  python tools/siapkan_gambar_uji.py            # buat kalau belum ada
  python tools/siapkan_gambar_uji.py --hapus    # bersihkan
"""
import argparse
import sys
from pathlib import Path

TUJUAN = Path('C:/Users/ariel/AppData/Local/LumaWall/Wallpapers/uji-statis-terang.png')

# Warna gambar uji. Dipakai juga oleh pemeriksa untuk memastikan yang terlihat
# benar-benar gambar ini.
KUNING = (240, 200, 60)
HIJAU = (70, 200, 140)
UKURAN = (1366, 768)


def pastikan(lebar=None, tinggi=None):
    """Buat gambar uji kalau belum ada. Kembalikan jalurnya."""
    if TUJUAN.exists():
        return TUJUAN

    TUJUAN.parent.mkdir(parents=True, exist_ok=True)
    w, h = lebar or UKURAN[0], tinggi or UKURAN[1]

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Pillow tidak selalu ada. Berkas PNG bisa ditulis langsung, dan cara itu
        # dipakai supaya pemeriksaan tidak bergantung pada paket tambahan.
        _tulis_png_polos(TUJUAN, w, h)
        return TUJUAN

    gambar = Image.new('RGB', (w, h), KUNING)
    kuas = ImageDraw.Draw(gambar)
    kuas.rectangle([int(w * 0.07), int(h * 0.13), int(w * 0.93), int(h * 0.87)], fill=HIJAU)
    gambar.save(TUJUAN)
    return TUJUAN


def _tulis_png_polos(jalur, lebar, tinggi):
    """PNG dua warna tanpa Pillow.

    Hanya cukup untuk gambar uji: seluruh badan gambar satu warna, jadi setiap
    baris pikselnya identik dan bisa diulang. Formatnya PNG 8-bit RGB, tanpa
    kompresi - sengaja, supaya tidak perlu pustaka zlib untuk membuatnya.
    """
    import struct
    import zlib

    baris = b'\x00' + bytes(HIJAU) * lebar
    mentah = baris * tinggi

    def potongan(jenis, data):
        return (struct.pack('>I', len(data)) + jenis + data
                + struct.pack('>I', zlib.crc32(jenis + data) & 0xFFFFFFFF))

    isi = (b'\x89PNG\r\n\x1a\n'
           + potongan(b'IHDR', struct.pack('>IIBBBBB', lebar, tinggi, 8, 2, 0, 0, 0))
           + potongan(b'IDAT', zlib.compress(mentah, 1))
           + potongan(b'IEND', b''))
    jalur.write_bytes(isi)


def hapus():
    if TUJUAN.exists():
        TUJUAN.unlink()
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hapus', action='store_true')
    args = ap.parse_args()

    if args.hapus:
        print('  gambar uji dihapus' if hapus() else '  gambar uji memang tidak ada')
        return 0

    jalur = pastikan()
    print('  gambar uji siap: %s' % jalur)
    return 0


if __name__ == '__main__':
    sys.exit(main())
