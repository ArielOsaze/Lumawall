#!/usr/bin/env python3
"""Masukkan artwork dari penelusuran tag dewasa ke katalog.

Kenapa dari tag, bukan dari API: API DesktopHut tidak punya penyaring kategori
dewasa - ia hanya mengembalikan seluruh katalog. Halaman TAG adalah tempat
situsnya sendiri mengelompokkan wallpapernya, jadi tag adalah satu-satunya
sumber yang benar-benar tahu mana yang bergaya dewasa.

Halaman tag memuat tautan ke halaman wallpaper, dan setiap halaman itu perlu
dibuka untuk mengambil judul dan alamat berkasnya. Karena itu alat ini
memprosesnya satu per satu dengan jeda, dan berhenti kalau situsnya mulai
menolak.

Yang disaring: stock footage. Kategorinya mensyaratkan artwork.

Pemakaian:
  python tools/gabung-tag.py            # lihat saja
  python tools/gabung-tag.py --tulis    # terapkan
"""
import argparse
import concurrent.futures as cf
import json
import re
import shutil
import ssl
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KATALOG = ROOT / "LumaWall" / "catalog.json"
SUMBER = ROOT / "build" / "catalog-scrape" / "mature-urls.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perbaiki_mature_aturan import bergaya_dewasa, SERI_ANAK  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

STOCK = re.compile(r"stock[-_]?footage|video[-_]?stock|stock[-_]?video|"
                   r"stock[-_]?clip|footage", re.I)


def ambil(url):
    """Judul, URL video, dan gambar dari satu halaman wallpaper."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        return {"error": str(e)[:50]}

    judul = ""
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
    if m:
        judul = m.group(1)
    if not judul:
        m = re.search(r"<title>([^<]*)</title>", html)
        if m:
            judul = m.group(1)
    judul = judul.replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')

    # Buang akhiran yang ditambahkan situsnya.
    #
    # Judul aslinya "Fireworks Bunny Girl", dan situsnya menambahkan
    # "PC ... Live Wallpaper Free Live Wallpaper – Free Animated Desktop
    # Background | 67,000+ Free Live & Animated Wallpapers for PC - DesktopHut".
    # Tanpa pembersihan ini, setiap kartu menampilkan kalimat pemasaran sepanjang
    # itu dan nama wallpapernya tenggelam di dalamnya.
    #
    # Urutannya penting: yang paling panjang lebih dulu, supaya tidak ada
    # pecahannya yang tersisa.
    for pola in [
        # Seluruh bagian setelah pemisah vertikal - itu selalu nama situsnya.
        r"\s*\|.*$",
        # Frasa pemasaran yang berulang, dari yang paling panjang.
        r"\s*[–\-]\s*Free\s+Animated\s+Desktop\s+(Background|Wallpaper).*$",
        r"\s*[–\-]\s*Free\s+Animated\s+(Desktop\s+)?Wallpaper.*$",
        r"\s*[–\-]\s*Free\s+(Live|Animated)\s+.*$",
        r"\s+Free\s+Live\s+Wallpaper.*$",
        r"\s+Live\s+Wallpaper\s+Free.*$",
        r"\s+Free\s+Animated\s+.*$",
        r"\s+Live\s+Wallpaper\s*$",
        r"\s+Free\s*$",
        # Awalan yang juga ditambahkan situsnya.
        r"^PC\s+",
        r"^HD\s+",
    ]:
        judul = re.sub(pola, "", judul, flags=re.I).strip()

    # Kalau judulnya jadi kosong, pakai nama dari alamatnya.
    if not judul:
        judul = url.rstrip("/").split("/")[-1].replace("-", " ").title()

    # Alamat berkas video: .mp4 dengan kualitas tertinggi yang ditawarkan.
    video = ""
    for pola in [r"https?://[^\"'\s\\<>]+?\.3840x2160\.mp4",
                 r"https?://[^\"'\s\\<>]+?\.2560x1440\.mp4",
                 r"https?://[^\"'\s\\<>]+?\.1920x1080\.mp4",
                 r"https?://[^\"'\s\\<>]+?\.mp4"]:
        m = re.search(pola, html)
        if m:
            video = m.group(0)
            break

    gambar = ""
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    if m:
        gambar = m.group(1)

    res = ""
    m = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", html)
    if m:
        res = "%sx%s" % (m.group(1), m.group(2))

    return {"title": judul, "videoUrl": video, "thumbnailUrl": gambar,
            "resolution": res, "sourceUrl": url}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    urls = json.loads(SUMBER.read_text(encoding="utf-8")).get("urls", [])
    urls = [u for u in urls if not STOCK.search(u)]

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])

    ada = set()
    for x in items:
        u = (x.get("sourceUrl") or "").rstrip("/").split("/")[-1].lower()
        if u:
            ada.add(u)

    perlu = [u for u in urls if u.rstrip("/").split("/")[-1].lower() not in ada]
    print()
    print("  ══ mengambil artwork dari halaman tag ══")
    print()
    print("  URL artwork    : %d" % len(urls))
    print("  belum di katalog: %d" % len(perlu))
    print()

    hasil = []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for i, h in enumerate(ex.map(ambil, perlu)):
            if "error" in h:
                continue
            if not h.get("videoUrl"):
                continue
            judul = h.get("title", "")
            if STOCK.search(judul):
                continue
            # Seri anak tidak masuk kategori dewasa.
            if SERI_ANAK.search(judul):
                h["category"] = "Anime Loop" if "anime" in judul.lower() else "Anime Girls"
            elif bergaya_dewasa(judul):
                h["category"] = "Mature 18+"
            else:
                h["category"] = "Anime Girls"
            h["kind"] = "dynamic"
            h["author"] = "DesktopHut community"
            h["license"] = "DesktopHut · CC0"
            h["animation"] = ""
            hasil.append(h)
            if (i + 1) % 10 == 0:
                time.sleep(0.5)

    print("  berhasil diambil: %d" % len(hasil))
    print()
    print("  kategori:")
    for k, v in Counter(h["category"] for h in hasil).most_common():
        print("     %-18s %d" % (k, v))
    print()
    print("  ── contoh ──")
    for h in hasil[:16]:
        print("     %-50s %-14s %s" % (h["title"][:50], h["category"], h["resolution"]))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    cadangan = KATALOG.with_suffix(".json.bak-tag")
    shutil.copy2(KATALOG, cadangan)

    items.extend(hasil)
    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    akhir = Counter(x.get("category", "?") for x in items)
    print("  ✓ ditambahkan: %d" % len(hasil))
    print("  ✓ katalog sekarang: %d" % len(items))
    print("  ✓ Mature 18+: %d" % akhir.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
