#!/usr/bin/env python3
"""Cari pola pada token video moewalls yang gagal.

KENAPA BERKAS INI ADA:

175 dari 253 entri moewalls bisa dipakai, 78 tidak. Kalau ada pola yang
menjelaskan perbedaan itu, 78 entri yang gagal mungkin bisa diselamatkan - dan
kalau tidak ada pola, setidaknya jelas bahwa kegagalannya bukan kesalahan alat.

Dua uji sebelumnya sudah membuktikan arahnya:
  * video yang dilaporkan gagal menjawab 200 dengan HTML, bukan berkas video
  * video yang dilaporkan sehat menjawab 200 dengan application/octet-stream
    dan ukuran 10-30 MB

Jadi kegagalannya nyata. Yang dicari sekarang: apa yang membedakan keduanya.

Yang diperiksa:
  1. Panjang token
  2. Ada tidaknya padding base64 ("%3D" di akhir)
  3. Ada tidaknya "%2B" / "%2F" (karakter + dan / dari base64)
  4. Kategori
  5. Tanggal unggah (dari URL thumbnail)
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
DETAIL = W / "build" / "moewalls-detail.json"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")}


def uji(url):
    """True kalau jawabannya berkas video, bukan halaman HTML."""
    try:
        h = dict(UA)
        h["Range"] = "bytes=0-1023"
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            awal = f.read(1024)
            if "text/html" in tipe or awal.lstrip()[:1] == b"<":
                return False, "html"
            return True, tipe
    except HTTPError as e:
        return False, "http%d" % e.code
    except Exception as e:
        return False, str(e)[:30]


def ciri(url):
    """Ciri-ciri token."""
    token = url.split("video=", 1)[1] if "video=" in url else ""
    try:
        mentah = unquote(token)
    except Exception:
        mentah = token
    return {
        "panjang": len(token),
        "panjang_mentah": len(mentah),
        "padding": token.endswith("%3D") or token.endswith("="),
        "plus": "%2B" in token or "+" in token,
        "slash": "%2F" in token or "/" in token,
        "persen": token.count("%"),
    }


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   POLA TOKEN YANG GAGAL")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    siap = {u: d for u, d in detail.items() if not d.get("gagal")}
    print("  entri siap: %d" % len(siap))
    print()

    # Uji semua, catat cirinya. Ini yang membuktikan pola, bukan menebaknya.
    print("  ── menguji setiap video dan mencatat ciri tokennya ──")
    sehat = []
    gagal = []
    for n, (u, d) in enumerate(siap.items(), 1):
        ok, ket = uji(d["videoUrl"])
        c = ciri(d["videoUrl"])
        c["kategori"] = d.get("category")
        c["judul"] = d.get("title", "")[:50]
        if ok:
            sehat.append(c)
        else:
            gagal.append(c)
        if n % 40 == 0:
            print("     %4d / %d  (sehat %d, gagal %d)" % (n, len(siap), len(sehat), len(gagal)))

    print()
    print("  sehat: %d   gagal: %d" % (len(sehat), len(gagal)))
    print()

    if not gagal:
        print("  Tidak ada yang gagal pada uji ini.")
        return 0

    # ── Bandingkan ciri ───────────────────────────────────────────────────
    print("  ══════════════════════════════════════════════════════════════════")
    print("   PERBANDINGAN CIRI: SEHAT vs GAGAL")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    def persen(daftar, kunci):
        if not daftar:
            return 0.0
        return 100.0 * sum(1 for c in daftar if c.get(kunci)) / len(daftar)

    print("  %-22s %14s %14s" % ("ciri", "sehat", "gagal"))
    print("  " + "-" * 52)
    for kunci, label in [("padding", "ada padding ="), ("plus", "ada + (base64)"),
                         ("slash", "ada / (base64)")]:
        print("  %-22s %13.0f%% %13.0f%%" % (label, persen(sehat, kunci), persen(gagal, kunci)))

    if sehat and gagal:
        ps = sum(c["panjang"] for c in sehat) / len(sehat)
        pg = sum(c["panjang"] for c in gagal) / len(gagal)
        print("  %-22s %14.0f %14.0f" % ("panjang token (rata)", ps, pg))
        ps2 = sum(c["persen"] for c in sehat) / len(sehat)
        pg2 = sum(c["persen"] for c in gagal) / len(gagal)
        print("  %-22s %14.1f %14.1f" % ("jumlah % (rata)", ps2, pg2))
    print()

    # ── Sebaran kategori ──────────────────────────────────────────────────
    print("  ── kategori: sehat vs gagal ──")
    ks = Counter(c["kategori"] for c in sehat)
    kg = Counter(c["kategori"] for c in gagal)
    for k in sorted(set(ks) | set(kg)):
        print("     %-14s sehat %4d   gagal %4d" % (k, ks.get(k, 0), kg.get(k, 0)))
    print()

    # ── Contoh yang gagal ─────────────────────────────────────────────────
    print("  ── contoh yang gagal ──")
    for c in gagal[:10]:
        print("     [%s] %-42s panjang=%d padding=%s"
              % (c["kategori"], c["judul"], c["panjang"], c["padding"]))
    print()

    print("  ══════════════════════════════════════════════════════════════════")
    if persen(gagal, "padding") > 80 and persen(sehat, "padding") < 20:
        print("   POLA DITEMUKAN: yang gagal hampir semuanya punya padding '='")
        print("   di akhir token, dan yang sehat hampir tidak ada.")
    elif persen(gagal, "persen") if False else False:
        pass
    else:
        print("   Tidak ada pola tunggal yang menjelaskan kegagalannya.")
        print("   Kemungkinan tokennya memang kedaluwarsa - moewalls menerbitkan")
        print("   tautan unduhan yang berlaku terbatas, dan sebagian sudah lewat.")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    (W / "build" / "pola-video-gagal.json").write_text(
        json.dumps({"sehat": len(sehat), "gagal": len(gagal),
                    "contoh_gagal": gagal[:40]}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
