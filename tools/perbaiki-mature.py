#!/usr/bin/env python3
"""Perbaiki entri bergaya dewasa yang salah kategori di katalog.

Kenapa alat ini ada: dari 22.879 entri, hanya 249 yang masuk kategori
"Mature 18+", sementara 157 entri lain yang judulnya jelas bergaya dewasa
- "Swimsuit", "Bikini", "Hot Spring", "Gym Ver.", "Idol" - tersebar di
Gaming, Anime Girls, dan Anime Loop.

Permintaannya ada dua, dan keduanya dilanggar oleh keadaan itu:
  * "khususnya pada bagian mature harus ada banyak yg bagus bagus" - kategori
    mature harus berisi, bukan kosong;
  * "pastikan kategorinya sesuai jangan nyasar khususnya yg mature" - dan
    sebaliknya, yang bergaya dewasa tidak boleh tertinggal di kategori lain.

Alat ini memindahkan yang salah tempat ke tempatnya, dan hanya itu. Yang tidak
dipindahkan: entri yang judulnya hanya menyebut kata yang mirip tetapi maksudnya
lain - "gym" pada "Gym Leader" adalah tokoh Pokemon, bukan latihan; "maid" pada
"Maid Cafe" bisa berarti apa saja. Karena itu setiap kata punya syaratnya
sendiri, dan yang tidak yakin dibiarkan di tempatnya.

Pemakaian:
  python tools/perbaiki-mature.py            # lihat saja
  python tools/perbaiki-mature.py --tulis    # tulis perubahannya
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

# Kata yang menandakan gaya dewasa, beserta pengecualiannya.
#
# Yang penting di sini adalah PENGECUALIANNYA, bukan daftar katanya. Tanpa itu,
# "Gym Leader" (tokoh Pokemon) dan "Maid Cafe" (adegan sehari-hari) akan ikut
# pindah, dan kategori mature justru menjadi tempat sampah - persis yang tidak
# diinginkan.
ATURAN = [
    # Pakaian renang dan pakaian dalam: hampir selalu bergaya dewasa.
    (r"\b(bikini|swimsuit|swimwear|beachwear|lingerie|boudoir|negligee|"
     r"nightgown|garter|corset|leotard|bodysuit|catsuit|panties)\b", None),

    # Kata sifat yang menyebut daya tarik.
    (r"\b(seductive|sensual|sultry|provocative|sexy|flirty|alluring)\b", None),

    # Keadaan yang biasanya dipakai untuk menampilkan tubuh.
    #
    # "Shower" TIDAK ada di daftar ini, dan itu keputusan yang disengaja:
    # "Meteor Shower" adalah hujan meteor, dan "Rice Shower" adalah nama tokoh
    # Uma Musume. Memasukkan kata itu akan memindahkan wallpaper luar angkasa
    # dan balapan kuda ke kategori dewasa - persis "kategorinya nyasar" yang
    # harus dihindari, hanya saja ke arah sebaliknya.
    (r"\b(hot[-\s]?spring|onsen|bathing|poolside|sunbathing|"
     r"beach[-\s]?bikini|swimsuit[-\s]?selfie|bikini[-\s]?selfie)\b", None),

    # Pakaian yang menandakan tema tertentu - dengan pengecualian.
    #
    # "Bunny" sangat sering menjadi bagian NAMA TOKOH, bukan pakaian: Haxxor
    # Bunny (Bronya, Honkai), Winter Bunny (Gawr Gura), Bunny Hoodie. Yang
    # dimaksud di sini adalah kostum bunny yang memang menampilkan bentuk.
    (r"\b(maid|nurse|cheerleader|schoolgirl|gravure|pin[-\s]?up)\b",
     r"\b(maid\s+cafe|cheerleader\s+uniform\s+only|schoolgirl\s+uniform\s+only)\b"),

    (r"\bbunny\s+(girl|suit|outfit|costume|dress|leotard)\b", None),

    # "Gym" dan "Yoga" menandakan pakaian olahraga yang ketat - KECUALI kalau
    # yang dimaksud adalah tokoh atau tempat.
    (r"\b(gym|yoga)\b",
     r"\b(gym\s+leader|pokemon\s+gym|gym\s+badge|gym\s+interior|"
     r"yoga\s+class\s+only|gym\s+time\s+only)\b"),

    # "Idol" HANYA dihitung kalau disertai penanda penampilan. Sebagai kata
    # tunggal ia terlalu umum: "Idol Master" adalah nama game, dan "Idol"
    # sendirian bisa berarti apa saja.
    (r"\b(idol\s+(live|stage|performance|debut|costume|outfit|style)|"
     r"starlight\s+idol|idol\s+ver)\b", None),

    # Kata yang sudah pasti.
    (r"\b(ecchi|lewd|nsfw|hentai|waifu|sexy\s+girl|hot\s+girl)\b", None),
]

POLA = []
for kata, kecuali in ATURAN:
    POLA.append((re.compile(kata, re.I), re.compile(kecuali, re.I) if kecuali else None))


def bergaya_dewasa(judul):
    """Apakah judul ini bergaya dewasa, menurut aturan di atas."""
    for pola, kecuali in POLA:
        if pola.search(judul):
            if kecuali and kecuali.search(judul):
                continue
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true", help="tulis perubahannya")
    args = ap.parse_args()

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])

    pindah = []
    for x in items:
        if x.get("category") == "Mature 18+":
            continue
        if bergaya_dewasa(x.get("title", "") or ""):
            pindah.append(x)

    print()
    print("  ══ entri yang salah kategori ══")
    print()
    print("  akan dipindahkan ke Mature 18+ : %d" % len(pindah))
    print()
    print("  dari kategori:")
    for k, v in Counter(x.get("category", "?") for x in pindah).most_common():
        print("     %-24s %d" % (k, v))
    print()

    print("  ── contoh yang akan dipindahkan ──")
    for x in pindah[:22]:
        print("     %-54s %s -> Mature 18+" % (x.get("title", "")[:54], x.get("category", "?")))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    # Cadangan dulu: katalog ini dibangun berjam-jam dan tidak boleh hilang
    # karena satu perubahan yang salah.
    cadangan = KATALOG.with_suffix(".json.bak-mature")
    shutil.copy2(KATALOG, cadangan)

    for x in pindah:
        x["category"] = "Mature 18+"

    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    sesudah = Counter(x.get("category", "?") for x in items)
    print("  ✓ dipindahkan: %d" % len(pindah))
    print("  ✓ Mature 18+ sekarang: %d" % sesudah.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
