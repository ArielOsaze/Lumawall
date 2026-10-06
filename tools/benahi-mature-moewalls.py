#!/usr/bin/env python3
"""Benahi judul entri Mature dari moewalls memakai tag aslinya.

KENAPA ALAT INI ADA:

Pemeriksa katalog menolak entri Mature yang judulnya tidak memuat kata
pembenar. Untuk entri dari moewalls, buktinya sudah tersimpan di
build/catalog-scrape/moewalls-dewasa.json: tag asli halaman itu, misalnya

    eyjafjalla-summer-flower-arknights-live-wallpaper
        tags: [..., 'beach', ...]

"beach" bukan kata yang membenarkan Mature menurut MATURE_WORDS, tetapi
tag itu menjelaskan gambarnya. Yang dipakai di sini hanya tag yang benar-benar
ada di MATURE_WORDS - kalau tidak ada, entri itu memang tidak punya dasar dan
harus dikeluarkan dari kategori Mature, bukan diberi alasan buatan.

Entri yang tidak punya tag pembenar DIPINDAHKAN ke kategori yang sesuai
(Anime Girls), bukan dibiarkan di Mature tanpa alasan.
"""

import json
import re
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SCRAPE = W / "build" / "catalog-scrape" / "moewalls-dewasa.json"

MATURE_WORDS = set("""nsfw ecchi hentai lewd sexy seductive sensual sultry provocative erotic
lingerie bikini swimsuit swimwear cleavage boudoir gravure pin-up pinup topless
undress busty voluptuous stripper nude naked milf panties nightgown negligee
corset garter thigh-high thigh-highs hot""".split())


def kata(teks):
    return set(re.split(r"[^a-z0-9]+", teks.lower())) - {""}


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBENAHI MATURE MOEWALLS DENGAN TAG ASLINYA")
print("  ══════════════════════════════════════════════════════════════════")
print()

katalog = json.load(open(CATALOG, encoding="utf-8"))
items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
kunci = "Items" if isinstance(katalog, dict) and "Items" in katalog else None

# Tag asli tiap halaman moewalls, dari hasil scrape sebelumnya.
scr = json.load(open(SCRAPE, encoding="utf-8")).get("item", {})
tag_menurut_slug = {}
for slug, v in scr.items():
    t = v.get("tags") or []
    if t:
        tag_menurut_slug[slug] = [str(x).replace("-", " ") for x in t]
print("  tag asli tersedia untuk %d halaman moewalls" % len(tag_menurut_slug))
print()

mat = [e for e in items if e.get("category") == "Mature 18+"]
tanpa_dasar = [e for e in mat
               if not (kata(e.get("title", "") + " " + e.get("videoUrl", "")) & MATURE_WORDS)
               and "wallhaven" not in (e.get("videoUrl", "") + e.get("license", "")).lower()]
print("  mature tanpa dasar (bukan wallhaven): %d" % len(tanpa_dasar))
print()

diperbaiki = 0
dipindah = 0
for e in tanpa_dasar:
    # Slug halaman ada di judul yang asli, tetapi setelah beberapa penggantian
    # judulnya bisa berubah. URL-nya dipakai sebagai gantinya: moewalls
    # menyimpan slug di halaman sumbernya.
    sumber = (e.get("sourceUrl") or "") + " " + (e.get("videoUrl") or "")
    m = re.search(r"moewalls\.com/([a-z0-9-]+?)(?:-live-wallpaper)?/?$", sumber)
    slug = m.group(1) if m else ""
    tag = tag_menurut_slug.get(slug) or tag_menurut_slug.get(slug + "-live-wallpaper")

    if not tag:
        # Cari berdasarkan judul: slug dibentuk dari judul.
        judul_slug = re.sub(r"[^a-z0-9]+", "-", e.get("title", "").lower()).strip("-")
        for s, t in tag_menurut_slug.items():
            if s.startswith(judul_slug[:28]) or judul_slug.startswith(s[:28]):
                tag = t
                break

    if tag:
        pembenar = [x for x in tag if kata(x) & MATURE_WORDS]
        if pembenar:
            e["title"] = "%s - %s" % (e["title"][:70], pembenar[0].title())
            diperbaiki += 1
            continue

    # Tidak ada tag pembenar: entri ini memang tidak punya dasar. Dipindahkan
    # ke Anime Girls, bukan dibiarkan di Mature.
    e["category"] = "Anime Girls"
    dipindah += 1

print("  judul dibenahi : %d" % diperbaiki)
print("  dipindah ke Anime Girls: %d" % dipindah)
print()

if diperbaiki or dipindah:
    if kunci:
        katalog[kunci] = items
        keluar = katalog
    else:
        keluar = items
    CATALOG.write_text(json.dumps(keluar, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  ditulis: %s" % CATALOG)

mat = [e for e in items if e.get("category") == "Mature 18+"]
sisa = [e for e in mat
        if not (kata(e.get("title", "") + " " + e.get("videoUrl", "")) & MATURE_WORDS)]
print()
print("  Mature sekarang        : %d" % len(mat))
print("  masih tanpa dasar      : %d" % len(sisa))
for e in sisa[:8]:
    print("     %s" % e.get("title", "")[:66])
print()
