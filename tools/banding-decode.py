#!/usr/bin/env python3
"""Ukur biaya decode: berkas ASLI vs salinan BARU (24 fps + keyframe rapat).

Kenapa dipisah dari ukur-decode.py: yang ini membandingkan tiga hal sekaligus,
supaya sumbangan tiap perbaikan terlihat - bukan hanya "sekarang lebih baik".

  asli            berkas 4K/2560 apa adanya
  salinan lama    hasil perkecil, tanpa batas fps, keyframe 8,3 detik
  salinan baru    hasil perkecil + 24 fps + keyframe 1,8 detik

Yang diukur adalah kenaikan beban decode GPU di atas garis dasar, memakai
ffmpeg dengan NVDEC pada kecepatan putar asli. Wallpaper yang sedang jalan
tidak diganggu: pengukurannya memakai selisih, bukan penghentian.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

CACHE = Path(os.environ["LOCALAPPDATA"]) / "LumaWall" / "VideoCache"
CONFIG = Path(os.environ["LOCALAPPDATA"]) / "LumaWall" / "config.json"
COUNTER = r"\GPU Engine(*engtype_VideoDecode*)\Utilization Percentage"


def ukur(detik=6, jeda=0.5):
    script = (
        "$v=@();"
        "for ($i=0; $i -lt %d; $i++) {"
        "  $c = Get-Counter '%s' -EA SilentlyContinue;"
        "  $t = ($c.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum;"
        "  $v += [math]::Round($t,2);"
        "  Start-Sleep -Milliseconds %d"
        "};"
        "$v -join ' '"
    ) % (int(detik / jeda), COUNTER, int(jeda * 1000))
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, timeout=180).stdout
    nilai = [float(x) for x in out.split() if x.replace(".", "", 1).isdigit()]
    if not nilai:
        return 0.0, 0.0
    return sum(nilai) / len(nilai), max(nilai)


def decode(berkas, detik=6):
    p = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-hwaccel", "cuda",
         "-re", "-i", str(berkas), "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    time.sleep(1.5)
    avg, maks = ukur(detik)
    try:
        p.terminate()
        p.wait(timeout=10)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    time.sleep(1.2)
    return avg, maks


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   BIAYA DECODE: ASLI vs SALINAN BARU (24 fps, keyframe rapat)")
print("  ══════════════════════════════════════════════════════════════════")
print()

dasar, _ = ukur()
print("  garis dasar (wallpaper yang sedang jalan): %.1f%%" % dasar)
print()

# Berkas yang diuji: yang asli dipakai, dan salinan barunya.
d = json.load(open(CONFIG, encoding="utf-8"))
mv = {e["Key"]: e["Value"] for e in (d.get("MonitorVideos") or [])}

print("  %-46s %10s %10s" % ("berkas", "rata-rata", "puncak"))
print("  " + "-" * 68)

total_baru = 0.0
for device, asli in sorted(mv.items()):
    if not os.path.exists(asli):
        continue
    nama = Path(asli).stem
    salinan = None
    for f in sorted(CACHE.glob(nama + "-*24fps-*.mp4")):
        salinan = f
        break

    avg_a, maks_a = decode(asli)
    print("  %-46s %9.1f%% %9.1f%%" % ("asli   " + Path(asli).name[:38], avg_a - dasar, maks_a - dasar))

    if salinan is not None:
        avg_b, maks_b = decode(salinan)
        print("  %-46s %9.1f%% %9.1f%%" % ("baru   " + salinan.name[:38], avg_b - dasar, maks_b - dasar))
        total_baru += avg_b - dasar
    print()

print("  " + "-" * 68)
print("  jumlah ketiga salinan baru : %.1f%%" % total_baru)
print()
