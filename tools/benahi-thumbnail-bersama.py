#!/usr/bin/env python3
"""Perbaiki thumbnail yang DIPAKAI BERSAMA oleh wallpaper yang berbeda.

KENAPA ALAT INI ADA:

Pemeriksa duplikat melaporkan 3 kelompok thumbnail yang sama. Setelah diperiksa
satu per satu, TIDAK ADA wallpaper yang duplikat - videonya berbeda semua:

    Wuthering Waves Jinhsi  app1077904-preview.mp4  (halaman ...-hf0y)
    Wuthering Waves Jinhsi  app1077863-preview.mp4  (halaman ...-h02d)
    Blue Archive Hoshino    app1057942-preview.mp4
    Blue Archive Shizuka    app1057909-preview.mp4

Yang sama hanya thumbnailnya, karena DesktopHut memberi gambar pratinjau yang
sama untuk wallpaper yang berbeda - dan judul yang sama untuk dua unggahan
Jinhsi yang berbeda.

Membuang entri itu akan menghapus wallpaper yang sah. Yang benar: beri mereka
thumbnail dari frame videonya sendiri, seperti 53 entri sebelumnya.

Alat ini juga melaporkan judul yang sama persis, supaya bisa diputuskan apakah
itu memang dua wallpaper berbeda atau satu yang terunggah dua kali.
"""

import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SIMPAN = W / "site" / "assets" / "thumbs"
PUBLIK = "https://lumawall.xinet.id/assets/thumbs/"

FFMPEG = shutil.which("ffmpeg")

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   THUMBNAIL YANG DIPAKAI BERSAMA")
print("  ══════════════════════════════════════════════════════════════════")
print()

if not FFMPEG:
    print("  ! ffmpeg tidak ditemukan")
    sys.exit(1)

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
kunci = "Items" if isinstance(d, dict) and "Items" in d else None


def norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = u.split("#")[0]
    return u.rstrip("/")


# ── 1. kelompok thumbnail bersama ─────────────────────────────────────────
grup = defaultdict(list)
for i, e in enumerate(items):
    u = norm_url(e.get("thumbnailUrl"))
    if u and "lumawall.xinet.id" not in u:
        grup[u].append(i)

bersama = {u: idx for u, idx in grup.items() if len(idx) > 1}
print("  thumbnail yang dipakai lebih dari satu entri: %d kelompok" % len(bersama))
print()

# ── 2. apakah videonya juga sama? ─────────────────────────────────────────
duplikat_nyata = []
perlu_thumbnail = []

for u, idx in bersama.items():
    video = defaultdict(list)
    for i in idx:
        video[norm_url(items[i].get("videoUrl"))].append(i)

    sama = {v: ids for v, ids in video.items() if len(ids) > 1}
    if sama:
        for v, ids in sama.items():
            duplikat_nyata.append((v, ids))
            print("  ! WALLPAPER DUPLIKAT NYATA (video sama):")
            for i in ids:
                print("        [%d] %s" % (i, items[i].get("title", "")[:60]))
    else:
        # Video berbeda semua: yang sama hanya thumbnailnya.
        perlu_thumbnail.extend(idx)
        print("  thumbnail sama, video BERBEDA (%d entri) - ambil frame sendiri:" % len(idx))
        for i in idx:
            print("        [%d] %-46s %s" % (i, items[i].get("title", "")[:46],
                                             (items[i].get("videoUrl") or "")[-40:]))
    print()

if duplikat_nyata:
    print("  ! Ada %d kelompok wallpaper yang benar-benar duplikat." % len(duplikat_nyata))
    print("    Itu harus dibuang, bukan diberi thumbnail baru.")
    print()

if not perlu_thumbnail:
    print("  tidak ada yang perlu diperbaiki")
    sys.exit(0)

# ── 3. ambil frame sendiri untuk tiap entri ───────────────────────────────
print("  ── mengambil frame dari video masing-masing ──")
SIMPAN.mkdir(parents=True, exist_ok=True)
berhasil = 0
gagal = []

for n, i in enumerate(perlu_thumbnail, 1):
    e = items[i]
    video = e.get("videoUrl") or ""
    nama = re.sub(r"[^a-z0-9]+", "-", (e.get("title") or "w").lower()).strip("-")[:48]
    # Nomor indeks disertakan: judulnya bisa sama persis untuk dua wallpaper
    # berbeda, dan tanpa itu berkasnya saling menimpa.
    keluar = SIMPAN / ("%s-%d.jpg" % (nama, i))

    if not (keluar.exists() and keluar.stat().st_size > 2000):
        sumber = (e.get("sourceUrl") or "").strip() or (video.split("/download.php")[0] + "/")
        ok = False
        pesan = ""
        for detik in [None, "2"]:
            arg = [FFMPEG, "-y"]
            if detik:
                arg += ["-ss", detik]
            arg += ["-headers",
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
                    "Referer: " + sumber + "\r\n",
                    "-i", video, "-frames:v", "1", "-update", "1",
                    "-vf", "scale=640:-2", "-q:v", "4", str(keluar)]
            r = subprocess.run(arg, capture_output=True, timeout=180, errors="replace")
            if r.returncode == 0 and keluar.exists() and keluar.stat().st_size > 2000:
                ok = True
                break
            pesan = (r.stderr or "")[-120:]

        if not ok:
            gagal.append((i, pesan.replace("\n", " ")[:80]))
            continue

    e["thumbnailUrl"] = PUBLIK + keluar.name
    berhasil += 1

print()
print("  berhasil: %d" % berhasil)
print("  gagal   : %d" % len(gagal))
for i, sebab in gagal:
    print("     [%d] %s" % (i, sebab))
print()

if kunci:
    d[kunci] = items
    keluar_json = d
else:
    keluar_json = items
CATALOG.write_text(json.dumps(keluar_json, ensure_ascii=False, indent=1), encoding="utf-8")
print("  ditulis: %s" % CATALOG)

# ── 4. periksa ulang ──────────────────────────────────────────────────────
grup = defaultdict(list)
for i, e in enumerate(items):
    u = norm_url(e.get("thumbnailUrl"))
    if u:
        grup[u].append(i)
sisa = {u: idx for u, idx in grup.items() if len(idx) > 1}
print()
print("  thumbnail yang masih dipakai bersama: %d kelompok" % len(sisa))
for u, idx in list(sisa.items())[:5]:
    print("     %s" % u[-70:])
    for i in idx:
        print("        [%d] %s" % (i, items[i].get("title", "")[:56]))
print()
