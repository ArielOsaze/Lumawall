"""Add the missing Studio/Timer copy, and name the page Luma Studio.

The Studio page was built with 88 translation keys that were never added to the
Copy dictionary in MainWindow.cs. Tr() returns the key itself when it is not in
the dictionary, so every label on that page rendered as raw text: a slider was
labelled "studio.brightness", a shape button said "timer.pill", and the nav rail
said "nav.studio". Nothing threw and nothing was logged - the page simply looked
broken, which is exactly the kind of fault that survives a build-and-click test.

The dictionary is four parallel strings per key: Indonesian, English, Chinese,
Japanese - the same order and the same four languages as the rest of the file.

Written as a script rather than a hand edit so the wording can be reviewed as a
table, and so re-running it is a no-op once the keys are present.
"""

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "LumaWall" / "MainWindow.cs"

# key: (Indonesian, English, Chinese, Japanese)
COPY = {
    # The nav rail. Short, because the rail is narrow; the page heading carries
    # the full product name.
    # Measured at 50.58 DIP against the 64 DIP available inside a rail label
    # (tools/measure-nav-label.ps1), so the full name fits without an ellipsis.
    "nav.studio": ("Luma Studio", "Luma Studio", "Luma Studio", "Luma Studio"),

    # The page itself.
    "studio.title": ("Luma Studio", "Luma Studio", "Luma Studio", "Luma Studio"),
    "studio.sub": (
        "Atur warna, filter, dan bentuk wallpaper untuk tiap monitor.",
        "Tune colour, filters and framing for each display.",
        "为每台显示器调整色彩、滤镜与画面构图。",
        "モニターごとに色、フィルター、表示方法を調整します。",
    ),

    # Which monitor the controls below apply to.
    "studio.display": (
        "Monitor yang sedang diatur",
        "Display being edited",
        "正在调整的显示器",
        "調整するモニター",
    ),
    "studio.primary": ("Utama", "Primary", "主显示器", "メイン"),

    # ── colour ───────────────────────────────────────────────────────────────
    "studio.look": ("Warna", "Colour", "色彩", "カラー"),
    "studio.brightness": ("Kecerahan", "Brightness", "亮度", "明るさ"),
    "studio.contrast": ("Kontras", "Contrast", "对比度", "コントラスト"),
    "studio.saturation": ("Saturasi", "Saturation", "饱和度", "彩度"),
    "studio.hue": ("Rona", "Hue", "色相", "色相"),
    "studio.gamma": ("Gamma", "Gamma", "伽马", "ガンマ"),

    "studio.filter": ("Filter", "Filter", "滤镜", "フィルター"),
    "filter.none": ("Tanpa filter", "None", "无", "なし"),
    "filter.grayscale": ("Hitam putih", "Grayscale", "灰度", "グレースケール"),
    "filter.sepia": ("Sepia", "Sepia", "怀旧", "セピア"),
    "filter.cool": ("Dingin", "Cool", "冷色", "クール"),
    "filter.warm": ("Hangat", "Warm", "暖色", "ウォーム"),
    "filter.vivid": ("Vivid", "Vivid", "鲜艳", "ビビッド"),
    "filter.noir": ("Noir", "Noir", "黑色电影", "ノワール"),
    "filter.dream": ("Dream", "Dream", "梦幻", "ドリーム"),

    "studio.flip": ("Cermin", "Mirror", "镜像", "ミラー"),
    "flip.none": ("Normal", "Normal", "正常", "標準"),
    "flip.h": ("Kiri-kanan", "Left to right", "左右", "左右"),
    "flip.v": ("Atas-bawah", "Top to bottom", "上下", "上下"),
    "flip.both": ("Keduanya", "Both", "两者", "両方"),

    # ── HDR ──────────────────────────────────────────────────────────────────
    "studio.hdr": ("HDR", "HDR", "HDR", "HDR"),
    "studio.hdrOn": ("Pemetaan tone", "Tone mapping", "色调映射", "トーンマッピング"),
    "studio.hdrHint": (
        "Menjaga detail di bagian terang dan gelap pada wallpaper berkontras tinggi.",
        "Keeps detail in the bright and dark parts of a high-contrast wallpaper.",
        "保留高对比壁纸明暗两处的细节。",
        "コントラストの強い壁紙でも明部と暗部のディテールを保ちます。",
    ),
    "studio.hdrExposure": ("Eksposur", "Exposure", "曝光", "露出"),
    "studio.hdrHighlight": ("Kompresi sorotan", "Highlight compression", "高光压缩", "ハイライト圧縮"),

    # ── framing ──────────────────────────────────────────────────────────────
    "studio.framing": ("Bingkai", "Framing", "构图", "フレーミング"),
    "studio.fit": ("Cara mengisi layar", "How it fills the screen", "填充方式", "表示方法"),
    "fit.cover": ("Penuh, tepi terpotong", "Fill, edges cropped", "铺满并裁剪", "画面いっぱい（切り抜き）"),
    "fit.contain": ("Utuh, ada garis tepi", "Whole image, letterboxed", "完整显示（留边）", "全体表示（余白あり）"),
    "fit.fill": ("Regangkan mengikuti layar", "Stretch to the screen", "拉伸铺满", "画面に合わせて伸縮"),
    "fit.center": ("Ukuran asli di tengah", "Actual size, centred", "原始大小居中", "等倍で中央"),
    "studio.zoom": ("Zoom", "Zoom", "缩放", "ズーム"),
    "studio.panX": ("Geser mendatar", "Pan horizontally", "水平平移", "横方向の位置"),
    "studio.panY": ("Geser tegak", "Pan vertically", "垂直平移", "縦方向の位置"),

    # ── playback ─────────────────────────────────────────────────────────────
    "studio.playback": ("Pemutaran", "Playback", "播放", "再生"),
    "studio.rate": ("Kecepatan putar", "Playback speed", "播放速度", "再生速度"),
    "studio.pingpong": ("Maju-mundur", "Play forward then back", "往复播放", "ピンポン再生"),
    "studio.pingpongHint": (
        "Memutar maju lalu mundur, halus untuk loop pendek.",
        "Plays forward then backward, smooth for a short loop.",
        "先正放再倒放，短循环更顺滑。",
        "順再生と逆再生を繰り返し、短いループが滑らかになります。",
    ),
    "studio.on": ("Aktif", "On", "开启", "オン"),
    "studio.off": ("Mati", "Off", "关闭", "オフ"),
    "studio.reset": ("Atur ulang monitor ini", "Reset this display", "重置此显示器", "このモニターをリセット"),
    "studio.resetAll": ("Atur ulang semua", "Reset everything", "全部重置", "すべてリセット"),

    # ── one wallpaper across several monitors ────────────────────────────────
    "studio.span": ("Wallpaper menyambung", "One wallpaper across monitors", "跨显示器延展", "モニターをまたぐ表示"),
    "studio.spanHint": (
        "Satu wallpaper membentang di beberapa monitor sekaligus.",
        "One wallpaper spanning several monitors at once.",
        "一张壁纸同时横跨多台显示器。",
        "1枚の壁紙を複数のモニターにまたがって表示します。",
    ),
    "studio.spanSingle": ("Butuh dua monitor atau lebih.", "Needs two or more displays.", "需要两台或更多显示器。", "2台以上のモニターが必要です。"),
    "studio.spanWith": ("Sambung dengan {0}", "Stretch with {0}", "与 {0} 拼接", "{0} とつなげる"),
    "studio.spanOn": ("Nyalakan", "Turn on", "开启", "オン"),
    "studio.spanOff": ("Matikan", "Turn off", "关闭", "オフ"),
    "studio.spanActive": ("Sedang aktif: {0}", "Active now: {0}", "当前启用：{0}", "現在有効：{0}"),
    "studio.spanApplied": ("Wallpaper disambung.", "Wallpaper stretched.", "壁纸已延展。", "壁紙をつなげました。"),
    "studio.spanNoWallpaper": ("Pilih wallpaper dulu di Koleksi.", "Pick a wallpaper in Library first.", "请先在媒体库选择壁纸。", "先にライブラリで壁紙を選んでください。"),
    "studio.remove": ("Hapus", "Remove", "移除", "削除"),

    # ── the desktop timer ────────────────────────────────────────────────────
    "studio.timer": ("Timer desktop", "Desktop timer", "桌面计时器", "デスクトップタイマー"),
    "timer.enable": ("Tampilkan timer", "Show a timer", "显示计时器", "タイマーを表示"),
    "timer.hint": (
        "Menampilkan jam atau hitung mundur di atas wallpaper.",
        "Shows a clock or countdown on top of the wallpaper.",
        "在壁纸上方显示时钟或倒计时。",
        "壁紙の上に時計やカウントダウンを表示します。",
    ),
    "timer.mode": ("Mode", "Mode", "模式", "モード"),
    "timer.countdown": ("Hitung mundur", "Countdown", "倒计时", "カウントダウン"),
    "timer.clock": ("Jam", "Clock", "时钟", "時計"),
    "timer.stopwatch": ("Stopwatch", "Stopwatch", "秒表", "ストップウォッチ"),
    "timer.shape": ("Bentuk", "Shape", "形状", "形"),
    "timer.pill": ("Kapsul", "Pill", "胶囊", "ピル"),
    "timer.circle": ("Bulat", "Circle", "圆形", "円"),
    "timer.square": ("Kotak", "Square", "方形", "四角"),
    "timer.bare": ("Tanpa latar", "No background", "无底色", "背景なし"),
    "timer.position": ("Penempatan", "Placement", "位置", "配置"),
    "timer.tl": ("Kiri atas", "Top left", "左上", "左上"),
    "timer.tc": ("Tengah atas", "Top centre", "上中", "上中央"),
    "timer.tr": ("Kanan atas", "Top right", "右上", "右上"),
    "timer.ml": ("Kiri tengah", "Middle left", "左中", "左中央"),
    "timer.mc": ("Tengah", "Centre", "正中", "中央"),
    "timer.mr": ("Kanan tengah", "Middle right", "右中", "右中央"),
    "timer.bl": ("Kiri bawah", "Bottom left", "左下", "左下"),
    "timer.bc": ("Tengah bawah", "Bottom centre", "下中", "下中央"),
    "timer.br": ("Kanan bawah", "Bottom right", "右下", "右下"),
    "timer.size": ("Ukuran", "Size", "大小", "サイズ"),
    "timer.opacity": ("Transparansi", "Opacity", "不透明度", "不透明度"),
    "timer.offsetX": ("Geser mendatar", "Horizontal offset", "水平偏移", "横オフセット"),
    "timer.offsetY": ("Geser tegak", "Vertical offset", "垂直偏移", "縦オフセット"),
    "timer.length": ("Durasi (detik)", "Duration (seconds)", "时长（秒）", "時間（秒）"),
    "timer.blink": ("Berkedip di akhir", "Blink at the end", "结束时闪烁", "終了時に点滅"),
    "timer.blinkHint": (
        "Membuat timer berkedip saat hitung mundur habis.",
        "Makes the timer blink when the countdown reaches zero.",
        "倒计时归零时让计时器闪烁。",
        "カウントダウンが0になると点滅します。",
    ),
    "timer.restart": ("Mulai ulang", "Restart", "重新开始", "リスタート"),
    "timer.restarted": ("Timer dimulai ulang.", "Timer restarted.", "计时器已重新开始。", "タイマーをリスタートしました。"),
    "timer.pause": ("Jeda", "Pause", "暂停", "一時停止"),
}


def escape(value):
    """Escape for a C# string literal. The copy is prose, so only the quote matters."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main():
    raw = SOURCE.read_bytes()

    # The file already holds Chinese and Japanese text, so it is UTF-8. Preserve a
    # byte-order mark if one is present: csc reads a BOM-less file as the system
    # code page, which would turn every one of those strings into mojibake.
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")

    existing = set(re.findall(r'\{\s*"([A-Za-z][A-Za-z0-9._]*)"\s*,\s*new\[\]', text))
    todo = {k: v for k, v in COPY.items() if k not in existing}

    print("  keys already in the dictionary: %d" % (len(COPY) - len(todo)))
    print("  keys to add: %d" % len(todo))

    if not todo:
        print("  nothing to do")
        return 0

    # The file is checked out with CRLF endings, and the anchors below are written
    # with "\n". Matching fails silently as "the anchor is not where I expect",
    # which reads like the wrong file rather than the wrong line ending.
    nl = "\r\n" if "\r\n" in text else "\n"
    if nl != "\n":
        print("  line endings: CRLF")

    # Append to the end of the Copy initialiser rather than rewriting it, so the
    # existing 103 entries keep their exact formatting and review history.
    last_entry = '            { "inspector.detected", new[] { "terdeteksi", "detected", "已检测", "検出" } }'
    anchor = last_entry + nl + "        };"
    if anchor not in text:
        print("  ERROR: the end of the Copy dictionary is not where this script expects.")
        print("  Look for the closing brace of Copy in MainWindow.cs and update the anchor.")
        return 1

    lines = []
    for key in sorted(todo):
        id_txt, en_txt, zh_txt, ja_txt = todo[key]
        lines.append(
            '            { "%s", new[] { "%s", "%s", "%s", "%s" } },'
            % (key, escape(id_txt), escape(en_txt), escape(zh_txt), escape(ja_txt))
        )

    block = last_entry + "," + nl + nl.join(lines) + nl + "        };"
    text = text.replace(anchor, block, 1)

    # Every value must have exactly four languages, or Tr() indexes past the end
    # for Chinese and Japanese and the app throws on a page switch.
    bad = [k for k, v in COPY.items() if len(v) != 4]
    if bad:
        print("  ERROR: these keys do not have four languages: %s" % ", ".join(bad))
        return 1

    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    SOURCE.write_bytes(out)

    print("  wrote %d entries; dictionary is now %d keys" % (len(todo), len(COPY)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
