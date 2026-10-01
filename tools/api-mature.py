#!/usr/bin/env python3
"""Kumpulkan wallpaper dewasa DesktopHut lewat API-nya, bukan dengan mengurai HTML.

Kenapa lewat API: situs itu punya /api/wallpapers yang mengembalikan JSON dengan
judul, slug, resolusi, dan URL pratinjau - semuanya sudah terstruktur. Mengurai
HTML berarti menebak dari bentuk tautan, dan itu rapuh: satu perubahan tata letak
membuat pengumpul mengembalikan nol tanpa error, yang persis "0 item" yang
sempat terjadi.

API-nya mengembalikan maksimal 50 entri per halaman dan menyertakan
`meta.has_more`, jadi penelusurannya jelas: jalan sampai has_more bernilai salah.

Yang disaring:
  * Stock footage dibuang. Kategorinya mensyaratkan artwork, dan halaman
    /tag/adult berisi rekaman kamera yang "adult" dalam arti demografis.
  * Resolusi di bawah HD dibuang - katalog tidak boleh berisi wallpaper pecah.

Pemakaian:
  python tools/api-mature.py
  python tools/api-mature.py --halaman-maks 200
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

API = "https://desktophut.com/api/wallpapers?per_page=50&page=%d"

# Stock footage bukan artwork.
STOCK = re.compile(r"stock[-_]?footage|video[-_]?stock|stock[-_]?video|"
                   r"stock[-_]?clip|footage", re.I)

# Judul yang menandakan stock footage meski slug-nya tidak.
STOCK_JUDUL = re.compile(r"\b(stock|footage|royalty[- ]free clip|"
                         r"video[- ]stock|business[- ]woman|office[- ]woman)\b", re.I)

# Kata yang menandakan wallpaper bergaya dewasa. Dipakai untuk memilih dari
# seluruh API, karena API-nya tidak punya penyaring kategori dewasa.
DEWASA = re.compile(
    r"\b(bikini|swimsuit|swimwear|lingerie|lingerie[- ]model|boudoir|gravure|"
    r"pin[- ]?up|seductive|sensual|sultry|provocative|sexy|seksi|"
    r"cleavage|busty|curvy|voluptuous|big[- ]breasts|large[- ]breasts|"
    r"leotard|bodysuit|catsuit|stockings|thigh[- ]highs|garter|corset|"
    r"nightgown|negligee|topless|nude|naked|undress|bra|panties|"
    r"bath|bathing|shower|onsen|hot[- ]spring|poolside|beach[- ]bikini|"
    r"cheerleader|schoolgirl|nurse|maid|bunny[- ]girl|bunny|"
    r"cat[- ]girl|fox[- ]girl|waifu|ecchi|lewd|nsfw|hentai|"
    r"gravure|idol|cosplay|yoga|gym|massage|bedroom)\b",
    re.I,
)

# Resolusi: hanya HD ke atas.
def hd_atau_lebih(res):
    m = re.match(r"(\d+)\s*[x×]\s*(\d+)", res or "")
    if not m:
        return False
    w, h = int(m.group(1)), int(m.group(2))
    # HD berarti sisi pendek minimal 720, dan orientasi mendatar.
    if h > w:
        return False
    return h >= 720


def ambil(halaman):
    """Satu halaman API."""
    try:
        req = urllib.request.Request(API % halaman, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return halaman, d.get("data", []), d.get("meta", {})
    except Exception as e:
        return halaman, [], {"error": str(e)[:60]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman-maks", type=int, default=400)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    kemajuan = OUT / "api-mature.json"
    sudah = read_json(kemajuan, {"halaman": 0, "items": []}) if kemajuan.exists() else {"halaman": 0, "items": []}
    items = list(sudah.get("items", []))
    mulai = int(sudah.get("halaman", 0)) + 1

    print()
    print("  ══ API DesktopHut ══")
    print("     sudah terkumpul: %d entri" % len(items))
    print("     mulai dari halaman %d" % mulai)
    print()

    halaman = mulai
    habis = False
    while not habis and halaman <= args.halaman_maks:
        kelompok = list(range(halaman, min(halaman + args.workers * 2, args.halaman_maks + 1)))

        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            hasil = list(ex.map(ambil, kelompok))

        for nomor, data, meta in hasil:
            if meta.get("error"):
                continue
            for x in data:
                judul = x.get("title") or ""
                slug = x.get("slug") or ""
                if STOCK.search(slug) or STOCK_JUDUL.search(judul):
                    continue
                if not hd_atau_lebih(x.get("resolution")):
                    continue
                items.append({
                    "id": x.get("id"),
                    "title": judul,
                    "slug": slug,
                    "resolution": x.get("resolution"),
                    "thumbnailUrl": x.get("thumbnail_url"),
                    "previewUrl": x.get("preview_clip_url"),
                    "sourceUrl": "https://desktophut.com/" + slug,
                })
            if not meta.get("has_more"):
                habis = True

        halaman += args.workers * 2
        write_json(kemajuan, {"halaman": halaman - 1, "items": items})
        print("     halaman %-5d  entri terkumpul: %d%s"
              % (halaman - 1, len(items), "  (habis)" if habis else ""))

    # Pisahkan yang bergaya dewasa dari sisanya. Yang dewasa masuk daftar
    # adult-urls.json supaya pengumpul memasukkannya ke kategori Mature atas
    # dasar penilaian atas namanya, bukan tebakan.
    dewasa = [x for x in items
              if DEWASA.search(x["title"]) or DEWASA.search(x["slug"])]
    write_json(OUT / "adult-urls.json", {"urls": sorted(x["sourceUrl"] for x in dewasa)})

    print()
    print("  ══ selesai ══")
    print("     total entri HD    : %d" % len(items))
    print("     bergaya dewasa    : %d" % len(dewasa))
    print("     disimpan          : %s" % kemajuan)
    print("     daftar dewasa     : %s" % (OUT / "adult-urls.json"))
    print()

    # Contoh, supaya isinya bisa diperiksa dan bukan hanya dihitung.
    print("  ── contoh yang terpilih ──")
    for x in dewasa[:15]:
        print("     %-56s %s" % (x["title"][:56], x["resolution"]))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
