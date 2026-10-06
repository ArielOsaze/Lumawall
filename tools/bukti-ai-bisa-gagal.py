#!/usr/bin/env python3
"""Buktikan pemeriksa AI bisa GAGAL - dan berapa cakupannya.

KENAPA ALAT INI ADA:

Pemeriksa yang selalu melaporkan "0 entri AI" tidak membuktikan apa pun. Ia
harus terbukti BISA menemukan karya AI kalau ada - kalau tidak, angkanya tidak
berarti, dan itu pelajaran yang sudah berulang di proyek ini (pemeriksa katalog
sempat menyatakan katalog sehat padahal 1.152 entri belum diperiksa).

Dua hal yang diperiksa di sini:

  1. Cakupan: berapa entri Mature baru yang sebenarnya ada, dan berapa yang
     sudah diperiksa. Pemeriksaan sebelumnya berjalan saat katalog masih 1.152
     entri baru; setelah pembersihan jumlahnya berubah.

  2. Kemampuan gagal: sebuah entri wallhaven yang diketahui bertanda
     "Midjourney" disisipkan sebagai kasus uji, dan polanya HARUS menangkapnya.
     Kalau tidak, "0" tadi tidak berarti apa-apa.
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
HASIL = W / "build" / "periksa-ai.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Pola yang sama dengan tools/periksa-ai-lengkap.py.
AI_TAG = re.compile(
    r"(^|\b)("
    r"a\.i\.|"
    r"ai[- ]generated|ai[- ]art|ai[- ]illustration|"
    r"generated\s+by\s+ai|made\s+with\s+ai|made\s+by\s+ai|"
    r"artificial\s+intelligence|"
    r"midjourney|stable[- ]diffusion|novelai|niji[- ]?journey|"
    r"dall[- ]?e|dall\u00b7e"
    r")\b", re.I)

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBUKTIKAN PEMERIKSA AI BISA GAGAL + CAKUPANNYA")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── 1. Kasus uji: entri yang diketahui bertanda Midjourney ────────────────
print("  ── kasus uji: entri wallhaven yang bertanda Midjourney ──")
wid = "kx1rem"
try:
    r = urllib.request.Request("https://wallhaven.cc/api/v1/w/%s" % wid, headers=UA)
    data = json.loads(urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace"))
    tags = [t["name"] for t in (data.get("data", {}).get("tags") or [])]
    print("     id %s, tag: %s" % (wid, ", ".join(tags[:8])))
    tertangkap = [t for t in tags if AI_TAG.search(t)]
    print()
    print("     tertangkap polanya: %s" % (tertangkap or "TIDAK ADA"))
    if not tertangkap:
        print()
        print("     ! GAGAL: karya AI yang diketahui tidak terdeteksi.")
        print("       Angka '0' pada pemeriksaan sebelumnya tidak berarti apa-apa.")
        sys.exit(1)
    print()
    print("     -> BISA GAGAL. Pemeriksa ini benar-benar bisa menemukan karya AI.")
except Exception as e:
    print("     ! tidak bisa mengambil kasus uji: %s" % str(e)[:60])
    sys.exit(1)

# ── 2. Cakupan ────────────────────────────────────────────────────────────
print()
print("  ── cakupan pemeriksaan ──")
d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
mat = [e for e in items
       if e.get("category") == "Mature 18+"
       and "wallhaven" in (e.get("license", "") + e.get("videoUrl", "")).lower()]
print("     entri Mature dari wallhaven sekarang: %d" % len(mat))

id_katalog = set()
for e in mat:
    m = re.search(r"-\s*([A-Z0-9]{6})\s*$", e.get("title", ""))
    if m:
        id_katalog.add(m.group(1).lower())
print("     yang punya id                       : %d" % len(id_katalog))

sudah = set(json.load(open(HASIL, encoding="utf-8")).keys()) if HASIL.exists() else set()
print("     sudah diperiksa sebelumnya          : %d" % len(sudah))

belum = id_katalog - sudah
print("     belum diperiksa                     : %d" % len(belum))
if belum:
    print()
    for i in sorted(belum)[:20]:
        print("        %s" % i)
    if len(belum) > 20:
        print("        ... dan %d lagi" % (len(belum) - 20))
print()
