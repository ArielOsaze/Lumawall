#!/usr/bin/env python3
"""Panen wallpaper dewasa dari moewalls, memakai TAG SITUSNYA SENDIRI.

KENAPA ALAT INI ADA:

Kategori "Mature 18+" pernah berisi 319 entri, tetapi setelah diperiksa satu per
satu, hanya 20 yang benar-benar dewasa. 219 entri tidak punya satu pun kata
dewasa di judulnya, dan 80 entri hanya dibenarkan kata generik seperti "girl",
"maid", "idol" - sehingga "Miku Starlight Idol" dianggap dewasa.

Penyebabnya: kategorinya ditentukan dari TEBAKAN atas kata di judul. Itu tidak
bisa bekerja. Judul wallpaper anime penuh kata seperti "girl", "maid", "bunny",
dan tidak satu pun menandakan konten dewasa.

Yang bisa bekerja adalah tag yang situsnya sendiri pakai. moewalls memberi
setiap wallpapernya daftar tag, dan tag itu tersimpan di sini - jadi tidak perlu
menebak, dan tidak perlu mempercayai halaman tag (halaman tag DesktopHut
terbukti berisi rekomendasi umum: /tag/bra di sana berisi "Arcane - Jinx" dan
"Rain-Soaked GT-R").

Diukur langsung: dari 6792 wallpaper moewalls yang sudah dikumpulkan, 252
memiliki tag dewasa yang nyata.

DUA TINGKAT, dan bedanya penting:

  JELAS    swimsuit, bikini, lingerie, succubus, panties, bra, bedroom, bed,
           bath, shower, towel, nurse, bunny-suit, pajamas, nightgown,
           negligee, corset, stockings

           Tag-tag ini menandakan pakaian dalam, kamar tidur, atau mandi. Tidak
           ada alasan lain sebuah wallpaper memakainya.

  SUGESTIF beach, summer, pool, maid, sleeping, cosplay, kiss, romantic, hot

           Tag-tag ini sering muncul di wallpaper yang sama sekali tidak
           dewasa - "beach" ada di wallpaper pemandangan pantai, "sleeping" ada
           di wallpaper kucing tidur. Ini TIDAK dipakai untuk memasukkan, hanya
           dilaporkan, supaya keputusannya bisa dilihat.

Pemakaian:
  python tools/panen-moewalls.py
  python tools/panen-moewalls.py --sugestif      (ikutkan tingkat sugestif)
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json  # noqa: E402

SUMBER = ROOT / "build" / "catalog-moewalls" / "adopted.json"
OUT = ROOT / "build" / "catalog-scrape"

# Tag yang menandakan konten dewasa dengan sendirinya. Tidak ada alasan lain
# sebuah wallpaper memakai tag ini.
#
# "bed" dan "bedroom" SENGAJA tidak ada di sini. Keduanya terlihat seperti
# penanda yang jelas, tetapi setelah diperiksa, 18 dari 21 wallpaper bertag itu
# sama sekali bukan dewasa: "Galactic Bedroom View", "Pixel Room Rainy Night",
# "Japanese Room", "Snowy Afternoon Cozy Bedroom". Yang membuat sebuah kamar
# tidur layak masuk kategori dewasa bukan kamarnya, melainkan apa yang ada di
# dalamnya - dan itu tidak bisa dibaca dari tag kamarnya.
JELAS = {
    "swimsuit", "swimwear", "bikini", "lingerie", "underwear", "bra",
    "panties", "succubus", "bath", "shower", "towel",
    "bunny-suit", "pajamas", "pyjamas", "nightgown", "negligee",
    "corset", "stockings", "garter", "thighs", "boudoir", "gravure",
    "pinup", "pin-up", "sexy", "seductive", "sensual", "sultry", "ecchi",
    "hentai", "lewd", "nsfw", "erotic", "topless", "undress", "cleavage",
    "busty", "voluptuous", "milf", "nude",
}

# Tag yang sering muncul di wallpaper biasa. Tidak dipakai untuk memasukkan.
#
# "nurse" ada di sini, bukan di atas, karena "nurse" bisa berarti perawat dalam
# adegan rumah sakit biasa. Begitu juga "bed" dan "bedroom" - keduanya terlalu
# sering muncul di wallpaper kamar tidur yang tidak dewasa.
SUGESTIF = {
    "beach", "summer", "pool", "maid", "sleeping", "cosplay", "kiss",
    "romantic", "hot", "gym", "yoga", "bunny", "kimono", "shorts",
    "bikini-model", "lingerie-model", "nightwear", "bathtub", "onsen",
    "hot-spring", "sunbathing", "swim", "nurse", "bed", "bedroom",
}

# Judul yang menandakan wallpapernya bukan manusia - pemandangan, hewan, mobil.
# "Sleeping" ada di "Sleeping Cat", dan "Beach" ada di "Tropical Beach Sunset".
BUKAN_MANUSIA = re.compile(
    r"\b(cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|"
    r"landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|room\s+view|sky|space|galaxy|nebula|"
    r"abstract|pattern|wall|architecture|temple|shrine|garden|flower|"
    r"lofi|lo-?fi|rain|snow|autumn|winter)\b",
    re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sugestif", action="store_true",
                    help="ikutkan juga tag sugestif (beach, pool, maid, ...)")
    args = ap.parse_args()

    d = json.load(open(SUMBER, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", d.get("adopted", []))
    print()
    print("  == moewalls: %d wallpaper ==" % len(items))
    print()

    jelas, sugestif = [], []
    for x in items:
        tg = x.get("_tags") or []
        if isinstance(tg, str):
            tg = [tg]
        tg = {str(t).lower().strip() for t in tg}
        judul = x.get("title") or ""
        if not judul or BUKAN_MANUSIA.search(judul):
            continue

        kena_jelas = tg & JELAS
        kena_sugestif = tg & SUGESTIF
        if kena_jelas:
            x = dict(x)
            x["_mature_tags"] = sorted(kena_jelas)
            jelas.append(x)
        elif kena_sugestif:
            x = dict(x)
            x["_mature_tags"] = sorted(kena_sugestif)
            sugestif.append(x)

    print("  JELAS    (tag menandakan dewasa) : %d" % len(jelas))
    print("  SUGESTIF (tag bisa berarti biasa): %d" % len(sugestif))
    print()

    print("  == 30 contoh JELAS ==")
    for x in jelas[:30]:
        print("     %-56s %s" % ((x.get("title") or "")[:56],
                                 ",".join(x["_mature_tags"])[:30]))
    print()
    print("  == 15 contoh SUGESTIF ==")
    for x in sugestif[:15]:
        print("     %-56s %s" % ((x.get("title") or "")[:56],
                                 ",".join(x["_mature_tags"])[:30]))
    print()

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "mature-moewalls.json", {
        "jelas": jelas,
        "sugestif": sugestif,
    })

    print("  disimpan: %s" % (OUT / "mature-moewalls.json"))
    print()

    if args.sugestif:
        print("  CATATAN: --sugestif dipakai. Tingkat sugestif IKUT dimasukkan,")
        print("  dan itu akan membawa wallpaper biasa seperti pantai dan kucing")
        print("  tidur ke kategori dewasa.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
