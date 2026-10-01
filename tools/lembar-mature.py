#!/usr/bin/env python3
"""Susun lembar kontak dari kandidat dewasa, untuk ditinjau dengan mata.

KENAPA:

Kategori "Mature 18+" pernah berisi 319 entri dan hanya 20 yang benar-benar
dewasa. Dua cara sudah dicoba dan keduanya gagal:

  1. Kata di judul. "girl", "maid", "bunny", "idol" muncul di ribuan wallpaper
     anime yang tidak dewasa. Ini yang membuat "Miku Starlight Idol" masuk
     kategori dewasa.

  2. Tag situsnya. Lebih baik, tetapi tetap tidak cukup: tag "bath" ada di
     "Deadpool Bathing" (komik), tag "shower" ada di "Windmill Meteor Shower"
     (kincir angin), dan tag "bra,panties" ada di "Bojack Horseman Chilling In
     The Pool" (kuda kartun).

Yang bisa memutuskan adalah melihat gambarnya. Karena itu alat ini menyusun
thumbnail kandidat menjadi lembar bernomor, supaya setiap kandidat bisa
dinyatakan layak atau tidak dengan melihatnya - dan keputusan itu disimpan
beserta alasannya.

Pemakaian:
  python tools/lembar-mature.py            (bangun lembar)
  python tools/lembar-mature.py --periksa  (tampilkan hasil tinjauan)
"""
import argparse
import concurrent.futures as cf
import json
import re
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json  # noqa: E402

OUT = ROOT / "build" / "mature-lembar"
STATE = ROOT / "mature-audit" / "tinjauan.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Satu lembar: 6 kolom x 5 baris = 30 thumbnail.
KOLOM, BARIS = 6, 5
TW, TH = 300, 169          # ukuran thumbnail 16:9
PAD, LABEL = 6, 22


def kandidat():
    """Semua kandidat dewasa dari setiap sumber, dengan asalnya."""
    hasil = {}

    # 1. moewalls, tag jelas
    p = ROOT / "build" / "catalog-scrape" / "mature-moewalls.json"
    if p.exists():
        d = json.load(open(p, encoding="utf-8"))
        for x in d.get("jelas", []):
            u = x.get("sourceUrl") or ""
            if u:
                hasil[u] = {"title": x.get("title", ""), "thumb": x.get("thumbnailUrl", ""),
                            "asal": "moewalls-jelas", "url": u,
                            "videoUrl": x.get("videoUrl", ""),
                            "resolution": x.get("resolution", "")}
        for x in d.get("sugestif", []):
            u = x.get("sourceUrl") or ""
            if u and u not in hasil:
                hasil[u] = {"title": x.get("title", ""), "thumb": x.get("thumbnailUrl", ""),
                            "asal": "moewalls-sugestif", "url": u,
                            "videoUrl": x.get("videoUrl", ""),
                            "resolution": x.get("resolution", "")}

    # 2. desktophut, judul memuat kata dewasa
    p = ROOT / "build" / "catalog-scrape" / "mature-kartu.json"
    if p.exists():
        d = json.load(open(p, encoding="utf-8"))
        for s, x in (d.get("kartu") or {}).items():
            u = x.get("url") or ""
            if u and u not in hasil:
                hasil[u] = {"title": x.get("title", ""), "thumb": x.get("thumbnailUrl", ""),
                            "asal": "desktophut", "url": u, "videoUrl": "",
                            "resolution": x.get("resolution", "")}

    # 3. katalog sekarang: entri mature yang judulnya memuat kata dewasa kuat
    KUAT = re.compile(
        r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
        r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
        r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|milf)\b", re.I)
    p = ROOT / "LumaWall" / "catalog.json"
    if p.exists():
        d = json.load(open(p, encoding="utf-8"))
        items = d if isinstance(d, list) else d.get("items", [])
        for x in items:
            if x.get("category") != "Mature 18+":
                continue
            if not KUAT.search(x.get("title") or ""):
                continue
            u = x.get("sourceUrl") or x.get("videoUrl") or ""
            if u and u not in hasil:
                hasil[u] = {"title": x.get("title", ""), "thumb": x.get("thumbnailUrl", ""),
                            "asal": "katalog-sekarang", "url": u,
                            "videoUrl": x.get("videoUrl", ""),
                            "resolution": x.get("resolution", "")}

    return hasil


def unduh(slug, url):
    """Satu thumbnail. Mengembalikan (slug, bytes atau None)."""
    if not url:
        return slug, None
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return slug, r.read()
    except Exception:
        return slug, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periksa", action="store_true")
    args = ap.parse_args()

    if args.periksa:
        t = read_json(STATE, {})
        putusan = t.get("putusan", {})
        layak = [k for k, v in putusan.items() if v.get("layak")]
        print()
        print("  ditinjau : %d" % len(putusan))
        print("  layak    : %d" % len(layak))
        print("  tidak    : %d" % (len(putusan) - len(layak)))
        print()
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    k = kandidat()
    print()
    print("  == kandidat: %d ==" % len(k))
    from collections import Counter
    for a, n in Counter(v["asal"] for v in k.values()).most_common():
        print("     %-20s %4d" % (a, n))
    print()

    # Urut tetap, supaya nomor di lembar tidak berubah antar-jalan.
    urut = sorted(k.items())
    print("  mengunduh %d thumbnail ..." % len(urut))
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        hasil = dict(ex.map(lambda a: unduh(a[0], a[1]["thumb"]), urut))

    ada = [(u, v) for u, v in urut if hasil.get(u)]
    print("  thumbnail berhasil: %d dari %d" % (len(ada), len(urut)))
    print()

    # Simpan thumbnail ke disk, lalu susun lembar dengan PowerShell.
    th_dir = OUT / "thumbs"
    th_dir.mkdir(exist_ok=True)
    nomor = {}
    for i, (u, v) in enumerate(ada, 1):
        f = th_dir / ("%04d.jpg" % i)
        f.write_bytes(hasil[u])
        nomor["%04d" % i] = {"url": u, "title": v["title"], "asal": v["asal"],
                             "videoUrl": v.get("videoUrl", ""),
                             "resolution": v.get("resolution", ""),
                             "thumbnailUrl": v.get("thumb", "")}

    write_json(OUT / "nomor.json", nomor)

    # Susun lembar dengan PIL.
    #
    # Versi pertama memakai PowerShell + System.Drawing, dan hasilnya lembar
    # yang KOSONG: ukurannya benar, tetapi tidak satu pun thumbnail tergambar.
    # Sebabnya akses properti dinamis `$nomor.$nama` dengan nama berawalan
    # angka - PowerShell membacanya sebagai angka, bukan sebagai nama properti.
    # Dibangun ulang dengan PIL, yang tidak punya masalah itu.
    from PIL import Image, ImageDraw, ImageFont

    def font(ukuran, tebal=False):
        for nama in (("seguisb.ttf" if tebal else "segoeui.ttf"),
                     "arial.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(nama, ukuran)
            except Exception:
                continue
        return ImageFont.load_default()

    f_nomor = font(20, True)
    f_judul = font(14)

    per = KOLOM * BARIS
    w = KOLOM * (TW + PAD) + PAD
    h = BARIS * (TH + LABEL + PAD) + PAD

    kunci = sorted(nomor)
    jumlah = (len(kunci) + per - 1) // per
    ditulis = []
    for l in range(jumlah):
        kanvas = Image.new("RGB", (w, h), (18, 18, 20))
        g = ImageDraw.Draw(kanvas)
        for i in range(per):
            idx = l * per + i
            if idx >= len(kunci):
                break
            nama = kunci[idx]
            f = th_dir / (nama + ".jpg")
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
            g.text((x, y + TH + 2), "#" + nama, font=f_nomor, fill=(255, 214, 10))
            judul = (nomor[nama].get("title") or "")[:46]
            g.text((x + 52, y + TH + 6), judul, font=f_judul, fill=(190, 190, 196))
        keluar = OUT / ("lembar-%02d.jpg" % (l + 1))
        kanvas.save(keluar, quality=88)
        ditulis.append(keluar)

    print("  lembar tersusun: %d" % len(ditulis))
    print()
    print("  nomor.json : %s" % (OUT / "nomor.json"))
    print("  lembar     : %s" % OUT)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
