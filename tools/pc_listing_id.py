"""Isi Store listing bahasa Indonesia untuk LumaWall.

Pemakaian:
  python tools/pc_listing_id.py --fill     # isi field yang kosong
  python tools/pc_listing_id.py --list     # lihat field
"""
import argparse
import sys
import time

import uiautomation as auto
import win32gui

TITLE = 'Store listings'


def chrome():
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        cls = win32gui.GetClassName(h)
        t = win32gui.GetWindowText(h)
        if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and TITLE in t:
            found.append(h)
    win32gui.EnumWindows(cb, None)
    return found[0] if found else None


def items(hwnd):
    win = auto.ControlFromHandle(hwnd)
    out = []

    def walk(c, d=0):
        if d > 30:
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids:
            try:
                out.append((k.ControlTypeName, k.Name or '', k))
            except Exception:
                continue
            walk(k, d + 1)
    walk(win)
    return out


ID = {
    'Description*': (
        "LumaWall menghidupkan desktop Windows kamu dengan wallpaper bergerak yang halus "
        "dan dipercepat GPU. Pilih dari katalog bawaan berisi lebih dari 22.000 karya "
        "animasi HD dan 4K, atau pakai file video milikmu sendiri. LumaWall merender "
        "setiap frame di GPU, jadi desktop tetap responsif walau wallpaper terus bergerak.\n\n"
        "Pasang wallpaper berbeda untuk setiap monitor, atur tone mapping, tambahkan "
        "widget jam desktop bergaya iOS, dan biarkan semuanya berjalan tenang di tray. "
        "LumaWall dibeli sekali, tanpa langganan.\n\n"
        "Keunggulan:\n"
        "- Lebih dari 22.000 wallpaper dinamis pilihan, semuanya HD atau lebih tinggi\n"
        "- Wallpaper per monitor dengan penempatan mandiri\n"
        "- Rendering GPU yang menjaga pemakaian CPU tetap rendah\n"
        "- Sepuluh gaya widget jam bergaya iOS dengan latar transparan\n"
        "- Kontrol penuh atas jeda, kecepatan putar, dan volume\n"
        "- Tetap bekerja offline dengan file video milikmu\n"
        "- Antarmuka bahasa Indonesia dan Inggris"
    ),
    "What's new in this version": (
        "Versi 4.5.9\n"
        "- Hentikan wallpaper lalu pasang lagi tidak lagi menyisakan layar hitam; "
        "frame terakhir tetap terlihat sampai wallpaper berikutnya siap\n"
        "- Wallpaper gambar sekarang muncul di Windows 11 - sebelumnya tidak terlihat "
        "sama sekali walau log menyebut sudah siap\n"
        "- Wallpaper tidak lagi terpotong di layar 1366x768\n"
        "- Berpindah antara wallpaper gambar dan video tidak lagi menghitam\n"
        "- Wallpaper tidak lagi hitam setelah keluar dari aplikasi fullscreen"
    ),
    'Product features': (
        "Mesin wallpaper dinamis;Wallpaper per monitor;Dipercepat GPU;"
        "Katalog 22.000+ wallpaper;Widget jam;Siap 4K;Putar offline;Tanpa langganan"
    ),
    'Short title': 'LumaWall - Wallpaper Hidup',
    'Voice title': 'LumaWall wallpaper hidup',
    'Short description': (
        "Wallpaper hidup untuk Windows. Lebih dari 22.000 karya dinamis HD dan 4K, "
        "pengaturan per monitor, dipercepat GPU, plus widget jam bergaya iOS. "
        "Beli sekali, tanpa langganan."
    ),
    'Copyright and trademark info': (
        "Hak cipta (c) 2026 Xinet Group. Seluruh hak dilindungi. "
        "LumaWall adalah merek dagang Xinet Group."
    ),
    'Additional license terms': (
        "LumaWall dilisensikan, bukan dijual. Ini adalah lisensi beli sekali untuk "
        "pemakaian pribadi pada perangkat Windows yang masuk dengan akun Microsoft kamu. "
        "Karya seni wallpaper tetap milik pembuatnya masing-masing."
    ),
    'Developed by': 'Xinet Group',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--fill', action='store_true')
    args = ap.parse_args()

    hwnd = chrome()
    if hwnd is None:
        print('Chrome tidak ditemukan')
        return 2
    all_items = items(hwnd)

    edits = []
    for ct, n, k in all_items:
        if ct == 'EditControl':
            r = k.BoundingRectangle
            if r.right > r.left and r.left > 280:
                try:
                    v = k.GetValuePattern().Value or ''
                except Exception:
                    v = None
                edits.append((r.top, n, k, v))
    edits.sort()

    if args.list:
        for top, n, k, v in edits:
            print('   y=%-6d %-42s %s' % (top, n[:42], ('KOSONG' if not v else '%d char' % len(v))))
        return 0

    if args.fill:
        done = 0
        for top, n, k, v in edits:
            key = None
            for want in ID:
                if want.lower() == n.lower():
                    key = want
                    break
            if key is None:
                continue
            if v:
                print('   lewati %-40s (sudah ada isi)' % n[:40])
                continue
            try:
                k.GetValuePattern().SetValue(ID[key])
                print('   OK  %-40s (%d char)' % (n[:40], len(ID[key])))
                done += 1
                time.sleep(0.35)
            except Exception as e:
                print('   GAGAL %-40s %s' % (n[:40], e))
        print('selesai: %d field terisi' % done)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
