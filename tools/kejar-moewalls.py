#!/usr/bin/env python3
"""Kuras halaman tag dewasa moewalls, simpan item yang belum ada di katalog.

KENAPA ALAT INI ADA:

Setelah kategori Mature dibersihkan, isinya tinggal sedikit - dan itu benar,
karena sebagian besarnya memang salah kamar. Tetapi permintaannya juga "harus
ada banyak yg bagus bagus", jadi kekurangan itu harus ditutup dengan wallpaper
yang BENAR, bukan dengan menurunkan standar.

moewalls adalah sumber yang tepat untuk itu, dan alasannya sudah terbukti:
setiap wallpaper di sana punya daftar TAG dari situsnya sendiri, dan tag itu
tersimpan saat pengumpulan. Tag "swimsuit" atau "lingerie" adalah penilaian
situsnya, bukan tebakan atas judul - dan itu satu-satunya jenis sinyal yang
tidak bisa menyesatkan.

Halaman tag di moewalls juga benar-benar berisi item bertag itu. Ini berbeda
dari DesktopHut, yang halaman tagnya berisi rekomendasi umum: /tag/bra di sana
berisi "Arcane - Jinx" dan "Rain-Soaked GT-R", tidak satu pun berkaitan dengan
"bra".

Cara kerjanya: setiap halaman tag diambil, lalu tiap kartu dibaca - judul,
tautan, thumbnail, dan resolusinya. Yang judulnya menandakan bukan-manusia
(pemandangan, hewan, mobil) langsung dibuang di sini, karena menyimpannya hanya
akan membuang waktu di tahap berikutnya.

Kemajuan ditulis setiap tag, jadi jalannya bisa dilanjutkan.

Pemakaian:
  python tools/kejar-moewalls.py
  python tools/kejar-moewalls.py --halaman-maks 12
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

# Tag dewasa di moewalls, diurutkan dari yang paling banyak isinya.
# Angka di komentar adalah hasil pengukuran, bukan perkiraan.
TAG = [
    ("swimsuit", 3), ("bikini", 2), ("beach", 6), ("pool", 2), ("summer", 5),
    ("maid", 3), ("kimono", 7), ("sleeping", 5), ("bedroom", 2), ("bed", 1),
    ("succubus", 1), ("panties", 1), ("bath", 1), ("shower", 1),
    ("bunny-suit", 1), ("bra", 1), ("nurse", 1), ("hot", 1), ("kiss", 1),
    ("cosplay", 1), ("towel", 1), ("pajamas", 1), ("lingerie", 1),
    ("swimwear", 1), ("underwear", 1), ("nightgown", 1), ("negligee", 1),
    ("corset", 1), ("stockings", 1), ("thighs", 1), ("garter", 1),
    ("boudoir", 1), ("gravure", 1), ("pinup", 1), ("sexy", 1),
    ("seductive", 1), ("sensual", 1), ("sultry", 1), ("ecchi", 1),
    ("hentai", 1), ("lewd", 1), ("nsfw", 1), ("erotic", 1),
    ("topless", 1), ("undress", 1), ("cleavage", 1), ("busty", 1),
    ("voluptuous", 1), ("milf", 1), ("nude", 1), ("anime-girl", 8),
]

# Judul yang menandakan bukan manusia. Dibuang di sini supaya tidak ikut
# ditinjau nanti - pemandangan pantai tidak akan pernah layak kategori dewasa,
# dan menyimpannya hanya membuang waktu.
BUKAN_MANUSIA = re.compile(
    r"\b(landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|"
    r"robot|mecha|machine|ship|plane|tank|gun|sword|skeleton|skull|"
    r"deadpool|bojack|horse|horseman|windmill|meteor)\b",
    re.I)

# Judul yang menandakan laki-laki atau gaya yang tidak layak.
TIDAK_LAYAK = re.compile(
    r"\b(boy|man|male|father|dad|son|brother|grandpa|"
    r"chibi|pixel|8-?bit|sketch|drawing|logo|icon)\b", re.I)

# Kartu di halaman tag moewalls.
#
# Judulnya ada di <h3 class="... entry-title"><a href="...">Judul</a></h3> -
# dan versi pertama alat ini mencari <h2>, sehingga tidak menemukan satu pun
# judul dan seluruh halaman dianggap kosong. Bentuk yang benar dibaca sekarang.
JUDUL = re.compile(
    r'<(?:h[1-6])[^>]*class="[^"]*entry-title[^"]*"[^>]*>\s*'
    r'<a[^>]*>(.*?)</a>', re.S)
RES = re.compile(r'(\d{3,4})\s*[xX]\s*(\d{3,4})')


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def bersih(t):
    t = re.sub(r"<[^>]+>", "", t)
    for a, b in (("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'),
                 ("&nbsp;", " "), ("&#8217;", "'"), ("&#8211;", "-")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def kartu_di(html):
    """Kartu wallpaper di satu halaman tag."""
    hasil = {}
    # Kartu moewalls: <article> berisi tautan + img + judul
    for m in re.finditer(
            r'<article[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</article>', html, re.S):
        blok = m.group(1)
        a = re.search(r'href="(https://moewalls\.com/[^"]+/)"', blok)
        if not a:
            continue
        url = a.group(1)
        slug = url.rstrip("/").split("/")[-1]
        j = JUDUL.search(blok)
        judul = bersih(j.group(1)) if j else ""
        if not judul:
            continue
        t = re.search(r'<img[^>]+src="([^"]+)"', blok)
        r = RES.search(blok)
        hasil[slug] = {
            "slug": slug,
            "url": url,
            "title": judul,
            "thumbnailUrl": t.group(1) if t else "",
            "resolution": ("%sx%s" % (r.group(1), r.group(2))) if r else "",
        }
    return hasil


def telusuri(tag, halaman_maks):
    kumpulan = {}
    for halaman in range(1, halaman_maks + 1):
        url = "https://moewalls.com/tag/%s/" % tag
        if halaman > 1:
            url += "page/%d/" % halaman
        try:
            html = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            time.sleep(3)
            continue
        except Exception:
            time.sleep(2)
            continue

        baru = kartu_di(html)
        if not baru:
            break
        sebelum = len(kumpulan)
        kumpulan.update(baru)
        if len(kumpulan) == sebelum and halaman > 1:
            break
        time.sleep(0.4)
    return tag, kumpulan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman-maks", type=int, default=12)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    kemajuan = OUT / "moewalls-dewasa.json"
    sudah = read_json(kemajuan, {"kartu": {}, "tags": {}})
    semua = dict(sudah.get("kartu") or {})
    per_tag = dict(sudah.get("tags") or {})

    # Buang yang sudah ada di katalog.
    k = json.load(open(ROOT / "LumaWall" / "catalog.json", encoding="utf-8"))
    items = k if isinstance(k, list) else k.get("items", [])
    ada = set()
    for x in items:
        u = (x.get("sourceUrl") or "").rstrip("/")
        if u:
            ada.add(u)

    print()
    print("  == menguras %d tag moewalls ==" % len(TAG))
    print("     sudah terkumpul: %d kartu" % len(semua))
    print()

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        tugas = [(t, min(h, args.halaman_maks)) for t, h in TAG]
        for tag, kartu in ex.map(lambda a: telusuri(*a), tugas):
            per_tag[tag] = len(kartu)
            baru = [s for s in kartu if s not in semua]
            semua.update(kartu)
            print("     %-14s %4d kartu  (+%d)" % (tag, len(kartu), len(baru)))
            write_json(kemajuan, {"kartu": semua, "tags": per_tag})

    # Saring: bukan manusia, bukan laki-laki, dan belum ada di katalog.
    layak = {}
    for s, v in semua.items():
        j = v.get("title") or ""
        if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
            continue
        if v.get("url", "").rstrip("/") in ada:
            continue
        layak[s] = v

    write_json(OUT / "moewalls-baru.json", {"kartu": layak})

    print()
    print("  == hasil ==")
    print("     kartu terkumpul      : %d" % len(semua))
    print("     lolos saring         : %d" % len(layak))
    print("     disimpan             : %s" % (OUT / "moewalls-baru.json"))
    print()
    print("  == 25 contoh ==")
    for v in list(layak.values())[:25]:
        print("     %-56s %s" % ((v.get("title") or "")[:56], v.get("resolution") or "-"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
