"""Isi Store listing bahasa tambahan (Chinese / Japanese) untuk LumaWall.

Pemakaian:
  python tools/pc_listing_extra.py --lang zh --fill
  python tools/pc_listing_extra.py --lang ja --fill
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
        if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and 'Partner Center' in t:
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


# Terjemahan ringkas tapi lengkap (tanpa karakter yang bermasalah)
ZH = {
    'Description*': (
        "LumaWall 用流畅的 GPU 加速动态壁纸让你的 Windows 桌面动起来。"
        "内置超过 22,000 张高清和 4K 动态壁纸，也可以使用你自己的视频文件。"
        "LumaWall 在 GPU 上渲染每一帧，因此桌面保持流畅，壁纸持续播放。\n\n"
        "可以为每台显示器设置不同的壁纸，调整色调映射，添加 iOS 风格的桌面时钟小组件，"
        "并让一切在托盘中安静运行。LumaWall 一次购买，无需订阅。\n\n"
        "主要特色：\n"
        "- 超过 22,000 张精选动态壁纸，全部高清或更高\n"
        "- 每台显示器独立壁纸与位置\n"
        "- GPU 渲染，CPU 占用低\n"
        "- 十种 iOS 风格时钟样式，背景透明\n"
        "- 完全控制暂停、播放速度和音量\n"
        "- 使用你自己的视频文件离线播放\n"
        "- 支持中文界面"
    ),
    "What's new in this version": (
        "版本 4.5.9\n"
        "- 停止壁纸后再次应用，屏幕不再长时间变黑；最后一帧会保留到新壁纸就绪\n"
        "- 图片壁纸现在能在 Windows 11 上显示——此前日志显示已就绪却始终不可见\n"
        "- 1366x768 屏幕上壁纸不再被裁切\n"
        "- 在图片壁纸和视频壁纸之间切换不再变黑\n"
        "- 关闭全屏应用后壁纸不再变黑"
    ),
    'Product features': (
        "动态壁纸引擎;每屏壁纸;GPU 加速;22,000+ 壁纸库;时钟小组件;支持 4K;离线播放;无需订阅"
    ),
    'Short title': 'LumaWall - 动态壁纸',
    'Voice title': 'LumaWall 动态壁纸',
    'Short description': (
        "适用于 Windows 的动态壁纸。超过 22,000 张高清和 4K 动态作品，支持多显示器，"
        "GPU 加速，并带 iOS 风格时钟小组件。一次购买，无需订阅。"
    ),
    'Copyright and trademark info': (
        "版权所有 (c) 2026 Xinet Group。保留所有权利。LumaWall 是 Xinet Group 的商标。"
    ),
    'Additional license terms': (
        "LumaWall 为授权使用而非销售。这是一次性购买许可，供你在使用 Microsoft 账户登录的 "
        "Windows 设备上个人使用。壁纸艺术作品归其各自创作者所有。"
    ),
    'Developed by': 'Xinet Group',
}

JA = {
    'Description*': (
        "LumaWall は、なめらかな GPU アクセラレーションのライブ壁紙で Windows デスクトップを"
        "彩ります。HD と 4K のアニメーション作品を 22,000 点以上収録したカタログから選ぶか、"
        "お手持ちの動画ファイルを使用できます。すべてのフレームを GPU で描画するため、"
        "壁紙が動き続けてもデスクトップは快適なままです。\n\n"
        "モニターごとに別々の壁紙を設定し、トーンマッピングを調整し、"
        "iOS 風のデスクトップ時計ウィジェットを追加して、すべてをトレイで静かに動作させられます。"
        "LumaWall は買い切りで、サブスクリプションはありません。\n\n"
        "主な特長:\n"
        "- 厳選された 22,000 点以上のライブ壁紙、すべて HD 以上\n"
        "- モニターごとの壁紙と配置設定\n"
        "- CPU 使用率を抑える GPU レンダリング\n"
        "- 背景が透明な iOS 風クロック 10 スタイル\n"
        "- 一時停止、再生速度、音量を完全にコントロール\n"
        "- お手持ちの動画でオフライン再生\n"
        "- 日本語インターフェースに対応"
    ),
    "What's new in this version": (
        "バージョン 4.5.9\n"
        "- 壁紙を停止して再適用しても画面が長時間黒くならなくなりました。最後のフレームは次の壁紙の準備ができるまで表示されます\n"
        "- 画像壁紙が Windows 11 で表示されるようになりました。以前はログに準備完了と出ても見えませんでした\n"
        "- 1366x768 の画面で壁紙が切り取られなくなりました\n"
        "- 画像壁紙と動画壁紙を切り替えても黒くならなくなりました\n"
        "- 全画面アプリを閉じた後に壁紙が黒くならなくなりました"
    ),
    'Product features': (
        "ライブ壁紙エンジン;モニター別壁紙;GPU アクセラレーション;22,000+ 壁紙カタログ;"
        "時計ウィジェット;4K 対応;オフライン再生;サブスクリプションなし"
    ),
    'Short title': 'LumaWall - ライブ壁紙',
    'Voice title': 'LumaWall ライブ壁紙',
    'Short description': (
        "Windows 用のライブ壁紙。22,000 点以上の HD・4K アニメーション作品、"
        "マルチモニター対応、GPU アクセラレーション、iOS 風の時計ウィジェット付き。"
        "買い切りでサブスクリプションなし。"
    ),
    'Copyright and trademark info': (
        "Copyright (c) 2026 Xinet Group. All rights reserved. "
        "LumaWall は Xinet Group の商標です。"
    ),
    'Additional license terms': (
        "LumaWall は販売ではなくライセンスされます。Microsoft アカウントでサインインした "
        "Windows デバイスでの個人利用を目的とした買い切りライセンスです。"
        "壁紙アートワークの権利は各制作者に帰属します。"
    ),
    'Developed by': 'Xinet Group',
}

LANGS = {'zh': ZH, 'ja': JA}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', required=True, choices=sorted(LANGS))
    ap.add_argument('--fill', action='store_true')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    hwnd = chrome()
    if hwnd is None:
        print('Chrome Partner Center tidak ditemukan')
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
    edits.sort(key=lambda t: t[0])

    data = LANGS[args.lang]

    if args.list:
        for top, n, k, v in edits:
            print('   y=%-6d %-42s %s' % (top, n[:42], ('KOSONG' if not v else '%d char' % len(v))))
        return 0

    if args.fill:
        done = 0
        for top, n, k, v in edits:
            key = None
            for want in data:
                if want.lower() == n.lower():
                    key = want
                    break
            if key is None:
                continue
            if v:
                print('   lewati %-40s (sudah ada isi)' % n[:40])
                continue
            try:
                k.GetValuePattern().SetValue(data[key])
                print('   OK  %-40s (%d char)' % (n[:40], len(data[key])))
                done += 1
                time.sleep(0.35)
            except Exception as e:
                print('   GAGAL %-40s %s' % (n[:40], e))
        print('selesai: %d field terisi' % done)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
