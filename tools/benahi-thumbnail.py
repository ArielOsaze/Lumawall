#!/usr/bin/env python3
"""Perbaiki thumbnail yang tidak bisa ditampilkan.

KENAPA ALAT INI ADA:

Ada 54 entri yang memakai thumbnail placeholder "nsfw_min.png" dari DesktopHut
sendiri - situsnya memang tidak menyediakan pratinjau untuk wallpaper itu. Dan
ada 3 entri yang thumbnailUrl-nya KOSONG. Ketiga jenis itu tampil di katalog
sebagai kotak abu-abu atau hitam, tanpa memberi tahu apa isinya.

Yang TIDAK boleh dilakukan: menyimpan thumbnail sebagai berkas lokal dengan
jalur file://. Katalog ini ikut dipaketkan ke installer dan MSIX, jadi jalur
lokal mesin ini akan menunjuk berkas yang tidak ada di PC pembeli - dan yang
tampil bukan gambar, melainkan kotak kosong. Lebih buruk daripada sekarang.

Yang dipakai: sumber thumbnail lain yang bisa diakses siapa pun.

  * Untuk DesktopHut: halaman wallpaper-nya menyediakan gambar pratinjau di
    /images/ dan /uploads/ selain placeholder itu. Yang dicari adalah gambar
    yang BUKAN placeholder, dan yang cocok dengan nama wallpapernya.

  * Kalau tidak ada: video-nya sendiri dipakai sebagai sumber gambar di sisi
    aplikasi - WebView2 bisa menampilkan frame video sebagai poster, dan
    thumbnailUrl dikosongkan supaya aplikasi memakai jalur itu.

Alat ini melaporkan mana yang berhasil, mana yang tidak, dan TIDAK menulis
jalur lokal ke katalog.
"""

import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PLACEHOLDER = "nsfw_min.png"
JEDA = 1.2
_terakhir = [0.0]


def get(url, timeout=45):
    selang = time.time() - _terakhir[0]
    if selang < JEDA:
        time.sleep(JEDA - selang)
    try:
        r = urllib.request.Request(url, headers=UA)
        isi = urllib.request.urlopen(r, timeout=timeout, context=ctx).read().decode("utf-8", "replace")
        _terakhir[0] = time.time()
        return isi
    except Exception:
        _terakhir[0] = time.time()
        return None


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMPERBAIKI THUMBNAIL YANG TIDAK BISA DITAMPILKAN")
print("  ══════════════════════════════════════════════════════════════════")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
kunci = "Items" if isinstance(d, dict) and "Items" in d else None

perlu = []
for i, e in enumerate(items):
    t = e.get("thumbnailUrl") or ""
    if not t.strip() or PLACEHOLDER in t:
        perlu.append(i)

print("  entri yang thumbnailnya tidak bisa ditampilkan: %d" % len(perlu))
print("     thumbnail kosong  : %d" % sum(1 for i in perlu if not (items[i].get("thumbnailUrl") or "").strip()))
print("     placeholder NSFW  : %d" % sum(1 for i in perlu if PLACEHOLDER in (items[i].get("thumbnailUrl") or "")))
print()

# ── Cari gambar pratinjau asli di halaman sumbernya ───────────────────────
berhasil = 0
tetap = []

for n, i in enumerate(perlu, 1):
    e = items[i]
    halaman = e.get("sourceUrl") or ""
    judul_slug = re.sub(r"[^a-z0-9]+", "-", (e.get("title") or "").lower()).strip("-")

    ketemu = None
    if halaman and "desktophut" in halaman:
        html = get(halaman)
        if html:
            # Semua gambar di halaman, kecuali placeholder dan logo.
            gambar = re.findall(r'(https://[^"\'\s]*?\.(?:jpg|jpeg|png|webp))', html)
            kandidat = []
            for g in gambar:
                gl = g.lower()
                if PLACEHOLDER in gl or "logo" in gl or "icon" in gl or "banner" in gl:
                    continue
                if "/images/" in gl and "thumb" not in gl:
                    continue
                kandidat.append(g)

            # Utamakan yang namanya mirip judulnya.
            for g in kandidat:
                if judul_slug[:22] in g.lower():
                    ketemu = g
                    break
            if not ketemu and kandidat:
                ketemu = kandidat[0]

    if ketemu:
        e["thumbnailUrl"] = ketemu
        berhasil += 1
    else:
        # Tidak ada gambar lain: thumbnailUrl dikosongkan supaya aplikasi
        # memakai video sebagai sumber pratinjaunya, bukan placeholder "NSFW"
        # yang tidak memberi tahu apa pun.
        e["thumbnailUrl"] = ""
        tetap.append(i)

    if n % 10 == 0:
        print("     %d / %d  (berhasil %d)" % (n, len(perlu), berhasil))

print()
print("  gambar pratinjau asli ditemukan : %d" % berhasil)
print("  dikosongkan (pakai video)       : %d" % len(tetap))
print()

if kunci:
    d[kunci] = items
    keluar = d
else:
    keluar = items
CATALOG.write_text(json.dumps(keluar, ensure_ascii=False, indent=1), encoding="utf-8")
print("  ditulis: %s" % CATALOG)

# Periksa ulang
kosong = sum(1 for e in items if not (e.get("thumbnailUrl") or "").strip())
ph = sum(1 for e in items if PLACEHOLDER in (e.get("thumbnailUrl") or ""))
print()
print("  thumbnail kosong sekarang : %d" % kosong)
print("  placeholder tersisa        : %d" % ph)
print()
