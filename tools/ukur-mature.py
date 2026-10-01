#!/usr/bin/env python3
"""Cari berapa banyak wallpaper dinamis dewasa yang benar-benar tersedia.

Kenapa alat ini ada: kategori "Mature 18+" hanya berisi 249 dari 22.879 entri
(1,1%), dan permintaannya adalah "khususnya pada bagian mature harus ada banyak
yg bagus bagus". Menambah jumlahnya tidak bisa dilakukan dengan menebak: situs
sumber tidak punya halaman kategori dewasa, jadi yang bisa dipakai adalah
PENCARIAN mereka. Alat ini mengukur berapa hasil nyata yang keluar dari setiap
kata kunci, supaya keputusan berikutnya berdasar angka.

Pemakaian:
  python tools/ukur-mature.py
"""
import concurrent.futures as cf
import re
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Kata kunci yang dipakai orang untuk mencari wallpaper bergaya dewasa. Yang
# dicari bukan kata "nsfw" (situs ini tidak memakainya), melainkan nama-nama
# pakaian dan pose yang muncul di judul wallpaper seperti itu.
KATA = [
    "bikini", "swimsuit", "lingerie", "bunny", "maid", "nurse", "kimono",
    "yukata", "beach", "poolside", "hot-spring", "onsen", "lingerie-set",
    "seductive", "sensual", "cleavage", "leotard", "bodysuit", "catsuit",
    "stockings", "thigh-highs", "heels", "garter", "corset", "nightgown",
    "negligee", "topless", "nude", "naked", "bra", "panties", "undress",
    "gravure", "idol", "cosplay", "waifu", "ecchi", "lewd", "nsfw",
    "big-breasts", "curvy", "voluptuous", "sultry", "provocative",
    "bath", "shower", "bedroom", "lingerie-model", "pin-up", "playboy",
]

# Situs yang punya pencarian dan sudah dipakai katalog ini.
SUMBER = {
    "desktophut": "https://desktophut.com/search/%s",
    "moewalls": "https://moewalls.com/?s=%s",
}


def hitung(url):
    """Berapa tautan wallpaper yang muncul di halaman hasil pencarian."""
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=25, context=CTX).read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:40]

    # Tautan detail punya bentuk /slug-kode4 - itu penanda yang paling andal
    # di kedua situs.
    tautan = set(re.findall(r'href="/([a-z0-9][a-z0-9-]*-[a-z0-9]{4})"', html, re.I))
    # moewalls memakai bentuk lain: /kategori/judul-live-wallpaper-1234/
    tautan |= set(re.findall(r'href="/(?:anime|games|movies|fantasy|abstract|animal|landscape|lifestyle|others|pixel-art|sci-fi|vehicle)/[^"]*?(\d{3,6})/', html, re.I))
    return len(tautan), ""


def main():
    print()
    print("  ══ berapa banyak wallpaper dewasa yang tersedia? ══")
    print()
    print("  %-22s %-12s %s" % ("kata kunci", "desktophut", "moewalls"))
    print("  " + "-" * 52)

    total = {"desktophut": 0, "moewalls": 0}
    pekerjaan = []
    for kata in KATA:
        for nama, pola in SUMBER.items():
            pekerjaan.append((kata, nama, pola % kata))

    hasil = {}
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        tugas = {pool.submit(hitung, url): (kata, nama) for kata, nama, url in pekerjaan}
        for t in cf.as_completed(tugas):
            kata, nama = tugas[t]
            try:
                n, _ = t.result()
            except Exception:
                n = -1
            hasil[(kata, nama)] = n

    for kata in KATA:
        d = hasil.get((kata, "desktophut"), 0)
        m = hasil.get((kata, "moewalls"), 0)
        tanda_d = "?" if d < 0 else str(d)
        tanda_m = "?" if m < 0 else str(m)
        if d > 0:
            total["desktophut"] += d
        if m > 0:
            total["moewalls"] += m
        if d > 0 or m > 0:
            print("  %-22s %-12s %s" % (kata, tanda_d, tanda_m))

    print()
    print("  ── jumlah tautan yang muncul (bukan entri unik) ──")
    for nama in SUMBER:
        print("     %-14s %d" % (nama, total[nama]))
    print()
    print("  Catatan: angka ini jumlah tautan di halaman PERTAMA tiap kata kunci.")
    print("  Entri uniknya lebih sedikit karena satu wallpaper bisa muncul di")
    print("  beberapa kata kunci, dan halaman berikutnya perlu ditelusuri terpisah.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
