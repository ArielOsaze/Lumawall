#!/usr/bin/env python3
"""Uji SEMUA thumbnail katalog - mana yang benar-benar tidak muncul.

KENAPA ALAT INI ADA:

Dilaporkan: "masih banyak yang fotonya error, ga muncul". Laporan sebelumnya
hanya memeriksa thumbnail yang KOSONG di berkas katalog, dan hasilnya 0 - jadi
alat itu menyatakan semuanya beres sementara pengguna masih melihat gambar
rusak di layar.

Sebabnya: thumbnailUrl yang terisi belum tentu bisa dimuat. Alamatnya bisa
sudah mati (404), ditolak (403), atau mengembalikan halaman HTML alih-alih
gambar. Tidak satu pun dari itu terlihat dari berkas katalog - hanya terlihat
dengan benar-benar meminta alamatnya.

Jadi alat ini MEMINTA setiap alamat, satu per satu, dan mencatat jawabannya.
Itu satu-satunya cara mengetahui gambar mana yang tidak muncul.

Yang dianggap RUSAK:
  * HTTP 404 / 410          - berkasnya sudah tidak ada
  * HTTP 403 / 401          - ditolak, gambar tidak akan tampil
  * HTTP 5xx                - server bermasalah
  * jawaban bukan gambar    - HTML halaman error, bukan berkas gambar
  * isi kosong (0 byte)
  * tidak menjawab sama sekali (timeout / DNS gagal)

Hasilnya disimpan ke berkas, supaya bisa dilanjutkan dan diperiksa ulang
tanpa meminta ulang semua alamat.
"""

import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"
HASIL = W / "build" / "periksa-thumbnail.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://lumawall.xinet.id/",
}

# Batas waktu per permintaan. Thumbnail itu berkas kecil; kalau lebih dari ini,
# gambar itu memang tidak akan sempat muncul di layar pengguna.
BATAS = 20

PEKERJA = 24


def periksa(url):
    """Kembalikan (keadaan, keterangan, ukuran)."""
    if not url or not url.strip():
        return "KOSONG", "alamat kosong", 0

    url = url.strip()

    for percobaan in range(2):
        try:
            # GET, bukan HEAD: banyak CDN menjawab HEAD dengan 403 atau 405
            # sementara GET biasa berhasil, jadi HEAD akan melaporkan gambar
            # sehat sebagai rusak.
            req = Request(url, headers=UA, method="GET")
            with urlopen(req, timeout=BATAS) as f:
                tipe = (f.headers.get("Content-Type") or "").lower()
                # Baca hanya awal berkas: cukup untuk memastikan ada isinya,
                # tanpa mengunduh seluruh gambar.
                potongan = f.read(2048)
                panjang = f.headers.get("Content-Length")

                if not potongan:
                    return "RUSAK", "isi kosong", 0

                # Halaman HTML berarti alamatnya mengarah ke halaman error,
                # bukan ke berkas gambar.
                if "text/html" in tipe or potongan.lstrip()[:1] in (b"<",):
                    return "RUSAK", "bukan gambar (HTML)", len(potongan)

                if "image" not in tipe and not potongan[:3] in (b"\xff\xd8\xff", b"\x89PN", b"GIF", b"RIF"):
                    return "RUSAK", "jenis tidak dikenal: " + (tipe or "kosong"), len(potongan)

                ukuran = int(panjang) if (panjang or "").isdigit() else len(potongan)
                return "OK", tipe, ukuran

        except HTTPError as e:
            if e.code in (403, 401) and percobaan == 0:
                # Sekali lagi tanpa Referer: sebagian host menolak Referer asing.
                try:
                    req = Request(url, headers={"User-Agent": UA["User-Agent"]}, method="GET")
                    with urlopen(req, timeout=BATAS) as f:
                        potongan = f.read(2048)
                        if potongan and potongan.lstrip()[:1] != b"<":
                            return "OK", "ok tanpa referer", len(potongan)
                except Exception:
                    pass
                return "DITOLAK", "HTTP %d" % e.code, 0
            if e.code in (404, 410):
                return "HILANG", "HTTP %d" % e.code, 0
            if 500 <= e.code < 600:
                return "RUSAK", "HTTP %d" % e.code, 0
            if e.code in (403, 401):
                return "DITOLAK", "HTTP %d" % e.code, 0
            return "RUSAK", "HTTP %d" % e.code, 0

        except (URLError, OSError) as e:
            if percobaan == 0:
                time.sleep(1.0)
                continue
            return "GAGAL", str(e)[:60], 0

        except Exception as e:
            return "GAGAL", str(e)[:60], 0

    return "GAGAL", "tidak menjawab", 0


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MENGUJI SEMUA THUMBNAIL KATALOG")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    print("  entri katalog: %d" % len(items))
    print()

    # Hasil lama dipakai ulang: hanya alamat yang belum pernah diuji yang
    # diminta lagi. Menguji ulang 26 ribu alamat setiap kali akan membuang
    # puluhan menit tanpa menambah pengetahuan.
    sudah = {}
    if HASIL.exists():
        try:
            sudah = json.loads(HASIL.read_text(encoding="utf-8")).get("hasil", {})
            print("  hasil lama dipakai ulang: %d alamat" % len(sudah))
        except Exception:
            sudah = {}

    alamat = []
    for it in items:
        u = (it.get("thumbnailUrl") or "").strip()
        if u and u not in sudah:
            alamat.append(u)
    alamat = list(dict.fromkeys(alamat))
    print("  alamat yang perlu diuji: %d" % len(alamat))
    print()

    hasil = dict(sudah)
    selesai = 0
    mulai = time.time()

    if alamat:
        with ThreadPoolExecutor(max_workers=PEKERJA) as pool:
            tugas = {pool.submit(periksa, u): u for u in alamat}
            for t in as_completed(tugas):
                u = tugas[t]
                try:
                    keadaan, ket, ukuran = t.result()
                except Exception as e:
                    keadaan, ket, ukuran = "GAGAL", str(e)[:60], 0
                hasil[u] = {"keadaan": keadaan, "ket": ket, "ukuran": ukuran}
                selesai += 1
                if selesai % 500 == 0:
                    lewat = time.time() - mulai
                    print("     %6d / %d  (%.0f dtk)" % (selesai, len(alamat), lewat))
                    HASIL.parent.mkdir(parents=True, exist_ok=True)
                    HASIL.write_text(json.dumps({"hasil": hasil}, ensure_ascii=False), encoding="utf-8")

    HASIL.parent.mkdir(parents=True, exist_ok=True)
    HASIL.write_text(json.dumps({"hasil": hasil}, ensure_ascii=False), encoding="utf-8")

    # ── Ringkasan ─────────────────────────────────────────────────────────
    print()
    print("  ── ringkasan ──")
    hitung = Counter(v["keadaan"] for v in hasil.values())
    for keadaan, n in hitung.most_common():
        print("     %-10s %6d" % (keadaan, n))

    rusak = [u for u, v in hasil.items() if v["keadaan"] != "OK"]
    print()
    print("     thumbnail bermasalah: %d dari %d" % (len(rusak), len(hasil)))
    print()

    # Sebaran per host: satu host yang bermasalah menjelaskan ribuan gambar
    # sekaligus, dan itu mengubah cara memperbaikinya.
    print("  ── sebaran masalah per host ──")
    per_host = Counter()
    for u in rusak:
        per_host[urlparse(u).netloc] += 1
    for host, n in per_host.most_common(15):
        print("     %-32s %6d" % (host, n))
    print()

    # Contoh tiap jenis masalah
    print("  ── contoh ──")
    for keadaan in ("HILANG", "DITOLAK", "RUSAK", "GAGAL"):
        contoh = [u for u, v in hasil.items() if v["keadaan"] == keadaan][:3]
        for u in contoh:
            print("     %-9s %s" % (keadaan, u[:96]))
    print()

    print("  hasil lengkap: %s" % HASIL)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
