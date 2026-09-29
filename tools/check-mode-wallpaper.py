#!/usr/bin/env python3
"""Pastikan setiap mode wallpaper benar-benar menggambar, bukan hitam.

Dilaporkan: "ada bug bug lain yg buat jd hitam". Bug seperti itu hanya bisa
dibuktikan dengan mengukur layar sungguhan, jadi itulah yang dilakukan di sini.

Yang diuji adalah kedua mode yang punya jalur kode berbeda:

  video   -> WebView2 + dekode perangkat keras
  statis  -> permukaan GDI biasa, tanpa WebView2 sama sekali

Keduanya harus menghasilkan gambar, dan yang diperiksa bukan sekadar "terang":
warna yang terbaca dibandingkan dengan warna gambar ujinya. Pemeriksa yang hanya
memeriksa kecerahan akan meloloskan wallpaper yang salah, dan pernah juga
meloloskan jendela aplikasi sendiri yang kebetulan berdiri di atas layar uji -
karena itu layarnya dibersihkan lebih dulu lewat ukur_layar.

Pemakaian:
  python tools/check-mode-wallpaper.py --display DISPLAY3
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ukur_layar  # noqa: E402

CONFIG = Path('C:/Users/ariel/AppData/Local/LumaWall/config.json')
CADANGAN = Path('C:/Users/ariel/AppData/Local/LumaWall/config.json.cadangan-uji')
GAMBAR = Path('C:/Users/ariel/AppData/Local/LumaWall/Wallpapers/uji-statis-terang.png')


def baca_config():
    return json.loads(CONFIG.read_text(encoding='utf-8-sig'))


def tulis_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')


def peta_monitor(cfg):
    """MonitorVideos sebagai dict device -> berkas.

    Di config bentuknya daftar pasangan Key/Value, bukan objek. Membacanya
    sebagai objek langsung gagal dengan AttributeError, jadi bentuknya
    diseragamkan di sini dan hanya di sini.
    """
    mv = cfg.get('MonitorVideos')
    if isinstance(mv, dict):
        return dict(mv)
    hasil = {}
    if isinstance(mv, list):
        for item in mv:
            if isinstance(item, dict) and 'Key' in item:
                hasil[item['Key']] = item.get('Value')
    return hasil


def set_monitor(cfg, device, berkas):
    """Tulis satu pemetaan monitor, dengan bentuk yang sama seperti aslinya."""
    mv = cfg.get('MonitorVideos')
    if isinstance(mv, dict):
        mv[device] = berkas
        return
    if not isinstance(mv, list):
        mv = []
        cfg['MonitorVideos'] = mv
    for item in mv:
        if isinstance(item, dict) and item.get('Key') == device:
            item['Value'] = berkas
            return
    mv.append({'Key': device, 'Value': berkas})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    monitor = ukur_layar.pilih(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ uji kedua mode wallpaper di %s ══' % args.display)
    print()
    print('  layar: %s' % ('%s %dx%d di (%d,%d)'
                           % (monitor['device'], monitor['width'], monitor['height'],
                              monitor['x'], monitor['y'])))
    print()

    if not CONFIG.exists():
        print('  config tidak ada: %s' % CONFIG)
        return 1
    # Gambar uji dibuat di sini, bukan diandalkan sudah ada. Sebelumnya
    # pemeriksaan ini gagal begitu gambar itu dibersihkan - kegagalan yang tidak
    # ada hubungannya dengan wallpaper yang sedang diuji.
    import siapkan_gambar_uji
    siapkan_gambar_uji.pastikan()

    shutil.copy2(CONFIG, CADANGAN)
    asli = baca_config()
    device = monitor['device']
    semula = peta_monitor(asli).get(device)
    print('  wallpaper semula di layar ini: %s'
          % (Path(semula).name if semula else '(tidak ada)'))
    print()

    video = None
    for p in (asli.get('Library') or []):
        s = str(p)
        if s.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')) and Path(s).exists():
            video = Path(s)
            break
    if video is None:
        print('  ! tidak ada berkas video di library')
        return 1

    print('  gambar uji: %s' % GAMBAR.name)
    print('  video uji : %s' % video.name)
    print()

    gagal = []
    hasil = {}

    try:
        for mode, berkas in (('statis', GAMBAR), ('video', video)):
            print('  ── mode %s ──' % mode)
            cfg = baca_config()
            set_monitor(cfg, device, str(berkas))
            tulis_config(cfg)

            ukur_layar.jalankan_app()

            # Layar uji harus bersih dulu, atau yang terukur adalah jendela
            # aplikasi sendiri - terang, diam, dan selalu tampak benar.
            if not ukur_layar.bersihkan_layar(monitor):
                print('     ! layar uji tidak bisa dibersihkan - pengukuran tidak sah')
                gagal.append(mode)
                print()
                continue

            detik = ukur_layar.tunggu_tergambar(monitor)
            if detik is None:
                print('     ! layar tetap kosong setelah menunggu')
                gagal.append(mode)
                print()
                continue

            time.sleep(3)
            warna = ukur_layar.baca_warna(monitor)
            n = ukur_layar.baca(monitor)
            hasil[mode] = n
            print('     tergambar setelah %d detik' % detik)
            print('     kecerahan %.1f / 255   %s' % (n, ' '.join(warna)))
            if n < 8:
                print('     \u2717 LAYAR HITAM - mode ini tidak menggambar apa pun')
                gagal.append(mode)
            else:
                print('     \u2713 menggambar')
            print()
    finally:
        print('  ── memulihkan config semula ──')
        if CADANGAN.exists():
            shutil.copy2(CADANGAN, CONFIG)
            CADANGAN.unlink()
            print('     dipulihkan')
        ukur_layar.jalankan_app()
        print()

    print('  ══ kesimpulan ══')
    for mode, n in hasil.items():
        print('     %-8s %.1f / 255' % (mode, n))
    if gagal:
        print()
        print('  %d mode bermasalah: %s' % (len(gagal), ', '.join(gagal)))
        return 1
    print()
    print('  kedua mode menggambar dengan benar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
