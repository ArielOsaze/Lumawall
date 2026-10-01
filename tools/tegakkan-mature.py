#!/usr/bin/env python3
"""Pastikan setiap entri Mature 18+ punya alasan yang bisa dibaca.

Kenapa ini perlu: kategori dewasa adalah satu-satunya kategori yang punya
AKIBAT. Kategori lain salah tempat berarti wallpaper muncul di tab yang keliru;
kategori ini salah tempat berarti sesuatu yang tidak pantas muncul di daftar
yang orang buka dengan harapan tertentu - atau sebaliknya, sesuatu yang pantas
disembunyikan di balik peringatan justru muncul tanpa peringatan.

Karena itu aturannya sederhana dan bisa diperiksa: setiap entri mature harus
punya SATU dari dua hal -
  * penanda "reviewed" - entri itu sudah ditinjau dan memang dewasa; atau
  * kata yang membenarkannya di judul atau alamatnya.

Yang tidak punya keduanya dikeluarkan ke kategori yang sesuai isinya. Contoh
yang harus keluar: "Yamato", "Yelan", "Zani Skyline Drift" - judulnya hanya
nama tokoh, tidak ada apa pun yang menandakan kategori dewasa.

Pemakaian:
  python tools/tegakkan-mature.py            # lihat saja
  python tools/tegakkan-mature.py --tulis    # terapkan
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perbaiki_mature_aturan import SERI_ANAK  # noqa: E402

# Kata yang membenarkan sebuah entri ada di kategori dewasa.
#
# Daftar ini sama dengan yang dipakai pemeriksa katalog - dan itu disengaja:
# kalau keduanya berbeda, alat ini akan mengeluarkan entri yang oleh pemeriksa
# dianggap benar, dan keduanya akan bertengkar selamanya.
PEMBENAR = {
    "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry",
    "provocative", "lingerie", "bikini", "swimsuit", "cleavage", "boudoir",
    "gravure", "pin-up", "pinup", "bath", "bathing", "shower", "hot",
    "girl", "girls", "waifu", "maid", "idol", "model", "onsen", "poolside",
    "topless", "nude", "naked", "undress", "panties", "leotard", "bodysuit",
    "catsuit", "garter", "corset", "negligee", "nightgown", "cheerleader",
    "nurse", "bunny", "gym", "yoga", "massage", "bedroom", "beach",

    # Kata yang juga membenarkan, dan harus ada di sini supaya alat ini tidak
    # mengeluarkan entri yang jelas bergaya dewasa hanya karena katanya tidak
    # ada di daftar. "Alluring" dan "Sunbathing" keduanya menandakan gaya yang
    # sama jelasnya dengan "seductive" dan "bathing".
    "alluring", "sunbathing", "swimwear", "beachwear", "flirty",
    "voluptuous", "curvy", "busty", "thigh", "thighs", "stockings",
    "heels", "sundress", "wet", "soaked", "lingerie-model",
}


def kategori_untuk(x):
    """Kategori yang sesuai isinya, untuk entri yang keluar dari Mature."""
    teks = ((x.get("title", "") or "") + " " + (x.get("sourceUrl", "") or "")).lower()
    if re.search(r"genshin|honkai|wuthering|blue archive|nikke|azur lane|"
                 r"valorant|league|dota|fortnite|apex|overwatch|minecraft|"
                 r"cyberpunk|elden|witcher|gta|pubg|roblox|arknights|"
                 r"pokemon|zelda|mario|sonic|zenless|star rail|uma musume|"
                 r"punishing|pgr|tekken|street fighter|final fantasy|"
                 r"nier|tower of fantasy|snowbreak", teks):
        return "Gaming"
    if re.search(r"naruto|one piece|jujutsu|demon slayer|attack on titan|"
                 r"chainsaw|spy x family|frieren|oshi no ko|sakura|"
                 r"solo leveling|overlord|re:zero|konosuba|vocaloid|"
                 r"hatsune|miku|anime|manga|waifu", teks):
        return "Anime Loop"
    if re.search(r"\b(space|galaxy|nebula|planet|star|cosmos|astronaut|"
                 r"moon|mars|saturn|earth|meteor|eclipse|aurora)\b", teks):
        return "Space"
    if re.search(r"\b(nature|landscape|forest|mountain|ocean|sea|beach|"
                 r"waterfall|river|lake|sunset|sunrise|sky|cloud|rain|"
                 r"snow|winter|autumn|spring|summer|flower|tree)\b", teks):
        return "Nature"
    if re.search(r"\b(city|urban|street|neon|tokyo|skyline|building|"
                 r"bridge|traffic|subway|downtown)\b", teks):
        return "City"
    if re.search(r"\b(car|cars|supercar|jdm|drift|racing|motorcycle|"
                 r"ferrari|lamborghini|porsche|bmw|nissan|toyota|honda)\b", teks):
        return "Cars"
    if re.search(r"\b(animal|cat|dog|wolf|lion|tiger|bird|eagle|owl|"
                 r"fish|shark|whale|dolphin|horse|fox|bear|dragon|snake)\b", teks):
        return "Animals"
    if re.search(r"\b(abstract|particle|geometric|pattern|fluid|gradient|"
                 r"smoke|ink|glow|minimal|3d|render|pixel)\b", teks):
        return "Abstract"
    if re.search(r"\b(movie|film|marvel|dc|star wars|harry potter|matrix|"
                 r"avengers|spiderman|batman|joker)\b", teks):
        return "Movies"
    if re.search(r"\b(fantasy|magic|wizard|knight|castle|elf|myth|demon|"
                 r"angel|fairy|vampire|samurai|ninja)\b", teks):
        return "Fantasy"
    if re.search(r"\b(horror|scary|creepy|ghost|zombie|halloween|skull|"
                 r"skeleton|death)\b", teks):
        return "Horror"
    if re.search(r"\b(music|concert|band|guitar|piano|singer|kpop)\b", teks):
        return "Music"
    if re.search(r"\b(sport|football|soccer|basketball|nba|boxing|ufc|"
                 r"mma|f1|skate|surf|ski|snowboard)\b", teks):
        return "Sports"
    return "Anime Girls"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])

    # Daftar entri yang SUDAH DITINJAU, dan itu yang menentukan.
    #
    # Pemeriksa katalog memakai daftar ini - bukan penanda di dalam entri -
    # untuk memutuskan entri mana yang boleh ada di kategori dewasa tanpa
    # alasan kata. Memakai sumber yang berbeda berarti alat ini dan pemeriksa
    # akan bertengkar: yang satu mengeluarkan entri yang oleh yang lain
    # dianggap benar.
    selected = json.loads((ROOT / "mature-audit" / "selected.json").read_text(encoding="utf-8"))
    ditinjau = {str(s["motionId"]) for s in selected}

    def motion_id(x):
        m = re.search(r"/media/(\d+)/", x.get("videoUrl", "") or "")
        return m.group(1) if m else ""

    mature = [x for x in items if x.get("category") == "Mature 18+"]
    keluar = []
    for x in mature:
        if motion_id(x) in ditinjau:
            continue

        # Seri anak tidak boleh ada di sini, apa pun katanya.
        judul = x.get("title", "") or ""
        slug = (x.get("sourceUrl", "") or "").replace("-", " ")
        if SERI_ANAK.search(judul) or SERI_ANAK.search(slug):
            keluar.append(x)
            continue

        kata = set(re.split(r"[^a-z0-9]+",
                            (judul + " " + (x.get("videoUrl", "") or "") + " " + slug).lower())) - {""}
        if not (kata & PEMBENAR):
            keluar.append(x)

    print()
    print("  ══ menegakkan kategori Mature 18+ ══")
    print()
    print("  mature sekarang  : %d" % len(mature))
    print("  akan dikeluarkan : %d" % len(keluar))
    print()
    print("  tujuan:")
    for k, v in Counter(kategori_untuk(x) for x in keluar).most_common():
        print("     %-18s %d" % (k, v))
    print()
    print("  ── daftar lengkap ──")
    for x in keluar:
        print("     %-52s -> %s" % (x.get("title", "")[:52], kategori_untuk(x)))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    cadangan = KATALOG.with_suffix(".json.bak-tegak")
    shutil.copy2(KATALOG, cadangan)

    for x in keluar:
        x["category"] = kategori_untuk(x)

    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    akhir = Counter(x.get("category", "?") for x in items)
    print("  ✓ dikeluarkan: %d" % len(keluar))
    print("  ✓ Mature 18+ sekarang: %d" % akhir.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
