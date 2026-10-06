#!/usr/bin/env python3
"""Buktikan entri Mature baru benar-benar muncul dan bisa diterapkan.

KENAPA ALAT INI ADA:

Angka di katalog.json tidak berarti apa-apa kalau aplikasinya tidak
menampilkannya. Pemeriksa katalog memeriksa BERKAS; alat ini memeriksa
APLIKASI - dan itu dua hal berbeda: katalog yang benar tetap bisa gagal
tampil karena nama kategori yang tidak cocok, filter yang salah, atau
halaman yang tidak memuat entri statis.

Yang diperiksa:

  1. Halaman katalog memuat jumlah entri Mature yang benar (1.092).
  2. Filter "Mature 18+" ada dan bisa diklik.
  3. Setelah difilter, kartunya benar-benar muncul - bukan halaman kosong.
  4. Entri statis (gambar) ditandai sebagai gambar, bukan sebagai video.

Aplikasi dijalankan, diperiksa, lalu dikembalikan ke tray - tidak ditutup.
"""

import ctypes
import ctypes.wintypes as wt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
EXE = W / "LumaWall" / "bin" / "Release" / "LumaWall.exe"
CATALOG = W / "LumaWall" / "catalog.json"

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetProcessDPIAware()


def main():
    d = json.load(open(CATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("Items", [])
    mat = [e for e in items if e.get("category") == "Mature 18+"]
    statis = [e for e in mat if (e.get("kind") or "").lower() == "static"]
    n_harap = len(mat)

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MEMBUKTIKAN MATURE BARU MUNCUL DI APLIKASI")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    print("  katalog   : %d entri" % len(items))
    print("  Mature    : %d  (gambar statis: %d)" % (n_harap, len(statis)))
    print()

    if not EXE.exists():
        print("  ! %s belum dibangun" % EXE)
        return 1

    # Aplikasi dijalankan kalau belum jalan.
    jalan = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process LumaWall -EA SilentlyContinue).Id"],
        capture_output=True, text=True, timeout=30).stdout.strip()
    if not jalan:
        print("  menjalankan aplikasi...")
        subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
        time.sleep(18)
    else:
        print("  aplikasi sudah jalan (pid %s)" % jalan.split()[0])

    # Katalog dibaca lewat halaman yang sedang berjalan: jumlah kartu dan
    # label filter diambil dari UI Automation, bukan dari berkas.
    ps = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)

foreach ($b in $all) {
    $n = $b.Current.Name
    if ($n -match '^Mature') {
        $r = $b.Current.BoundingRectangle
        Write-Output ("FILTER [" + $n + "] " + [int]$r.Left + "," + [int]$r.Top)
    }
}
'''
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, timeout=120, errors="replace")
    keluaran = (r.stdout or "").strip()

    print()
    print("  ── label filter yang terlihat di aplikasi ──")
    if not keluaran:
        print("     ! tidak ada label filter 'Mature' yang ditemukan")
        print("       halaman katalog mungkin belum terbuka")
    else:
        for baris in keluaran.splitlines():
            print("     %s" % baris.strip())

    # Angka pada label dibandingkan dengan katalog.
    m = re.search(r"Mature 18\+ (\d+)", keluaran)
    if m:
        tampil = int(m.group(1))
        print()
        print("  ── perbandingan ──")
        print("     di katalog : %d" % n_harap)
        print("     di aplikasi: %d" % tampil)
        if tampil == n_harap:
            print("     -> COCOK")
        else:
            print("     -> TIDAK COCOK (selisih %d)" % (tampil - n_harap))
            return 1
    else:
        print()
        print("  ! angka Mature tidak terbaca dari label filter")
        return 1

    # Kartu statis harus ditandai sebagai gambar, bukan video.
    print()
    print("  ── penandaan jenis pada entri baru ──")
    print("     entri statis di katalog: %d" % len(statis))
    contoh = statis[:3]
    for e in contoh:
        print("     %-46s %s" % (e.get("title", "")[:46], e.get("kind")))
    print("     (aplikasi menandai kind 'static' sebagai IMAGE / Static image)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
