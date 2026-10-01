#!/usr/bin/env python3
"""Tetapkan kategori Mature 18+ dengan sinyal yang bisa diaudit.

MASALAH YANG DIPERBAIKI:

Kategori "Mature 18+" berisi 319 entri, dan setelah diperiksa:

    219  tidak punya satu pun kata dewasa di judulnya
         ("2B Silent Elegance", "Acheron (Honkai Star Rail)", "Akagimi")
     80  hanya dibenarkan kata generik - "girl", "maid", "idol", "waifu"
         ("Miku Starlight Idol", "Anime Girl Maid Dance")
     20  benar-benar dewasa

Jadi 94% isinya salah kamar. Penyebabnya: keanggotaan ditentukan dari tebakan
atas kata di judul, dan daftar katanya memuat kata yang tidak menandakan apa pun
- "girl" ada di ribuan wallpaper anime, dan "idol" ada di nama Hatsune Miku.

APA YANG DIPAKAI SEKARANG - tiga sinyal, berurutan menurut kekuatannya:

  1. TAG SITUSNYA. moewalls memberi setiap wallpaper daftar tag, dan tag itu
     tersimpan di build/catalog-moewalls/adopted.json. Tag "swimsuit" atau
     "lingerie" adalah penilaian situsnya sendiri, bukan tebakan. Ini sinyal
     terkuat yang tersedia, dan tetap disaring subjek bukan-manusia.

  2. JUDUL, dengan daftar kata yang KETAT. Hanya kata yang tidak punya arti lain
     di wallpaper: bikini, swimsuit, lingerie, cleavage, nsfw, ecchi, lewd,
     topless, boudoir, gravure, pin-up, busty, voluptuous, nude, milf, erotic,
     seductive, sensual, sultry, provocative, sexy.

     Kata yang DIBUANG dari daftar lama, beserta alasannya:
       girl, girls  - ada di ribuan wallpaper anime yang tidak dewasa
       maid, bunny  - kostum, bukan konten
       idol, model  - nama Hatsune Miku dan nama karakter
       hot          - "Hot Air Balloon", "Hot Springs"
       bath, shower - "Deadpool Bathing", "Windmill Meteor Shower"
       gym, yoga    - olahraga
       beach, pool  - pemandangan
       nurse, cheerleader, schoolgirl - kostum
       leotard, bodysuit, catsuit - pakaian super, bukan pakaian dalam

  3. TINJAUAN VISUAL (mature-audit/tinjauan.json), kalau ada.

Entri yang tidak lolos TIDAK dibuang: dikembalikan ke kategori yang benar
(Gaming, Anime Girls, Anime Loop, atau Dynamic). Wallpapernya tetap bagus, hanya
salah kamar - dan kategori yang isinya salah lebih buruk daripada kategori yang
isinya sedikit, karena yang pertama membuat pengguna tidak bisa mempercayai
kategori mana pun.

Pemakaian:
  python tools/tegakkan-mature3.py            (periksa saja)
  python tools/tegakkan-mature3.py --tulis    (terapkan)
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
MOE = ROOT / "build" / "catalog-moewalls" / "adopted.json"
TINJAUAN = ROOT / "mature-audit" / "tinjauan.json"

# Kata yang TIDAK punya arti lain di sebuah wallpaper. Ini satu-satunya daftar
# yang boleh memasukkan entri ke Mature atas dasar judulnya.
KETAT = re.compile(
    r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
    r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
    r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|naked|milf|"
    r"panties|nightgown|negligee|corset|garter|thigh-?highs?|"
    r"hot\s+girl|cute\s+hot|sexy\s+girl)\b",
    re.I)

# Tag moewalls yang menandakan konten dewasa dengan sendirinya.
TAG_KETAT = {
    "swimsuit", "swimwear", "bikini", "lingerie", "underwear", "bra",
    "panties", "succubus", "bath", "shower", "towel", "bunny-suit",
    "pajamas", "pyjamas", "nightgown", "negligee", "corset", "stockings",
    "garter", "thighs", "boudoir", "gravure", "pinup", "pin-up", "sexy",
    "seductive", "sensual", "sultry", "ecchi", "hentai", "lewd", "nsfw",
    "erotic", "topless", "undress", "cleavage", "busty", "voluptuous",
    "milf", "nude",
}

# Subjek bukan-manusia. Tag "bath" ada di "Deadpool Bathing", tag "shower" ada
# di "Windmill Meteor Shower" - keduanya bukan konten dewasa.
BUKAN_MANUSIA = re.compile(
    r"\b(deadpool|bojack|windmill|meteor|horse|horseman|"
    r"cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|dragon|"
    r"landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"robot|mecha|machine|ship|plane|tank|gun|skeleton|skull|"
    r"bear|dance|dancing|m4|rifle|weapon)\b",
    re.I)

# Judul yang menandakan entri TIDAK layak apa pun tagnya.
TIDAK_LAYAK = re.compile(
    r"\b(boy|man|male|father|dad|son|brother|grandpa|"
    r"chibi|sd|pixel|8-?bit|sketch|drawing|logo|icon)\b", re.I)

GAMING = re.compile(
    r"\b(genshin|honkai|wuthering|zenless|valorant|league of legends|overwatch|"
    r"elden|zelda|mario|sonic|fortnite|apex|dota|blue archive|nikke|azur lane|"
    r"arknights|fate|nier|2b|acheron|raiden|hu tao|ganyu|shenhe|furina|"
    r"seele|kafka|firefly|jinhsi|cartethyia|astra|ellen|miyabi|burnice|"
    r"snowbreak|reverse 1999|path to nowhere|umamusume|princess connect|"
    r"granblue|star rail|impact|zzz|punishing|tower of fantasy|"
    r"honkai star rail|destiny|warframe|apex|pubg|minecraft|roblox)\b", re.I)

ANIME = re.compile(
    r"\b(anime|manga|naruto|one piece|jujutsu|demon slayer|attack on titan|"
    r"chainsaw|frieren|dragon ball|bleach|hunter x hunter|tokyo ghoul|"
    r"my hero|spy x family|evangelion|gundam|sailor moon|inuyasha|konosuba|"
    r"re:zero|re zero|overlord|sword art online|steins|spirited away|ghibli|"
    r"vocaloid|hatsune|miku|bocchi|rascal|spy family|dandadan|oshi no ko)\b",
    re.I)


def kategori_baru(judul):
    if GAMING.search(judul):
        return "Gaming"
    if ANIME.search(judul):
        return "Anime Loop"
    return "Anime Girls"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    # Sinyal 1: tag moewalls.
    tag_layak = {}
    if MOE.exists():
        m = json.load(open(MOE, encoding="utf-8"))
        for x in m if isinstance(m, list) else m.get("items", m.get("adopted", [])):
            tg = x.get("_tags") or []
            if isinstance(tg, str):
                tg = [tg]
            kena = {str(t).lower().strip() for t in tg} & TAG_KETAT
            u = x.get("sourceUrl") or ""
            if u and kena:
                tag_layak[u] = sorted(kena)
    print("  tag moewalls layak : %d" % len(tag_layak))

    # Sinyal 3: tinjauan visual.
    tinjau = {}
    if TINJAUAN.exists():
        t = json.load(open(TINJAUAN, encoding="utf-8"))
        for k, v in (t.get("putusan") or {}).items():
            if v.get("layak") and v.get("url"):
                tinjau[v["url"]] = True
    print("  tinjauan visual    : %d" % len(tinjau))
    print()

    sekarang = [x for x in items if x.get("category") == "Mature 18+"]
    print("  Mature sekarang    : %d" % len(sekarang))
    print()

    tetap, keluar = [], []
    sebab = Counter()
    for x in sekarang:
        j = x.get("title") or ""
        u = x.get("sourceUrl") or x.get("videoUrl") or ""
        if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
            keluar.append(x)
            sebab["subjek bukan manusia / tidak layak"] += 1
            continue
        if u in tinjau:
            tetap.append(x)
            sebab["tinjauan visual"] += 1
            continue
        if u in tag_layak:
            tetap.append(x)
            sebab["tag situs"] += 1
            continue
        if KETAT.search(j):
            tetap.append(x)
            sebab["judul (kata ketat)"] += 1
            continue
        keluar.append(x)
        sebab["tidak ada bukti apa pun"] += 1

    print("  == sebab tetap di Mature ==")
    for k, v in sebab.most_common():
        print("     %-32s %4d" % (k, v))
    print()
    print("  TETAP  : %d" % len(tetap))
    print("  KELUAR : %d" % len(keluar))
    print()

    # Masuk: entri dari luar Mature yang layak.
    sudah = {(x.get("sourceUrl") or x.get("videoUrl") or "") for x in tetap}
    masuk = []
    for x in items:
        if x.get("category") == "Mature 18+":
            continue
        j = x.get("title") or ""
        u = x.get("sourceUrl") or x.get("videoUrl") or ""
        if u in sudah or BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
            continue
        if u in tag_layak or u in tinjau or KETAT.search(j):
            masuk.append(x)
            sudah.add(u)

    print("  MASUK dari kategori lain: %d" % len(masuk))
    print()

    print("  == 30 yang TETAP ==")
    for x in tetap[:30]:
        print("     %-58s" % (x.get("title") or "")[:58])
    print()
    print("  == 20 yang KELUAR ==")
    for x in keluar[:20]:
        print("     %-52s -> %s" % ((x.get("title") or "")[:52],
                                    kategori_baru(x.get("title") or "")))
    print()
    print("  == 20 yang MASUK ==")
    for x in masuk[:20]:
        print("     %-58s" % (x.get("title") or "")[:58])
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-tegak3")

    for x in keluar:
        x["category"] = kategori_baru(x.get("title") or "")
    for x in masuk:
        x["category"] = "Mature 18+"

    write_json(KATALOG, items if isinstance(d, list) else d)

    # selected.json dipakai pemeriksa. Sekarang isinya entri yang LOLOS saja.
    daftar = []
    for x in items:
        if x.get("category") != "Mature 18+":
            continue
        m = re.search(r"/media/(\d+)/", x.get("videoUrl") or "")
        daftar.append({
            "motionId": m.group(1) if m else "",
            "title": x.get("title") or "",
            "sourceUrl": x.get("sourceUrl") or "",
        })
    write_json(ROOT / "mature-audit" / "selected.json", daftar)

    akhir = [x for x in items if x.get("category") == "Mature 18+"]
    print("  DITULIS")
    print("     katalog : %s" % KATALOG)
    print("     Mature  : %d" % len(akhir))
    print("     seleksi : %s" % (ROOT / "mature-audit" / "selected.json"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
