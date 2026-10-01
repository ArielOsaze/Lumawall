#!/usr/bin/env python3
"""Ambil videoUrl setiap kandidat DesktopHut, lalu tambahkan yang layak.

KENAPA ALAT INI ADA:

Kategori Mature sudah dibersihkan - 299 entri yang tidak punya bukti apa pun
sudah dikembalikan ke kategori yang benar. Sekarang isinya 58, dan itu jujur
tetapi sedikit. Permintaannya adalah kategori itu harus BANYAK dan isinya bagus,
dan kekurangan itu harus ditutup dengan wallpaper yang benar.

Halaman tag DesktopHut hanya memberi judul, tautan, dan thumbnail - TIDAK
videoUrl-nya. Hanya halaman masing-masing wallpaper yang memuat videoUrl, dan
entri tanpa videoUrl akan tampil sebagai kotak abu-abu. Karena itu setiap
kandidat yang layak dikunjungi satu per satu.

Yang dikunjungi hanya kandidat yang JUDULNYA memuat kata ketat - daftar kata
yang tidak punya arti lain di sebuah wallpaper. Halaman tagnya sendiri tidak
dipercaya: /tag/bra di DesktopHut berisi "Arcane - Jinx" dan "Rain-Soaked GT-R",
tidak satu pun berkaitan dengan "bra".

Kemajuan ditulis setiap 25 wallpaper, jadi jalannya bisa dilanjutkan.

Pemakaian:
  python tools/ambil-video-desktophut.py
  python tools/ambil-video-desktophut.py --pekerja 8
"""
import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Kata yang tidak punya arti lain di sebuah wallpaper.
KETAT = re.compile(
    r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
    r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
    r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|naked|milf|"
    r"panties|nightgown|negligee|corset|garter|thigh-?highs?|"
    r"hot\s+girl|cute\s+hot|sexy\s+girl)\b",
    re.I)

BUKAN_MANUSIA = re.compile(
    r"\b(deadpool|bojack|windmill|meteor|horse|horseman|"
    r"cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|dragon|"
    r"landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"robot|mecha|machine|ship|plane|tank|gun|skeleton|skull|"
    r"bear|dance|dancing|m4|rifle|weapon)\b",
    re.I)

TIDAK_LAYAK = re.compile(
    r"\b(boy|man|male|father|dad|son|brother|grandpa|"
    r"chibi|sd|pixel|8-?bit|sketch|drawing|logo|icon)\b", re.I)

# Halaman wallpaper DesktopHut memuat video di <video><source src="..."> atau
# dalam tag meta. Keduanya dicoba.
VIDEO = [
    re.compile(r'<source[^>]+src="([^"]+\.mp4[^"]*)"', re.I),
    re.compile(r'"contentUrl"\s*:\s*"([^"]+\.mp4[^"]*)"', re.I),
    re.compile(r'(https://www\.desktophut\.com/files/[^"\']+\.mp4)', re.I),
    re.compile(r'(https://desktophut\.com/files/[^"\']+\.mp4)', re.I),
]
RES = re.compile(r'"resolution"\s*:\s*"(\d{3,4}x\d{3,4})"|(\d{3,4})\s*[xX]\s*(\d{3,4})')


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def satu(url):
    """Satu halaman wallpaper: videoUrl dan resolusinya."""
    try:
        h = get(url)
    except urllib.error.HTTPError as e:
        return url, "", "", "HTTP %s" % e.code
    except Exception as e:
        return url, "", "", str(e)[:40]
    v = ""
    for p in VIDEO:
        m = p.search(h)
        if m:
            v = m.group(1)
            break
    if not v:
        return url, "", "", "tidak ada video"
    r = ""
    m = RES.search(h)
    if m:
        r = m.group(1) or ("%sx%s" % (m.group(2), m.group(3)))
    return url, v, r, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pekerja", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    maju = OUT / "desktophut-video.json"
    sudah = read_json(maju, {"video": {}, "gagal": {}})
    video = dict(sudah.get("video") or {})
    gagal = dict(sudah.get("gagal") or {})

    # Kandidat: judul memuat kata ketat, bukan bukan-manusia.
    sumber = OUT / "mature-kartu.json"
    if not sumber.exists():
        print("  TIDAK ADA %s - jalankan tools/panen-mature.py dulu" % sumber)
        return 1
    d = json.load(open(sumber, encoding="utf-8"))
    kartu = d.get("kartu") or {}

    calon = []
    for s, v in kartu.items():
        j = v.get("title") or ""
        u = v.get("url") or ""
        if not u or u in video or u in gagal:
            continue
        if not KETAT.search(j):
            continue
        if BUKAN_MANUSIA.search(j) or TIDAK_LAYAK.search(j):
            continue
        calon.append((s, u, j))

    print()
    print("  == kandidat DesktopHut ==")
    print("     kartu diperiksa     : %d" % len(kartu))
    print("     sudah punya videoUrl: %d" % len(video))
    print("     perlu dikunjungi    : %d" % len(calon))
    print()

    if not calon:
        print("  tidak ada yang perlu dikunjungi")
        return 0

    n = 0
    with cf.ThreadPoolExecutor(max_workers=args.pekerja) as ex:
        for url, v, r, err in ex.map(lambda a: satu(a[1]), calon):
            n += 1
            if v:
                video[url] = {"videoUrl": v, "resolution": r}
            else:
                gagal[url] = err
            if n % 25 == 0:
                write_json(maju, {"video": video, "gagal": gagal})
                print("     %d/%d  (video: %d, gagal: %d)"
                      % (n, len(calon), len(video), len(gagal)))

    write_json(maju, {"video": video, "gagal": gagal})

    print()
    print("  == hasil ==")
    print("     videoUrl didapat : %d" % len(video))
    print("     gagal            : %d" % len(gagal))
    print("     disimpan         : %s" % maju)
    print()
    print("  == 20 contoh ==")
    for u, v in list(video.items())[:20]:
        judul = next((k[2] for k in calon if k[1] == u), "")
        print("     %-50s %s" % (judul[:50], v.get("resolution") or "-"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
