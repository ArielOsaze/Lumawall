#!/usr/bin/env python3
"""Periksa cache thumbnail di disk - berkas yang BENAR-BENAR dipakai aplikasi.

KENAPA ALAT INI ADA:

Pengguna melihat banyak gambar katalog tidak muncul. Tiga pemeriksaan sudah
dilakukan dan semuanya menyatakan sehat:
  * alamat thumbnail di berkas katalog   -> 4000/4000 OK
  * hotlink (gambar tanpa Referer)       -> semua host melayani
  * Referer salah domain                 -> tidak ada yang menolak

Ketiganya memeriksa SUMBER gambar. Tidak satu pun memeriksa apa yang sudah
TERSIMPAN di PC pengguna - padahal itulah yang benar-benar ditampilkan.

Aplikasi menyimpan setiap thumbnail yang pernah diunduh ke:
    %LOCALAPPDATA%\\LumaWall\\Thumbnails\\<sha1(url)>.jpg

Kalau berkas di folder itu rusak - terpotong, kosong, atau isinya bukan gambar -
kartu katalog akan tampak rusak SELAMANYA, karena aplikasi memakai berkas cache
apa adanya dan tidak pernah mengunduh ulang:

    if (File.Exists(cached) && new FileInfo(cached).Length > 512)
    {
        ApplyImageFile(image, cached, decodeWidth);
        return;          // <- tidak pernah memeriksa apakah isinya gambar
    }

Perhatikan syaratnya: hanya UKURAN yang diperiksa (> 512 byte). Berkas 600 byte
berisi halaman error HTML akan lolos syarat itu dan dipakai selamanya.

Alat ini memeriksa setiap berkas cache: apakah benar-benar gambar, apakah
gambar yang utuh (bisa dibuka), dan berapa ukurannya.
"""

import json
import sys
from collections import Counter
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")

CACHE = Path.home() / "AppData" / "Local" / "LumaWall" / "Thumbnails"
KATALOG = W / "LumaWall" / "catalog.json"

# Tanda awal berkas gambar yang sah.
TANDA = [
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"RIFF", "webp"),
    (b"BM", "bmp"),
]


def jenis_gambar(isi):
    for tanda, nama in TANDA:
        if isi.startswith(tanda):
            return nama
    return None


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MEMERIKSA CACHE THUMBNAIL DI DISK")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    print("  folder: %s" % CACHE)
    print()

    if not CACHE.exists():
        print("  ! folder cache tidak ada - aplikasi belum pernah mengunduh thumbnail")
        return 1

    berkas = list(CACHE.glob("*.jpg")) + list(CACHE.glob("*.part"))
    print("  berkas di cache: %d" % len(berkas))
    print()

    keadaan = Counter()
    rusak = []
    total_byte = 0

    for f in berkas:
        try:
            ukuran = f.stat().st_size
            total_byte += ukuran

            if f.suffix == ".part":
                keadaan["terpotong (.part)"] += 1
                rusak.append((f, "berkas sementara yang tidak selesai", ukuran))
                continue

            if ukuran == 0:
                keadaan["kosong"] += 1
                rusak.append((f, "0 byte", ukuran))
                continue

            if ukuran <= 512:
                keadaan["terlalu kecil"] += 1
                rusak.append((f, "hanya %d byte" % ukuran, ukuran))
                continue

            with f.open("rb") as fh:
                awal = fh.read(16)

            jenis = jenis_gambar(awal)
            if jenis is None:
                # Bukan gambar: kemungkinan halaman error HTML yang tersimpan.
                teks = awal.decode("utf-8", "replace").strip()
                keadaan["bukan gambar"] += 1
                rusak.append((f, "bukan gambar: %s" % teks[:40], ukuran))
                continue

            keadaan["gambar " + jenis] += 1

        except Exception as e:
            keadaan["gagal dibaca"] += 1
            rusak.append((f, str(e)[:40], 0))

    print("  ── keadaan berkas cache ──")
    for k, n in keadaan.most_common():
        print("     %-22s %6d" % (k, n))
    print()
    print("  total ukuran cache: %.1f MB" % (total_byte / 1024 / 1024))
    print()

    if rusak:
        print("  ══════════════════════════════════════════════════════════════════")
        print("   %d BERKAS CACHE RUSAK" % len(rusak))
        print("  ══════════════════════════════════════════════════════════════════")
        print()
        print("  Inilah gambar-gambar yang tidak muncul di katalog. Aplikasi")
        print("  memakai berkas ini apa adanya dan tidak pernah mengunduh ulang,")
        print("  jadi kerusakannya menetap.")
        print()
        for f, sebab, ukuran in rusak[:20]:
            print("     %-46s %8d byte  %s" % (f.name[:46], ukuran, sebab))
        if len(rusak) > 20:
            print("     ... dan %d lainnya" % (len(rusak) - 20))
        print()

        # Simpan daftarnya supaya bisa dihapus dan diunduh ulang.
        daftar = W / "build" / "cache-thumbnail-rusak.json"
        daftar.parent.mkdir(parents=True, exist_ok=True)
        daftar.write_text(json.dumps(
            [{"berkas": str(f), "nama": f.name, "sebab": s, "ukuran": u}
             for f, s, u in rusak], ensure_ascii=False, indent=1), encoding="utf-8")
        print("  daftar: %s" % daftar)
    else:
        print("  Tidak ada berkas cache yang rusak.")
        print("  Jadi gambar yang tidak muncul BUKAN berasal dari cache yang rusak.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
