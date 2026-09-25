<div align="center">

<img src="site/assets/logo/logo-150.png" width="96" alt="LumaWall">

# LumaWall

**Live wallpaper engine untuk Windows — wallpaper video di GPU, bukan CPU.**

[![Version](https://img.shields.io/badge/version-4.0.1-ff3b57?style=flat-square)](../../releases)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4?style=flat-square)](#syarat-sistem)
[![.NET](https://img.shields.io/badge/.NET%20Framework-4.8-512bd4?style=flat-square)](https://dotnet.microsoft.com/download/dotnet-framework)
[![License](https://img.shields.io/badge/license-MIT-35d6e8?style=flat-square)](LICENSE.txt)

[**Situs web**](https://arielosaze.github.io/Lumawall/) &middot; [Unduh](../../releases/latest) &middot; [Laporkan masalah](../../issues)

</div>

---

## Apa ini

LumaWall menempatkan wallpaper video di lapisan desktop Windows (WorkerW) untuk
setiap monitor, dengan **hardware video decode di GPU** dan kompositing lewat DWM.
Pemakaian CPU tetap di bawah 1% saat wallpaper berjalan.

Berbeda dari wallpaper engine lain, pause bekerja **per-monitor**: game fullscreen
di satu layar hanya menghentikan wallpaper di layar itu, dan wallpaper kembali
berjalan sekitar **4 milidetik** setelah game ditutup — dipicu oleh event sistem
Windows, bukan polling.

## Keunggulan

| | |
|---|---|
| **GPU hardware decode** | NVDEC / DXVA, kompositing DWM. CPU < 1% untuk tiga wallpaper 1080p. |
| **Pause per-monitor** | Fullscreen/maximized di satu layar tidak menghentikan layar lain. |
| **Respons 4 ms** | Dipicu WinEvent hook. Terukur 4 ms saat pause, 1 ms saat resume. |
| **Pulih sendiri** | Explorer restart? Wallpaper dibangun ulang otomatis dalam < 4 detik. |
| **Hemat RAM** | Wallpaper statis dirender langsung tanpa WebView2 (hemat ±130 MB/layar). |
| **Profil multi-display** | Simpan susunan wallpaper semua monitor, pulihkan dengan satu klik. |
| **Katalog 5.000+** | Cari, filter, unduh. Setiap unduhan menyertakan `.license.txt`. |
| **Empat bahasa** | Indonesia, English, 简体中文, 日本語. |
| **Tanpa iklan** | Tidak ada iklan, akun, atau telemetri. |

## Unduh

**[arielosaze.github.io/Lumawall](https://arielosaze.github.io/Lumawall/)** &mdash;
atau ambil langsung dari halaman [Releases](../../releases/latest):

| Berkas | Ukuran | Untuk |
|---|---|---|
| `LumaWall-Setup-4.0.1.exe` | 14,5 MB | Pemasangan normal |
| `LumaWall_4.0.1.0_x64.msix` | 13,7 MB | Microsoft Store / sideload |
| `LumaWall-portable-4.0.1.zip` | 13,0 MB | Tanpa instalasi |

## Syarat sistem

- Windows 10 versi 1809 (build 17763) atau lebih baru, atau Windows 11
- Prosesor & Windows 64-bit (x64)
- WebView2 Runtime — sudah tersedia di Windows 11 dan Windows 10 yang terbarui.
  Aplikasi akan memberi tahu bila belum ada, disertai tautan unduh gratisnya.

## Membangun dari sumber

```powershell
# Butuh Visual Studio Build Tools dengan komponen .NET desktop
msbuild LumaWall\LumaWall.csproj /p:Configuration=Release `
  /p:FrameworkPathOverride="C:\Windows\Microsoft.NET\Framework64\v4.0.30319"

# Paket MSIX (butuh Windows SDK: makeappx)
powershell -File build_msix.ps1
powershell -File validate_msix.ps1      # 42 pemeriksaan
```

## Struktur

```
LumaWall/
  Program.cs        mesin: WebView2, WorkerW hosting, manajemen wallpaper
  MainWindow.cs     antarmuka WPF
  Icons.cs          ikon vektor (tanpa font emoji)
  catalog.json      katalog bawaan
site/               situs pemasaran
  index.html
  assets/shots/     tangkapan layar asli aplikasi
  assets/video/     video promo
tools/              skrip pembangun & pengujian
```

## Situs & video

- Situs: <https://arielosaze.github.io/Lumawall/>
- Video promo 52 detik dirender dari frame memakai tangkapan layar asli aplikasi:
  [`site/assets/video/lumawall-promo.mp4`](site/assets/video/lumawall-promo.mp4)
- Tangkapan layar diambil langsung dari aplikasi yang berjalan, bukan mockup:
  [`tools/capture-ui-for-site.ps1`](tools/capture-ui-for-site.ps1)

## Pengujian

Repositori ini menyertakan skrip yang membuktikan perilaku yang diklaim, bukan
sekadar menjalankan aplikasi:

```powershell
powershell -File tools\production-check.ps1        # 12 pemeriksaan penerimaan
powershell -File tools\timing-guarantees-test.ps1  # pause/resume/apply
powershell -File tools\explorer-recovery-test.ps1  # pemulihan setelah shell crash
powershell -File tools\permonitor-test.ps1         # pause per-monitor
powershell -File tools\render-check.ps1            # wallpaper benar-benar beranimasi
powershell -File validate_msix.ps1                 # 42 pemeriksaan paket Store
```

## Lisensi

MIT — lihat [LICENSE.txt](LICENSE.txt).

Wallpaper dalam katalog memiliki lisensinya masing-masing; setiap unduhan
menyertakan berkas `.license.txt` berisi kreator, lisensi, dan tautan sumber.

---

<div align="center">
<sub>Part of <b>Xinet Group</b></sub>
</div>
