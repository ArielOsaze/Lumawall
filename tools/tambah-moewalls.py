#!/usr/bin/env python3
"""Tambahkan wallpaper moewalls baru ke katalog, dengan dua penjaga.

Alat ini melanjutkan tools/ambil-video-moewalls.py: alat itu sudah mengambil
videoUrl dan TAG ASLI untuk 139 wallpaper moewalls yang belum ada di katalog.
Alat ini memasukkannya.

DUA PENJAGA, dan keduanya menangkap hal yang tidak terlihat dari judul:

  1. AI-GENERATED. Sebagian halaman moewalls menandai wallpapernya dengan tag
     "ai-art" - 18 dari 139. Katalog mensyaratkan artwork, dan itu permintaan
     yang eksplisit: "wajib artwork bukan ai generated yg free". Entri bertag itu
     DIBUANG, bukan dimasukkan. Judulnya tidak menunjukkan apa pun - "Moonlight
     Beach" dan "Summer Cloud Cottage" terlihat seperti wallpaper biasa.

  2. TAG SIDEBAR. Dua belas tag muncul di SEMUA 139 halaman - "clouds",
     "night", "raining", "sky", "trees", "video-games", dan seterusnya. Itu
     navigasi situsnya, bukan tag wallpaper. Kalau tidak dibuang, setiap
     wallpaper akan tampak seperti wallpaper hujan dan video game.

Kategorinya ditentukan dari TAG SPESIFIK saja, dan urutannya penting: kategori
dewasa diperiksa lebih dulu, karena sebuah wallpaper bisa sekaligus bertag
"swimsuit" dan "beach" - dan kalau "beach" diperiksa lebih dulu, ia akan masuk
Nature, padahal yang ditonjolkan adalah pakaian renangnya.

Pemakaian:
  python tools/tambah-moewalls.py            (periksa saja)
  python tools/tambah-moewalls.py --tulis    (terapkan)
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json  # noqa: E402

KATALOG = ROOT / "LumaWall" / "catalog.json"
VIDEO = ROOT / "build" / "catalog-scrape" / "moewalls-video.json"
KARTU = ROOT / "build" / "catalog-scrape" / "moewalls-baru.json"

# Tag yang menandakan konten dewasa dengan sendirinya.
DEWASA = {
    "swimsuit", "swimwear", "bikini", "lingerie", "underwear", "bra",
    "panties", "succubus", "bath", "shower", "towel", "bunny-suit",
    "pajamas", "pyjamas", "nightgown", "negligee", "corset", "stockings",
    "garter", "thighs", "boudoir", "gravure", "pinup", "pin-up", "sexy",
    "seductive", "sensual", "sultry", "ecchi", "hentai", "lewd", "nsfw",
    "erotic", "topless", "undress", "cleavage", "busty", "voluptuous",
    "milf", "nude",
}

# Tag yang menentukan kategori lain.
#
# URUTAN PEMERIKSAAN PENTING, dan itu pelajaran dari kesalahan: "Anime Girl
# Summertime Beach" punya tag "beach", dan kalau tag pemandangan diperiksa
# sebelum tag gaya, wallpaper itu masuk Nature - padahal yang ditonjolkan
# karakternya, bukan pantainya. Nature hanya untuk wallpaper yang benar-benar
# pemandangan, yaitu yang TIDAK punya subjek berkarakter.
GAME = {
    "genshin-impact", "honkai", "wuthering-waves", "zenless-zone-zero",
    "valorant", "league-of-legends", "overwatch", "elden-ring", "zelda",
    "minecraft", "fortnite", "apex-legends", "dota", "pubg", "roblox",
    "blue-archive", "nikke", "azur-lane", "arknights", "fate", "nier",
    "video-games", "video-game", "game", "games",
}
ANIME_SERI = {
    "one-piece", "naruto", "jujutsu-kaisen", "demon-slayer", "bleach",
    "attack-on-titan", "chainsaw-man", "dragon-ball", "my-hero-academia",
    "spy-x-family", "evangelion", "sailor-moon", "inuyasha", "konosuba",
    "re-zero", "overlord", "sword-art-online", "steins-gate", "frieren",
    "bocchi-the-rock", "oshi-no-ko", "dandadan", "vocaloid", "pokemon",
    "digimon", "yu-gi-oh", "gundam", "doraemon", "conan", "slam-dunk",
}

# Penanda bahwa wallpapernya berisi KARAKTER, bukan pemandangan. Ini yang
# mencegah "Anime Girl Summertime Beach" masuk Nature.
KARAKTER = {
    "anime-girl", "anime-boy", "girl", "boy", "waifu", "character",
    "maid", "kimono", "traditional-clothes", "japanese-clothes",
    "long-hair", "short-hair", "blonde-hair", "blue-hair", "pink-hair",
    "white-hair", "red-hair", "black-hair", "twintails", "ponytail",
    "animal-ears", "cat-ears", "fox-ears", "horns", "wings",
    "school-girl", "school-uniform", "uniform", "dress", "white-dress",
    "blue-eyes", "red-eyes", "green-eyes", "purple-eyes",
    "smiling", "looking-at-viewer", "sitting", "standing", "lying",
    "holding", "hugging", "sleeping", "relaxing", "chilling",
}

NATURE = {
    "anime-landscape", "landscape", "scenery", "nature", "forest",
    "mountain", "mountains", "cherry-blossoms", "sakura", "flower-petals",
    "falling-leaves", "snow", "autumn", "spring", "waves", "beach",
    "sea", "ocean", "lake", "river", "waterfall", "garden", "flowers",
    "sky", "clouds", "sunset", "sunrise", "stars", "night-sky", "moon",
}
SPACE = {"space", "galaxy", "nebula", "cosmos", "planets", "universe"}
CARS = {"car", "cars", "vehicles", "motorcycle", "racing", "jdm"}
CITY = {"city", "cityscape", "urban", "street", "cyberpunk", "neon-city",
        "tokyo", "buildings"}
FOOD = {"food", "cooking", "cafe", "coffee", "restaurant"}
SPORT = {"sports", "football", "soccer", "basketball", "baseball"}
MUSIC = {"music", "musical-instrument", "piano", "guitar", "headphones"}

# Tag yang menandakan bukan manusia, dan karena itu tidak boleh masuk kategori
# dewasa - "bath" ada di wallpaper pemandangan, "shower" ada di kincir angin.
BUKAN_MANUSIA = re.compile(
    r"\b(deadpool|bojack|windmill|meteor|horse|horseman|"
    r"cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|dragon|"
    r"landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"robot|mecha|machine|ship|plane|tank|gun|skeleton|skull|"
    r"bear|dance|dancing|m4|rifle|weapon|blue archive)\b", re.I)

TIDAK_LAYAK = re.compile(
    r"\b(boy|man|male|father|dad|son|brother|grandpa|"
    r"chibi|sd|pixel|8-?bit|sketch|drawing|logo|icon)\b", re.I)


def kategori(tags, judul):
    """Kategori dari tag spesifik, dengan urutan yang disengaja."""
    if tags & DEWASA and not BUKAN_MANUSIA.search(judul) and not TIDAK_LAYAK.search(judul):
        return "Mature 18+"
    if tags & GAME:
        return "Gaming"
    if tags & ANIME_SERI:
        return "Anime Loop"
    if tags & SPACE:
        return "Space"
    if tags & CARS:
        return "Cars"
    if tags & CITY:
        return "City"
    if tags & SPORT:
        return "Sports"
    if tags & MUSIC:
        return "Music"

    # Nature HANYA kalau tidak ada penanda karakter. Tanpa pemeriksaan ini,
    # "Anime Girl Summertime Beach" masuk Nature karena tag "beach" - padahal
    # yang ditonjolkan karakternya.
    if (tags & NATURE) and not (tags & KARAKTER):
        return "Nature"

    # Bergaya anime tanpa seri dan tanpa tema yang lebih khusus.
    return "Anime Girls"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    if not VIDEO.exists() or not KARTU.exists():
        print("  TIDAK ADA berkas masukan")
        return 1

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    vid = json.load(open(VIDEO, encoding="utf-8"))
    item = vid.get("item") or {}
    kk = json.load(open(KARTU, encoding="utf-8"))
    kartu = kk.get("kartu") or {}
    print("  kartu moewalls baru : %d" % len(kartu))
    print("  sudah ada videoUrl  : %d" % len(item))
    print()

    # Tag sidebar: muncul di SEMUA halaman, jadi itu navigasi situs.
    tc = Counter()
    for v in item.values():
        for t in v.get("tags") or []:
            tc[t] += 1
    n = len(item)
    sidebar = {t for t, c in tc.items() if c == n and n > 3}
    print("  tag sidebar dibuang : %d  (%s)"
          % (len(sidebar), ", ".join(sorted(sidebar)[:6])))
    print()

    ada_vid = {(x.get("videoUrl") or "").strip() for x in items}
    ada_url = {(x.get("sourceUrl") or "").rstrip("/") for x in items}

    tambah = []
    dibuang_ai = []
    dibuang_lain = []
    for slug, v in item.items():
        vu = (v.get("videoUrl") or "").strip()
        k = kartu.get(slug) or {}
        judul = k.get("title") or ""
        if not vu or not judul:
            dibuang_lain.append((judul or slug, "tidak ada video atau judul"))
            continue
        if vu in ada_vid:
            continue

        tags = {t for t in (v.get("tags") or []) if t not in sidebar}

        # PENJAGA 1: AI-generated. Katalog mensyaratkan artwork.
        if "ai-art" in tags or "ai-generated" in tags or "midjourney" in tags:
            dibuang_ai.append((judul, sorted(tags & {"ai-art", "ai-generated", "midjourney"})))
            continue

        res = v.get("resolution") or ""
        m = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", res)
        if m:
            w, hh = int(m.group(1)), int(m.group(2))
            if min(w, hh) < 720:
                dibuang_lain.append((judul, "di bawah HD (%s)" % res))
                continue
            if hh > w:
                dibuang_lain.append((judul, "potret (%s)" % res))
                continue

        tambah.append({
            "title": judul,
            "videoUrl": vu,
            "thumbnailUrl": k.get("thumbnailUrl") or "",
            "sourceUrl": (k.get("url") or "").rstrip("/"),
            "resolution": res,
            "category": kategori(tags, judul),
            "kind": "video",
            "animation": "video",
            "author": "",
            "license": "",
        })
        ada_vid.add(vu)

    print("  == hasil penyaringan ==")
    print("     layak ditambah   : %d" % len(tambah))
    print("     dibuang (AI)     : %d" % len(dibuang_ai))
    print("     dibuang (lain)   : %d" % len(dibuang_lain))
    print()

    if dibuang_ai:
        print("  == dibuang karena AI-GENERATED ==")
        for j, t in dibuang_ai:
            print("     %-56s %s" % (j[:56], ",".join(t)))
        print()

    c = Counter(x["category"] for x in tambah)
    print("  == kategori yang ditambahkan ==")
    for k, v in c.most_common():
        print("     %-14s %4d" % (k, v))
    print()
    print("  == 30 contoh ==")
    for x in tambah[:30]:
        print("     [%-12s] %-50s %s" % (x["category"][:12], x["title"][:50],
                                         x.get("resolution") or "-"))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-moe")
    semua = items + tambah
    write_json(KATALOG, semua if isinstance(d, list) else dict(d, items=semua))

    daftar = []
    for x in semua:
        if x.get("category") != "Mature 18+":
            continue
        mm = re.search(r"/media/(\d+)/", x.get("videoUrl") or "")
        daftar.append({
            "motionId": mm.group(1) if mm else "",
            "title": x.get("title") or "",
            "sourceUrl": x.get("sourceUrl") or "",
        })
    write_json(ROOT / "mature-audit" / "selected.json", daftar)

    print("  DITULIS")
    print("     katalog : %d entri" % len(semua))
    print("     Mature  : %d" % len([x for x in semua if x.get("category") == "Mature 18+"]))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
