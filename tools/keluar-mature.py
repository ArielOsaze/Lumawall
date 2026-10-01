#!/usr/bin/env python3
"""Keluarkan entri yang tidak layak dari kategori Mature 18+.

Kenapa ini perlu terpisah: pemeriksa katalog sudah menetapkan batas yang jelas -
tidak ada tokoh anak-anak, tidak ada seri yang tokohnya berseragam sekolah -
dan 25 entri di kategori Mature melanggar batas itu. Mereka masuk karena aturan
kategori sebelumnya menyaring dari KATA ("swimsuit", "bikini") tanpa melihat
SIAPA yang ada di gambar.

Contoh yang harus keluar:
  "Blue Archive Chiaki Swimsuit"     - tokoh berseragam sekolah
  "Schoolgirl Chisa Wuthering Waves" - namanya sudah menyebut sekolah
  "Pokemon - Gengar Bathing"         - seri Pokemon

Yang TIDAK dikeluarkan: entri yang tokohnya jelas dewasa. "2B Bodysuit" adalah
tokoh dewasa dari NieR, dan "Prinz Eugen Bikini" dari Azur Lane - keduanya tetap
di kategori Mature. Aturannya memakai daftar seri dan penanda usia, bukan
kecurigaan atas pakaiannya.

Pemakaian:
  python tools/keluar-mature.py            # lihat saja
  python tools/keluar-mature.py --tulis    # terapkan
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

# Penanda usia yang eksplisit. Ini dipakai bersama SERI_ANAK.
USIA = re.compile(
    r"\b(loli|lolita|child|kid|kids|little\s+girl|baby|infant|toddler|"
    r"daughter|schoolgirl|school\s+girl|student|elementary|middle\s+school|"
    r"kindergarten|nursery|juvenile|underage|teen|teenager)\b",
    re.I,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])

    mature = [x for x in items if x.get("category") == "Mature 18+"]
    keluar = []
    for x in mature:
        judul = x.get("title", "") or ""
        slug = (x.get("sourceUrl", "") or "").replace("-", " ")
        if SERI_ANAK.search(judul) or SERI_ANAK.search(slug):
            keluar.append(x)
        elif USIA.search(judul) or USIA.search(slug):
            keluar.append(x)

    # Ke mana mereka pergi: kembali ke kategori yang sesuai isinya, bukan
    # ditumpuk ke satu keranjang. Wallpaper Blue Archive adalah wallpaper game.
    def kategori_baru(x):
        judul = (x.get("title", "") or "").lower()
        slug = (x.get("sourceUrl", "") or "").lower()
        teks = judul + " " + slug
        if re.search(r"genshin|honkai|wuthering|blue archive|nikke|azur lane|"
                     r"valorant|league|dota|fortnite|apex|overwatch|minecraft|"
                     r"cyberpunk|elden|witcher|gta|pubg|roblox|arknights|"
                     r"pokemon|zelda|mario|sonic|zenless|star rail|uma musume|"
                     r"punishing|nikke|pgr", teks):
            return "Gaming"
        if re.search(r"naruto|one piece|jujutsu|demon slayer|attack on titan|"
                     r"chainsaw|spy x family|frieren|oshi no ko|anime|manga", teks):
            return "Anime Loop"
        return "Anime Girls"

    print()
    print("  ══ entri yang keluar dari Mature 18+ ══")
    print()
    print("  akan dikeluarkan : %d dari %d" % (len(keluar), len(mature)))
    print()
    print("  tujuan:")
    for k, v in Counter(kategori_baru(x) for x in keluar).most_common():
        print("     %-18s %d" % (k, v))
    print()
    print("  ── daftar lengkap ──")
    for x in keluar:
        print("     %-52s -> %s" % (x.get("title", "")[:52], kategori_baru(x)))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    cadangan = KATALOG.with_suffix(".json.bak-keluar")
    shutil.copy2(KATALOG, cadangan)

    for x in keluar:
        x["category"] = kategori_baru(x)

    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    akhir = Counter(x.get("category", "?") for x in items)
    print("  ✓ dikeluarkan: %d" % len(keluar))
    print("  ✓ Mature 18+ sekarang: %d" % akhir.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
