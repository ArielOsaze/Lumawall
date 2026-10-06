#!/usr/bin/env python3
"""Periksa apakah entri Mature baru ditandai AI-generated.

KENAPA ALAT INI ADA:

Permintaannya: "wajib artwork bukan ai generated yg free". Pemeriksa katalog
memeriksa judul, dan judul dari tag wallhaven jarang memuat penanda AI - jadi
"0 entri AI" di laporan bisa berarti "tidak ada yang DITANDAI", bukan "tidak
ada yang AI".

wallhaven punya tag untuk karya buatan mesin. Tag itu hanya muncul di halaman
detail, bukan di hasil pencarian. Alat ini mengambil tag sebenarnya dari
sejumlah entri Mature baru dan melaporkan berapa yang bertanda AI.

Hasilnya menentukan: kalau ada, entri itu harus dibuang - bukan dibiarkan
dengan alasan "judulnya tidak menyebut AI".
"""

import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
JEDA = 1.5
SAMPEL = 60

# Tag wallhaven yang menandakan karya buatan mesin.
#
# "ai" HARUS dicocokkan sebagai kata utuh, bukan sebagai substring: h-AI-r,
# t-AI-l, r-AI-nbow, n-AI-ls, dan p-AI-nted semuanya memuat "ai", dan
# pencocokan substring melaporkan 1022 dari 1058 entri sebagai karya AI -
# kesimpulan yang sepenuhnya salah.
AI_TAG = re.compile(
    r"(^|\b)(ai|a\.i\.|ai[- ]generated|ai[- ]art|generated|"
    r"artificial|midjourney|stable[- ]diffusion|novelai|niji)\b", re.I)

_terakhir = [0.0]


def get_json(url, timeout=60, percobaan=4):
    for i in range(percobaan):
        selang = time.time() - _terakhir[0]
        if selang < JEDA:
            time.sleep(JEDA - selang)
        try:
            r = urllib.request.Request(url, headers=UA)
            isi = urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")
            _terakhir[0] = time.time()
            return json.loads(isi)
        except Exception as e:
            _terakhir[0] = time.time()
            if "429" in str(e):
                time.sleep(20 + 15 * i)
                continue
            if i == percobaan - 1:
                return None
            time.sleep(3 * (i + 1))
    return None


def ambil(e):
    m = re.search(r"-\s*([A-Z0-9]{6})\s*$", e.get("title", ""))
    if not m:
        return None
    wid = m.group(1).lower()
    d = get_json("https://wallhaven.cc/api/v1/w/%s" % wid)
    if not d:
        return (wid, None, None)
    data = d.get("data") or {}
    tags = [str(t.get("name", "")).lower() for t in (data.get("tags") or [])]
    return (wid, tags, data.get("file_type"))


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMERIKSA PENANDA AI PADA ENTRI MATURE BARU")
print("  ══════════════════════════════════════════════════════════════════")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
mat = [e for e in items
       if e.get("category") == "Mature 18+"
       and "wallhaven" in (e.get("license", "") + e.get("videoUrl", "")).lower()]
print("  entri wallhaven di Mature: %d" % len(mat))

import random
random.seed(3)
sampel = random.sample(mat, min(SAMPEL, len(mat)))
print("  diperiksa %d entri (tag asli dari halaman detail)" % len(sampel))
print()

with ThreadPoolExecutor(max_workers=4) as ex:
    hasil = list(ex.map(ambil, sampel))

bertanda = []
gagal = 0
for h in hasil:
    if not h:
        continue
    wid, tags, ft = h
    if tags is None:
        gagal += 1
        continue
    kena = [t for t in tags if AI_TAG.search(t)]
    if kena:
        bertanda.append((wid, kena))

print("  gagal diambil : %d" % gagal)
print("  bertanda AI   : %d dari %d" % (len(bertanda), len(sampel) - gagal))
if bertanda:
    print()
    for wid, kena in bertanda[:20]:
        print("     %-10s %s" % (wid, kena))
print()

if bertanda:
    rasio = len(bertanda) / max(1, len(sampel) - gagal)
    perkiraan = int(rasio * len(mat))
    print("  PERKIRAAN: sekitar %d dari %d entri Mature baru adalah karya AI." % (perkiraan, len(mat)))
    print("  Entri itu harus dibuang - permintaannya 'wajib artwork bukan ai generated'.")
    print()
    sys.exit(1)

print("  Tidak ada penanda AI pada sampel ini.")
print()
