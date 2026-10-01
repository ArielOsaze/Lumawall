#!/usr/bin/env python3
"""Panen wallpaper dewasa dari DesktopHut dengan penyaring yang jujur.

KENAPA ALAT INI ADA - dan apa yang salah sebelumnya:

Kategori "Mature 18+" pernah berisi 319 entri, tetapi setelah diperiksa satu per
satu, hanya 20 yang benar-benar dewasa. 219 entri tidak punya satu pun kata
dewasa di judulnya ("2B Silent Elegance", "Acheron (Honkai Star Rail)"), dan 80
entri hanya dibenarkan kata generik seperti "girl", "maid", "idol", "waifu" -
sehingga "Miku Starlight Idol" dan "Anime Girl Maid Dance" dianggap dewasa.

Penyebabnya ada dua, dan keduanya diperbaiki di sini:

1. Halaman TAG tidak bisa dipercaya untuk kategorisasi.

   /tag/bra berisi "Arcane - Jinx", "Rain-Soaked GT-R", dan "The North Face
   Capsule" - tidak satu pun berkaitan dengan "bra". Situs itu mengisi halaman
   tag yang isinya sedikit dengan rekomendasi umum, jadi daftar di halaman tag
   BUKAN daftar item yang benar-benar bertag itu.

   Karena itu keanggotaan tidak lagi ditentukan oleh halaman tag mana item itu
   ditemukan. Halaman tag hanya dipakai untuk MENEMUKAN kandidat; yang
   menentukan apakah sebuah item benar-benar dewasa adalah JUDULNYA SENDIRI.

2. Kata generik membenarkan terlalu banyak.

   Kata seperti "girl", "maid", "idol", "waifu", "model", dan "hot" muncul di
   ribuan wallpaper anime yang sama sekali tidak dewasa. Kata-kata itu sekarang
   TIDAK dianggap bukti.

Jadi aturannya satu kalimat: sebuah item masuk Mature hanya kalau judulnya
sendiri memuat kata yang jelas dewasa atau sugestif. Tidak ada pengecualian,
dan tidak ada tebakan dari kategori lain.

Akibatnya jumlahnya akan lebih sedikit daripada 319 - dan itu memang benar.
Kategori yang isinya salah lebih buruk daripada kategori yang isinya sedikit,
karena yang pertama membuat penggunanya tidak bisa mempercayai kategori mana pun.

Pemakaian:
  python tools/panen-mature.py
  python tools/panen-mature.py --halaman-maks 50
"""
import argparse
import concurrent.futures as cf
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

# Tag yang ditelusuri. Hanya dipakai untuk MENEMUKAN kandidat.
TAG = [
    "adult", "bikini", "beach-bikini", "swimsuit", "lingerie", "sexy",
    "seductive", "sensual", "sultry", "provocative", "boudoir", "gravure",
    "pinup", "topless", "undress", "nightgown", "negligee", "corset",
    "stockings", "garter", "thigh-highs", "leotard", "bodysuit", "catsuit",
    "bathing", "shower", "bedroom", "massage", "hot", "bra", "panties",
    "cleavage", "busty", "curvy", "voluptuous", "milf", "nude",
]

# Kata yang HARUS ada di judul. Ini satu-satunya bukti yang diterima.
#
# Dipisah dua tingkat supaya bisa diperiksa berapa banyak yang datang dari
# masing-masing - dan supaya keputusan "tingkat mana yang dipakai" bisa
# diambil dengan melihat angkanya, bukan dengan menebak.
JELAS = re.compile(
    r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
    r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
    r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|milf|"
    r"panties|nightgown|negligee|corset|garter|thigh-?highs?|"
    r"hot\s+girl|cute\s+hot|sexy\s+girl)\b",
    re.I)

# Sugestif: bisa dewasa, bisa tidak, tergantung judulnya. Dipakai hanya untuk
# melaporkan, tidak untuk memasukkan.
SUGESTIF = re.compile(
    r"\b(bra|stockings|leotard|bodysuit|catsuit|bathing|shower|massage|"
    r"sunbath\w*|poolside|bathhouse|onsen|hot\s+spring|beach|pool|"
    r"bunny|maid|nurse|schoolgirl|cheerleader|yoga|gym)\b",
    re.I)

KARTU = re.compile(
    r'<a\s+href="(/[^"]+)"\s+class="wallpaper-card[^"]*"\s+title="([^"]*)"'
    r'[^>]*>(.*?)</a>',
    re.S)
THUMB_KARTU = re.compile(r'<img\s+src="([^"]+)"')
RES_KARTU = re.compile(r'<span class="badge-res">(.*?)</span>', re.S)

# Stock footage bukan artwork.
STOCK = re.compile(r"\b(stock\s*(video|footage)|video\s*stock|footage)\b", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def bersih(teks):
    teks = re.sub(r"<[^>]+>", "", teks)
    for a, b in (("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'),
                 ("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">")):
        teks = teks.replace(a, b)
    return re.sub(r"\s+", " ", teks).strip()


def kartu_di(html):
    """Kartu wallpaper di satu halaman, dengan judulnya."""
    hasil = {}
    for href, judul_atribut, isi in KARTU.findall(html):
        if href.startswith(("/tag/", "/page/", "/collections", "/explore")):
            continue
        judul = re.sub(r"^Download\s+", "", bersih(judul_atribut), flags=re.I).strip()
        if not judul or STOCK.search(judul):
            continue
        slug = href.rstrip("/").split("/")[-1]
        t = THUMB_KARTU.search(isi)
        r = RES_KARTU.search(isi)
        hasil[slug] = {
            "slug": slug,
            "url": "https://desktophut.com" + href,
            "title": judul,
            "thumbnailUrl": t.group(1) if t else "",
            "resolution": bersih(r.group(1)) if r else "",
        }
    return hasil


def telusuri_tag(tag, halaman_maks):
    kumpulan = {}
    for halaman in range(1, halaman_maks + 1):
        url = "https://desktophut.com/tag/%s" % tag
        if halaman > 1:
            url += "?page=%d" % halaman
        if halaman > 1:
            # Situs ini membalas 410 kalau diminta terlalu cepat - bukan 429,
            # jadi tidak terlihat seperti pembatasan laju padahal itu.
            time.sleep(1.2)
        try:
            html = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            time.sleep(4)
            continue
        except Exception:
            time.sleep(3)
            continue

        baru = kartu_di(html)
        if not baru:
            break
        sebelum = len(kumpulan)
        kumpulan.update(baru)
        if len(kumpulan) == sebelum and halaman > 1:
            break
    return tag, kumpulan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman-maks", type=int, default=50)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print()
    print("  == memanen %d tag ==" % len(TAG))
    print()

    semua = {}
    per_tag = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tag, kartu in ex.map(lambda t: telusuri_tag(t, args.halaman_maks), TAG):
            per_tag[tag] = len(kartu)
            baru = [s for s in kartu if s not in semua]
            semua.update(kartu)
            print("     %-16s %4d kartu  (+%d baru)" % (tag, len(kartu), len(baru)))
            write_json(OUT / "mature-kartu.json", {
                "kartu": semua, "tags": per_tag})

    # Penyaring jujur: judulnya sendiri harus memuat kata dewasa.
    jelas = {s: k for s, k in semua.items() if JELAS.search(k["title"])}
    sugestif = {s: k for s, k in semua.items()
                if s not in jelas and SUGESTIF.search(k["title"])}

    print()
    print("  == hasil ==")
    print("     kandidat terkumpul       : %d" % len(semua))
    print("     judul memuat kata JELAS  : %d" % len(jelas))
    print("     judul hanya sugestif     : %d" % len(sugestif))
    print()

    write_json(OUT / "mature-jelas.json", {"kartu": jelas})
    write_json(OUT / "mature-sugestif.json", {"kartu": sugestif})

    print("  == 25 contoh yang JELAS ==")
    for k in list(jelas.values())[:25]:
        print("     %-62s %s" % (k["title"][:62], k["resolution"] or "-"))
    print()
    print("  == 12 contoh yang hanya sugestif ==")
    for k in list(sugestif.values())[:12]:
        print("     %-62s %s" % (k["title"][:62], k["resolution"] or "-"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
