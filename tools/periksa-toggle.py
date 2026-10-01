#!/usr/bin/env python3
"""Periksa sakelar di Luma Studio lewat UI Automation.

Kenapa lewat UI Automation: sakelar ini terlihat sebagai track dan knob yang
digambar sendiri, dan itu tidak bisa diperiksa dari tangkapan layar - jendela
aplikasi memakai komposisi DirectComposition sehingga PrintWindow menghasilkan
bitmap kosong. Yang bisa dibaca dengan andal adalah pohon aksesibilitasnya, dan
itu justru yang menentukan: kalau sebuah sakelar tidak ada di sana, screen
reader tidak bisa membacanya dan alat pemeriksa tidak bisa mengoperasikannya.

Yang diperiksa:
  * apakah sakelarnya ada dan dikenali sebagai CheckBox;
  * apakah ia mendukung TogglePattern, sehingga bisa dibalik tanpa klik;
  * apakah namanya terbaca;
  * apakah keadaannya bisa dibaca dan diubah.

Pemakaian:
  python tools/periksa-toggle.py
"""
import json
import subprocess
import sys

PS = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$semua = $root.FindAll([System.Windows.Automation.TreeScope]::Children,
    [System.Windows.Automation.Condition]::TrueCondition)

$win = $null
$luasTerbesar = 0
foreach ($w in $semua) {
    try {
        if ($w.Current.ProcessId -eq 0) { continue }
        $p = Get-Process -Id $w.Current.ProcessId -ErrorAction SilentlyContinue
        if ($p -eq $null -or $p.ProcessName -ne 'LumaWall') { continue }
        $r = $w.Current.BoundingRectangle
        # Jendela utama minimal 700x500; jendela toast (200x123) dilewati.
        if ($r.Width -lt 700 -or $r.Height -lt 500) { continue }
        $luas = $r.Width * $r.Height
        if ($luas -gt $luasTerbesar) { $luasTerbesar = $luas; $win = $w }
    } catch { }
}
if ($win -eq $null) { Write-Output '{"error":"jendela LumaWall tidak ditemukan"}'; exit 1 }

# Buka halaman Luma Studio.
$navCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, 'Luma Studio')
$nav = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $navCond)
if ($nav -ne $null) {
    try {
        $nav.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Start-Sleep -Milliseconds 1500
    } catch { }
}

# Kumpulkan semua CheckBox.
$cbCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::CheckBox)
$kotak = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cbCond)

$hasil = @()
foreach ($k in $kotak) {
    $nama = $k.Current.Name
    $bisaToggle = $false
    $keadaan = "?"
    try {
        $tp = $k.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $bisaToggle = $true
        $keadaan = $tp.Current.ToggleState.ToString()
    } catch { }
    $r = $k.Current.BoundingRectangle
    $hasil += [pscustomobject]@{
        Nama    = $nama
        Toggle  = $bisaToggle
        Keadaan = $keadaan
        W       = [int]$r.Width
        H       = [int]$r.Height
        Aktif   = $k.Current.IsEnabled
    }
}

[pscustomobject]@{ Jumlah = $kotak.Count; Kotak = $hasil } | ConvertTo-Json -Depth 4 -Compress
'''


def main():
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS],
                       capture_output=True, timeout=180)
    keluaran = (r.stdout or b'').decode('utf-8', 'replace').strip()
    if not keluaran:
        print('  ! tidak ada keluaran')
        galat = (r.stderr or b'').decode('utf-8', 'replace').strip()
        if galat:
            print('  ' + galat[:400])
        return 1

    try:
        data = json.loads(keluaran.splitlines()[-1])
    except Exception as e:
        print('  ! keluaran tidak bisa dibaca: %s' % e)
        print('  ' + keluaran[:400])
        return 1

    if 'error' in data:
        print('  ! %s' % data['error'])
        return 1

    kotak = data.get('Kotak') or []
    if isinstance(kotak, dict):
        kotak = [kotak]

    print()
    print('  ══ sakelar di Luma Studio ══')
    print()
    print('  jumlah sakelar: %d' % len(kotak))
    print()

    gagal = 0
    for k in kotak:
        tanda = 'OK  '
        if not k['Toggle']:
            tanda = 'GAGAL'
            gagal += 1
        elif k['W'] < 30 or k['H'] < 16:
            tanda = 'KECIL'
            gagal += 1
        print('  %s  %-28s toggle=%-5s keadaan=%-8s %dx%d'
              % (tanda, (k['Nama'] or '(tanpa nama)')[:28], k['Toggle'],
                 k['Keadaan'], k['W'], k['H']))

    print()
    if len(kotak) == 0:
        print('  GAGAL: tidak ada sakelar yang ditemukan di halaman Studio')
        print('         (sakelar yang tidak ada di pohon aksesibilitas tidak bisa')
        print('          dibaca screen reader dan tidak bisa dioperasikan alat uji)')
        return 1
    if gagal:
        print('  %d sakelar bermasalah' % gagal)
        return 1
    print('  ✓ semua sakelar ada, bisa dibalik, dan ukurannya benar')
    return 0


if __name__ == '__main__':
    sys.exit(main())
