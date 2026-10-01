#!/usr/bin/env python3
"""Masukkan entri API DesktopHut ke katalog, dengan kategori yang benar.

Kenapa lewat API: /api/wallpapers mengembalikan JSON terstruktur - judul, slug,
resolusi, URL pratinjau - jadi tidak perlu mengurai HTML dan tidak perlu
menebak. Resolusinya juga sudah diukur oleh situsnya, sehingga aturan "wajib
HD dan ga pecah" bisa ditegakkan tanpa mengunduh berkasnya satu per satu.

Yang dijaga:
  * Entri yang sudah ada tidak diduplikasi - dicocokkan lewat slug.
  * Stock footage dibuang. Kategorinya mensyaratkan artwork.
  * Resolusi di bawah HD dibuang.
  * Entri bergaya dewasa masuk kategori Mature 18+ dengan aturan yang sama
    seperti alat perbaikan kategori, sehingga "kategorinya sesuai" berlaku
    untuk yang baru maupun yang lama.

Pemakaian:
  python tools/gabung-api.py            # lihat saja
  python tools/gabung-api.py --tulis    # terapkan
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KATALOG = ROOT / "LumaWall" / "catalog.json"
API = ROOT / "build" / "catalog-scrape" / "api-mature.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perbaiki_mature_aturan import bergaya_dewasa  # noqa: E402

# Stock footage bukan artwork.
STOCK = re.compile(r"stock[-_]?footage|video[-_]?stock|stock[-_]?video|"
                   r"stock[-_]?clip|footage", re.I)
STOCK_JUDUL = re.compile(r"\b(stock|footage|royalty[- ]free|video[- ]stock)\b", re.I)

# Kata kunci kategori. Urutannya penting: yang khusus dulu.
KATEGORI = [
    ("Gaming", r"\b(genshin|honkai|wuthering|blue archive|nikke|azur lane|"
               r"valorant|league of legends|dota|counter[- ]strike|csgo|cs2|"
               r"fortnite|apex|overwatch|minecraft|cyberpunk|elden ring|"
               r"witcher|gta|call of duty|battlefield|pubg|roblox|"
               r"arknights|fate|evangelion|zelda|mario|pokemon|sonic|"
               r"punishing|uma musume|zenless|star rail|pgr|nikke)\b"),
    ("Anime Girls", r"\b(anime girl|waifu|idol|schoolgirl|kimono|maid|neko|"
                    r"cat[- ]girl|fox[- ]girl|vtuber|cosplay)\b"),
    ("Anime Loop", r"\b(anime|manga|shonen|seinen|isekai|mecha|gundam|naruto|"
                   r"one piece|jujutsu|demon slayer|attack on titan|"
                   r"chainsaw man|spy x family|frieren|oshi no ko)\b"),
    ("Nature", r"\b(nature|landscape|forest|mountain|ocean|sea|beach|waterfall|"
               r"river|lake|sunset|sunrise|sky|cloud|rain|snow|winter|autumn|"
               r"spring|summer|flower|tree|grass|desert|jungle|underwater|"
               r"aurora|storm|lightning)\b"),
    ("City", r"\b(city|urban|street|neon|tokyo|skyline|building|architecture|"
             r"bridge|traffic|subway|downtown|vaporwave|synthwave|retrowave)\b"),
    ("Space", r"\b(space|galaxy|nebula|planet|star|cosmos|astronaut|universe|"
              r"moon|mars|saturn|earth|black hole|sci[- ]?fi|spaceship|"
              r"meteor|asteroid|eclipse)\b"),
    ("Cars", r"\b(car|cars|supercar|jdm|drift|racing|motorcycle|bike|ferrari|"
             r"lamborghini|porsche|bmw|nissan|toyota|honda|mclaren|bugatti)\b"),
    ("Animals", r"\b(animal|cat|cats|dog|dogs|wolf|lion|tiger|bird|eagle|owl|"
                r"fish|shark|whale|dolphin|horse|fox|bear|dragon|snake|corgi)\b"),
    ("Abstract", r"\b(abstract|particle|geometric|pattern|fluid|gradient|smoke|"
                 r"ink|glow|loop|minimal|3d|render|waveform|audio|pixel)\b"),
    ("Movies", r"\b(movie|film|cinema|marvel|dc|star wars|harry potter|matrix|"
               r"avengers|spiderman|batman|joker|stranger things)\b"),
    ("Music", r"\b(music|concert|band|guitar|piano|dj|singer|kpop|bts|"
              r"billie eilish|taylor swift)\b"),
    ("Sports", r"\b(sport|football|soccer|basketball|nba|nfl|baseball|boxing|"
               r"ufc|mma|f1|formula 1|skate|surf|ski|snowboard)\b"),
    ("Fantasy", r"\b(fantasy|magic|wizard|knight|castle|elf|dwarf|myth|"
                r"mythology|demon|angel|fairy|vampire|samurai|ninja)\b"),
    ("Horror", r"\b(horror|scary|creepy|ghost|zombie|halloween|skull|"
               r"skeleton|death)\b"),
]

POLA_KATEGORI = [(nama, re.compile(pola, re.I)) for nama, pola in KATEGORI]


def kategori_untuk(judul, slug):
    """Kategori untuk satu entri: mature dulu, lalu yang khusus, lalu umum."""
    if bergaya_dewasa(judul) or bergaya_dewasa(slug.replace("-", " ")):
        return "Mature 18+"
    for nama, pola in POLA_KATEGORI:
        if pola.search(judul) or pola.search(slug.replace("-", " ")):
            return nama
    return "Dynamic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])

    ada = set()
    for x in items:
        u = (x.get("sourceUrl") or "").rstrip("/").split("/")[-1].lower()
        if u:
            ada.add(u)

    api = json.loads(API.read_text(encoding="utf-8")).get("items", [])

    baru = []
    dilewat = Counter()
    for x in api:
        slug = (x.get("slug") or "").lower()
        judul = x.get("title") or ""

        if not slug or slug in ada:
            dilewat["sudah ada"] += 1
            continue
        if STOCK.search(slug) or STOCK_JUDUL.search(judul):
            dilewat["stock footage"] += 1
            continue

        baru.append({
            "title": judul,
            "videoUrl": x.get("previewUrl") or "",
            "thumbnailUrl": x.get("thumbnailUrl") or "",
            "license": "DesktopHut · CC0",
            "sourceUrl": x.get("sourceUrl") or "",
            "category": kategori_untuk(judul, slug),
            "kind": "dynamic",
            "author": "DesktopHut community",
            "animation": "",
            "resolution": x.get("resolution") or "",
        })
        ada.add(slug)

    print()
    print("  ══ menggabungkan entri API ══")
    print()
    print("  katalog sekarang : %d" % len(items))
    print("  entri API        : %d" % len(api))
    print("  akan ditambahkan : %d" % len(baru))
    print()
    print("  dilewati:")
    for k, v in dilewat.most_common():
        print("     %-18s %d" % (k, v))
    print()
    print("  kategori entri baru:")
    for k, v in Counter(x["category"] for x in baru).most_common():
        print("     %-18s %d" % (k, v))
    print()
    print("  ── contoh entri mature baru ──")
    mat = [x for x in baru if x["category"] == "Mature 18+"]
    for x in mat[:16]:
        print("     %-54s %s" % (x["title"][:54], x["resolution"]))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    cadangan = KATALOG.with_suffix(".json.bak-api")
    shutil.copy2(KATALOG, cadangan)

    items.extend(baru)
    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    sesudah = Counter(x.get("category", "?") for x in items)
    print("  ✓ ditambahkan: %d" % len(baru))
    print("  ✓ katalog sekarang: %d" % len(items))
    print("  ✓ Mature 18+ sekarang: %d" % sesudah.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
