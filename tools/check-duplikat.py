#!/usr/bin/env python3
"""Periksa duplikat di katalog secara MENYELURUH, bukan hanya URL yang sama.

KENAPA ALAT INI ADA:

Permintaannya: "jangan smpe ada wallpaper duplikat yaa".

Pemeriksa katalog sudah menghitung duplikat, tetapi hanya SATU jenis: videoUrl
yang sama persis. Wallpaper yang sama bisa masuk dua kali dengan cara yang tidak
tertangkap oleh itu:

  1. URL berbeda, berkas sama
     Wallhaven menyajikan gambar yang sama lewat beberapa alamat (mis. path
     /full/21/216jxy.png dan /full/21/216jxy.jpg untuk berkas yang sama), dan
     thumbnail-nya bisa sama.

  2. Judul sama, URL berbeda
     Sumber berbeda bisa memuat wallpaper yang sama dengan nama yang sama.

  3. Gambar sama, id berbeda
     Wallhaven mengizinkan gambar yang sama diunggah ulang; id-nya berbeda
     tetapi isinya sama.

  4. Satu wallpaper di dua kategori
     Entri yang sama bisa muncul di "Anime Girls" dan "Mature 18+" sekaligus.

Alat ini memeriksa keempatnya, lalu melaporkan yang benar-benar duplikat -
bukan sekadar mirip. Judul yang mirip saja tidak dihitung: "Albedo Overlord"
dan "Albedo Overlord Swimsuit" adalah dua wallpaper yang berbeda.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   PEMERIKSAAN DUPLIKAT MENYELURUH")
print("  ══════════════════════════════════════════════════════════════════")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
print("  entri: %d" % len(items))
print()

masalah = []


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


def norm_judul(t):
    """Judul tanpa id di ujung, tanpa tanda baca, huruf kecil."""
    t = (t or "").strip().lower()
    t = re.sub(r"-\s*[a-z0-9]{6}\s*$", "", t)      # id wallhaven di ujung
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ── 1. videoUrl sama ──────────────────────────────────────────────────────
print("  ── 1. videoUrl yang sama persis ──")
grup = defaultdict(list)
for i, e in enumerate(items):
    u = norm_url(e.get("videoUrl"))
    if u:
        grup[u].append(i)
dup = {u: idx for u, idx in grup.items() if len(idx) > 1}
print("     %d kelompok" % len(dup))
if dup:
    masalah.append(("videoUrl sama", dup))
    for u, idx in list(dup.items())[:6]:
        print("        %s" % u[:76])
        for i in idx[:3]:
            print("           [%d] %s" % (i, items[i].get("title", "")[:56]))
print()

# ── 2. thumbnailUrl sama ──────────────────────────────────────────────────
print("  ── 2. thumbnailUrl yang sama persis ──")
grup = defaultdict(list)
for i, e in enumerate(items):
    u = norm_url(e.get("thumbnailUrl"))
    if u:
        grup[u].append(i)
dup = {u: idx for u, idx in grup.items() if len(idx) > 1}
print("     %d kelompok" % len(dup))
if dup:
    masalah.append(("thumbnailUrl sama", dup))
    for u, idx in list(dup.items())[:6]:
        print("        %s" % u[:76])
        for i in idx[:3]:
            print("           [%d] %s" % (i, items[i].get("title", "")[:56]))
print()

# ── 3. judul sama (setelah id dibuang) ────────────────────────────────────
print("  ── 3. judul sama, setelah id dibuang ──")
grup = defaultdict(list)
for i, e in enumerate(items):
    t = norm_judul(e.get("title"))
    if t:
        grup[t].append(i)
dup = {t: idx for t, idx in grup.items() if len(idx) > 1}
print("     %d kelompok" % len(dup))
if dup:
    masalah.append(("judul sama", dup))
    for t, idx in sorted(dup.items(), key=lambda x: -len(x[1]))[:10]:
        print("        %-52s %d kali" % (t[:52], len(idx)))
        for i in idx[:3]:
            print("           [%d] %s" % (i, items[i].get("videoUrl", "")[-60:]))
print()

# ── 4. satu wallpaper di dua kategori ─────────────────────────────────────
print("  ── 4. judul sama tetapi kategori berbeda ──")
kat = defaultdict(set)
for e in items:
    t = norm_judul(e.get("title"))
    if t:
        kat[t].add(e.get("category"))
beda = {t: k for t, k in kat.items() if len(k) > 1}
print("     %d judul muncul di lebih dari satu kategori" % len(beda))
if beda:
    masalah.append(("judul di dua kategori", beda))
    for t, k in list(beda.items())[:10]:
        print("        %-46s %s" % (t[:46], sorted(k)))
print()

# ── 5. id wallhaven ganda ─────────────────────────────────────────────────
print("  ── 5. id wallhaven yang sama ──")
grup = defaultdict(list)
for i, e in enumerate(items):
    m = re.search(r"-\s*([A-Za-z0-9]{6})\s*$", e.get("title", ""))
    u = (e.get("videoUrl") or "").lower()
    if m and "wallhaven" in u:
        grup[m.group(1).lower()].append(i)
dup = {k: idx for k, idx in grup.items() if len(idx) > 1}
print("     %d id ganda" % len(dup))
if dup:
    masalah.append(("id wallhaven ganda", dup))
    for k, idx in list(dup.items())[:10]:
        print("        %s" % k)
        for i in idx[:3]:
            print("           [%d] %s" % (i, items[i].get("title", "")[:56]))
print()

# ── Ringkasan ─────────────────────────────────────────────────────────────
print("  ══════════════════════════════════════════════════════════════════")
if not masalah:
    print("   TIDAK ADA DUPLIKAT")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
else:
    print("   DITEMUKAN %d JENIS DUPLIKAT" % len(masalah))
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    for nama, isi in masalah:
        print("     %-26s %d kelompok" % (nama, len(isi)))
    print()

# Sebaran per kategori, untuk melihat apakah ada kategori yang isinya sama
print("  ── jumlah entri per kategori ──")
c = Counter(e.get("category") or "?" for e in items)
for k, v in c.most_common():
    print("     %-16s %d" % (k, v))
print()
