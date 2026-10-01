#!/usr/bin/env python3
"""Susun lembar kontak dari entri Mature YANG ADA DI KATALOG, untuk ditinjau.

KENAPA ALAT INI TERPISAH:

tools/lembar-mature.py menyusun lembar dari KANDIDAT BARU - wallpaper yang belum
ada di katalog, ditemukan dari tag moewalls dan judul desktophut. Lembar itu
menjawab "apa yang bisa DITAMBAHKAN".

Alat ini menyusun lembar dari entri yang SUDAH ada di kategori Mature. Itu
pertanyaan yang berbeda dan lebih mendesak: dari 319 entri yang sekarang ada di
sana, berapa yang benar-benar layak? Pemeriksaan awal menunjukkan hanya 20.

Lembarnya memakai thumbnailUrl yang sudah tersimpan di katalog, jadi tidak perlu
mengunduh apa pun - dan yang ditinjau persis entri yang dikirim ke pengguna,
bukan kandidat.

Pemakaian:
  python tools/lembar-katalog.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json  # noqa: E402

OUT = ROOT / "build" / "mature-katalog-lembar"
KATALOG = ROOT / "LumaWall" / "catalog.json"

KOLOM, BARIS = 6, 5
TW, TH = 300, 169
PAD, LABEL = 6, 24


def main():
    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    mat = [x for x in items if x.get("category") == "Mature 18+"]

    print()
    print("  == entri Mature di katalog: %d ==" % len(mat))
    print()

    OUT.mkdir(parents=True, exist_ok=True)

    # Nomor tetap: urut judul, supaya nomor di lembar tidak berubah.
    mat.sort(key=lambda x: (x.get("title") or "").lower())
    nomor = {}
    for i, x in enumerate(mat, 1):
        k = "%04d" % i
        nomor[k] = {
            "title": x.get("title") or "",
            "thumb": x.get("thumbnailUrl") or "",
            "videoUrl": x.get("videoUrl") or "",
            "sourceUrl": x.get("sourceUrl") or "",
            "resolution": x.get("resolution") or "",
            "category_lama": x.get("category") or "",
        }
    write_json(OUT / "nomor.json", nomor)

    from PIL import Image, ImageDraw, ImageFont
    import concurrent.futures as cf
    import ssl
    import urllib.request

    CTX = ssl.create_default_context()
    CTX.check_hostname = False
    CTX.verify_mode = ssl.CERT_NONE
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def unduh(k):
        u = nomor[k]["thumb"]
        if not u:
            return k, None
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
                return k, r.read()
        except Exception:
            return k, None

    print("  mengunduh %d thumbnail ..." % len(nomor))
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        hasil = dict(ex.map(unduh, sorted(nomor)))
    ada = {k: b for k, b in hasil.items() if b}
    print("  berhasil: %d dari %d" % (len(ada), len(nomor)))
    print()

    th_dir = OUT / "thumbs"
    th_dir.mkdir(exist_ok=True)
    for k, b in ada.items():
        (th_dir / (k + ".jpg")).write_bytes(b)

    def font(ukuran, tebal=False):
        for nama in (("seguisb.ttf" if tebal else "segoeui.ttf"),
                     "arial.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(nama, ukuran)
            except Exception:
                continue
        return ImageFont.load_default()

    f_nomor = font(20, True)
    f_judul = font(13)

    per = KOLOM * BARIS
    w = KOLOM * (TW + PAD) + PAD
    h = BARIS * (TH + LABEL + PAD) + PAD
    kunci = sorted(ada)
    jumlah = (len(kunci) + per - 1) // per

    for l in range(jumlah):
        kanvas = Image.new("RGB", (w, h), (18, 18, 20))
        g = ImageDraw.Draw(kanvas)
        for i in range(per):
            idx = l * per + i
            if idx >= len(kunci):
                break
            k = kunci[idx]
            f = th_dir / (k + ".jpg")
            if not f.exists():
                continue
            kol, bar = i % KOLOM, i // KOLOM
            x = PAD + kol * (TW + PAD)
            y = PAD + bar * (TH + LABEL + PAD)
            try:
                img = Image.open(f).convert("RGB").resize((TW, TH), Image.LANCZOS)
                kanvas.paste(img, (x, y))
            except Exception:
                g.rectangle([x, y, x + TW, y + TH], fill=(40, 40, 44))
            g.text((x, y + TH + 3), "#" + k, font=f_nomor, fill=(255, 214, 10))
            judul = (nomor[k]["title"] or "")[:52]
            g.text((x + 56, y + TH + 7), judul, font=f_judul, fill=(190, 190, 196))
        kanvas.save(OUT / ("lembar-%02d.jpg" % (l + 1)), quality=88)

    print("  lembar tersusun: %d" % jumlah)
    print("  %s" % OUT)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
