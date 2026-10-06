#!/usr/bin/env python3
"""Cetak HANYA duplikat yang berkasnya sama, ringkas.

KENAPA ALAT INI ADA:

tools/lihat-duplikat.py mencetak seluruh data tiap entri, dan itu terlalu
panjang untuk dibaca. Yang dibutuhkan hanya daftar: kelompok mana, entri mana
saja di dalamnya, dan indeksnya - supaya bisa dihapus.
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
print("  ══ DUPLIKAT: BERKAS SAMA ══")
print()

buang = set()

for kunci in ["videoUrl", "thumbnailUrl"]:
    grup = defaultdict(list)
    for i, e in enumerate(items):
        u = norm_url(e.get(kunci))
        if u:
            grup[u].append(i)

    dup = {u: idx for u, idx in grup.items() if len(idx) > 1}
    print("  ── %s: %d kelompok ──" % (kunci, len(dup)))
    print()

    for u, idx in dup.items():
        # Yang dipertahankan: entri pertama. Sisanya duplikat.
        simpan = idx[0]
        for i in idx[1:]:
            buang.add(i)

        print("     URL  : %s" % u[-80:])
        for n, i in enumerate(idx):
            tanda = "SIMPAN" if i == simpan else "BUANG"
            print("        %s [%d] %-34s | %s" % (tanda, i, items[i].get("category", "")[:34],
                                                  items[i].get("title", "")[:40]))
        print()

print("  ══ ringkasan ══")
print("     entri yang akan dibuang: %d" % len(buang))
print()

if buang:
    print("     indeks: %s" % sorted(buang))
    print()
    for i in sorted(buang):
        e = items[i]
        print("     [%d] %s" % (i, e.get("title", "")[:60]))
        print("          kategori : %s" % e.get("category"))
        print("          videoUrl : %s" % (e.get("videoUrl") or "")[-70:])
    print()
