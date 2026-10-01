#!/usr/bin/env python3
"""Tarik wallpaper moewalls lewat WordPress REST API, bukan scraping.

KENAPA ALAT INI ADA - dan apa yang salah dengan cara sebelumnya:

Seluruh moewalls adalah WordPress, dan WordPress membuka REST API-nya:

    /wp-json/wp/v2/posts?tags=<id>&per_page=100&page=<n>

Itu memberi daftar postingan yang BENAR-BENAR bertag itu, langsung dari
situsnya, tanpa membaca HTML dan tanpa menebak apa pun. Cara sebelumnya -
menelusuri halaman /tag/<nama>/ dan membaca kartunya - bekerja, tetapi:

  * hanya memberi halaman pertama untuk tag yang isinya sedikit
  * resolusi harus dibaca dari class elemen
  * tag harus dibaca dari tautan di halaman
  * dan yang paling penting: halaman tag DesktopHut terbukti berisi
    rekomendasi umum, jadi "ada di halaman tag" tidak pernah menjadi bukti
    keanggotaan. API tidak punya masalah itu.

Yang ditelusuri hanya tag dewasa. Tag itu dipilih dari daftar 2000 tag yang
situsnya sendiri daftarkan, dan setiap jumlah di bawah diambil dari API:

    swimsuit 35, bikini 18, succubus 14, panties 6

Tag sugestif (beach, pool, summer, maid, bunny, sleeping, bedroom, bed, kiss,
kimono, gym, school uniform) ikut ditarik TERPISAH, supaya keputusan "dipakai
atau tidak" bisa diambil dengan melihat isinya - bukan dengan menebak.

Pemakaian:
  python tools/api-moewalls.py
  python tools/api-moewalls.py --semua     (ikutkan tag sugestif)
"""
import argparse
import json
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

# Tag yang menandakan konten dewasa dengan sendirinya. Jumlah di komentar
# adalah yang situsnya sendiri laporkan lewat API.
DEWASA = {
    "swimsuit": 1025,        # 35
    "bikini": 3240,          # 18
    "succubus": 3074,        # 14
    "panties": 1786,         # 6
}

# Tag sugestif: sering muncul di wallpaper biasa, jadi hanya dipakai kalau
# diminta dengan --semua.
SUGESTIF = {
    "beach": 415,            # 83
    "pool": 1868,            # 19
    "summer": 710,           # 68
    "maid": 383,             # 43
    "bunny": 1190,           # 12
    "sleeping": 328,         # 71
    "bedroom": 801,          # 19
    "bed": 1204,             # 15
    "kiss": 4547,            # 5
    "kimono": 691,           # 105
    "gym": 4539,             # 4
    "school uniform": 348,   # 258
}


def api(path, timeout=30):
    u = "https://moewalls.com/wp-json/wp/v2/" + path
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def postingan(tag_id, maks=6):
    """Semua postingan bertag ini, lengkap dengan media dan tagnya."""
    hasil = []
    for hal in range(1, maks + 1):
        try:
            d = api("posts?tags=%d&per_page=100&page=%d&_embed=1" % (tag_id, hal))
        except urllib.error.HTTPError as e:
            # 400 = halaman di luar jangkauan. Itu akhir yang wajar.
            if e.code in (400, 404):
                break
            time.sleep(2)
            continue
        except Exception:
            time.sleep(2)
            continue
        if not d:
            break
        hasil.extend(d)
        if len(d) < 100:
            break
        time.sleep(0.4)
    return hasil


def bersih(html):
    import re
    t = re.sub(r"<[^>]+>", " ", html or "")
    for a, b in (("&amp;", "&"), ("&#8217;", "'"), ("&#8211;", "-"),
                 ("&#039;", "'"), ("&#8217;", "'"), ("&quot;", '"'),
                 ("&nbsp;", " "), ("&#215;", "x")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semua", action="store_true",
                    help="ikutkan juga tag sugestif")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    maju = OUT / "moewalls-api.json"
    sudah = read_json(maju, {"item": {}, "tags": {}})
    item = dict(sudah.get("item") or {})
    per_tag = dict(sudah.get("tags") or {})

    pilih = dict(DEWASA)
    if args.semua:
        pilih.update(SUGESTIF)

    print()
    print("  == WordPress API moewalls ==")
    print("     %d tag ditelusuri" % len(pilih))
    print()

    for nama, tid in pilih.items():
        d = postingan(tid)
        baru = 0
        for p in d:
            slug = p.get("slug") or ""
            if not slug or slug in item:
                continue

            # Media (thumbnail) ada di _embedded.
            thumb = ""
            try:
                m = p["_embedded"]["wp:featuredmedia"][0]
                thumb = m.get("source_url") or ""
            except Exception:
                pass

            # Tautan download ada di isi postingan sebagai id="moe-download".
            isi = (p.get("content") or {}).get("rendered") or ""
            import re
            tok = re.search(r'data-url\s*=\s*"([^"]+)"', isi)
            vid = ("https://go.moewalls.com/download.php?video=" + tok.group(1)) if tok else ""

            # Resolusi ada di class elemen postingannya.
            kelas = " ".join(p.get("class_list") or [])
            res = ""
            r = re.search(r"resolutions-(\d{3,4})x(\d{3,4})", kelas)
            if r:
                res = "%sx%s" % (r.group(1), r.group(2))

            # SEMUA tag postingan ini, dari API - bukan dari tautan halaman.
            tags = []
            try:
                tags = [t.get("name", "").lower()
                        for t in p["_embedded"]["wp:term"][0]]
            except Exception:
                pass

            item[slug] = {
                "slug": slug,
                "title": bersih((p.get("title") or {}).get("rendered") or ""),
                "url": p.get("link") or "",
                "thumbnailUrl": thumb,
                "videoUrl": vid,
                "resolution": res,
                "tags": sorted(set(tags)),
                "dari_tag": nama,
            }
            baru += 1

        per_tag[nama] = {"id": tid, "postingan": len(d), "baru": baru}
        print("     %-18s %4d postingan  (+%d baru)" % (nama, len(d), baru))
        write_json(maju, {"item": item, "tags": per_tag})

    print()
    print("  == hasil ==")
    print("     total item   : %d" % len(item))
    print("     punya video  : %d" % len([v for v in item.values() if v.get("videoUrl")]))
    print("     punya resolusi: %d" % len([v for v in item.values() if v.get("resolution")]))
    print("     disimpan     : %s" % maju)
    print()

    from collections import Counter
    c = Counter(v.get("dari_tag") for v in item.values())
    print("  == dari tag mana ==")
    for k, v in c.most_common():
        print("     %-18s %4d" % (k, v))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
