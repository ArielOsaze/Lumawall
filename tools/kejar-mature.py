#!/usr/bin/env python3
"""Telusuri halaman tag dewasa DesktopHut dan kumpulkan URL-nya.

Kenapa alat ini ada: kategori "Mature 18+" hanya berisi 249 dari 22.879 entri,
dan permintaannya adalah kategori itu harus banyak dan isinya bagus. Situs
sumbernya tidak punya halaman kategori dewasa, tetapi ia PUNYA halaman tag -
dan tag-tag itu adalah cara situs itu sendiri mengelompokkan wallpapernya.
Memakai tag berarti kategorinya berasal dari situsnya, bukan dari tebakan atas
kata-kata di judul.

Yang ditelusuri hanya tag dewasa. Halaman tag lain sudah pernah ditelusuri dan
hasilnya ada di katalog; menelusurinya lagi hanya akan menghasilkan URL yang
sudah ada.

Setiap halaman ditelusuri sampai habis, bukan hanya halaman pertama: satu tag
bisa punya puluhan halaman, dan berhenti di halaman pertama akan menghasilkan
kategori yang isinya sedikit - persis masalah yang sedang diperbaiki.

Kemajuan ditulis setelah setiap tag, supaya jalannya bisa dilanjutkan.

Pemakaian:
  python tools/kejar-mature.py
  python tools/kejar-mature.py --halaman-maks 30
"""
import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Tag dewasa di DesktopHut. Ini yang situsnya sendiri pakai untuk mengelompokkan
# wallpaper bergaya dewasa, jadi kategorinya berasal dari situsnya.
TAG = [
    "adult", "bikini", "lingerie", "swimsuit", "sexy", "hot", "seductive",
    "sensual", "pinup", "gravure", "boudoir", "nude", "beach-bikini",
    "leotard", "bodysuit", "catsuit", "stockings", "thigh-highs", "garter",
    "corset", "nightgown", "negligee", "topless", "bra", "panties", "undress",
    "big-breasts", "curvy", "voluptuous", "sultry", "provocative", "cleavage",
    "busty", "milf", "shemale", "hentai", "ecchi", "lewd", "nsfw",
    "bathing", "shower", "bedroom", "massage", "yoga", "gym", "cheerleader",
    "schoolgirl", "nurse", "maid", "bunny", "cat-girl", "fox-girl",
]

# Halaman tag memuat tautan ke halaman lain di situs yang sama. Yang diinginkan
# hanya tautan ke wallpaper, dan bentuknya bisa dibedakan.
BUKAN_WALLPAPER = re.compile(
    r"^/(tag|page|search|collections|explore|rankings|featured|popular|"
    r"must-have|ai-generator|about|community|cookies|dmca|how-to|privacy|"
    r"software|terms|rankings|users|login|register|upload|random)/",
    re.I,
)

# Stock footage BUKAN artwork, dan kategorinya mensyaratkan artwork.
#
# Halaman /tag/adult di situs ini berisi dua hal yang sangat berbeda: rekaman
# kamera wanita di kantor dan kolam renang - yang "adult" dalam arti demografis,
# bukan dalam arti kategori ini - dan artwork bergaya anime. Membiarkan keduanya
# masuk berarti kategori Mature berisi video kantor, dan itu persis "kategorinya
# nyasar" yang harus dihindari.
#
# Penandanya ada di nama berkasnya sendiri: situs itu menamai rekamannya dengan
# "Stock-Footage", "Video-Stock", atau "Stock-Video".
STOCK = re.compile(r"stock[-_]?footage|video[-_]?stock|stock[-_]?video", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def tautan_wallpaper(html):
    """Tautan ke halaman wallpaper, bukan ke halaman situs."""
    hasil = set()
    for href in re.findall(r'href="(/[^"?#]+)"', html):
        if BUKAN_WALLPAPER.match(href):
            continue
        # Stock footage bukan artwork: kategorinya mensyaratkan artwork.
        if STOCK.search(href):
            continue
        # Halaman wallpaper punya akhiran kode 4 huruf, mis. -gjwl
        if re.search(r"-[a-z0-9]{4}$", href, re.I):
            hasil.add("https://desktophut.com" + href)
    return hasil


def telusuri_tag(tag, halaman_maks):
    """Semua URL wallpaper di satu tag, sampai halamannya habis."""
    kumpulan = set()
    for halaman in range(1, halaman_maks + 1):
        url = "https://desktophut.com/tag/%s" % tag
        if halaman > 1:
            url += "?page=%d" % halaman
        try:
            html = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            time.sleep(2)
            continue
        except Exception:
            time.sleep(2)
            continue

        baru = tautan_wallpaper(html)
        if not baru:
            break

        sebelum = len(kumpulan)
        kumpulan |= baru
        # Kalau satu halaman tidak menambah apa pun, halamannya sudah berulang
        # atau habis - berhenti daripada menelusuri halaman kosong tanpa akhir.
        if len(kumpulan) == sebelum and halaman > 1:
            break

    return tag, kumpulan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman-maks", type=int, default=40)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    kemajuan = OUT / "mature-urls.json"
    sudah = read_json(kemajuan, {"urls": [], "tags": {}}) if kemajuan.exists() else {"urls": [], "tags": {}}
    semua = set(sudah.get("urls", []))
    per_tag = dict(sudah.get("tags", {}))

    print()
    print("  ══ menelusuri %d tag dewasa ══" % len(TAG))
    print("     sudah terkumpul: %d URL" % len(semua))
    print()

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tag, urls in ex.map(lambda t: telusuri_tag(t, args.halaman_maks), TAG):
            baru = urls - semua
            per_tag[tag] = len(urls)
            semua |= urls
            print("     %-16s %4d item  (+%d baru)" % (tag, len(urls), len(baru)))

            # Ditulis setiap tag, supaya jalannya bisa dilanjutkan kalau
            # dihentikan di tengah - dan supaya hasil yang sudah didapat tidak
            # hilang karena satu tag yang gagal.
            write_json(kemajuan, {"urls": sorted(semua), "tags": per_tag})

    # Tandai sebagai dewasa, supaya pengumpul memasukkannya ke kategori mature
    # atas dasar penilaian situsnya sendiri, bukan tebakan atas judulnya.
    write_json(OUT / "adult-urls.json", {"urls": sorted(semua)})

    print()
    print("  ══ selesai ══")
    print("     URL dewasa terkumpul : %d" % len(semua))
    print("     disimpan             : %s" % kemajuan)
    print("     daftar dewasa        : %s" % (OUT / "adult-urls.json"))
    print()
    print("  Langkah berikutnya: jalankan pengumpulnya untuk mengukur dan")
    print("  memasukkan berkas-berkas ini ke katalog.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
