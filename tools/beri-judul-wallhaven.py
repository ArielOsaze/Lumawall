#!/usr/bin/env python3
"""Beri judul yang bermakna pada entri wallhaven.

KENAPA ALAT INI ADA:

Hasil pencarian wallhaven tidak memuat judul yang bisa dibaca - nama berkasnya
adalah ID acak seperti "wallhaven-e8vlpr.png", sehingga entri akan muncul di
katalog sebagai "Wallhaven E8vlpr". Judul seperti itu tidak berguna: pengguna
tidak bisa mencari dengan kata kunci, dan kartunya tidak memberi tahu apa pun
tentang isinya.

Tag aslinya ada di halaman detail /w/{id}. Dua sampai empat tag pertama biasanya
sudah menggambarkan wallpapernya dengan baik ("anime girl sunset"), dan itulah
yang dipakai sebagai judul.

Ini 333 permintaan tambahan, jadi dijalankan paralel - kalau berurutan, ini
memakan delapan menit untuk hal yang bisa selesai dalam satu menit.
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
BERKAS = W / "build" / "wallhaven-baru.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Tag ada di elemen berkelas "tagname"; teksnya adalah nama tagnya.
POLA_TAG = re.compile(r'<a[^>]+class="tagname"[^>]*>([^<]+)</a>', re.I)
# Cadangan: ambil dari atribut title kalau teksnya kosong.
POLA_TAG_JUDUL = re.compile(r'<a[^>]+class="tagname"[^>]+title="([^"]+)"', re.I)

# Tag yang tidak menjelaskan isi gambar - dibuang dari judul.
TAG_SAMPAH = {
    "anime", "anime girls", "girl", "girls", "female", "1girl", "1boy",
    "wallpaper", "hd", "high resolution", "art", "artwork", "digital art",
    "illustration", "fan art", "person", "people", "simple background",
    "looking at viewer", "long hair", "short hair",
}


def ambil_tag(url):
    """Ambil beberapa tag pertama dari halaman detail.

    Ada jeda kecil dan satu percobaan ulang: wallhaven membatasi permintaan yang
    datang terlalu cepat, dan penolakannya tidak selalu berupa error - sebagian
    hanya mengembalikan halaman tanpa tag, sehingga alat akan melaporkan
    "selesai" padahal tag-nya tidak terambil.
    """
    html = None
    for percobaan in range(2):
        try:
            req = Request(url, headers=UA)
            with urlopen(req, timeout=25) as f:
                html = f.read().decode("utf-8", "replace")
            if 'class="tagname"' in html:
                break
        except Exception:
            html = None
        time.sleep(0.8)
    if not html:
        return []

    tag = POLA_TAG.findall(html)
    if not tag:
        # Sebagian halaman hanya memberi kategori tag di atribut title
        # ("Nature > Landscapes"); diambil bagian terakhirnya saja.
        tag = [x.split("&gt;")[-1] for x in POLA_TAG_JUDUL.findall(html)]
    bersih = []
    for t in tag:
        t = " ".join(t.split()).strip()
        if not t or len(t) > 34:
            continue
        if t.lower() in TAG_SAMPAH:
            continue
        if t.lower() in [b.lower() for b in bersih]:
            continue
        bersih.append(t)
    return bersih


def judul_dari(entri):
    """Judul dari 2-4 tag pertama."""
    time.sleep(0.15)
    tag = ambil_tag(entri["sourceUrl"])
    if not tag:
        return entri
    pilih = tag[:3]
    judul = " ".join(w.capitalize() if w.islower() else w for w in pilih)
    entri["title"] = judul[:70]
    entri["animation"] = ", ".join(tag[:8])
    return entri


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MEMBERI JUDUL PADA ENTRI WALLHAVEN")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if not BERKAS.exists():
        print("  ! berkas tidak ada: %s" % BERKAS)
        return 1

    entri = json.loads(BERKAS.read_text(encoding="utf-8"))
    print("  entri: %d" % len(entri))
    print()
    print("  ── mengambil tag dari halaman detail ──")

    mulai = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        hasil = list(pool.map(judul_dari, entri))

    berhasil = sum(1 for x in hasil if not x["title"].startswith("Wallhaven "))
    print("     selesai dalam %.0f detik" % (time.time() - mulai))
    print("     judul dari tag : %d" % berhasil)
    print("     tetap ID       : %d" % (len(hasil) - berhasil))
    print()

    print("  ── contoh judul baru ──")
    for x in hasil[:10]:
        print("     %-52s  %s" % (x["title"][:52], x["category"]))
    print()

    BERKAS.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  disimpan: %s" % BERKAS)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
