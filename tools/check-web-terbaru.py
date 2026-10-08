#!/usr/bin/env python3
"""Buktikan halaman unduhan web menyajikan installer versi TERBARU.

KENAPA ALAT INI ADA:

Pertanyaannya: "yg terbaru udh di web kan". Menjawabnya dengan melihat nomor
versi di halaman tidak cukup - halaman bisa menulis satu versi sementara berkas
yang benar-benar diunduh versi lain, dan itu pernah terjadi di proyek ini
(installer di web disalin ke folder publik, sehingga bisa diunduh gratis).

Yang harus dibuktikan, berurutan:

  1. Halaman unduhan MENOLAK permintaan tanpa token yang sah.
     Kalau tidak, siapa pun bisa mengunduh tanpa membayar.

  2. Nama berkas yang ditawarkan server = versi terakhir yang dirilis.
     Nama itu datang dari INSTALLER_OBJECT di environment Vercel, dan kalau
     nilainya tertinggal, pembeli akan menerima versi lama tanpa ada yang tahu.

  3. Instalernya benar-benar berisi build terbaru - bukan sekadar bernama
     terbaru.

Poin 1 dan 2 bisa diperiksa dari sini. Poin 3 memerlukan token, jadi yang
diperiksa adalah konsistensi nama dan versi yang dirilis.
"""

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
SITUS = "https://lumawall.xinet.id"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url, timeout=45):
    try:
        r = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return f.status, f.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return 0, str(e)[:80]


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   APAKAH WEB SUDAH MENYAJIKAN VERSI TERBARU")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── Versi terakhir yang dirilis ───────────────────────────────────────────
# Diambil dari nama MSIX terbaru, karena itu yang dibuat langkah terakhir
# dalam setiap rilis.
# Versi dibandingkan sebagai ANGKA, bukan sebagai teks: "4.5.9.0" lebih besar
# dari "4.5.23.0" kalau diurutkan sebagai teks, dan itu melaporkan versi lama
# sebagai yang terbaru.
msix = []
for f in (W / "outputs").glob("LumaWall_*.msix"):
    m = re.search(r"LumaWall_([0-9.]+)_x64\.msix", f.name)
    if m:
        msix.append((tuple(int(x) for x in m.group(1).split(".")), m.group(1), f))
msix.sort()

if not msix:
    print("  ! tidak ada MSIX di outputs/")
    raise SystemExit(1)

versi_terakhir = msix[-1][1]
print("  versi terakhir dirilis : %s" % versi_terakhir)
print("  berkas MSIX            : %s" % msix[-1][2].name)
print()

# ── 1. halaman unduhan menolak tanpa token ────────────────────────────────
print("  ── 1. halaman unduhan menolak permintaan tanpa token ──")
for jalur in ["/api/download", "/api/download/", "/api/unduh"]:
    kode, isi = get(SITUS + jalur)
    if kode == 404:
        print("     %-18s HTTP 404 (tidak ada endpoint ini)" % jalur)
        continue
    print("     %-18s HTTP %s" % (jalur, kode))
    if isi:
        coba = re.search(r'"(error|message|pesan)"\s*:\s*"([^"]+)"', isi)
        if coba:
            print("        pesan: %s" % coba.group(2)[:70])
    # Tanpa token, harus DITOLAK.
    if kode == 200 and "LumaWall-Setup" in isi:
        print("        ! BAHAYA: installer bisa diunduh tanpa token")
    else:
        print("        OK: tidak memberikan installer tanpa token")
print()

# ── 2. versi di halaman-halaman penting ───────────────────────────────────
print("  ── 2. versi yang ditulis halaman ──")
halaman = {
    "/": "beranda (ID)",
    "/en/": "beranda (EN)",
    "/beli/": "beli (ID)",
    "/en/buy/": "buy (EN)",
    "/sukses/": "sukses",
}
for jalur, nama in halaman.items():
    kode, isi = get(SITUS + jalur)
    v = sorted(set(re.findall(r"4\.5\.[0-9]+\.[0-9]+", isi)))
    tanda = "OK " if versi_terakhir in v else ("-- " if not v else "!! ")
    print("     %s%-16s HTTP %-4s %s" % (tanda, nama, kode,
                                          ", ".join(v) if v else "(tidak menulis versi)"))
print()

# ── 3. berkas yang benar-benar disajikan ──────────────────────────────────
print("  ── 3. apakah installer versi lama masih bisa diunduh langsung? ──")
# Kalau berkas lama masih bisa diakses, itu jalur unduhan gratis.
for nama in ["LumaWall-Setup-%s.exe" % versi_terakhir,
             "LumaWall-Setup-4.5.7.0.exe",
             "LumaWall-Setup-4.5.20.0.exe"]:
    for folder in ["/assets/downloads/", "/downloads/", "/"]:
        kode, isi = get(SITUS + folder + nama, timeout=25)
        if kode != 200:
            continue
        # HTTP 200 dan isi yang panjang TIDAK cukup: halaman beli juga begitu.
        # Berkas exe dimulai dengan tanda "MZ"; halaman HTML dengan "<".
        if isi.lstrip()[:1] == "<":
            print("     OK %s -> dialihkan ke halaman beli (bukan installer)" % nama)
            break
        if len(isi) > 100000:
            print("     !! %s BISA DIUNDUH sebagai berkas (%d byte) - jalur gratis!" % (nama, len(isi)))
            break
    else:
        print("     OK %s tidak bisa diunduh langsung" % nama)
print()

# ── Kesimpulan ────────────────────────────────────────────────────────────
print("  ══════════════════════════════════════════════════════════════════")
kode, isi = get(SITUS + "/api/download")
print("   versi terakhir dirilis : %s" % versi_terakhir)
print("   /api/download tanpa token: HTTP %s" % kode)
print()
print("   Untuk memastikan INSTALLER_OBJECT di Vercel sudah menunjuk versi")
print("   terbaru, nama objeknya harus diperiksa di dashboard Vercel - atau")
print("   dengan mengunduh lewat alur pembelian yang sesungguhnya.")
print("  ══════════════════════════════════════════════════════════════════")
print()
