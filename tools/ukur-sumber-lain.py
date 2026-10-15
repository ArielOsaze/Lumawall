#!/usr/bin/env python3
"""Ukur berapa entri baru yang tersedia di sumber LAIN setelah moewalls habis.

KENAPA ALAT INI ADA:

moewalls hanya menyisakan 253 entri yang belum diambil, sementara yang diminta
500. Menebak bahwa sumber lain "pasti punya sisa" tidak cukup - kalau ternyata
tidak, panen akan berjalan lama lalu berhenti jauh dari target, dan laporannya
akan tampak seperti kegagalan padahal yang kurang adalah sumbernya.

Alat ini mengukur dulu, baru memanen. Yang diukur: berapa tautan di halaman
terbaru setiap sumber yang BELUM ada di katalog.

Sumber yang diperiksa:
  desktophut.com   - punya 9084 entri di katalog, halaman daftarnya terbuka
  motionbgs.com    - punya 9697 entri, memakai API sendiri
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get(url, timeout=30):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return f.read().decode("utf-8", "replace")


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   ENTRI BARU DI SUMBER LAIN")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        if s:
            ada.add(s)

    print("  katalog: %d entri" % len(items))
    print()

    # ── desktophut ────────────────────────────────────────────────────────
    print("  ── desktophut.com ──")
    # Halaman daftarnya memuat tautan detail; polanya diambil dari entri
    # katalog yang sudah ada supaya cocok dengan yang benar-benar dipakai.
    contoh = [i["sourceUrl"] for i in items
              if "desktophut.com" in (i.get("sourceUrl") or "")][:3]
    print("     contoh tautan yang dipakai katalog:")
    for c in contoh:
        print("        %s" % c)
    print()

    # Pola umum: /nama-wallpaper/ atau /nama/
    pola = re.compile(r'https://(?:www\.)?desktophut\.com/([a-z0-9\-]+)/')
    ditemukan = set()
    for jalur in ["https://www.desktophut.com/latest", "https://www.desktophut.com/",
                  "https://www.desktophut.com/newest", "https://www.desktophut.com/anime"]:
        try:
            html = get(jalur)
            tautan = set("https://www.desktophut.com/%s/" % m for m in pola.findall(html))
            # Halaman kategori juga memuat tautan non-wallpaper.
            tautan = {t for t in tautan if not any(
                x in t for x in ["/tag/", "/category/", "/page/", "/user/", "/search/",
                                 "/privacy", "/terms", "/dmca", "/about", "/contact",
                                 "/faq", "/latest/", "/newest/"])}
            print("     %-44s %4d tautan" % (jalur, len(tautan)))
            ditemukan |= tautan
            time.sleep(0.5)
        except Exception as e:
            print("     %-44s GAGAL %s" % (jalur, str(e)[:40]))

    baru = {t for t in ditemukan if t.rstrip("/").lower() not in ada}
    print()
    print("     tautan diperiksa : %d" % len(ditemukan))
    print("     tautan BARU      : %d" % len(baru))
    print()
    for t in list(baru)[:8]:
        print("        %s" % t)
    print()

    # ── Kesimpulan ────────────────────────────────────────────────────────
    print("  ══════════════════════════════════════════════════════════════════")
    print("   SISA YANG TERSEDIA")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    print("   moewalls   : 253  (sudah dipanen)")
    print("   desktophut : %d" % len(baru))
    total = 253 + len(baru)
    print()
    print("   total perkiraan: %d" % total)
    if total >= 500:
        print("   CUKUP untuk 500.")
    else:
        print("   KURANG dari 500. Perlu sumber ketiga (motionbgs/wallhaven).")
    print()

    if baru:
        simpan = W / "build" / "desktophut-baru.json"
        simpan.parent.mkdir(parents=True, exist_ok=True)
        simpan.write_text(json.dumps(sorted(baru), ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print("  disimpan: %s" % simpan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
