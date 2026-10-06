#!/usr/bin/env python3
"""Cari sumber anime mature yang bisa memberi minimal 1000 entri.

KENAPA ALAT INI ADA:

Keluhannya: "cari yg mature banyakin ini cuma 69 masa aku mat at least 1000 buat
mature pastiin anime mature ya". Katalog sekarang punya 69 entri Mature, dan
sumbernya (tag dewasa moewalls) hanya punya sekitar 100 judul.

Yang perlu dijawab lebih dulu: apakah ada sumber yang bisa memberi 1000, dan
apakah isinya benar-benar anime. Tanpa itu, menambah entri hanya akan mengisi
kategori dengan yang bukan anime - dan itu justru yang dilarang.

Alat ini memeriksa kandidat sumber satu per satu dan melaporkan berapa entri
anime yang benar-benar bisa diambil dari masing-masing.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url, timeout=45):
    r = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")


def get_json(url, timeout=45):
    return json.loads(get(url, timeout))


def coba_moewalls_tags():
    """Semua tag moewalls yang menandakan konten dewasa."""
    print("  ── moewalls: seluruh daftar tag ──")
    hasil = {}
    for halaman in range(1, 11):
        try:
            d = get_json("https://moewalls.com/wp-json/wp/v2/tags?per_page=100&page=%d&orderby=count&order=desc" % halaman)
        except Exception:
            break
        if not d:
            break
        for t in d:
            hasil[t["name"].lower()] = t["count"]
    print("     total tag: %d" % len(hasil))

    # Tag yang menandakan konten dewasa, dalam bahasa Inggris dan Jepang.
    dewasa = ["swimsuit", "bikini", "succubus", "panties", "lingerie", "bunny",
              "nude", "naked", "ecchi", "hentai", "lewd", "sexy", "sensual",
              "seductive", "boudoir", "gravure", "pinup", "lingerie", "bra",
              "cleavage", "boobs", "breasts", "thigh", "thighs", "midriff",
              "undress", "topless", "nsfw", "adult", "mature", "hot", "sexy"]
    ditemukan = []
    for t in dewasa:
        if t in hasil:
            ditemukan.append((t, hasil[t]))
    ditemukan.sort(key=lambda x: -x[1])
    print("     tag dewasa yang ada:")
    total = 0
    for t, n in ditemukan:
        print("        %-12s %d" % (t, n))
        total += n
    print("     jumlah tag dewasa: %d, total entri: %d" % (len(ditemukan), total))
    return hasil


def coba_wallhaven():
    """Wallhaven punya API publik dengan tag dan filter kategori anime."""
    print()
    print("  ── wallhaven: API publik ──")
    try:
        d = get_json("https://wallhaven.cc/api/v1/search?q=anime&categories=010&purity=110&per_page=24&page=1")
        info = d.get("meta", {})
        print("     total hasil: %s" % info.get("total"))
        print("     per halaman : %s" % info.get("per_page"))
        if info.get("total"):
            print("     -> BISA dipakai: %s entri" % info["total"])
    except Exception as e:
        print("     gagal: %s" % e)


def coba_zerochan():
    """Zerochan: galeri anime besar, punya halaman tag."""
    print()
    print("  ── zerochan: halaman tag ──")
    try:
        html = get("https://www.zerochan.net/Swimsuit")
        m = re.search(r"([\d,]+)\s*(?:images|pictures|entries)", html, re.I)
        if m:
            print("     Swimsuit: %s gambar" % m.group(1))
        else:
            print("     tidak ada angka yang terbaca")
    except Exception as e:
        print("     gagal: %s" % e)


def coba_konachan():
    """Konachan: papan gambar anime, punya API berbasis tag."""
    print()
    print("  ── konachan: API tag ──")
    for tag in ["swimsuit", "bikini", "lingerie", "underwear", "cleavage"]:
        try:
            d = get_json("https://konachan.net/post.json?tags=%s+rating:questionable&limit=1" % tag)
            # Hitung lewat header tidak tersedia di urllib, jadi pakai cara lain.
            print("     %-12s ada %d hasil di halaman pertama" % (tag, len(d)))
        except Exception as e:
            print("     %-12s gagal: %s" % (tag, str(e)[:60]))


def coba_safebooru():
    """Safebooru: API publik tanpa kunci, dengan tag dan rating."""
    print()
    print("  ── safebooru: API publik ──")
    for tag in ["swimsuit", "bikini", "lingerie", "cleavage", "underwear"]:
        try:
            url = ("https://safebooru.org/index.php?page=dapi&s=post&q=index"
                   "&limit=1&tags=%s" % urllib.parse.quote(tag))
            html = get(url)
            m = re.search(r'count="(\d+)"', html)
            if m:
                print("     %-12s %s gambar" % (tag, m.group(1)))
            else:
                print("     %-12s tidak ada count" % tag)
        except Exception as e:
            print("     %-12s gagal: %s" % (tag, str(e)[:60]))


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   SUMBER KANDIDAT UNTUK KATEGORI MATURE")
print("  ══════════════════════════════════════════════════════════════════")
print()

coba_moewalls_tags()
coba_wallhaven()
coba_zerochan()
coba_safebooru()
