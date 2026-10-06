#!/usr/bin/env python3
"""Cari tahu bagaimana wallhaven sebenarnya menandai karya AI.

KENAPA ALAT INI ADA:

Dua percobaan sebelumnya sama-sama salah, dengan arah yang berlawanan:

  Percobaan 1: "ai" sebagai substring -> 1022 dari 1058 dituduh AI (salah)
  Percobaan 2: "ai" sebagai kata utuh -> "Hayasaka Ai" ikut tertangkap (salah)
  Percobaan 3: hanya frasa lengkap ("ai-generated", "midjourney") -> mungkin
               MELEWATKAN karya AI yang ditandai wallhaven dengan tag lain

Percobaan 3 belum diuji terhadap kenyataan. Alat ini mengujinya: karya AI yang
sudah diketahui dicari di wallhaven, lalu tag yang benar-benar dipakainya
dibaca. Polanya harus dibentuk dari kenyataan itu, bukan dari dugaan.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
JEDA = 1.5
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


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   BAGAIMANA WALLHAVEN MENANDAI KARYA AI")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── 1. Tag apa saja yang mengandung "ai" di wallhaven? ───────────────────
print("  ── tag wallhaven yang mengandung 'ai' ──")
semua = {}
for hal in range(1, 6):
    d = get_json("https://wallhaven.cc/api/v1/tags?per_page=100&page=%d" % hal)
    if not d or not d.get("data"):
        break
    for t in d["data"]:
        semua[t["name"]] = t.get("count") or 0

print("  total tag dibaca: %d" % len(semua))
print()
kandidat = {n: c for n, c in semua.items()
            if re.search(r"\bai\b", n, re.I) or "generat" in n.lower() or "diffus" in n.lower()}
print("  yang berkaitan dengan AI:")
for n, c in sorted(kandidat.items(), key=lambda x: -x[1])[:25]:
    print("     %-34s %d" % (n, c))
print()

# ── 2. Cari karya AI lewat kata kunci, baca tag sebenarnya ────────────────
print("  ── mencari karya AI dan membaca tagnya ──")
tag_terpakai = Counter()
contoh = []
for kueri in ["ai generated", "ai art", "artificial intelligence", "midjourney", "stable diffusion"]:
    d = get_json("https://wallhaven.cc/api/v1/search?q=%s&categories=010&purity=110&per_page=4&sorting=relevance"
                 % urllib.parse.quote(kueri))
    if not d or not d.get("data"):
        print("     %-22s tidak ada hasil" % kueri)
        continue
    print("     %-22s %d hasil" % (kueri, d["meta"]["total"]))
    for e in d["data"][:2]:
        wid = e["id"]
        det = get_json("https://wallhaven.cc/api/v1/w/%s" % wid)
        if not det:
            continue
        tags = [t["name"] for t in (det.get("data", {}).get("tags") or [])]
        for t in tags:
            tag_terpakai[t] += 1
        contoh.append((wid, kueri, tags))

print()
print("  ── tag yang paling sering muncul pada hasil itu ──")
for t, n in tag_terpakai.most_common(20):
    print("     %-34s %d" % (t, n))
print()

print("  ── contoh: apakah ada tag penanda AI? ──")
for wid, kueri, tags in contoh[:6]:
    ai = [t for t in tags if re.search(r"\bai\b|generat|diffus|midjourney", t, re.I)]
    print("     %-10s (dari '%s')" % (wid, kueri))
    print("        tag AI: %s" % (ai or "TIDAK ADA"))
    print("        semua : %s" % ", ".join(tags[:10]))
    print()

print("  ── kesimpulan ──")
if any(re.fullmatch(r"ai", t, re.I) for t in tag_terpakai):
    print("     wallhaven memakai tag 'ai' (kata tunggal) untuk karya mesin.")
    print("     Pencocokan harus PERSIS 'ai' sebagai satu tag utuh - bukan")
    print("     substring, dan bukan kata di dalam tag yang lebih panjang.")
elif tag_terpakai:
    print("     Tidak ada tag 'ai' tunggal. Tag penanda yang terlihat:")
    for t, n in tag_terpakai.most_common(5):
        print("        %s" % t)
else:
    print("     Tidak ada hasil - pencarian tidak menemukan karya bertanda AI.")
print()
