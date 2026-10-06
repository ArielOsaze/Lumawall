#!/usr/bin/env python3
"""Cari sumber VIDEO anime mature, bukan gambar statis.

KENAPA ALAT INI ADA:

Katalog LumaWall adalah wallpaper bergerak: setiap entri harus punya videoUrl,
bukan sekadar gambar. wallhaven dan safebooru punya ratusan ribu gambar anime
dewasa, tetapi itu gambar - dan entri tanpa video tidak bisa dipakai.

Jadi yang dicari di sini adalah sumber yang punya VIDEO, dan banyak. Diperiksa:
  - moewalls (sumber yang sudah dipakai) - berapa tag dewasa yang ada
  - desktophut (sumber kedua) - berapa halaman tag dewasanya
  - wallhaven (punya API tapi gambar saja) - dikonfirmasi tidak bisa

Hasilnya dipakai untuk memutuskan dari mana 1000 entri Mature akan diambil.
"""

import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url, timeout=45):
    r = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")


def get_json(url, timeout=45):
    return json.loads(get(url, timeout))


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   SUMBER VIDEO ANIME MATURE")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── 1. moewalls: seluruh tag, cari yang menandakan konten dewasa ──────────
print("  ── moewalls: semua tag yang menandakan konten dewasa ──")
semua = {}
for halaman in range(1, 11):
    try:
        d = get_json("https://moewalls.com/wp-json/wp/v2/tags?per_page=100&page=%d&orderby=count&order=desc" % halaman)
    except Exception:
        break
    if not d:
        break
    for t in d:
        semua[t["name"].lower()] = t["count"]

# Kata yang benar-benar menandakan konten dewasa, bukan sekadar anime.
DEWASA = {
    "swimsuit", "bikini", "succubus", "panties", "lingerie", "bunny",
    "nude", "naked", "ecchi", "lewd", "sexy", "sensual", "seductive",
    "boudoir", "gravure", "pinup", "bra", "cleavage", "breasts", "boobs",
    "thigh", "thighs", "midriff", "undress", "topless", "nsfw", "adult",
    "mature", "nightgown", "negligee", "garter", "corset", "bodysuit",
    "catsuit", "stockings", "leotard", "voluptuous", "curvy", "sultry",
    "provocative", "hot", "beach-bikini", "micro-bikini", "one-piece",
    "school-swimsuit", "sukumizu", "onsen", "bath", "shower",
}
ada = sorted([(t, semua[t]) for t in DEWASA if t in semua], key=lambda x: -x[1])
print("     tag dewasa ditemukan: %d" % len(ada))
total = 0
for t, n in ada:
    print("        %-18s %d" % (t, n))
    total += n
print("     jumlah entri (dengan tumpang tindih): %d" % total)
print()

# ── 2. desktophut: tag dewasa dan berapa halaman masing-masing ────────────
print("  ── desktophut: tag dewasa, berapa halaman ──")
DH = ["adult", "bikini", "lingerie", "swimsuit", "sexy", "hot", "seductive",
      "sensual", "pinup", "gravure", "boudoir", "nude", "beach-bikini",
      "leotard", "bodysuit", "catsuit", "stockings", "thigh-highs", "garter",
      "corset", "nightgown", "negligee", "topless", "bra", "panties",
      "undress", "big-breasts", "curvy", "voluptuous", "sultry", "provocative"]
jumlah = 0
for tag in DH:
    try:
        html = get("https://desktophut.com/tag/%s" % tag, timeout=30)
        # Cari jumlah halaman dari pagination
        halaman = set(re.findall(r"/tag/%s\?page=(\d+)" % re.escape(tag), html))
        n = max((int(x) for x in halaman), default=1)
        # Cari jumlah item
        m = re.search(r"(\d+)\s*(?:wallpapers|results|videos)", html, re.I)
        print("     %-16s %s halaman" % (tag, n))
        jumlah += n * 20   # sekitar 20 per halaman
    except Exception as e:
        print("     %-16s gagal: %s" % (tag, str(e)[:50]))
print("     perkiraan total: %d" % jumlah)
print()

# ── 3. wallhaven: dikonfirmasi gambar saja ────────────────────────────────
print("  ── wallhaven: gambar saja, tidak ada video ──")
try:
    d = get_json("https://wallhaven.cc/api/v1/search?q=anime+swimsuit&categories=010&purity=110&per_page=1")
    jenis = set()
    for e in d.get("data", []):
        jenis.add(e.get("file_type", "?").split("/")[0])
    print("     jenis berkas: %s" % ", ".join(sorted(jenis)))
    print("     -> TIDAK BISA: tidak ada videoUrl")
except Exception as e:
    print("     gagal: %s" % e)
print()
