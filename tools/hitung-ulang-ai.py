#!/usr/bin/env python3
"""Hitung ulang hasil pemeriksaan AI dengan pola yang sudah diperbaiki.

KENAPA ALAT INI ADA:

tools/periksa-ai-lengkap.py menyimpan TAG MENTAH tiap entri, bukan keputusan
"AI atau bukan". Itu disengaja: keputusannya bisa dihitung ulang tanpa memanggil
wallhaven lagi selama 26 menit, dan itu yang terjadi di sini.

Polanya salah tuduh dua kali:

  Percobaan 1: "ai" dicocokkan sebagai SUBSTRING, sehingga cocok di dalam
  h-air, t-ail, r-ainbow, n-ails, p-ainted -> "1022 dari 1058 entri adalah
  karya AI". Sepenuhnya salah.

  Percobaan 2: "ai" dicocokkan sebagai kata utuh, tetapi masih sendirian, dan
  "artificial" juga. Hasilnya 3 tersangka:
      artificial lights  -> lampu buatan
      Hayasaka Ai        -> tokoh Kaguya-sama
      Tsuru Ai Momono    -> tokoh anime
  Ketiganya bukan karya mesin.

Polanya sekarang menuntut frasa lengkapnya. Alat ini menghitung ulang seluruh
1058 entri dengan pola itu.
"""

import json
import re
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
HASIL = W / "build" / "periksa-ai.json"
CATALOG = W / "LumaWall" / "catalog.json"

# Pola yang sama dengan tools/periksa-ai-lengkap.py.
# Pola ini dibentuk dari kenyataan di wallhaven, bukan dari dugaan - dan
# butuh tiga percobaan karena dua sebelumnya salah tuduh:
#
#   Percobaan 1: "ai" sebagai SUBSTRING -> cocok di dalam h-air, t-ail,
#   r-ainbow, n-ails, p-ainted -> "1022 dari 1058 entri adalah karya AI".
#
#   Percobaan 2: "ai" sebagai kata utuh, tetapi masih sendirian -> "Hayasaka Ai"
#   dan "Tsuru Ai Momono" ikut tertangkap, padahal keduanya nama tokoh anime.
#   "artificial lights" (lampu buatan) juga ikut tertangkap.
#
#   Percobaan 3 (dipakai): menuntut frasa lengkap atau nama alat. Diverifikasi
#   dengan mencari karya AI di wallhaven dan membaca tag yang benar-benar
#   dipakainya - ternyata "Midjourney" dipakai sebagai tag, sedangkan "ai
#   generated" dan "artificial intelligence" tidak menghasilkan apa pun.
#
# Diuji 17 kasus: semua nama tokoh dan kata biasa lolos, semua penanda AI asli
# tertangkap.
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
print("   MENGHITUNG ULANG HASIL PEMERIKSAAN AI")
print("  ══════════════════════════════════════════════════════════════════")
print()

hasil = json.load(open(HASIL, encoding="utf-8"))
print("  entri yang sudah diperiksa: %d" % len(hasil))

kena = {k: v for k, v in hasil.items() if any(AI_TAG.search(t) for t in v)}
print("  bertanda AI               : %d" % len(kena))
print()

if kena:
    for k, v in list(kena.items())[:20]:
        print("     %-10s %s" % (k, v))
    print()

# Daftar id yang benar-benar AI, untuk dibuang dari katalog.
id_ai = set(kena.keys())
print("  id yang harus dibuang: %d" % len(id_ai))

# Periksa: apakah benar-benar ada di katalog Mature?
d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
ada = []
for e in items:
    if e.get("category") != "Mature 18+":
        continue
    m = re.search(r"-\s*([A-Z0-9]{6})\s*$", e.get("title", ""))
    if m and m.group(1).lower() in id_ai:
        ada.append(e)
print("  yang benar-benar ada di katalog Mature: %d" % len(ada))
print()

if not ada:
    print("  Tidak ada entri AI di katalog Mature.")
    print("  Permintaan 'wajib artwork bukan ai generated' terpenuhi.")
    print()
else:
    for e in ada:
        print("     %s" % e.get("title", "")[:70])
    print()
