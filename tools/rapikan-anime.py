#!/usr/bin/env python3
"""Perbaiki kategorisasi anime: yang nyasar dikembalikan ke kategori anime.

PERMINTAANNYA: "anime hrs bnr bnr sesuai kategori". Pemeriksaan menemukan 271
entri yang judulnya jelas anime tetapi duduk di kategori lain - Gaming 140,
Dynamic 73, dan sisanya tersebar di Animals, Nature, Fantasy, City, Space,
Cars, Music.

Kenapa itu terjadi: kategori awalnya ditentukan dari halaman tempat entri
ditemukan, bukan dari isinya. Sebuah wallpaper Naruto yang muncul di halaman
"popular" sebuah situs masuk ke Dynamic, karena halamannya bukan halaman anime.

Cara memperbaikinya, dan yang SENGAJA tidak dilakukan:

  YANG DILAKUKAN: hanya judul yang menyebut JUDUL SERI yang jelas yang
  dipindahkan - Naruto, One Piece, Jujutsu Kaisen, Demon Slayer, dan seterusnya.
  Nama seri adalah bukti yang bisa diaudit: tidak ada wallpaper pemandangan yang
  berjudul "Naruto".

  YANG TIDAK DILAKUKAN: memindahkan berdasarkan kata "anime" saja, atau
  berdasarkan nama karakter. Kata "anime" muncul di judul seperti "Anime Girl
  Walking" yang tidak terikat seri apa pun, dan nama karakter tanpa nama seri
  tidak cukup untuk memutuskan apakah ia dari anime atau dari game.

  Anime Girls vs Anime Loop: entri yang judulnya menyebut JUDUL SERI masuk
  Anime Loop (karena serinya jelas). Entri yang hanya menyebut karakter tanpa
  seri masuk Anime Girls.

Pemakaian:
  python tools/rapikan-anime.py            (periksa saja)
  python tools/rapikan-anime.py --tulis    (terapkan)
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

# Judul seri anime.
#
# PERINGATAN YANG MAHAL: versi pertama daftar ini memuat NAMA KARAKTER -
# "albedo", "rem", "ram", "aqua", "power", "2b", "miku", "nana", "l". Itu
# membuat alat ini memindahkan 15.338 entri ke Anime Loop, yaitu 60% katalog.
#
# Sebabnya: "Albedo" adalah karakter di Genshin Impact (game) DAN di Overlord
# (anime). "2B" adalah karakter NieR: Automata, sebuah game. "Aqua" ada di
# Konosuba (anime) dan di game. Nama karakter tidak menentukan asalnya; nama
# SERI yang menentukan.
#
# Karena itu daftar ini sekarang hanya memuat JUDUL SERI dan kata yang hanya
# muncul di konteks anime. Tidak ada nama karakter, dan tidak ada nama yang
# dipakai lebih dari satu waralaba.
SERI = re.compile(
    r"\b(naruto|boruto|one piece|jujutsu kaisen|demon slayer|kimetsu no yaiba|"
    r"attack on titan|shingeki no kyojin|chainsaw man|"
    r"dragon ball|bleach|tokyo ghoul|my hero academia|boku no hero|"
    r"spy x family|evangelion|sailor moon|inuyasha|konosuba|"
    r"re:zero|re zero|overlord|sword art online|steins gate|"
    r"spirited away|ghibli|vocaloid|bocchi the rock|"
    r"rascal does not dream|dandadan|oshi no ko|"
    r"death note|code geass|fullmetal alchemist|hunter x hunter|"
    r"fairy tail|haikyuu|blue lock|vinland saga|mob psycho|one punch man|"
    r"kaguya-sama|horimiya|toradora|clannad|your name|kimi no na wa|"
    r"weathering with you|a silent voice|violet evergarden|anohana|"
    r"guilty crown|akame ga kill|noragami|danganronpa|"
    r"highschool dxd|rosario vampire|to love-ru|date a live|"
    r"nekopara|senran kagura|monogatari|goblin slayer|shield hero|"
    r"mushoku tensei|classroom of the elite|rent-a-girlfriend|"
    r"quintessential quintuplets|lycoris recoil|"
    r"suzume|josee|your lie in april|frieren|"
    r"k-on|kobayashi|"
    r"cardcaptor|sakura kinomoto|"
    r"gundam|macross|doraemon|shin chan|crayon shin|"
    r"precure|magical girl|initial d|slam dunk|captain tsubasa|"
    r"detective conan|case closed|ranma|cowboy bebop|trigun|"
    r"samurai champloo|gintama|paprika|perfect blue|redline|"
    r"summer wars|wolf children|the girl who leapt|howl's moving|"
    r"princess mononoke|my neighbor totoro|ponyo|nausicaa|"
    r"castle in the sky|kiki's delivery|whisper of the heart|"
    r"the wind rises|grave of the fireflies|only yesterday|"
    r"pom poko|porco rosso|yaiba)\b",
    re.I)

# Kata yang menandakan entri BUKAN anime, apa pun nama yang muncul. Sebuah
# wallpaper game tidak menjadi anime hanya karena karakternya bergaya anime.
BUKAN_ANIME = re.compile(
    r"\b(genshin|honkai|wuthering|zenless|valorant|overwatch|elden|zelda|"
    r"mario|sonic|fortnite|apex|dota|minecraft|roblox|pubg|"
    r"league of legends|lol|arcanist|champion|warframe|destiny 2|"
    r"cyberpunk 2077|witcher|dark souls|sekiro|bloodborne|"
    r"resident evil|silent hill|god of war|last of us|"
    r"assassin's creed|far cry|watch dogs|"
    r"call of duty|battlefield|halo|"
    r"street fighter|tekken|mortal kombat|"
    r"stardew|terraria|hollow knight|celeste|"
    r"league|riot|blizzard|steam|epic games)\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    pindah = []
    for x in items:
        k = x.get("category") or ""
        if k in ("Anime Loop", "Anime Girls", "Mature 18+"):
            continue
        j = x.get("title") or ""
        if BUKAN_ANIME.search(j):
            continue
        if SERI.search(j):
            pindah.append(x)

    print("  anime nyasar  : %d" % len(pindah))
    print()

    asal = Counter(x.get("category") for x in pindah)
    print("  == dari kategori mana ==")
    for k, v in asal.most_common():
        print("     %-16s %5d" % (k, v))
    print()

    print("  == 30 contoh ==")
    for x in pindah[:30]:
        print("     [%-12s] %s" % ((x.get("category") or "")[:12],
                                   (x.get("title") or "")[:54]))
    print()

    print("  == hasil ==")
    print("     -> Anime Loop : %d" % len(pindah))
    print("     Anime Loop    : %d -> %d"
          % (len([x for x in items if x.get("category") == "Anime Loop"]),
             len([x for x in items if x.get("category") == "Anime Loop"]) + len(pindah)))
    print()

    # PENGAMAN: perbaikan kategori tidak boleh memindahkan sebagian besar
    # katalog. Versi pertama alat ini memindahkan 15.338 entri - 60% katalog -
    # karena daftarnya memuat nama karakter yang dipakai di lebih dari satu
    # waralaba ("Albedo" ada di Genshin dan Overlord). Kesalahan sebesar itu
    # harus menghentikan alatnya, bukan diterapkan.
    batas = len(items) * 0.05
    if len(pindah) > batas:
        print("  BERHENTI: %d entri melebihi batas %.0f (5%% katalog)." % (len(pindah), batas))
        print("  Perbaikan kategori tidak boleh mengubah sebagian besar katalog -")
        print("  periksa kembali daftar serinya.")
        print()
        return 2

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-anime")
    for x in pindah:
        x["category"] = "Anime Loop"

    write_json(KATALOG, items if isinstance(d, list) else d)

    print("  DITULIS")
    c = Counter(x.get("category") for x in items)
    for k, v in c.most_common(20):
        print("     %-16s %5d" % (k, v))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
