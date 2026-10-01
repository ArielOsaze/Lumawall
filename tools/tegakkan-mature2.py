#!/usr/bin/env python3
"""Tegakkan kategori Mature 18+ dari hasil tinjauan, bukan dari tebakan.

MASALAH YANG DIPERBAIKI:

Kategori "Mature 18+" berisi 319 entri, dan setelah diperiksa satu per satu:

    219  tidak punya satu pun kata dewasa di judulnya
          ("2B Silent Elegance", "Acheron (Honkai Star Rail)", "Akagimi")
     80  hanya dibenarkan kata generik - "girl", "maid", "idol", "waifu"
          ("Miku Starlight Idol", "Anime Girl Maid Dance")
     20  benar-benar dewasa

Jadi 94% isinya salah. Penyebabnya: keanggotaan ditentukan dari tebakan atas
kata di judul, dan itu tidak bisa bekerja - judul wallpaper anime penuh kata
"girl" dan "maid" yang tidak menandakan apa pun.

APA YANG DIPAKAI SEKARANG:

Tinjauan visual. Kandidat disusun jadi lembar kontak bernomor
(tools/lembar-mature.py), dilihat gambarnya, lalu dinyatakan layak atau tidak.
Yang layak disimpan di mature-audit/tinjauan.json, dan hanya itu yang masuk
Mature. Aturan proyek memang sudah menetapkan ini sejak awal: sebuah entri
mencapai Mature hanya melalui seleksi yang ditinjau.

Entri yang tidak layak TIDAK dibuang - dikembalikan ke kategori yang benar
(Gaming, Anime Girls, Anime Loop, atau Dynamic), karena wallpapernya sendiri
tetap bagus, hanya salah kamar.

Pemakaian:
  python tools/tegakkan-mature2.py            (periksa saja, jangan tulis)
  python tools/tegakkan-mature2.py --tulis    (tulis perubahannya)
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
TINJAUAN = ROOT / "mature-audit" / "tinjauan.json"
MOE = ROOT / "build" / "catalog-scrape" / "mature-moewalls.json"
LEMBAR = ROOT / "build" / "mature-lembar" / "nomor.json"

# Subjek yang bukan manusia. Judul seperti "Deadpool Bathing", "Windmill Meteor
# Shower", dan "Bojack Horseman Chilling In The Pool" masuk daftar kandidat
# karena tagnya, tetapi gambarnya bukan manusia - dan kategori ini tentang
# manusia.
BUKAN_MANUSIA = re.compile(
    r"\b(deadpool|bojack|windmill|meteor|horse|horseman|"
    r"cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|dragon|"
    r"landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"robot|mecha|machine|ship|plane|tank|gun|sword|skeleton|skull)\b",
    re.I)

# Kategori tujuan untuk entri yang keluar dari Mature.
GAMING = re.compile(
    r"\b(genshin|honkai|wuthering|zenless|valorant|league|overwatch|elden|"
    r"zelda|mario|sonic|fortnite|apex|dota|blue archive|nikke|azur lane|"
    r"arknights|fate|nier|2b|acheron|raiden|hu tao|ganyu|shenhe|furina|"
    r"seele|kafka|firefly|jinhsi|cartethyia|astra|ellen|miyabi|burnice|"
    r"wuthering waves|punishing|tower of fantasy|nikke|snowbreak|"
    r"reverse 1999|path to nowhere|arknights|umamusume|princess connect|"
    r"granblue|honkai star rail|star rail|impact|zzz|wuthering)\b",
    re.I)
ANIME_LOOP = re.compile(
    r"\b(anime|manga|naruto|one piece|jujutsu|demon slayer|attack on titan|"
    r"chainsaw|frieren|dragon ball|bleach|hunter|tokyo ghoul|my hero|"
    r"spy x family|evangelion|gundam|sailor moon|cardcaptor|inuyasha|"
    r"konosuba|re:zero|re zero|overlord|sword art online|fate/|steins|"
    r"spirited away|ghibli|vocaloid|hatsune|miku)\b",
    re.I)


def kategori_baru(judul, sekarang):
    """Ke mana entri pergi kalau bukan mature lagi."""
    if GAMING.search(judul):
        return "Gaming"
    if ANIME_LOOP.search(judul):
        return "Anime Loop"
    # Sisanya karakter anime tanpa judul seri yang jelas.
    return "Anime Girls"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    # 1. Kumpulkan yang LAYAK, dari tinjauan visual.
    layak_url = set()
    sumber_layak = Counter()

    t = {}
    if TINJAUAN.exists():
        t = json.load(open(TINJAUAN, encoding="utf-8"))
    for k, v in (t.get("putusan") or {}).items():
        if v.get("layak") and v.get("url"):
            layak_url.add(v["url"])
            sumber_layak["tinjauan"] += 1

    if LEMBAR.exists() and TINJAUAN.exists():
        nomor = json.load(open(LEMBAR, encoding="utf-8"))
        for n, v in (t.get("putusan") or {}).items():
            if v.get("layak") and n in nomor:
                layak_url.add(nomor[n]["url"])
                sumber_layak["lembar"] += 1

    # 2. moewalls yang tagnya jelas - tetapi tanpa subjek bukan-manusia.
    if MOE.exists():
        m = json.load(open(MOE, encoding="utf-8"))
        for x in m.get("jelas", []):
            u = x.get("sourceUrl") or ""
            j = x.get("title") or ""
            if not u or BUKAN_MANUSIA.search(j):
                continue
            layak_url.add(u)
            sumber_layak["moewalls-jelas"] += 1

    print("  layak (hasil tinjauan + tag jelas): %d" % len(layak_url))
    for k, v in sumber_layak.most_common():
        print("     %-18s %4d" % (k, v))
    print()

    # 3. Terapkan.
    sekarang_mature = [x for x in items if x.get("category") == "Mature 18+"]
    print("  Mature sekarang : %d" % len(sekarang_mature))

    tetap, keluar = [], []
    for x in items:
        if x.get("category") != "Mature 18+":
            continue
        u = x.get("sourceUrl") or x.get("videoUrl") or ""
        if u in layak_url and not BUKAN_MANUSIA.search(x.get("title") or ""):
            tetap.append(x)
        else:
            keluar.append(x)

    # 4. Entri yang layak tetapi TIDAK ada di Mature - pindahkan masuk.
    ada_mature = {(x.get("sourceUrl") or x.get("videoUrl") or "") for x in tetap}
    masuk = []
    for x in items:
        if x.get("category") == "Mature 18+":
            continue
        u = x.get("sourceUrl") or x.get("videoUrl") or ""
        if u in layak_url and u not in ada_mature:
            masuk.append(x)
            ada_mature.add(u)

    print("  tetap Mature    : %d" % len(tetap))
    print("  keluar          : %d" % len(keluar))
    print("  masuk dari luar : %d" % len(masuk))
    print()

    print("  == keluar: ke mana mereka pergi ==")
    tujuan = Counter()
    for x in keluar:
        tujuan[kategori_baru(x.get("title") or "", x.get("category"))] += 1
    for k, v in tujuan.most_common():
        print("     %-14s %4d" % (k, v))
    print()

    print("  == 20 contoh yang KELUAR ==")
    for x in keluar[:20]:
        print("     %-56s -> %s" % ((x.get("title") or "")[:56],
                                    kategori_baru(x.get("title") or "", "")))
    print()
    print("  == semua yang TETAP (%d) ==" % len(tetap))
    for x in tetap:
        print("     %-58s" % (x.get("title") or "")[:58])
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    # 5. Tulis.
    shutil.copy2(KATALOG, str(KATALOG) + ".bak-tegak2")

    pindah = {}
    for x in keluar:
        pindah[id(x)] = kategori_baru(x.get("title") or "", x.get("category"))
    for x in masuk:
        pindah[id(x)] = "Mature 18+"

    for x in items:
        if id(x) in pindah:
            x["category"] = pindah[id(x)]

    write_json(KATALOG, items if isinstance(d, list) else d)

    # 6. Simpan daftar layak, supaya pemeriksa bisa memakainya.
    daftar = []
    for x in items:
        if x.get("category") == "Mature 18+":
            m = re.search(r"/media/(\d+)/", x.get("videoUrl") or "")
            daftar.append({
                "motionId": m.group(1) if m else "",
                "title": x.get("title") or "",
                "sourceUrl": x.get("sourceUrl") or "",
                "videoUrl": x.get("videoUrl") or "",
            })
    write_json(ROOT / "mature-audit" / "selected.json", daftar)

    print("  DITULIS")
    print("     katalog   : %s" % KATALOG)
    print("     cadangan  : %s.bak-tegak2" % KATALOG)
    print("     seleksi   : %s" % (ROOT / "mature-audit" / "selected.json"))
    print("     Mature    : %d" % len([x for x in items if x.get("category") == "Mature 18+"]))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
