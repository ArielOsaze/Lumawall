"""Finish wiring Studio: the timer commands, the nav entry, the route, and translations.

The app's copy table has FOUR languages, not two - Indonesian, English, Chinese and
Japanese - which is easy to miss and would leave two languages showing raw key names like
"studio.brightness". Every entry here carries all four.
"""

from pathlib import Path
import re

WINDOW = Path('LumaWall/MainWindow.cs')
with WINDOW.open(encoding='utf-8', newline='') as handle:
    text = handle.read()
original = text

# ── 1. the timer commands ────────────────────────────────────────────────────
anchor = '        private void ExitApp()\r\n'
assert anchor in text, 'ExitApp anchor not found'
if 'private void timerRefresh()' not in text:
    text = text.replace(anchor, (
        '        /// <summary>\r\n'
        '        /// The desktop timer\'s commands, called from the Studio page.\r\n'
        '        ///\r\n'
        '        /// Thin wrappers, so the page never touches the timer directly: the timer owns a\r\n'
        '        /// top-level window, and a page that could reach it could leave it in a state the\r\n'
        '        /// app does not know about.\r\n'
        '        /// </summary>\r\n'
        '        private void timerRefresh()\r\n'
        '        {\r\n'
        '            if (desktopTimer == null) desktopTimer = new DesktopTimer(delegate { return config.Timer; });\r\n'
        '            desktopTimer.Refresh();\r\n'
        '        }\r\n'
        '\r\n'
        '        private void timerReset()\r\n'
        '        {\r\n'
        '            if (desktopTimer == null) desktopTimer = new DesktopTimer(delegate { return config.Timer; });\r\n'
        '            desktopTimer.Reset();\r\n'
        '        }\r\n'
        '\r\n'
        '        private void timerPause()\r\n'
        '        {\r\n'
        '            if (desktopTimer == null) return;\r\n'
        '            desktopTimer.Pause();\r\n'
        '        }\r\n'
        '\r\n'
    ) + anchor, 1)

# ── 2. the route ─────────────────────────────────────────────────────────────
route_anchor = '            else if (page == "displays") pageHost.Content = BuildDisplays();\r\n'
assert route_anchor in text, 'route anchor not found'
if 'page == "studio"' not in text:
    text = text.replace(route_anchor, route_anchor + (
        '            else if (page == "studio") pageHost.Content = BuildStudio();\r\n'
    ), 1)

# ── 3. the sidebar entry, straight after Displays ────────────────────────────
nav_anchor = '            nav.Children.Add(NavRailButton("displays", Icons.Displays, "nav.displays"));\r\n'
assert nav_anchor in text, 'nav anchor not found'
if '"nav.studio"' not in text:
    text = text.replace(nav_anchor, nav_anchor + (
        '            nav.Children.Add(NavRailButton("studio", Icons.Sparkle, "nav.studio"));\r\n'
    ), 1)

# ── 4. the copy table, four languages ────────────────────────────────────────
# id, en, zh, ja - in the same order as every other entry in this table.
STRINGS = {
    'nav.studio': ('Studio', 'Studio', '工作室', 'スタジオ'),

    'studio.title': ('Studio', 'Studio', '工作室', 'スタジオ'),
    'studio.sub': (
        'Atur tampilan, framing, dan playback tiap monitor',
        'Per-monitor look, framing and playback',
        '逐个显示器调整外观、取景与播放',
        'モニターごとに見た目・フレーミング・再生を調整'),
    'studio.display': ('Monitor yang sedang diatur', 'Display being edited', '正在编辑的显示器', '編集中のモニター'),
    'studio.displayHint': (
        'Pengaturan di bawah berlaku untuk monitor ini ({0}).',
        'The settings below apply to this display ({0}).',
        '以下设置仅作用于该显示器（{0}）。',
        '以下の設定はこのモニター（{0}）に適用されます。'),
    'studio.primary': ('Utama', 'Primary', '主显示器', 'メイン'),
    'studio.look': ('Tampilan', 'Look', '外观', '見た目'),
    'studio.brightness': ('Kecerahan', 'Brightness', '亮度', '明るさ'),
    'studio.contrast': ('Kontras', 'Contrast', '对比度', 'コントラスト'),
    'studio.saturation': ('Saturasi', 'Saturation', '饱和度', '彩度'),
    'studio.hue': ('Hue', 'Hue', '色相', '色相'),
    'studio.gamma': ('Gamma', 'Gamma', '伽马', 'ガンマ'),
    'studio.filter': ('Filter', 'Filter', '滤镜', 'フィルター'),
    'studio.flip': ('Flip', 'Flip', '翻转', '反転'),

    'studio.hdr': ('HDR & tone mapping', 'HDR & tone mapping', 'HDR 与色调映射', 'HDR とトーンマッピング'),
    'studio.hdrOn': ('Tone mapping', 'Tone mapping', '色调映射', 'トーンマッピング'),
    'studio.hdrHint': (
        'Roll-off highlight dan exposure, dihitung di GPU. Frame yang didekode tidak diubah.',
        'Highlight roll-off and exposure, computed on the GPU. The decoded frames are untouched.',
        '高光滚降与曝光，由 GPU 计算，不改变已解码的帧。',
        'ハイライトのロールオフと露出を GPU で計算。デコード済みフレームは変更しません。'),
    'studio.hdrExposure': ('Exposure (stop)', 'Exposure (stops)', '曝光（档）', '露出（段）'),
    'studio.hdrHighlight': ('Titik roll-off', 'Roll-off point', '滚降起点', 'ロールオフ開始点'),

    'studio.framing': ('Framing', 'Framing', '取景', 'フレーミング'),
    'studio.fit': ('Mode pas', 'Fit mode', '适配方式', 'フィット'),
    'studio.zoom': ('Zoom', 'Zoom', '缩放', 'ズーム'),
    'studio.panX': ('Geser horizontal', 'Pan horizontally', '水平平移', '水平パン'),
    'studio.panY': ('Geser vertikal', 'Pan vertically', '垂直平移', '垂直パン'),

    'studio.playback': ('Playback', 'Playback', '播放', '再生'),
    'studio.rate': ('Kecepatan', 'Playback rate', '播放速度', '再生速度'),
    'studio.pingpong': ('Ping-pong', 'Ping-pong', '往返播放', 'ピンポン再生'),
    'studio.pingpongHint': (
        'Putar maju lalu mundur, bukan melompat ke awal.',
        'Play forward then backward instead of jumping to the start.',
        '正放后再倒放，而不是跳回开头。',
        '先頭に戻らず、正再生と逆再生を繰り返します。'),

    'studio.reset': ('Reset monitor ini', 'Reset this display', '重置此显示器', 'このモニターをリセット'),
    'studio.resetAll': ('Reset semua', 'Reset all', '全部重置', 'すべてリセット'),
    'studio.on': ('Aktif', 'On', '开', 'オン'),
    'studio.off': ('Mati', 'Off', '关', 'オフ'),

    'studio.span': ('Wallpaper menyambung', 'Stretched wallpaper', '跨屏壁纸', 'つながる壁紙'),
    'studio.spanHint': (
        'Satu wallpaper yang sama dibagi ke beberapa monitor, jadi gambarnya nyambung.',
        'One wallpaper split across several monitors, so the picture continues.',
        '同一张壁纸分布到多台显示器，画面连成一体。',
        '同じ壁紙を複数モニターに分割し、絵がつながります。'),
    'studio.spanSingle': ('Butuh minimal dua monitor.', 'Needs at least two monitors.', '至少需要两台显示器。', 'モニターが2台以上必要です。'),
    'studio.spanWith': ('Sambung ke {0}', 'Continue onto {0}', '连接到 {0}', '{0} につなげる'),
    'studio.spanOn': ('Nyalakan', 'Turn on', '开启', 'オン'),
    'studio.spanOff': ('Matikan', 'Turn off', '关闭', 'オフ'),
    'studio.spanActive': ('Aktif: {0}', 'Active: {0}', '已启用：{0}', '有効：{0}'),
    'studio.spanApplied': ('Wallpaper disambung', 'Wallpaper stretched', '壁纸已跨屏', '壁紙をつなげました'),
    'studio.spanNoWallpaper': ('Pilih wallpaper dulu', 'Choose a wallpaper first', '请先选择壁纸', '先に壁紙を選んでください'),
    'studio.remove': ('Hapus', 'Remove', '删除', '削除'),

    'studio.timer': ('Timer desktop', 'Desktop timer', '桌面计时器', 'デスクトップタイマー'),
    'timer.enable': ('Timer', 'Timer', '计时器', 'タイマー'),
    'timer.hint': (
        'Angka besar di atas desktop: hitung mundur, jam, atau stopwatch.',
        'A large readout over the desktop: a countdown, a clock, or a stopwatch.',
        '桌面上的大号读数：倒计时、时钟或秒表。',
        'デスクトップ上の大きな表示：カウントダウン・時計・ストップウォッチ。'),
    'timer.mode': ('Mode', 'Mode', '模式', 'モード'),
    'timer.countdown': ('Hitung mundur', 'Countdown', '倒计时', 'カウントダウン'),
    'timer.clock': ('Jam', 'Clock', '时钟', '時計'),
    'timer.stopwatch': ('Stopwatch', 'Stopwatch', '秒表', 'ストップウォッチ'),
    'timer.shape': ('Bentuk', 'Shape', '形状', '形'),
    'timer.pill': ('Pil', 'Pill', '胶囊', 'ピル'),
    'timer.circle': ('Bulat', 'Circle', '圆形', '円'),
    'timer.square': ('Kotak', 'Square', '方形', '四角'),
    'timer.bare': ('Tanpa latar', 'No background', '无背景', '背景なし'),
    'timer.position': ('Posisi', 'Position', '位置', '位置'),
    'timer.tl': ('Kiri atas', 'Top left', '左上', '左上'),
    'timer.tc': ('Tengah atas', 'Top centre', '上中', '上中央'),
    'timer.tr': ('Kanan atas', 'Top right', '右上', '右上'),
    'timer.ml': ('Kiri tengah', 'Middle left', '左中', '左中央'),
    'timer.mc': ('Tengah', 'Centre', '正中', '中央'),
    'timer.mr': ('Kanan tengah', 'Middle right', '右中', '右中央'),
    'timer.bl': ('Kiri bawah', 'Bottom left', '左下', '左下'),
    'timer.bc': ('Tengah bawah', 'Bottom centre', '下中', '下中央'),
    'timer.br': ('Kanan bawah', 'Bottom right', '右下', '右下'),
    'timer.size': ('Ukuran', 'Size', '大小', 'サイズ'),
    'timer.opacity': ('Transparansi', 'Opacity', '不透明度', '不透明度'),
    'timer.offsetX': ('Geser X', 'Offset X', 'X 偏移', 'X オフセット'),
    'timer.offsetY': ('Geser Y', 'Offset Y', 'Y 偏移', 'Y オフセット'),
    'timer.length': ('Durasi (detik)', 'Length (seconds)', '时长（秒）', '長さ（秒）'),
    'timer.blink': ('Berkedip di akhir', 'Blink at the end', '结束时闪烁', '終了時に点滅'),
    'timer.blinkHint': (
        'Hitung mundur berkedip saat habis.',
        'The countdown blinks when it reaches zero.',
        '倒计时归零时闪烁。',
        'カウントダウンが0になると点滅します。'),
    'timer.restart': ('Mulai ulang', 'Restart', '重新开始', '再スタート'),
    'timer.pause': ('Jeda / lanjut', 'Pause / resume', '暂停 / 继续', '一時停止 / 再開'),
    'timer.restarted': ('Timer dimulai ulang', 'Timer restarted', '计时器已重新开始', 'タイマーを再スタートしました'),

    'filter.none': ('Tanpa', 'None', '无', 'なし'),
    'filter.grayscale': ('Hitam putih', 'Grayscale', '黑白', 'モノクロ'),
    'filter.sepia': ('Sepia', 'Sepia', '复古', 'セピア'),
    'filter.cool': ('Dingin', 'Cool', '冷色', 'クール'),
    'filter.warm': ('Hangat', 'Warm', '暖色', 'ウォーム'),
    'filter.vivid': ('Vivid', 'Vivid', '鲜艳', 'ビビッド'),
    'filter.noir': ('Noir', 'Noir', '暗黑', 'ノワール'),
    'filter.dream': ('Dream', 'Dream', '梦幻', 'ドリーム'),

    'flip.none': ('Normal', 'Normal', '正常', '通常'),
    'flip.h': ('Kiri-kanan', 'Horizontal', '水平', '左右'),
    'flip.v': ('Atas-bawah', 'Vertical', '垂直', '上下'),
    'flip.both': ('Keduanya', 'Both', '双向', '両方'),

    'fit.cover': ('Penuh (crop)', 'Cover', '铺满（裁剪）', 'カバー'),
    'fit.contain': ('Utuh', 'Contain', '完整显示', '全体表示'),
    'fit.fill': ('Regang', 'Stretch', '拉伸', 'ストレッチ'),
    'fit.center': ('Asli', 'Original', '原始尺寸', '原寸'),
}

table_anchor = '            { "nav.displays", new[] { "Monitor", "Displays", "显示器", "モニター" } },\r\n'
assert table_anchor in text, 'copy table anchor not found'
if '"nav.studio"' not in text:
    lines = []
    for key, values in STRINGS.items():
        escaped = [v.replace('\\', '\\\\').replace('"', '\\"') for v in values]
        lines.append('            { "%s", new[] { "%s" } },' % (key, '", "'.join(escaped)))
    text = text.replace(table_anchor, table_anchor + '\r\n'.join(lines) + '\r\n', 1)

with WINDOW.open('w', encoding='utf-8', newline='') as handle:
    handle.write(text)

print('  timer commands:  %s' % ('private void timerRefresh()' in text))
print('  route:           %s' % ('page == "studio"' in text))
print('  nav entry:       %s' % ('NavRailButton("studio"' in text))
print('  copy keys added: %d' % len(STRINGS))
print('  bytes: %d -> %d' % (len(original), len(text)))

# ── 5. the icon the nav entry names ──────────────────────────────────────────
ICONS = Path('LumaWall/Icons.cs')
icons = ICONS.read_text(encoding='utf-8')
if 'public const string Sparkle' not in icons:
    print('  NOTE: Icons.Sparkle does not exist - switching the nav entry to Icons.Displays')
    with WINDOW.open(encoding='utf-8', newline='') as handle:
        fixed = handle.read()
    fixed = fixed.replace('NavRailButton("studio", Icons.Sparkle, "nav.studio")',
                          'NavRailButton("studio", Icons.Displays, "nav.studio")')
    with WINDOW.open('w', encoding='utf-8', newline='') as handle:
        handle.write(fixed)
    print('  nav icon:        Icons.Displays')
else:
    print('  nav icon:        Icons.Sparkle exists')
