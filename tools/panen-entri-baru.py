#!/usr/bin/env python3
"""Panen entri BARU dari moewalls sampai jumlah yang diminta.

KENAPA ALAT INI ADA:

Permintaannya "tambah 500 entri baru". Alat pencari sebelumnya hanya memeriksa
delapan halaman per kategori dan menemukan 78 kandidat - cukup untuk membuktikan
ada yang baru, tidak cukup untuk 500.

Alat ini melanjutkan pekerjaan itu sampai jumlahnya tercapai, dengan dua tahap
yang dipisah supaya bisa dilanjutkan kalau terputus:

  TAHAP 1  kumpulkan tautan wallpaper dari halaman kategori, sebanyak yang
           diperlukan, lewati yang sudah ada di katalog
  TAHAP 2  ambil detail setiap kandidat: judul, thumbnail, token video, kategori

Hasil tahap 1 disimpan lebih dulu, jadi kalau tahap 2 terputus, tautan yang
sudah dikumpulkan tidak hilang dan tidak perlu di-crawl ulang.

PENTING - kenapa token video diambil dari halaman detail:
moewalls tidak menyajikan alamat video di daftar kategori. Tokennya hanya ada di
halaman masing-masing wallpaper. Tanpa token itu, entri tidak bisa diputar, dan
entri yang tidak bisa diputar lebih buruk daripada tidak ada entri sama sekali.

Pemakaian:
  python tools/panen-entri-baru.py --target 500
  python tools/panen-entri-baru.py --target 500 --lanjut   (pakai kandidat yang sudah ada)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"
KANDIDAT = W / "build" / "moewalls-baru.json"
DETAIL = W / "build" / "moewalls-detail.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

KATEGORI = ["anime", "games", "movies", "nature", "cars", "superheroes",
            "sports", "tv-shows", "technology", "abstract", "food", "music"]

POLA_TAUTAN = re.compile(r'https://moewalls\.com/([a-z0-9\-]+)/([a-z0-9\-]+-live-wallpaper)/')

# Token video ada di halaman detail, di dalam pemanggil download.
POLA_TOKEN = re.compile(r'go\.moewalls\.com/download\.php\?video=([A-Za-z0-9]+)')
POLA_JUDUL = re.compile(r'<title>(.*?)</title>', re.S | re.I)
POLA_THUMB = re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', re.I)


def get(url, timeout=30):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return f.read().decode("utf-8", "replace")


def bersihkan_judul(teks):
    if not teks:
        return ""
    teks = re.sub(r"<[^>]+>", "", teks)
    teks = teks.replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')
    # Buang akhiran yang dipakai situsnya sendiri.
    teks = re.sub(r"\s*[-|]\s*Moewalls\s*$", "", teks, flags=re.I)
    teks = re.sub(r"\s*Live Wallpaper\s*$", "", teks, flags=re.I)
    return " ".join(teks.split()).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=500)
    p.add_argument("--lanjut", action="store_true", help="pakai kandidat yang sudah ada")
    p.add_argument("--maks-halaman", type=int, default=40, help="batas halaman per kategori")
    args = p.parse_args()

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   PANEN ENTRI BARU DARI MOEWALLS  (target %d)" % args.target)
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        if s:
            ada.add(s)
    print("  katalog: %d entri" % len(items))
    print()

    # ── TAHAP 1: kumpulkan tautan ─────────────────────────────────────────
    kandidat = {}
    if args.lanjut and KANDIDAT.exists():
        kandidat = json.loads(KANDIDAT.read_text(encoding="utf-8"))
        print("  kandidat dari berkas: %d" % len(kandidat))

    if len(kandidat) < args.target:
        print("  ── tahap 1: mengumpulkan tautan ──")
        for kat in KATEGORI:
            if len(kandidat) >= args.target:
                break
            for hal in range(1, args.maks_halaman + 1):
                if len(kandidat) >= args.target:
                    break
                url = ("https://moewalls.com/%s/" % kat if hal == 1
                       else "https://moewalls.com/%s/page/%d/" % (kat, hal))
                try:
                    html = get(url)
                except Exception:
                    break
                tautan = set(m.group(0) for m in POLA_TAUTAN.finditer(html))
                if not tautan:
                    break
                baru = [t for t in tautan if t.rstrip("/").lower() not in ada
                        and t not in kandidat]
                for t in baru:
                    kandidat[t] = kat
                print("     %-12s hal %-3d  %3d tautan  -> total %d kandidat"
                      % (kat, hal, len(tautan), len(kandidat)))
                time.sleep(0.5)

        KANDIDAT.parent.mkdir(parents=True, exist_ok=True)
        KANDIDAT.write_text(json.dumps(kandidat, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print("  kandidat tersimpan: %d" % len(kandidat))
    print()

    if not kandidat:
        print("  Tidak ada kandidat. Sumber ini sudah tersedot.")
        return 1

    # ── TAHAP 2: ambil detail ─────────────────────────────────────────────
    print("  ── tahap 2: mengambil detail ──")
    detail = {}
    if DETAIL.exists():
        try:
            detail = json.loads(DETAIL.read_text(encoding="utf-8"))
            print("     detail dari berkas: %d" % len(detail))
        except Exception:
            detail = {}

    daftar = [u for u in kandidat if u not in detail][:args.target]
    print("     perlu diambil: %d" % len(daftar))
    print()

    gagal = 0
    for n, url in enumerate(daftar, 1):
        try:
            html = get(url)
            token = POLA_TOKEN.search(html)
            if not token:
                gagal += 1
                detail[url] = {"gagal": "token video tidak ditemukan"}
                continue

            judul = bersihkan_judul(POLA_JUDUL.search(html).group(1) if POLA_JUDUL.search(html) else "")
            thumb = POLA_THUMB.search(html)

            detail[url] = {
                "title": judul,
                "category": kandidat[url],
                "videoUrl": "https://go.moewalls.com/download.php?video=" + token.group(1),
                "thumbnailUrl": thumb.group(1) if thumb else "",
                "sourceUrl": url,
            }
        except Exception as e:
            gagal += 1
            detail[url] = {"gagal": str(e)[:60]}

        if n % 25 == 0:
            print("     %4d / %d  (gagal: %d)" % (n, len(daftar), gagal))
            DETAIL.parent.mkdir(parents=True, exist_ok=True)
            DETAIL.write_text(json.dumps(detail, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        time.sleep(0.35)

    DETAIL.parent.mkdir(parents=True, exist_ok=True)
    DETAIL.write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── Ringkasan ─────────────────────────────────────────────────────────
    siap = {u: d for u, d in detail.items() if not d.get("gagal")}
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   kandidat        : %d" % len(kandidat))
    print("   detail diambil  : %d" % len(detail))
    print("   SIAP DIPAKAI    : %d" % len(siap))
    print("   gagal           : %d" % gagal)
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if siap:
        print("  contoh:")
        for u, d in list(siap.items())[:6]:
            print("     [%s] %s" % (d["category"], d["title"][:60]))
            print("        video : %s" % d["videoUrl"][:78])
            print("        thumb : %s" % d["thumbnailUrl"][:78])
        print()
        print("  detail: %s" % DETAIL)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
