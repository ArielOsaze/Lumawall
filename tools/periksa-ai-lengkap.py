#!/usr/bin/env python3
"""Periksa SELURUH entri Mature baru untuk penanda AI, dengan progres tersimpan.

KENAPA ALAT INI ADA:

Sampel 60 entri bersih, tetapi 0 dari 60 hanya membuktikan bahwa bagiannya
kecil - batas keyakinan 95% untuk 0/60 masih sekitar 5%, artinya bisa ada
sekitar 50 entri AI yang tidak terlihat. Permintaannya eksplisit: "wajib
artwork bukan ai generated". Karena itu seluruhnya diperiksa.

1058 entri x 1,5 detik (jeda yang diwajibkan wallhaven) = sekitar 26 menit,
jadi hasilnya disimpan setiap 25 entri. Kalau prosesnya berhenti, menjalankan
ulang alat ini melanjutkan dari yang sudah diperiksa, bukan mengulang dari awal.
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
JEDA = 1.5

# "ai" HARUS dicocokkan sebagai kata utuh: h-AI-r, t-AI-l, r-AI-nbow semuanya
# memuat "ai", dan pencocokan substring pernah melaporkan 1022 dari 1058 entri
# sebagai karya AI.
AI_TAG = re.compile(
    r"(^|\b)(ai|a\.i\.|ai[- ]generated|ai[- ]art|generated|artificial|"
    r"midjourney|stable[- ]diffusion|novelai|niji)\b", re.I)

_terakhir = [0.0]


def get_json(url, timeout=60, percobaan=5):
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


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMERIKSA SELURUH ENTRI MATURE BARU UNTUK PENANDA AI")
print("  ══════════════════════════════════════════════════════════════════")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
mat = [e for e in items
       if e.get("category") == "Mature 18+"
       and "wallhaven" in (e.get("license", "") + e.get("videoUrl", "")).lower()]

# Id tiap entri ada di judulnya, dan itu yang diperiksa.
id_perlu = []
for e in mat:
    m = re.search(r"-\s*([A-Z0-9]{6})\s*$", e.get("title", ""))
    if m:
        id_perlu.append(m.group(1).lower())

print("  entri Mature baru : %d" % len(mat))
print("  id yang diperiksa : %d" % len(id_perlu))

# Progres sebelumnya dipakai, supaya tidak mengulang 26 menit.
sudah = {}
if HASIL.exists():
    try:
        sudah = json.load(open(HASIL, encoding="utf-8"))
        print("  sudah diperiksa   : %d" % len(sudah))
    except Exception:
        sudah = {}

sisa = [i for i in id_perlu if i not in sudah]
print("  sisa              : %d" % len(sisa))
print()

if not sisa:
    print("  semua sudah diperiksa")
else:
    for n, wid in enumerate(sisa, 1):
        dd = get_json("https://wallhaven.cc/api/v1/w/%s" % wid)
        if dd is None:
            # Gagal diambil: TIDAK dicatat, supaya dicoba lagi lain kali.
            continue
        data = dd.get("data") or {}
        tags = [str(t.get("name", "")) for t in (data.get("tags") or [])]
        kena = [t for t in tags if AI_TAG.search(t)]
        sudah[wid] = kena

        if n % 25 == 0:
            HASIL.parent.mkdir(parents=True, exist_ok=True)
            HASIL.write_text(json.dumps(sudah, ensure_ascii=False), encoding="utf-8")
            jumlah_ai = sum(1 for v in sudah.values() if v)
            print("     %4d / %4d   bertanda AI: %d" % (n, len(sisa), jumlah_ai))

    HASIL.parent.mkdir(parents=True, exist_ok=True)
    HASIL.write_text(json.dumps(sudah, ensure_ascii=False), encoding="utf-8")

print()
bertanda = {k: v for k, v in sudah.items() if v}
print("  diperiksa   : %d" % len(sudah))
print("  bertanda AI : %d" % len(bertanda))
if bertanda:
    print()
    for k, v in list(bertanda.items())[:30]:
        print("     %-10s %s" % (k, v))
    print()
    print("  Entri ini harus dibuang: permintaannya 'wajib artwork bukan ai generated'.")
    print()
    sys.exit(1)

print("  Tidak ada entri Mature baru yang ditandai AI.")
print()
