#!/usr/bin/env python3
"""Cari tahu nama elemen apa yang sebenarnya terlihat UI Automation.

KENAPA ALAT INI ADA:

tools/shoot-ui.py gagal mengklik navigasi: "navigasi Displays: TIDAK ADA",
padahal halaman itu jelas ada di sidebar. Penyebabnya harus diketahui, bukan
ditebak - kalau tidak, alat tangkap layar akan terus memotret halaman yang
salah sambil melaporkan keberhasilan.

Alat ini menyebutkan nama setiap tombol di dalam jendela LumaWall, supaya
nama yang benar bisa dipakai.
"""

import subprocess
import sys

PS = r'''
param([string]$Judul)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement

# Semua jendela tingkat atas lebih dulu: kalau jendela LumaWall tidak ada di
# sini, masalahnya bukan nama elemen tapi jendelanya sendiri.
$condWin = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Window)
$windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $condWin)
Write-Output "JENDELA:"
foreach ($w in $windows) {
    $n = $w.Current.Name
    if ($n -ne '') { Write-Output ("  [" + $n + "]") }
}

# Lalu seluruh tombol di desktop, supaya terlihat nama sebenarnya.
$condBtn = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button)
$btns = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condBtn)
Write-Output ""
Write-Output ("TOMBOL: " + $btns.Count)
$i = 0
foreach ($b in $btns) {
    $n = $b.Current.Name
    $r = $b.Current.BoundingRectangle
    if ($n -ne '' -and $r.Width -gt 0) {
        Write-Output ("  [" + $n + "]  " + [int]$r.Left + "," + [int]$r.Top + " " + [int]$r.Width + "x" + [int]$r.Height)
        $i++
    }
    if ($i -gt 60) { break }
}
'''

r = subprocess.run(
    ['powershell', '-NoProfile', '-Command', PS],
    capture_output=True, text=True, timeout=120, errors='replace')
print(r.stdout)
if r.returncode != 0:
    print("galat:", r.stderr[:2000])
