#!/usr/bin/env python3
"""Panen entri baru dari wallpaperwaifu.

KENAPA ALAT INI ADA:

moewalls hanya menyisakan 175 entri yang videonya benar-benar bisa dipakai,
sementara yang diminta 500. wallpaperwaifu adalah sumber video kedua yang
strukturnya mirip: token unduhan ada di halaman detail, bukan di daftar.

Bedanya, tokennya ada di elemen id="wf-download" (moewalls memakai
id="moe-download"), dan token itu SUDAH ter-encode sehingga harus disimpan apa
adanya - sama seperti moewalls.

Alat ini melakukan hal yang sama dengan panen moewalls: kumpulkan tautan dari
halaman kategori, ambil detail setiap kandidat, lalu uji videonya supaya yang
tidak bisa diputar tidak ikut masuk.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"
HASIL = W / "build" / "wallpaperwaifu-baru.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

KATEGORI = {"anime": "Anime", "games": "Gaming", "movies": "Movies"}

POLA_TAUTAN = re.compile(r'https://wallpaperwaifu\.com/([a-z0-9\-]+)/([a-z0-9\-]+)/')
POLA_KELAS_TOKEN = re.compile(r'id="wf-download"[^>]*', re.I)
POLA_TOKEN = re.compile(r'data-url\s*=\s*"([^"]+)"', re.I)
POLA_JUDUL = re.compile(r"<title>(.*?)</title>", re.S | re.I)
POLA_THUMB = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', re.I)


def get(url, timeout=30):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return f.read().decode("utf-8", "replace")


def bersihkan(teks):
    if not teks:
        return ""
    teks = re.sub(r"<[^>]+>", "", teks)
    for a, b in [("&amp;", "&"), ("&#039;", "'"), ("&quot;", '"'), ("&#8217;", "'")]:
        teks = teks.replace(a, b)
    teks = re.sub(r"\s*[-|]\s*WallpaperWaifu\s*$", "", teks, flags=re.I)
    teks = re.sub(r"\s*Live Wallpaper\s*$", "", teks, flags=re.I)
    return " ".join(teks.split()).strip()


def uji_video(url):
    """True kalau jawabannya berkas video, bukan halaman HTML."""
    try:
        h = dict(UA)
        h["Range"] = "bytes=0-1023"
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            awal = f.read(1024)
            if not awal or "text/html" in tipe or awal.lstrip()[:1] == b"<":
                return False
            return True
    except HTTPError as e:
        if e.code == 416:
            return True
        return False
    except Exception:
        return False


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   PANEN ENTRI BARU DARI WALLPAPERWAIFU")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada = set()
    ada_video = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        v = (it.get("videoUrl") or "").strip()
        if s:
            ada.add(s)
        if v:
            ada_video.add(v)
    print("  katalog: %d entri" % len(items))
    print()

    # ── Kumpulkan tautan ──────────────────────────────────────────────────
    print("  ── mengumpulkan tautan ──")
    kandidat = {}
    for slug, nama in KATEGORI.items():
        try:
            html = get("https://wallpaperwaifu.com/%s/" % slug)
        except Exception as e:
            print("     %-8s GAGAL %s" % (slug, str(e)[:40]))
            continue
        tautan = set()
        for m in POLA_TAUTAN.finditer(html):
            if m.group(1) != slug:
                continue
            tautan.add("https://wallpaperwaifu.com/%s/%s/" % (slug, m.group(2)))
        baru = [t for t in tautan if t.rstrip("/").lower() not in ada]
        for t in baru:
            kandidat[t] = nama
        print("     %-8s %3d tautan, %3d baru" % (slug, len(tautan), len(baru)))
        time.sleep(0.6)

    print()
    print("  kandidat baru: %d" % len(kandidat))
    print()

    if not kandidat:
        print("  Tidak ada kandidat baru.")
        return 0

    # ── Ambil detail dan uji ──────────────────────────────────────────────
    print("  ── mengambil detail dan menguji video ──")
    siap = []
    gagal = 0
    for n, (url, nama) in enumerate(kandidat.items(), 1):
        try:
            html = get(url)
            token = None
            for kelas in POLA_KELAS_TOKEN.finditer(html):
                m = POLA_TOKEN.search(kelas.group(0))
                if m:
                    token = m.group(1)
                    break
            if not token:
                gagal += 1
                continue

            judul_m = POLA_JUDUL.search(html)
            thumb = POLA_THUMB.search(html)
            if not thumb:
                gagal += 1
                continue

            video = "https://go.wallpaperwaifu.com/download.php?video=" + token
            if video in ada_video:
                continue
            if not uji_video(video):
                gagal += 1
                continue

            ada_video.add(video)
            siap.append({
                "title": bersihkan(judul_m.group(1) if judul_m else ""),
                "videoUrl": video,
                "thumbnailUrl": thumb.group(1),
                "license": "WallpaperWaifu · free for personal use",
                "sourceUrl": url,
                "category": nama,
                "kind": "dynamic",
                "author": "WallpaperWaifu community",
                "animation": "",
                "resolution": "1920x1080",
            })
            print("     OK   %s" % siap[-1]["title"][:60])
        except Exception as e:
            gagal += 1
        time.sleep(0.4)

        if n % 25 == 0:
            print("     --- %d / %d (siap %d, gagal %d) ---" % (n, len(kandidat), len(siap), gagal))

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   siap dipakai : %d" % len(siap))
    print("   gagal        : %d" % gagal)
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if siap:
        HASIL.parent.mkdir(parents=True, exist_ok=True)
        HASIL.write_text(json.dumps(siap, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  disimpan: %s" % HASIL)
        print()
        for x in siap[:6]:
            print("     [%s] %s" % (x["category"], x["title"][:58]))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
