#!/usr/bin/env python3
"""Bersihkan kategori Mature, lalu isi dengan yang benar-benar layak.

INI PENGGANTI tools/tegakkan-mature3.py, dan bedanya penting: alat ini juga
MENAMBAH, bukan hanya membuang.

Keadaan yang diperbaiki:

Kategori "Mature 18+" berisi 319 entri, dan setelah diperiksa satu per satu:

    271  tidak punya bukti apa pun - bukan kata dewasa, bukan tag dewasa
         ("2B Silent Elegance", "Acheron (Honkai Star Rail)", "Akagimi")
     80  hanya dibenarkan kata generik - "girl", "maid", "idol", "waifu"
     21  punya bukti

Jadi 94% isinya salah kamar. Tetapi membuang 298 entri saja akan meninggalkan
kategori yang isinya sedikit, dan permintaannya adalah kategori itu harus banyak
dan isinya bagus. Karena itu dua hal dikerjakan sekaligus:

  1. BUANG yang tidak punya bukti - dan kembalikan ke kategori yang benar
     (Gaming / Anime Girls / Anime Loop), bukan dibuang dari katalog. Wallpaper
     itu tetap bagus, hanya salah kamar.

  2. ISI dengan yang layak, dari dua sumber yang buktinya bisa diaudit:

     a. build/catalog-moewalls/adopted.json - 6792 wallpaper moewalls yang sudah
        dikumpulkan LENGKAP DENGAN videoUrl, dan setiap item membawa daftar tag
        dari situsnya sendiri. Tag "swimsuit" atau "lingerie" di sana adalah
        penilaian moewalls, bukan tebakan atas judul.

     b. Judul dengan daftar kata KETAT - hanya kata yang tidak punya arti lain
        di sebuah wallpaper.

Kata yang DIBUANG dari daftar lama, beserta alasan mengapa:
    girl, girls   - ada di ribuan wallpaper anime yang tidak dewasa
    maid, bunny   - kostum, bukan konten
    idol, model   - nama Hatsune Miku dan nama karakter
    hot           - "Hot Air Balloon", "Hot Springs"
    bath, shower  - "Deadpool Bathing", "Windmill Meteor Shower"
    gym, yoga     - olahraga
    beach, pool   - pemandangan pantai dan kolam
    nurse, cheerleader, schoolgirl - kostum
    leotard, bodysuit, catsuit - pakaian super, bukan pakaian dalam

Pemakaian:
  python tools/rapikan-mature.py            (periksa saja)
  python tools/rapikan-mature.py --tulis    (terapkan)
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

# Kata yang TIDAK punya arti lain di sebuah wallpaper.
KETAT = re.compile(
    r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
    r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
    r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|naked|milf|"
    r"panties|nightgown|negligee|corset|garter|thigh-?highs?|"
    r"hot\s+girl|cute\s+hot|sexy\s+girl)\b",
    re.I)

# Tag moewalls yang menandakan konten dewasa dengan sendirinya.
#
# "bed" dan "bedroom" SENGAJA tidak ada di sini: 18 dari 21 wallpaper bertag itu
# bukan dewasa ("Galactic Bedroom View", "Pixel Room Rainy Night", "Japanese
# Room"). Yang membuat kamar tidur layak kategori dewasa bukan kamarnya.
TAG_KETAT = {
    "swimsuit", "swimwear", "bikini", "lingerie", "underwear", "bra",
    "panties", "succubus", "bath", "shower", "towel", "bunny-suit",
    "pajamas", "pyjamas", "nightgown", "negligee", "corset", "stockings",
    "garter", "thighs", "boudoir", "gravure", "pinup", "pin-up", "sexy",
    "seductive", "sensual", "sultry", "ecchi", "hentai", "lewd", "nsfw",
    "erotic", "topless", "undress", "cleavage", "busty", "voluptuous",
    "milf", "nude",
}

# Subjek bukan-manusia. Tag "bath" ada di "Deadpool Bathing" (komik), tag
# "shower" ada di "Windmill Meteor Shower" (kincir angin).
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

# Judul yang menandakan entri tidak layak apa pun tagnya.
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
    r"warframe|pubg|minecraft|roblox)\b", re.I)

ANIME = re.compile(
    r"\b(anime|manga|naruto|one piece|jujutsu|demon slayer|attack on titan|"
    r"chainsaw|frieren|dragon ball|bleach|hunter x hunter|tokyo ghoul|"
    r"my hero|spy x family|evangelion|gundam|sailor moon|inuyasha|konosuba|"
    r"re:zero|re zero|overlord|sword art online|steins|spirited away|ghibli|"
    r"vocaloid|hatsune|miku|bocchi|rascal|dandadan|oshi no ko)\b", re.I)


def kategori_baru(judul):
    """Ke mana entri pergi kalau bukan mature lagi."""
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

    # ---- 1. Buang yang tidak punya bukti ----
    sekarang = [x for x in items if x.get("category") == "Mature 18+"]
    print("  Mature sekarang : %d" % len(sekarang))
    print()

    tetap, keluar = [], []
    for x in sekarang:
        j = x.get("title") or ""
        if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
            keluar.append(x)
            continue
        if KETAT.search(j):
            tetap.append(x)
            continue
        keluar.append(x)

    print("  punya bukti (tetap) : %d" % len(tetap))
    print("  tidak punya bukti   : %d" % len(keluar))
    print()

    # ---- 2. Isi dari moewalls yang bertag jelas ----
    #
    # PENTING: seluruh 6792 moewalls SUDAH ada di katalog - irisan videoUrl-nya
    # 6792 dari 6792. Jadi yang dibutuhkan bukan MENAMBAH entri baru, melainkan
    # MEMINDAHKAN yang sudah ada ke kategori yang benar. Entri dengan tag
    # "swimsuit" atau "lingerie" saat ini duduk di Anime Girls atau Gaming, dan
    # itulah sebabnya Mature terlihat sedikit.
    #
    # Versi pertama alat ini mencari entri yang belum ada di katalog, sehingga
    # melaporkan "0 baru" dan tidak melakukan apa pun - padahal 53 wallpaper
    # bertag jelas sedang menunggu dipindahkan.
    masuk_moe = {}
    if MOE.exists():
        m = json.load(open(MOE, encoding="utf-8"))
        daftar = m if isinstance(m, list) else m.get("items", m.get("adopted", []))
        print("  moewalls diperiksa  : %d" % len(daftar))

        for x in daftar:
            tg = x.get("_tags") or []
            if isinstance(tg, str):
                tg = [tg]
            kena = {str(t).lower().strip() for t in tg} & TAG_KETAT
            if not kena:
                continue
            j = x.get("title") or ""
            if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
                continue
            v = (x.get("videoUrl") or "").strip()
            if v:
                masuk_moe[v] = sorted(kena)

    # Pindahkan entri katalog yang videonya bertag jelas.
    pindah_masuk = []
    for x in items:
        if x.get("category") == "Mature 18+":
            continue
        v = (x.get("videoUrl") or "").strip()
        if v in masuk_moe:
            j = x.get("title") or ""
            if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
                continue
            pindah_masuk.append(x)

    print("  moewalls bertag jelas: %d" % len(masuk_moe))
    print("  dipindahkan ke Mature: %d" % len(pindah_masuk))

    # Catatan: entri DesktopHut dari penelusuran tag TIDAK ditambahkan di sini.
    #
    # Kartu di halaman tag tidak memuat videoUrl - hanya halaman masing-masing
    # wallpaper yang memuatnya. Menambahkan entri tanpa videoUrl akan
    # menghasilkan kotak abu-abu di katalog, dan pemeriksa katalog memang
    # menolaknya. Menambahkannya memerlukan satu kunjungan per wallpaper, dan
    # itu pekerjaan terpisah - bukan sesuatu yang boleh disisipkan diam-diam di
    # sini dengan videoUrl kosong.
    tambah = []
    print()

    print("  == 25 yang TETAP ==")
    for x in tetap[:25]:
        print("     %-58s" % (x.get("title") or "")[:58])
    print()
    print("  == 20 yang KELUAR ==")
    for x in keluar[:20]:
        print("     %-52s -> %s" % ((x.get("title") or "")[:52],
                                    kategori_baru(x.get("title") or "")))
    print()
    print("  == 25 yang MASUK (dipindahkan) ==")
    for x in pindah_masuk[:25]:
        print("     %-58s" % (x.get("title") or "")[:58])
    print()

    akhir = len(tetap) + len(pindah_masuk) + len(tambah)
    print("  == hasil ==")
    print("     Mature sekarang : %d" % len(sekarang))
    print("     Mature nanti    : %d  (%d tetap + %d pindah + %d baru)"
          % (akhir, len(tetap), len(pindah_masuk), len(tambah)))
    print("     keluar ke lain  : %d" % len(keluar))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-rapikan")

    for x in keluar:
        x["category"] = kategori_baru(x.get("title") or "")
    for x in pindah_masuk:
        x["category"] = "Mature 18+"

    semua = items + tambah
    write_json(KATALOG, semua if isinstance(d, list) else dict(d, items=semua))

    # selected.json dipakai pemeriksa katalog.
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
    print("     katalog : %s" % KATALOG)
    print("     cadangan: %s.bak-rapikan" % KATALOG)
    print("     Mature  : %d" % len([x for x in semua if x.get("category") == "Mature 18+"]))
    print("     katalog : %d entri" % len(semua))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
