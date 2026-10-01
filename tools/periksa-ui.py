#!/usr/bin/env python3
"""Periksa tata letak Luma Studio dan Displays dari pohon elemen WPF.

Tangkapan layar tidak bisa dipakai untuk memeriksa UI aplikasi ini: jendelanya
memakai komposisi DirectComposition, sehingga PrintWindow menghasilkan bitmap
kosong dan CopyFromScreen menyalin jendela lain di atasnya. Yang bisa dibaca
dengan andal adalah pohon elemennya - dan itu justru cukup untuk menjawab
pertanyaan yang ada.

Pemeriksaannya memakai UI Automation, yang membaca tata letak SEBENARNYA setelah
WPF menghitungnya. Itu penting: sebuah kontrol bisa terlihat benar di kode dan
tetap meleset di layar, dan hanya tata letak hasil hitungan yang tahu.

Pemakaian:
  python tools/periksa-ui.py --halaman "Luma Studio"
  python tools/periksa-ui.py --halaman Monitor
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PS = r'''
param([string]$Halaman, [int]$LayarX, [int]$LayarY, [int]$LayarW, [int]$LayarH)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement

# Cari jendela LumaWall yang paling besar.
$semuaJendela = $root.FindAll([System.Windows.Automation.TreeScope]::Children,
    [System.Windows.Automation.Condition]::TrueCondition)
$win = $null
$luasTerbesar = 0
foreach ($w in $semuaJendela) {
    try {
        if ($w.Current.ProcessId -eq 0) { continue }
        $p = Get-Process -Id $w.Current.ProcessId -ErrorAction SilentlyContinue
        if ($p -eq $null -or $p.ProcessName -ne 'LumaWall') { continue }
        $r = $w.Current.BoundingRectangle
        # Jendela utama minimal 700x500. Tanpa ambang ini, jendela toast
        # (200x123) yang muncul sesaat ikut terpilih sebagai "terbesar" dan
        # seluruh pemeriksaan berjalan pada jendela yang salah - yang muncul
        # sebagai "0 elemen, tata letak bersih", lulus tanpa memeriksa apa pun.
        if ($r.Width -lt 700 -or $r.Height -lt 500) { continue }
        $luas = $r.Width * $r.Height
        if ($luas -gt $luasTerbesar) { $luasTerbesar = $luas; $win = $w }
    } catch { }
}
if ($win -eq $null) { Write-Output '{"error":"jendela LumaWall tidak ditemukan"}'; exit 1 }

# Dipindahkan ke layar uji supaya layar utama tidak tersentuh.
try {
    $t = $win.GetCurrentPattern([System.Windows.Automation.TransformPattern]::Pattern)
    $t.Move($LayarX + 10, $LayarY + 10)
    $t.Resize([Math]::Min(1400, $LayarW - 40), [Math]::Min(900, $LayarH - 40))
    Start-Sleep -Milliseconds 700
} catch { }

# Klik navigasi halaman.
$navCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, $Halaman)
$nav = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $navCond)
if ($nav -ne $null) {
    try {
        $inv = $nav.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $inv.Invoke()
        Start-Sleep -Milliseconds 1200
    } catch { }
}

$rw = $win.Current.BoundingRectangle
$elemen = @()
$semua = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition)
foreach ($e in $semua) {
    try {
        $r = $e.Current.BoundingRectangle
        if ($r.Width -le 0 -or $r.Height -le 0) { continue }
        $elemen += [pscustomobject]@{
            Nama  = $e.Current.Name
            Jenis = ($e.Current.ControlType.ProgrammaticName -replace 'ControlType\.','')
            X = [int]$r.Left; Y = [int]$r.Top
            W = [int]$r.Width; H = [int]$r.Height
            Aktif = $e.Current.IsEnabled
        }
    } catch { }
}

[pscustomobject]@{
    Jendela = @{ X=[int]$rw.Left; Y=[int]$rw.Top; W=[int]$rw.Width; H=[int]$rw.Height }
    Elemen = $elemen
} | ConvertTo-Json -Depth 5 -Compress
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--halaman', required=True)
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ukur_layar
    mon = ukur_layar.pilih(args.display)
    if mon is None:
        print('  layar tidak ada')
        return 1

    print()
    print('  ══ periksa UI: %s ══' % args.halaman)
    print()

    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', PS,
         '-Halaman', args.halaman,
         '-LayarX', str(mon['x']), '-LayarY', str(mon['y']),
         '-LayarW', str(mon['width']), '-LayarH', str(mon['height'])],
        capture_output=True, timeout=240)

    # Dibaca sebagai byte lalu didekode dengan toleransi, bukan text=True.
    #
    # PowerShell mengeluarkan byte sesuai halaman kode sistem, dan nama elemen
    # bisa memuat karakter apa pun - termasuk dari nama berkas wallpaper
    # pengguna. Membacanya sebagai UTF-8 ketat menggagalkan seluruh pemeriksaan
    # sebelum satu pun hasil terbaca.
    keluaran = (r.stdout or b'').decode('utf-8', 'replace').strip()
    if not keluaran:
        galat = (r.stderr or b'').decode('utf-8', 'replace').strip()
        print('  ! tidak ada keluaran')
        if galat:
            print('  %s' % galat[:400])
        return 1

    try:
        data = json.loads(keluaran.splitlines()[-1])
    except Exception as e:
        print('  ! keluaran tidak bisa dibaca: %s' % e)
        print('  %s' % keluaran[:400])
        return 1

    if 'error' in data:
        print('  ! %s' % data['error'])
        return 1

    win = data['Jendela']
    elemen = data.get('Elemen', [])
    if isinstance(elemen, dict):
        elemen = [elemen]

    print('  jendela: %dx%d di (%d,%d)' % (win['W'], win['H'], win['X'], win['Y']))
    print('  elemen terlihat: %d' % len(elemen))
    print()

    # ── 1. elemen yang keluar dari batas jendela ────────────────────────────
    keluar = []
    for e in elemen:
        if e['W'] < 40 or e['H'] < 14:
            continue
        if (e['X'] < win['X'] - 3 or e['Y'] < win['Y'] - 3
                or e['X'] + e['W'] > win['X'] + win['W'] + 3
                or e['Y'] + e['H'] > win['Y'] + win['H'] + 3):
            keluar.append(e)

    print('  ── keluar batas jendela ──')
    if keluar:
        for e in keluar[:14]:
            print('     %-34s %-11s (%4d,%4d) %dx%d'
                  % ((e['Nama'] or '(tanpa nama)')[:34], e['Jenis'],
                     e['X'] - win['X'], e['Y'] - win['Y'], e['W'], e['H']))
    else:
        print('     tidak ada')
    print()

    # ── 2. jenis kontrol ────────────────────────────────────────────────────
    jenis = {}
    for e in elemen:
        jenis[e['Jenis']] = jenis.get(e['Jenis'], 0) + 1
    print('  ── jenis kontrol ──')
    for k in sorted(jenis, key=lambda x: -jenis[x]):
        print('     %-16s %d' % (k, jenis[k]))
    print()

    # ── 3. kontrol mati ─────────────────────────────────────────────────────
    kontrol = [e for e in elemen
               if e['Jenis'] in ('CheckBox', 'Button', 'Slider', 'ComboBox',
                                 'RadioButton', 'Edit')]
    mati = [e for e in kontrol if not e['Aktif']]
    print('  ── kontrol ──')
    print('     total %d, nonaktif %d' % (len(kontrol), len(mati)))
    for e in mati[:8]:
        print('     nonaktif: %-30s %s' % ((e['Nama'] or '?')[:30], e['Jenis']))
    print()

    # ── 4. teks yang lebih lebar daripada kotaknya ──────────────────────────
    # Hanya elemen Text yang bisa diperiksa begini, dan hanya kalau namanya
    # cukup panjang untuk dicurigai.
    print('  ── teks panjang yang mungkin terpotong ──')
    panjang = [e for e in elemen if e['Jenis'] == 'Text' and len(e['Nama'] or '') > 46]
    if panjang:
        for e in panjang[:10]:
            print('     %3d huruf, lebar %4dpx: %s' % (len(e['Nama']), e['W'], e['Nama'][:52]))
    else:
        print('     tidak ada')
    print()

    # ── 5. tumpang tindih antar kontrol ─────────────────────────────────────
    # Kontrol (bukan teks) yang saling menimpa adalah cacat tata letak yang
    # nyata: pengguna tidak bisa menekan yang di bawah.
    tumpang = []
    ctrl = [e for e in kontrol if e['W'] >= 30 and e['H'] >= 18]
    for i in range(len(ctrl)):
        a = ctrl[i]
        for j in range(i + 1, len(ctrl)):
            b = ctrl[j]
            x1 = max(a['X'], b['X']); y1 = max(a['Y'], b['Y'])
            x2 = min(a['X'] + a['W'], b['X'] + b['W'])
            y2 = min(a['Y'] + a['H'], b['Y'] + b['H'])
            if x2 <= x1 or y2 <= y1:
                continue
            luas = (x2 - x1) * (y2 - y1)
            kecil = min(a['W'] * a['H'], b['W'] * b['H'])
            if luas > kecil * 0.3:
                tumpang.append((a, b, luas * 100 // kecil))

    print('  ── kontrol yang saling menimpa ──')
    if tumpang:
        for a, b, pct in tumpang[:10]:
            print('     %d%%  "%s" x "%s"' % (pct, (a['Nama'] or '?')[:24], (b['Nama'] or '?')[:24]))
    else:
        print('     tidak ada')
    print()

    masalah = len(keluar) + len(tumpang) + len(mati)
    if masalah == 0:
        print('  ✓ tata letak bersih')
        return 0
    print('  %d hal yang perlu diperiksa' % masalah)
    return 1


if __name__ == '__main__':
    sys.exit(main())
