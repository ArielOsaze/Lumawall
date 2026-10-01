#!/usr/bin/env python3
"""Kuras SEMUA sumber moewalls untuk wallpaper dewasa.

KENAPA ALAT INI ADA:

Mencari sumber konten dewasa yang benar-benar berisi, tanpa membuat kategori
lain kacau. Empat sumber diuji, dan hasilnya:

  1. REST API /wp-json/wp/v2/tags   -> TERBUKA. Memberi daftar 2000 tag
     beserta jumlahnya. Ini yang mengungkap tag mana yang benar-benar ada:
     swimsuit 35, bikini 18, succubus 14, panties 6, ecchi 10.

  2. REST API /wp-json/wp/v2/posts  -> DIBLOKIR (rest_forbidden). Jadi
     daftar postingan per tag tidak bisa diambil langsung.

  3. REST API /wp-json/wp/v2/search -> TERBUKA. Memberi postingan yang
     cocok dengan kata kunci, dan hasilnya persis sebanyak yang tag-nya
     laporkan. Ini pengganti endpoint posts yang diblokir.

  4. Halaman /tag/<nama>/page/<n>/   -> TERBUKA, dan PUNYA BANYAK HALAMAN.
     /tag/swimsuit punya 3 halaman (20 + 20 + 7), bukan satu seperti yang
     disangka sebelumnya.

Ketiganya dipakai bersama, lalu digabung dan dibuang duplikatnya. Yang tidak
bisa dipakai hanya posts, dan itu tidak masalah karena search memberi hal yang
sama.

Setiap kandidat dikunjungi halaman wallpapernya untuk mengambil videoUrl dan
TAG ASLINYA - tag dari halaman itu adalah penilaian situsnya sendiri.

Pemakaian:
  python tools/kuras-moewalls.py
"""
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

# Kata kunci yang jelas dewasa. Daftar ini dipakai untuk search API dan
# halaman tag.
KATA = [
    "swimsuit", "bikini", "succubus", "panties", "ecchi",
    "bath", "shower", "lingerie", "underwear", "bra",
    "cleavage", "busty", "voluptuous", "topless", "undress",
    "seductive", "sensual", "sultry", "sexy", "erotic",
    "nightgown", "negligee", "corset", "stockings", "garter",
    "boudoir", "gravure", "pinup", "milf", "nude",
]

# Halaman tag yang benar-benar ada, beserta jumlah halamannya.
TAG_HALAMAN = [
    ("swimsuit", 3), ("bikini", 2), ("succubus", 2), ("panties", 1),
    ("ecchi", 1), ("bunny", 2), ("beach", 5), ("pool", 2),
    ("maid", 3), ("sleeping", 4), ("bedroom", 2), ("kimono", 6),
    ("summer", 4), ("school-uniform", 13),
]

TOKEN = re.compile(r'data-url\s*=\s*"([^"]+)"', re.I)
TOKEN_KELAS = re.compile(r'id="moe-download"[^>]*', re.I)
TAG = re.compile(r'href="https://moewalls\.com/tag/([a-z0-9\-]+)/"', re.I)
RES_KELAS = re.compile(r'resolutions-(\d{3,4})x(\d{3,4})', re.I)
KARTU = re.compile(
    r'<a\s+href="(https://moewalls\.com/[a-z0-9\-]+/[a-z0-9\-]+/)"[^>]*>', re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def api(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def slug_dari(u):
    return (u or "").rstrip("/").split("/")[-1]


def kumpulkan_kandidat():
    """Slug dan judul dari ketiga sumber yang terbuka."""
    hasil = {}

    # Sumber 1: search API.
    for q in KATA:
        try:
            d = api("https://moewalls.com/wp-json/wp/v2/search"
                    "?search=%s&per_page=100" % urllib.request.quote(q))
        except Exception:
            time.sleep(1)
            continue
        for x in d:
            s = slug_dari(x.get("url"))
            if s and x.get("subtype") == "post":
                hasil.setdefault(s, {"slug": s, "title": x.get("title") or "",
                                     "url": x.get("url") or "", "dari": "search:%s" % q})
        time.sleep(0.3)

    # Sumber 2: halaman tag, SEMUA halamannya.
    for tag, maks in TAG_HALAMAN:
        for hal in range(1, maks + 1):
            u = "https://moewalls.com/tag/%s/" % tag
            if hal > 1:
                u += "page/%d/" % hal
            try:
                h = get(u)
            except Exception:
                break
            ada = 0
            for m in KARTU.finditer(h):
                url = m.group(1)
                # Halaman tag juga memuat tautan kategori; yang diinginkan
                # halaman wallpaper, dan itu punya 2 segmen setelah domain.
                if url.count("/") != 5:
                    continue
                s = slug_dari(url)
                if s and s not in hasil:
                    hasil[s] = {"slug": s, "title": "", "url": url,
                                "dari": "tag:%s" % tag}
                ada += 1
            if ada == 0:
                break
            time.sleep(0.4)

    return hasil


def lengkapi(k):
    """videoUrl, tag asli, dan resolusi dari halaman wallpapernya."""
    try:
        h = get(k["url"])
    except Exception as e:
        return k["slug"], {}, str(e)[:40]

    v = ""
    for m in TOKEN_KELAS.finditer(h):
        t = TOKEN.search(m.group(0))
        if t:
            v = "https://go.moewalls.com/download.php?video=" + t.group(1)
            break

    tags = sorted({t.lower() for t in TAG.findall(h)})
    r = RES_KELAS.search(h)

    judul = k.get("title") or ""
    if not judul:
        m = re.search(r'<title>([^<|]*)', h)
        if m:
            judul = m.group(1).strip()

    return k["slug"], {
        "slug": k["slug"],
        "title": judul,
        "url": k["url"],
        "videoUrl": v,
        "tags": tags,
        "resolution": ("%sx%s" % (r.group(1), r.group(2))) if r else "",
        "dari": k.get("dari") or "",
    }, ""


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print()
    print("  == 1. mengumpulkan kandidat dari 3 sumber ==")
    kandidat = kumpulkan_kandidat()
    print("     kandidat unik: %d" % len(kandidat))
    print()

    # Hanya yang belum ada di katalog.
    d = json.load(open(ROOT / "LumaWall" / "catalog.json", encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    ada = {(x.get("sourceUrl") or "").rstrip("/") for x in items}
    calon = [v for v in kandidat.values()
             if v["url"] and v["url"].rstrip("/") not in ada]
    print("     sudah ada di katalog: %d" % (len(kandidat) - len(calon)))
    print("     perlu dikunjungi    : %d" % len(calon))
    print()

    if not calon:
        print("  tidak ada yang baru")
        return 0

    maju = OUT / "moewalls-kuras.json"
    sudah = read_json(maju, {"item": {}})
    item = dict(sudah.get("item") or {})

    print("  == 2. mengambil videoUrl + tag asli ==")
    n = 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for slug, hasil, err in ex.map(lengkapi, calon):
            n += 1
            if hasil:
                item[slug] = hasil
            if n % 25 == 0:
                write_json(maju, {"item": item})
                print("     %d/%d  (berhasil: %d)" % (n, len(calon), len(item)))
            time.sleep(0.1)

    write_json(maju, {"item": item})

    # Saring: hanya yang punya video DAN tag dewasa.
    DEWASA = {
        "swimsuit", "swimwear", "bikini", "lingerie", "underwear", "bra",
        "panties", "succubus", "bath", "shower", "towel", "bunny-suit",
        "pajamas", "nightgown", "negligee", "corset", "stockings", "garter",
        "thighs", "boudoir", "gravure", "pinup", "pin-up", "sexy",
        "seductive", "sensual", "sultry", "ecchi", "hentai", "lewd", "nsfw",
        "erotic", "topless", "undress", "cleavage", "busty", "voluptuous",
        "milf", "nude",
    }
    layak = {}
    for s, v in item.items():
        if not v.get("videoUrl"):
            continue
        if not (set(v.get("tags") or []) & DEWASA):
            continue
        layak[s] = v

    write_json(OUT / "moewalls-dewasa.json", {"item": layak})

    print()
    print("  == hasil ==")
    print("     punya video       : %d" % len([v for v in item.values() if v.get("videoUrl")]))
    print("     punya tag dewasa  : %d" % len(layak))
    print("     disimpan          : %s" % (OUT / "moewalls-dewasa.json"))
    print()

    from collections import Counter
    tc = Counter()
    for v in layak.values():
        for t in set(v.get("tags") or []) & DEWASA:
            tc[t] += 1
    print("  == tag dewasa yang ditemukan ==")
    for t, c in tc.most_common():
        print("     %-16s %4d" % (t, c))
    print()
    print("  == 25 contoh ==")
    for v in list(layak.values())[:25]:
        print("     %-52s %-10s %s" % ((v.get("title") or "")[:52],
                                        v.get("resolution") or "-",
                                        ",".join(sorted(set(v.get("tags") or []) & DEWASA))[:24]))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
