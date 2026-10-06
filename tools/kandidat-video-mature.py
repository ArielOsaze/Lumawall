#!/usr/bin/env python3
"""Hitung kandidat video Mature yang belum masuk katalog.

KENAPA ALAT INI ADA:

Permintaannya: "sama tambahin lagi wallpaper dinamisnya khususnya pada bagian
mature harus ada banyak yg bagus bagus".

Kategori Mature sekarang 1.092 entri, tetapi hanya 34 yang dinamis - sisanya
gambar statis dari wallhaven. Menambah video berarti mencari kandidat yang
belum pernah diproses, dan itu tersebar di beberapa berkas hasil panen lama:

    mature-moewalls.json     moewalls, sudah punya tag bukti
    mature-jelas.json        DesktopHut, tag jelas
    mature-sugestif.json     DesktopHut, tag sugestif
    adult-urls.json          tautan tag dewasa
    mature-urls.json         tautan tag mature

Alat ini membandingkan semuanya dengan katalog, jadi yang benar-benar baru
saja yang dikunjungi - mengunjungi 500 halaman yang sudah ada hanya membuang
waktu dan memicu pembatasan situs.
"""

import json
import re
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
S = W / "build" / "catalog-scrape"
CATALOG = W / "LumaWall" / "catalog.json"

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   KANDIDAT VIDEO MATURE YANG BELUM MASUK KATALOG")
print("  ══════════════════════════════════════════════════════════════════")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
mat = [e for e in items if e.get("category") == "Mature 18+"]
print("  Mature di katalog : %d" % len(mat))
print("    statis          : %d" % sum(1 for e in mat if (e.get("kind") or "").lower() == "static"))
print("    dinamis/video   : %d" % sum(1 for e in mat if (e.get("kind") or "").lower() in ("dynamic", "video")))
print()

# Semua yang sudah ada di katalog, dalam bentuk yang bisa dibandingkan.
ada_url = set()
ada_slug = set()
for e in items:
    for k in ("videoUrl", "thumbnailUrl", "sourceUrl"):
        u = (e.get(k) or "").strip().lower()
        if u:
            ada_url.add(u)
            # Slug juga disimpan: url video dan halaman sumbernya berbeda,
            # tetapi slug-nya sama.
            m = re.search(r"desktophut\.com/(?:previews/)?([^/?]+)", u)
            if m:
                ada_slug.add(m.group(1).lower())
            m2 = re.search(r"moewalls\.com/([^/?]+)", u)
            if m2:
                ada_slug.add(m2.group(1).lower())

print("  slug yang sudah ada di katalog: %d" % len(ada_slug))
print()

# ── Kumpulkan kandidat dari tiap berkas ───────────────────────────────────
hasil = {}

def tambah(asal, slug, judul, url=""):
    s = (slug or "").strip().lower()
    if not s:
        return
    if s in ada_slug:
        return
    hasil.setdefault(asal, {})[s] = {"judul": judul, "url": url}

# moewalls: sudah punya tag bukti
f = S / "mature-moewalls.json"
if f.exists():
    for e in json.load(open(f, encoding="utf-8")).get("jelas", []):
        u = e.get("url") or e.get("videoUrl") or ""
        m = re.search(r"moewalls\.com/([^/?]+)", u)
        tambah("moewalls", m.group(1) if m else "", e.get("title", ""), u)

# DesktopHut: kartu dari tag
for nama, kunci in [("mature-jelas.json", "kartu"), ("mature-sugestif.json", "kartu"),
                    ("mature-kartu.json", "kartu")]:
    f = S / nama
    if not f.exists():
        continue
    for slug, v in json.load(open(f, encoding="utf-8")).get(kunci, {}).items():
        tambah("desktophut", slug, v.get("judul") or v.get("title") or slug,
               v.get("url") or "")

# Daftar tautan
for nama in ["adult-urls.json", "mature-urls.json"]:
    f = S / nama
    if not f.exists():
        continue
    for u in json.load(open(f, encoding="utf-8")).get("urls", []):
        m = re.search(r"desktophut\.com/([^/?]+)", u)
        if m:
            tambah("desktophut", m.group(1), m.group(1).replace("-", " "), u)

print("  ── kandidat yang belum masuk katalog ──")
total = 0
for asal, isi in hasil.items():
    print("     %-14s %d" % (asal, len(isi)))
    total += len(isi)
print()
print("  total kandidat baru: %d" % total)
print()

for asal, isi in hasil.items():
    print("  ── %s ──" % asal)
    for slug, v in list(isi.items())[:12]:
        print("     %-58s" % slug[:58])
    if len(isi) > 12:
        print("     ... dan %d lagi" % (len(isi) - 12))
    print()

# Simpan daftarnya supaya alat berikutnya tidak menghitung ulang.
keluar = W / "build" / "kandidat-video-mature.json"
keluar.write_text(json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
print("  disimpan: %s" % keluar)
print()
