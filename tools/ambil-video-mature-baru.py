#!/usr/bin/env python3
"""Saring kandidat video Mature dengan kata ketat, lalu ambil videoUrl-nya.

KENAPA ALAT INI ADA:

Permintaannya: "sama tambahin lagi wallpaper dinamisnya khususnya pada bagian
mature harus ada banyak yg bagus bagus".

Kategori Mature punya 1.092 entri tetapi hanya 34 yang dinamis. Ada 274
kandidat video dari DesktopHut yang belum pernah diproses - tetapi daftar itu
TIDAK BOLEH dipercaya begitu saja. Tag page DesktopHut sudah terbukti tidak
akurat: /tag/bra berisi "Arcane - Jinx" dan "Rain-Soaked GT-R", dan daftar
kandidat ini memuat "skull-island-pirate-ship-beach" serta
"one-peace-luffy-enjoying-beach" - tidak satu pun konten dewasa.

Jadi JUDULNYA yang disaring, bukan halamannya:

  HARUS memuat kata ketat - kata yang tidak punya arti lain di sebuah
  wallpaper: bikini, swimsuit, lingerie, cleavage, dan sejenisnya.

  TIDAK BOLEH memuat kata yang menandakan bukan manusia atau bukan konten
  dewasa: landscape, car, city, ship, dan sejenisnya.

  TIDAK BOLEH memuat penanda tokoh di bawah umur - pemeriksa katalog menolak
  judul seperti itu, dan penolakan itu benar.

Hanya kandidat yang lolos kedua saringan yang halamannya dikunjungi, karena
satu kunjungan per kandidat itu mahal dan situsnya membatasi permintaan.
"""

import concurrent.futures as cf
import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KANDIDAT = W / "build" / "kandidat-video-mature.json"
SIMPAN = W / "build" / "mature-video-baru.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PEKERJA = 6

# Kata yang membenarkan kategori Mature - sama dengan tools/check-catalog.py.
KETAT = re.compile(
    r"\b(nsfw|ecchi|hentai|lewd|sexy|seductive|sensual|sultry|provocative|"
    r"erotic|lingerie|bikini|swimsuit|swimwear|cleavage|boudoir|gravure|"
    r"pin-?up|topless|undress|busty|voluptuous|stripper|nude|naked|milf|"
    r"panties|nightgown|negligee|corset|garter|thigh-?highs?|"
    r"hot\s+girl|cute\s+hot|sexy\s+girl|wet\s+shirt|micro\s+bikini)\b",
    re.I)

# Bukan manusia, atau bukan konten dewasa. Tag page DesktopHut memuat ini.
BUKAN = re.compile(
    r"\b(skull|pirate|ship|warship|battleship|deadpool|bojack|windmill|meteor|"
    r"horse|horseman|cat|cats|kitten|dog|puppy|fox|wolf|bird|animal|pet|frog|"
    r"dragon|landscape|scenery|sunset|sunrise|mountain|forest|tree|trees|"
    r"car|cars|vehicle|motorcycle|bike|gt-?r|bmw|audi|ferrari|lamborghini|"
    r"city|street|building|sky|space|galaxy|nebula|abstract|pattern|"
    r"architecture|temple|shrine|garden|flower|lofi|lo-?fi|rain|snow|"
    r"luffy|naruto|goku|ichigo|saitama|monkey|d\.?\s*luffy)\b", re.I)

# Tokoh di bawah umur: pemeriksa katalog menolak ini, dan itu benar.
UNSAFE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|"
    r"student|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|"
    r"ibuki|blue archive|juvenile)\b", re.I)

_ssl = ssl.create_default_context()
_ssl.check_hostname = False
_ssl.verify_mode = ssl.CERT_NONE


def ambil_video(slug):
    """Kunjungi halaman DesktopHut dan ambil videoUrl-nya."""
    url = "https://desktophut.com/" + slug
    try:
        r = urllib.request.Request(url, headers=UA)
        isi = urllib.request.urlopen(r, timeout=45, context=_ssl).read().decode("utf-8", "replace")
    except Exception as e:
        return slug, None, str(e)[:40]

    # videoUrl ada di <video> atau di meta og:video
    m = re.search(r'<meta\s+property="og:video"\s+content="([^"]+)"', isi)
    if not m:
        m = re.search(r'<source\s+src="([^"]+\.mp4[^"]*)"', isi)
    if not m:
        m = re.search(r'(https://[^"\']*?desktophut\.com/[^"\']*?\.mp4)', isi)
    if not m:
        return slug, None, "videoUrl tidak ada"

    video = m.group(1)
    if video.startswith("//"):
        video = "https:" + video

    # Thumbnail
    t = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', isi)
    thumb = t.group(1) if t else ""

    # Judul yang bisa dibaca
    j = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', isi)
    judul = j.group(1) if j else slug.replace("-", " ")

    # Resolusi kalau ada
    res = ""
    rm = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", isi)
    if rm:
        res = "%sx%s" % (rm.group(1), rm.group(2))

    return slug, {"videoUrl": video, "thumbnailUrl": thumb, "title": judul,
                  "resolution": res, "page": url}, ""


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MENYARING & MENGAMBIL VIDEO MATURE BARU")
print("  ══════════════════════════════════════════════════════════════════")
print()

kandidat = json.load(open(KANDIDAT, encoding="utf-8"))
semua = {}
for asal, isi in kandidat.items():
    for slug, v in isi.items():
        semua[slug] = v

print("  kandidat dari daftar: %d" % len(semua))
print()

# ── Saringan 1: judul ─────────────────────────────────────────────────────
lolos = {}
alasan = {"tidak ada kata mature": 0, "bukan manusia": 0, "judul tidak aman": 0}
for slug, v in semua.items():
    judul = (v.get("judul") or slug).replace("-", " ")
    if UNSAFE.search(judul) or UNSAFE.search(slug):
        alasan["judul tidak aman"] += 1
        continue
    if BUKAN.search(judul) or BUKAN.search(slug):
        alasan["bukan manusia"] += 1
        continue
    if not (KETAT.search(judul) or KETAT.search(slug)):
        alasan["tidak ada kata mature"] += 1
        continue
    lolos[slug] = v

print("  ── saringan judul ──")
print("     lolos  : %d" % len(lolos))
for k, n in alasan.items():
    print("     ditolak: %-24s %d" % (k, n))
print()

if not lolos:
    print("  tidak ada yang lolos")
    sys.exit(0)

print("  ── kandidat yang lolos ──")
for slug in list(lolos)[:20]:
    print("     %s" % slug[:74])
if len(lolos) > 20:
    print("     ... dan %d lagi" % (len(lolos) - 20))
print()

# ── Saringan 2: halamannya dikunjungi ─────────────────────────────────────
print("  ── mengambil videoUrl dari %d halaman ──" % len(lolos))
mulai = time.time()
hasil = {}
gagal = 0
with cf.ThreadPoolExecutor(max_workers=PEKERJA) as ex:
    for slug, data, pesan in ex.map(ambil_video, list(lolos)):
        if data:
            hasil[slug] = data
        else:
            gagal += 1

print("     berhasil: %d" % len(hasil))
print("     gagal   : %d" % gagal)
print("     waktu   : %.0f detik" % (time.time() - mulai))
print()

# Simpan
SIMPAN.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
print("  disimpan: %s" % SIMPAN)
print()

print("  ── contoh yang berhasil ──")
for slug, v in list(hasil.items())[:10]:
    print("     %-46s" % v["title"][:46])
    print("        %s" % v["videoUrl"][:84])
print()
