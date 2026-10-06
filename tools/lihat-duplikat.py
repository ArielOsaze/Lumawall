#!/usr/bin/env python3
"""Tampilkan duplikat yang NYATA, dengan seluruh datanya.

KENAPA ALAT INI ADA:

Pemeriksaan menyeluruh menemukan empat jenis kecurigaan, dan tidak semuanya
duplikat nyata:

  videoUrl sama      2 kelompok  -> hampir pasti duplikat nyata
  thumbnailUrl sama  2 kelompok  -> hampir pasti duplikat nyata
  judul sama         1803 kelompok -> BIASANYA BUKAN duplikat: "Albedo Overlord"
                                    bisa ada sepuluh versi yang berbeda, dan
                                    itu wajar
  judul di dua kategori 590      -> biasanya juga bukan: wallpaper berbeda
                                    dengan judul yang kebetulan sama

Yang harus diperbaiki hanya yang BERKASNYA sama. Alat ini menampilkan seluruh
data tiap kelompok, supaya keputusannya bisa diperiksa - bukan ditebak.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])


def norm_url(u):
    """URL yang bisa dibandingkan, TANPA membuang identitas berkasnya.

    Query string tidak boleh dibuang: URL moewalls berbentuk
    go.moewalls.com/download.php?video=<token>, dan token itu yang membedakan
    satu berkas dari yang lain. Membuang query membuat seluruh 1.724 URL
    moewalls menjadi satu alamat yang sama, dan pemeriksa melaporkan ribuan
    duplikat palsu.

    Yang dibuang hanya fragmen dan parameter pelacak - bagian yang memang tidak
    menentukan berkas mana yang diambil.
    """
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = u.split("#")[0]
    # Parameter pelacak dibuang, sisanya dipertahankan.
    if "?" in u:
        dasar, _, query = u.partition("?")
        simpan = [p for p in query.split("&")
                  if p and not p.startswith(("utm_", "ref=", "fbclid=", "gclid="))]
        u = dasar + ("?" + "&".join(simpan) if simpan else "")
    return u.rstrip("/")


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   DUPLIKAT YANG BERKASNYA SAMA")
print("  ══════════════════════════════════════════════════════════════════")
print()

for nama, kunci in [("videoUrl", "videoUrl"), ("thumbnailUrl", "thumbnailUrl")]:
    print("  ── %s ──" % nama)
    grup = defaultdict(list)
    for i, e in enumerate(items):
        u = norm_url(e.get(kunci))
        if u:
            grup[u].append(i)

    dup = {u: idx for u, idx in grup.items() if len(idx) > 1}
    print("     kelompok duplikat: %d" % len(dup))
    print()
    for u, idx in dup.items():
        print("     URL: %s" % u[:92])
        for i in idx:
            e = items[i]
            print("        [%d] judul    : %s" % (i, e.get("title", "")[:66]))
            print("            kategori : %s" % e.get("category"))
            print("            kind     : %s" % e.get("kind"))
            print("            videoUrl : %s" % (e.get("videoUrl") or "")[-72:])
            print("            thumbUrl : %s" % (e.get("thumbnailUrl") or "")[-72:])
        print()

# ── Judul sama: apakah berkasnya juga sama? ───────────────────────────────
print("  ══════════════════════════════════════════════════════════════════")
print("   JUDUL SAMA: APAKAH BERKASNYA JUGA SAMA?")
print("  ══════════════════════════════════════════════════════════════════")
print()

def norm_judul(t):
    t = (t or "").strip().lower()
    t = re.sub(r"-\s*[a-z0-9]{6}\s*$", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

grup = defaultdict(list)
for i, e in enumerate(items):
    t = norm_judul(e.get("title"))
    if t:
        grup[t].append(i)

sama_berkas = 0
beda_berkas = 0
contoh_sama = []

for t, idx in grup.items():
    if len(idx) < 2:
        continue
    url = {norm_url(items[i].get("videoUrl")) for i in idx}
    if len(url) < len(idx):
        sama_berkas += 1
        contoh_sama.append((t, idx))
    else:
        beda_berkas += 1

print("  judul sama, berkas JUGA sama (duplikat nyata): %d kelompok" % sama_berkas)
print("  judul sama, berkas BERBEDA (wajar)           : %d kelompok" % beda_berkas)
print()

if contoh_sama:
    print("  ── kelompok yang berkasnya sama ──")
    for t, idx in contoh_sama[:20]:
        print("     %s" % t[:66])
        for i in idx:
            print("        [%d] %-40s %s" % (i, items[i].get("category"), (items[i].get("videoUrl") or "")[-58:]))
        print()

print("  ══════════════════════════════════════════════════════════════════")
print()
