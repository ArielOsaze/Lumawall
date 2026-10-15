#!/usr/bin/env python3
"""Panen wallpaper dari wallhaven - kategori umum, bukan dewasa.

KENAPA ALAT INI ADA:

Tiga sumber video sudah habis:
  moewalls       : 253 kandidat, 175 videonya benar-benar bisa dipakai
  motionbgs      : 10.635 slug, SEMUA sudah ada di katalog
  desktophut     : 6 tautan, dan itu bukan tautan wallpaper
  wallpaperwaifu : 67 kandidat, 22 videonya bisa dipakai

Total 197 entri baru, sementara yang diminta 500. wallhaven adalah sumber
terbesar yang tersisa: 17.963 hasil untuk kategori anime saja.

PENTING - wallhaven menyajikan GAMBAR, bukan video. Entri dari sini masuk
sebagai kind="static", sama seperti 1.081 entri wallhaven yang sudah ada di
katalog. Aplikasi menanganinya dengan kenburns (gambar diam dibuat bergerak),
dan itu sudah terbukti bekerja.

KENAPA purity=100:
wallhaven memakai tiga bit purity: SFW, sketchy, dan both. Nilainya diukur
langsung sebelumnya - 100 adalah SFW, 010 adalah sketchy, dan 110 keduanya.
Alat ini memakai 100 supaya yang diambil adalah wallpaper biasa, bukan yang
sensitif; entri dewasa sudah punya alatnya sendiri.

KENAPA sorting=date_added:
toplist TANPA topRange membatasi hasil di 67 - itu sudah diukur dan itu sebabnya
panen sebelumnya selalu berhenti di angka puluhan. date_added memberi 17.963.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"
HASIL = W / "build" / "wallhaven-baru.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}

# Kata kunci yang menghasilkan wallpaper bergaya game/anime, sesuai isi katalog.
KUNCI = [
    ("anime landscape", "Anime"),
    ("cyberpunk city", "Gaming"),
    ("fantasy landscape", "Nature"),
    ("space nebula", "Abstract"),
    ("samurai", "Anime"),
    ("mecha robot", "Gaming"),
    ("dark fantasy castle", "Movies"),
    ("japanese street night", "Nature"),
]


def get(url, timeout=45):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return json.loads(f.read().decode("utf-8", "replace"))


def bersihkan_judul(path):
    """Nama berkas wallhaven dipakai sebagai judul, dipisah tanda hubung."""
    nama = path.rstrip("/").split("/")[-1]
    nama = re.sub(r"\.[a-z0-9]+$", "", nama, flags=re.I)
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", nama) if w)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=320)
    args = p.parse_args()

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   PANEN WALLHAVEN (kategori umum, target %d)" % args.target)
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada_sumber = set()
    ada_thumb = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        t = (it.get("thumbnailUrl") or "").strip()
        if s:
            ada_sumber.add(s)
        if t:
            ada_thumb.add(t)
    print("  katalog: %d entri" % len(items))
    print()

    siap = []
    sudah = set()

    for kunci, kategori in KUNCI:
        if len(siap) >= args.target:
            break
        print("  ── %s -> %s ──" % (kunci, kategori))
        halaman = 1
        while len(siap) < args.target and halaman <= 12:
            url = ("https://wallhaven.cc/api/v1/search"
                   "?q=%s&categories=111&purity=100&atleast=1920x1080"
                   "&ratios=16x9&sorting=date_added&per_page=24&page=%d"
                   % (kunci.replace(" ", "%20"), halaman))
            try:
                jawab = get(url)
            except HTTPError as e:
                print("     halaman %d: HTTP %d" % (halaman, e.code))
                break
            except Exception as e:
                print("     halaman %d: %s" % (halaman, str(e)[:50]))
                break

            hasil = jawab.get("data") or []
            if not hasil:
                break

            masuk = 0
            for w_ in hasil:
                path = w_.get("path")
                thumb = w_.get("thumbs", {}).get("large") or w_.get("thumbs", {}).get("original")
                sumber = w_.get("url")
                if not path or not thumb or not sumber:
                    continue
                if sumber.rstrip("/").lower() in ada_sumber or thumb in ada_thumb:
                    continue
                if sumber in sudah:
                    continue
                sudah.add(sumber)

                res = "%sx%s" % (w_.get("dimension_x", 1920), w_.get("dimension_y", 1080))
                siap.append({
                    "title": bersihkan_judul(path),
                    "videoUrl": path,
                    "thumbnailUrl": thumb,
                    "license": "Wallhaven · free for personal use",
                    "sourceUrl": sumber,
                    "category": kategori,
                    "kind": "static",
                    "author": "Wallhaven community",
                    "animation": "",
                    "resolution": res,
                })
                masuk += 1

            print("     halaman %-2d  %2d hasil  (+%d)  total %d"
                  % (halaman, len(hasil), masuk, len(siap)))
            halaman += 1
            time.sleep(0.8)
        print()

    print("  ══════════════════════════════════════════════════════════════════")
    print("   siap dipakai : %d" % len(siap))
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if siap:
        from collections import Counter
        for k, n in Counter(x["category"] for x in siap).most_common():
            print("     %-16s %5d" % (k, n))
        print()
        HASIL.parent.mkdir(parents=True, exist_ok=True)
        HASIL.write_text(json.dumps(siap, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  disimpan: %s" % HASIL)
        print()
        for x in siap[:5]:
            print("     [%s] %s" % (x["category"], x["title"][:56]))
            print("        %s" % x["videoUrl"][:84])
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
