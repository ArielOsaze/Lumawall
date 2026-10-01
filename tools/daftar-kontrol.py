#!/usr/bin/env python3
"""Daftar SEMUA kontrol di jendela LumaWall, apa pun jenisnya.

Dipakai untuk menjawab pertanyaan "kenapa sakelarnya tidak terdeteksi": kalau
sakelarnya ada di pohon aksesibilitas tetapi dengan jenis yang berbeda dari yang
dicari, itu penyebabnya - dan itu terlihat dari daftar ini.

Pemakaian:
  python tools/daftar-kontrol.py
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
        if ($r.Width -lt 700 -or $r.Height -lt 500) { continue }
        $luas = $r.Width * $r.Height
        if ($luas -gt $luasTerbesar) { $luasTerbesar = $luas; $win = $w }
    } catch { }
}
if ($win -eq $null) { Write-Output '{"error":"jendela tidak ditemukan"}'; exit 1 }

$hasil = @()
$semuaElemen = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition)

foreach ($e in $semuaElemen) {
    try {
        $jenis = $e.Current.ControlType.ProgrammaticName -replace 'ControlType\.',''
        $nama = $e.Current.Name
        $r = $e.Current.BoundingRectangle
        # Hanya yang terlihat dan punya ukuran.
        if ($r.Width -le 0 -or $r.Height -le 0) { continue }
        $pola = @()
        foreach ($p in $e.GetSupportedPatterns()) {
            $pola += ($p.ProgrammaticName -replace 'Pattern\.','')
        }
        $hasil += [pscustomobject]@{
            Jenis = $jenis
            Nama  = $nama
            W     = [int]$r.Width
            H     = [int]$r.Height
            X     = [int]$r.Left
            Y     = [int]$r.Top
            Pola  = ($pola -join ',')
        }
    } catch { }
}

$hasil | ConvertTo-Json -Depth 3 -Compress
'''


def main():
    r = subprocess.run(['powershell', '-NoProfile', '-Command', PS],
                       capture_output=True, timeout=240)
    keluaran = (r.stdout or b'').decode('utf-8', 'replace').strip()
    if not keluaran:
        print('  ! tidak ada keluaran')
        galat = (r.stderr or b'').decode('utf-8', 'replace').strip()
        if galat:
            print('  ' + galat[:500])
        return 1

    try:
        data = json.loads(keluaran.splitlines()[-1])
    except Exception as e:
        print('  ! keluaran tidak bisa dibaca: %s' % e)
        print('  ' + keluaran[:500])
        return 1

    if isinstance(data, dict) and 'error' in data:
        print('  ! %s' % data['error'])
        return 1

    if isinstance(data, dict):
        data = [data]

    from collections import Counter
    jenis = Counter(e['Jenis'] for e in data)

    print()
    print('  ══ semua kontrol di jendela LumaWall ══')
    print()
    print('  total: %d' % len(data))
    print()
    print('  ── jenis kontrol ──')
    for k, v in jenis.most_common():
        print('     %-20s %d' % (k, v))
    print()

    # Cari apa pun yang mirip sakelar
    print('  ── yang namanya mengandung kata kunci sakelar ──')
    kunci = ['hdr', 'ping', 'timer', 'jam', 'tanggal', '12', 'blink', 'kedip',
             'aktif', 'enable', 'nyala', 'toggle', 'switch']
    ketemu = 0
    for e in data:
        nama = (e['Nama'] or '').lower()
        if any(k in nama for k in kunci):
            print('     %-14s %-34s %dx%d  pola=%s'
                  % (e['Jenis'], (e['Nama'] or '?')[:34], e['W'], e['H'], e['Pola'][:40]))
            ketemu += 1
    if ketemu == 0:
        print('     tidak ada')
    print()

    # Cari kontrol yang punya TogglePattern
    print('  ── kontrol dengan TogglePattern ──')
    toggle = [e for e in data if 'Toggle' in (e['Pola'] or '')]
    if toggle:
        for e in toggle:
            print('     %-14s %-34s %dx%d' % (e['Jenis'], (e['Nama'] or '?')[:34], e['W'], e['H']))
    else:
        print('     tidak ada')
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
