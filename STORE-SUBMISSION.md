# LumaWall — Microsoft Store submission pack

Everything needed to publish **LumaWall 4.0.1** to the Microsoft Store.

---

## 0. Status build saat ini

```
✅ Aplikasi       LumaWall 4.0.1 (C# WPF + WebView2, .NET FW 4.8, x64)
✅ Paket MSIX     outputs/LumaWall_4.0.1.0_x64.msix        13.67 MB
✅ Installer      outputs/LumaWall-Setup-4.0.1.exe          14.53 MB
✅ Portable       outputs/LumaWall-portable-4.0.1.zip       13.03 MB
✅ Logo           98 aset (semua ukuran + skala + altform)
✅ Validasi       40+ check LULUS (validate_msix.ps1)
✅ Performa       CPU ~19% (dari 169%), RAM ~800 MB, GPU decode aktif
✅ Anti-flicker   672 frame tes, 0 frame hitam
```

Jalankan validasi kapan saja:

```powershell
cd "C:\Users\ariel\Documents\Codex\2026-09-20\bik\work"
powershell -File validate_msix.ps1
```

---

## 1. Artefak yang siap diunggah

Semua ada di **`bik/outputs/`** — subfolder `store/` berisi paket MS + aset
marketing.

| File | Ukuran | Dipakai untuk |
|---|---|---|
| `outputs/store/LumaWall_4.0.1.0_x64.msix` | 13.67 MB | **Paket yang diunggah ke Partner Center** |
| `outputs/store/StoreListing_300x300.png` | 300×300 | Store listing icon |
| `outputs/store/BoxArt_1080x1080.png` | 1080×1080 | Box art (wajib) |
| `outputs/store/PosterArt_720x1080.png` | 720×1080 | Poster art (opsional) |
| `outputs/store/HeroArt_1920x1080.png` | 1920×1080 | Hero art (opsional) |
| `outputs/LumaWall-Setup-4.0.1.exe` | 14.53 MB | Installer klasik (sideload / situs sendiri) |
| `outputs/store/LumaWall-portable-4.0.1.zip` | 13.03 MB | Versi portable |
| `outputs/store/STORE-SUBMISSION.md` | — | Salinan dokumen ini |

### Identitas brand (satu sumber, tiga tempat)

Logo dibuat sekali oleh `make_store_assets.py` lalu dipakai di tiga tempat
sehingga tidak mungkin beda lagi:

| Tempat | Sumber |
|---|---|
| Ikon EXE + shortcut + installer | `LumaWall/app.ico` (7 ukuran: 16–256px) |
| Title bar di dalam aplikasi | `MainWindow.BuildLogoMark()` — grid 3×3 identik |
| Tile & splash MS Store | `LumaWall/Assets/*.png` (98 file) |

Mark: array 3×3 pane dengan gutter seragam, kolom **crimson → putih → cyan**,
di atas squircle gelap bergradasi. Tetap terbaca di 16px karena bentuknya blok
kontras, bukan garis tipis.

---

## 2. Yang WAJIB diganti sebelum submit

Nilai di bawah ini harus **persis** sama dengan yang ada di Partner Center.
Kalau tidak sama, submission akan ditolak saat validasi identitas.

Buka `msix/AppxManifest.xml`:

```xml
<Identity
  Name="LumaWall.DesktopEngine"      <!-- ganti dengan "Nama aplikasi" yang direservasi -->
  Publisher="CN=LumaWall"            <!-- ganti dengan "Publisher CN" dari Partner Center -->
  Version="4.0.1.0"
  ProcessorArchitecture="x64" />
```

Cara mendapatkannya:

1. Buka <https://partner.microsoft.com/dashboard>
2. **Apps and offers → Apps → New product → MSIX or PWA app**
3. Reservasi nama **LumaWall** → salin nilai **Package/Identity/Name**
4. **Product management → Product identity** → salin nilai **Package/Identity/Publisher** (format `CN=...`)

Setelah diganti, jalankan ulang:

```powershell
cd "C:\Users\ariel\Documents\Codex\2026-09-20\bik\work"
python make_store_assets.py      # regenerate aset (opsional)
powershell -File build_msix.ps1  # build ulang paket
```

---

## 3. Checklist persyaratan Store (sudah dipenuhi)

| Persyaratan | Status | Bukti |
|---|---|---|
| Identity Name & Publisher | ⚠️ perlu diisi dari Partner Center | `AppxManifest.xml` |
| Version format 4 angka | ✅ | `4.0.1.0` |
| ProcessorArchitecture x64 | ✅ | `x64` |
| TargetDeviceFamily Windows.Desktop | ✅ | MinVersion `10.0.17763.0` |
| StoreLogo 50×50 | ✅ | tervalidasi |
| Square44x44Logo 44×44 | ✅ | tervalidasi |
| Square150x150Logo 150×150 | ✅ | tervalidasi |
| Wide310x150Logo 310×150 | ✅ | tervalidasi |
| SplashScreen 620×300 | ✅ | tervalidasi |
| BadgeLogo 24×24 (monokrom) | ✅ | tervalidasi |
| Skala 125/150/200/400% | ✅ | 98 file aset |
| `runFullTrust` (reparent WorkerW + FFmpeg) | ✅ | capability dideklarasikan |
| Bahasa: id, en, zh, ja | ✅ | 4 `<Resource Language>` |
| Deskripsi & DisplayName | ✅ | manifest Properties |
| Startup task (ganti HKCU Run) | ✅ | `windows.startupTask` |
| Umur rating / kategori | ⚠️ isi kuesioner di Partner Center | — |
| Privacy policy URL | ⚠️ wajib kalau mengumpulkan data | lihat §5 |

---

## 4. Langkah submit

1. **Partner Center → Apps → New product → MSIX or PWA app**
2. Reservasi nama **LumaWall**, salin Identity (lihat §2)
3. Update `AppxManifest.xml`, jalankan `build_msix.ps1`
4. **Packages** → upload `LumaWall_4.0.0.0_x64.msix`
5. **Store listing** → unggah `store-art/*` dan isi:
   - Deskripsi singkat (≤ 100 karakter):
     > Live wallpaper engine: video & image wallpapers on every monitor, GPU-accelerated.
   - Deskripsi lengkap (≤ 10.000 karakter) — draf di §6
   - Kata kunci: `wallpaper`, `live wallpaper`, `video wallpaper`, `multi monitor`, `desktop`
6. **Age ratings** → isi kuesioner IARC
   - Catatan: katalog punya kategori **Mature 18+**. Pilih jawaban jujur
     "konten sugestif" supaya rating keluar benar (kemungkinan **PEGI 12 / ESRB T**),
     atau sembunyikan kategori itu lewat konfigurasi katalog untuk rating lebih rendah.
7. **Properties** → kategori `Personalization`, lalu **Submit**

---

## 5. Privacy policy (template)

Store mewajibkan URL privacy policy kalau aplikasi mengakses internet
(LumaWall mengunduh dari feed katalog dan memakai thumbnail online).

```
LumaWall Privacy Policy

LumaWall berjalan sepenuhnya di perangkat Anda.

Data yang dikumpulkan: tidak ada.
  - Tidak ada akun, tidak ada telemetri, tidak ada analitik.
  - Wallpaper yang Anda pilih disimpan lokal di
    %LOCALAPPDATA%\LumaWall\config.json.

Koneksi jaringan:
  - Hanya terjadi saat Anda menekan "Unduh" pada katalog, atau saat feed
    katalog dikonfigurasi. Permintaan langsung ke URL penyedia wallpaper
    yang Anda pilih. Tidak ada data yang dikirim ke pengembang.

Konten pihak ketiga:
  - Wallpaper diunduh dari penyedia asal; hak dan lisensi mengikuti sumber
    masing-masing, tercatat pada file .license.txt di samping setiap unduhan.

Kontak: <email-anda>
```

Simpan sebagai halaman publik (GitHub Pages / situs sendiri) lalu tempel URL-nya
di Partner Center.

---

## 6. Draf deskripsi Store (Indonesia)

**LumaWall — wallpaper hidup untuk semua monitor.**

LumaWall menghidupkan desktop Anda dengan video dan gambar, di setiap monitor,
tanpa membebani CPU.

**Dibuat untuk ringan**
Video didekode di GPU (hardware decode), jadi CPU tetap rendah. Pilih batas
15, 24, atau 30 FPS sesuai kebutuhan.

**Semua monitor, satu klik**
Tetapkan wallpaper berbeda untuk tiap layar, atau terapkan ke semua monitor
sekaligus. Simpan susunan favorit sebagai profil dan pulihkan dengan satu klik.

**Koleksi + katalog**
Tambahkan video dan gambar pribadi Anda, atau jelajahi katalog bawaan dengan
ribuan pilihan. Setiap unduhan menyimpan file lisensi berisi kreator dan sumber.

**Otomatis hemat daya**
Wallpaper berhenti sendiri saat aplikasi lain fullscreen, saat laptop memakai
baterai, atau saat Anda memintanya. Tidak ada gangguan saat bermain game.

**Fitur**
- Video dan gambar sebagai wallpaper desktop
- Multi-monitor: wallpaper berbeda per layar
- Profil multi-monitor yang bisa disimpan
- Batas FPS 15 / 24 / 30
- Pause otomatis (fullscreen, maximized, baterai)
- Optimalkan video ke FPS pilihan (butuh FFmpeg)
- Antarmuka 4 bahasa: Indonesia, English, 简体中文, 日本語
- Wallpaper tetap berjalan saat jendela ditutup ke system tray
- Jalankan otomatis saat masuk Windows

**Catatan**: LumaWall menempatkan wallpaper di lapisan desktop Windows
(WorkerW), jadi ikon desktop dan aplikasi Anda tetap berada di atasnya.
Ini bukan overlay topmost.

---

## 7. Cara rebuild semuanya dari nol

```powershell
cd "C:\Users\ariel\Documents\Codex\2026-09-20\bik\work"

# 1. aset logo MS Store + Store art + app.ico
python make_store_assets.py

# 2. compile aplikasi
& "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe" `
  LumaWall\LumaWall.csproj /p:Configuration=Release `
  /p:FrameworkPathOverride="C:\Windows\Microsoft.NET\Framework64\v4.0.30319" /v:minimal /nologo

# 3. installer klasik
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\LumaWall.iss

# 4. paket MS Store
powershell -File build_msix.ps1

# 5. validasi (opsional, sama seperti yang dipakai Store)
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" `
  test -appxpackagepath outputs\LumaWall_4.0.0.0_x64.msix `
  -reportoutputpath appcert-report.xml
```

---

## 8. Catatan penting untuk MSIX

- **Autostart**: di dalam MSIX, kunci `HKCU\...\Run` di-virtualisasi sehingga
  tidak berpengaruh. Manifest sudah mendeklarasikan `windows.startupTask`.
  Aplikasi tetap boleh menulis kunci Run (untuk build installer klasik),
  tapi di MSIX pakai **Task Manager → Startup** untuk mengaktifkannya.
- **FFmpeg**: fitur "Optimalkan" membutuhkan `ffmpeg.exe`. Untuk Store, taruh
  `ffmpeg.exe` di folder paket kalau ingin fitur ini jalan tanpa instalasi
  tambahan (perhatikan lisensi FFmpeg: build LGPL/GPL harus disertakan
  lisensinya di paket).
- **Unduhan wallpaper** disimpan di `%LOCALAPPDATA%\LumaWall` (di luar paket),
  jadi tidak kena masalah virtualisasi dan tetap ada saat aplikasi di-update.
- **WebView2 Runtime**: sudah tersedia di Windows 10/11 modern. Kalau ingin
  aman untuk perangkat lama, tambahkan `Microsoft.WebView2` sebagai
  framework dependency, atau biarkan aplikasi menampilkan pesan bila runtime
  tidak ditemukan.
