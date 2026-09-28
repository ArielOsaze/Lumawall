# LumaWall — Microsoft Store submission

Status: **siap submit**, kecuali dua nilai yang hanya bisa diambil dari Partner Center
(lihat §2). Paketnya sudah lolos validasi lokal.

Versi: **4.5.6.0**. Diperbarui: 28 September 2026.

---

## 1. Artefak

| Berkas | Ukuran | Dipakai untuk |
|---|---|---|
| `outputs/LumaWall_4.5.6.0_x64.msix` | 15.76 MB | **Yang diunggah ke Partner Center** |
| `site/assets/downloads/LumaWall-Setup-4.5.6.0.exe` | 15.6 MB | Installer klasik (situs sendiri) |
| `site/assets/downloads/LumaWall-portable-4.5.6.0.zip` | 14.3 MB | Versi portable |
| `store-art/BoxArt_1080x1080.png` | 1080×1080 | Box art (wajib) |
| `store-art/PosterArt_720x1080.png` | 720×1080 | Poster art |
| `store-art/HeroArt_1920x1080.png` | 1920×1080 | Hero art |
| `store-art/StoreListing_300x300.png` | 300×300 | Store listing icon |

Identitas paket (dari `msix/AppxManifest.xml`):

```
Name        XinetGroup.LumaWall
Publisher   CN=82AE483E-A9EB-487B-BDE6-4D690C249608
Version     4.5.6.0
Arch        x64
```

---

## 2. Dua nilai yang WAJIB diambil dari Partner Center

Paket akan ditolak saat validasi identitas kalau dua nilai ini tidak persis sama dengan
yang ada di akun Partner Center.

1. Buka <https://partner.microsoft.com/dashboard>
2. **Apps and offers → Apps → New product → MSIX or PWA app**
3. Reservasi nama **LumaWall** → salin **Package/Identity/Name**
4. **Product management → Product identity** → salin **Package/Identity/Publisher**
   (formatnya `CN=...`)

Lalu edit `msix/AppxManifest.xml`:

```xml
<Identity
  Name="XinetGroup.LumaWall"
  Publisher="CN=82AE483E-A9EB-487B-BDE6-4D690C249608"
  Version="4.5.6.0"
  ProcessorArchitecture="x64" />
```

Build ulang:

```bash
python tools/build_msix.ps1        # atau: python tools/release.py 4.4.10.0
python tools/check-store-package.py
```

Checker akan mengingatkan selama `Publisher` masih `CN=LumaWall`.

---

## 3. Yang sudah diverifikasi

`python tools/check-store-package.py` memeriksa aturan yang benar-benar menolak submission:

| Pemeriksaan | Hasil |
|---|---|
| Identity Name legal | ✅ `XinetGroup.LumaWall` |
| Publisher cocok Partner Center | ✅ `CN=82AE483E-...` |
| Version empat angka, cocok dengan nama berkas | ✅ `4.5.6.0` |
| Setiap aset yang dirujuk manifest ada di paket | ✅ 8/8 |
| Setiap aset berukuran sesuai namanya | ✅ `Square310x310Logo` benar 310×310 |
| StoreLogo ada (wajib) | ✅ 50×50 |
| `runFullTrust` dideklarasikan | ✅ |
| `internetClient` dideklarasikan | ✅ |
| WebView2 sebagai external dependency | ✅ |
| Tidak ada berkas yang ditolak Store | ✅ 0 |
| Ukuran paket wajar | ✅ 15.76 MB |

**Dua bug nyata yang ditemukan dan diperbaiki di sini:**

1. `Square310x310Logo.png` **tidak ada sama sekali**, dan manifest menunjuk berkas 150×150
   untuk slot 310×310. `Square71x71Logo` menunjuk berkas 44×44. Store menolak ukuran yang
   tidak sesuai nama. Diperbaiki: `tools/make-tile-assets.py` membuat kedelapan aset dari
   satu sumber, semua ukuran + varian skala 125/150/200/400%.
2. Validator di `tools/build_msix.ps1` memakai **daftar nama hardcoded** yang tidak memuat
   `Square71x71Logo` dan `Square310x310Logo` — itulah sebabnya bug di atas bisa lolos.
   Sekarang ukuran dibaca dari manifest itu sendiri, jadi aset baru otomatis ikut divalidasi.

Validasi tambahan yang bisa dijalankan kapan saja:

```bash
python tools/check-store-package.py     # tidak butuh admin
python tools/verify-all.py              # 42 checker untuk app + situs
```

### App Certification Kit (gate terakhir)

`appcert.exe` adalah alat resmi Microsoft dan **butuh shell Administrator** — dijalankan
tanpa elevasi ia gagal dengan "The requested operation requires elevation". Jalankan sendiri
dari PowerShell sebagai Administrator:

```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" `
  -appx "C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\outputs\LumaWall_4.5.6.0_x64.msix" `
  -reportoutputpath "C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\build\appcert.xml"
```

Partner Center menjalankan pemeriksaan yang sama saat submission, jadi kegagalan di sini
akan muncul sebagai penolakan di sana.

---

## 4. Aset halaman Store

Sudah disiapkan, tinggal diunggah:

| Slot Partner Center | Berkas | Ukuran |
|---|---|---|
| Box art (wajib) | `store-art/BoxArt_1080x1080.png` | 1080×1080 |
| Poster art | `store-art/PosterArt_720x1080.png` | 720×1080 |
| Hero art | `store-art/HeroArt_1920x1080.png` | 1920×1080 |
| Store listing icon | `store-art/StoreListing_300x300.png` | 300×300 |

Semua memakai logo "L" yang sama dengan situs, ikon aplikasi, dan tile Start menu.

---

## 5. Langkah submit

1. **Partner Center → Apps → New product → MSIX or PWA app**
2. Reservasi nama **LumaWall**, salin Identity (§2), perbarui manifest, build ulang
3. **Packages** → unggah `outputs/LumaWall_4.5.6.0_x64.msix`
4. **Store listing** → isi:
   - **Deskripsi singkat** (≤100 karakter):
     > Wallpaper hidup untuk setiap monitor. Video didekode GPU, CPU tetap rendah.
   - **Deskripsi lengkap** — draf di §7
   - **Kata kunci**: `wallpaper`, `live wallpaper`, `video wallpaper`, `multi monitor`, `desktop`
   - **Kategori**: Personalization
5. **Age ratings** → kuesioner IARC. Katalog memuat kategori **Mature 18+**, jadi jawab
   jujur "konten sugestif". Rating yang keluar kemungkinan PEGI 12 / ESRB T. Kalau kamu mau
   rating lebih rendah, sembunyikan kategori itu dari katalog sebelum submit.
6. **Properties** → kategori `Personalization`, lalu **Submit**

### URL privacy policy (wajib karena app mengakses internet)

```
https://lumawall.xinet.id/privacy/       (Indonesia)
https://lumawall.xinet.id/en/privacy/    (English)
```

Halaman ini sudah ada, sudah ditautkan di footer kedua versi situs, dan sudah masuk
`sitemap.xml`.

### Notes for certification (kolom ini wajib diisi, jangan dikosongkan)

Peninjau Microsoft menjalankan app-nya selama beberapa menit dan menilai dari apa yang
mereka lihat. LumaWall sengaja tidak menampilkan jendela saat start — desktop itu sendiri
produknya — dan tanpa penjelasan itu terlihat seperti app yang gagal jalan. Salin ini apa
adanya:

> LumaWall is a live wallpaper engine. On first launch it starts minimised to the system
> tray and begins rendering the selected wallpaper behind the desktop icons — the desktop
> itself is the product, so an empty-looking window is not a fault. Open it from the tray
> icon to see the interface.
>
> Two capabilities are used and both are necessary:
>
> * `runFullTrust` — the app reparents a window into Explorer's desktop layer (WorkerW) so
>   the wallpaper sits behind the icons and behind every application, exactly like the
>   built-in slideshow. It also starts a local FFmpeg process to decode video wallpapers.
> * `internetClient` — the wallpaper catalogue is browsed online, and the app checks for
>   updates.
>
> The catalogue contains no user-generated content. The mature category is a curated
> subset that is off by default and requires the user to switch it on in Luma Studio.
>
> To see it working: launch it, open LumaWall from the tray, and pick any wallpaper. The
> desktop changes immediately. Uninstalling restores the previous desktop wallpaper.

---

## 6. Catatan penting untuk MSIX

- **Autostart.** Di dalam MSIX, kunci `HKCU\...\Run` di-virtualisasi sehingga tidak
  berpengaruh. Manifest sudah mendeklarasikan `windows.startupTask`; pengguna
  mengaktifkannya lewat **Task Manager → Startup**.
- **Unduhan wallpaper** disimpan di `%LOCALAPPDATA%\LumaWall` (di luar paket), jadi tidak
  terkena virtualisasi dan tetap ada saat aplikasi diperbarui.
- **WebView2 Runtime** sudah tersedia di Windows 10/11 modern. Deklarasi
  `win32dependencies:ExternalDependency` membuat App Installer memasangnya otomatis kalau
  belum ada; `Optional="true"` menjaga instalasi offline tetap jalan (aplikasi menampilkan
  pesan yang jelas alih-alih gagal start).
- **FFmpeg** tidak dibundel. Fitur "Optimalkan" memerlukan `ffmpeg.exe` yang dipasang
  terpisah; tanpa itu fitur tersebut menampilkan pesan, dan sisa aplikasi tetap berfungsi.

---

## 7. Draf deskripsi Store

**LumaWall — wallpaper hidup untuk setiap monitor.**

LumaWall menghidupkan desktop dengan video dan gambar, di setiap monitor, tanpa membebani
CPU.

**Dibuat untuk ringan**
Video didekode di chip grafis, bukan CPU. Pilih batas 15, 24, atau 30 FPS sesuai kebutuhan.

**Semua monitor, satu klik**
Tetapkan wallpaper berbeda untuk tiap layar, atau terapkan ke semua monitor sekaligus.
Simpan susunan favorit sebagai profil dan pulihkan dengan satu klik.

**22.000+ wallpaper**
Jelajahi katalog bawaan yang seluruhnya dinamis dan HD, dengan 16 kategori. Atau tambahkan
video dan gambar pribadimu. Setiap unduhan menyimpan berkas lisensi berisi kreator dan
sumbernya.

**Widget jam di desktop**
Jam digital bergaya lock screen iOS, dengan sepuluh gaya, tanggal, dan format 12/24 jam.
Duduk di lapisan desktop yang sama dengan wallpaper, jadi tidak pernah menutupi aplikasi
yang sedang kamu buka. Di meja dengan beberapa monitor, jamnya bisa ditaruh di layar mana
saja — sama seperti wallpaper-nya.

**Otomatis hemat daya**
Wallpaper berhenti sendiri saat aplikasi lain fullscreen, saat laptop memakai baterai, atau
saat kamu memintanya. Tidak ada gangguan saat bermain game.

**Fitur**
- Video dan gambar sebagai wallpaper desktop
- Multi-monitor: wallpaper berbeda per layar
- Profil multi-monitor yang bisa disimpan
- Batas FPS 15 / 24 / 30
- Pause otomatis (fullscreen, maximized, baterai)
- Widget jam: 10 gaya, tanggal, format 12/24 jam, posisi bebas, pilih layar
- Optimalkan video ke FPS pilihan (butuh FFmpeg)
- Antarmuka 4 bahasa: Indonesia, English, 简体中文, 日本語
- Wallpaper tetap berjalan saat jendela ditutup ke system tray
- Jalankan otomatis saat masuk Windows
- Semua kontrol bisa dioperasikan pembaca layar (UI Automation)

**Catatan**: LumaWall menempatkan wallpaper di lapisan desktop Windows (WorkerW), jadi ikon
desktop dan aplikasi kamu tetap berada di atasnya. Ini bukan overlay topmost.

---

## 8. Rebuild semuanya

```bash
python tools/make-tile-assets.py    # 8 aset tile × 5 skala, dari satu sumber
python tools/release.py 4.4.10.0    # app, installer, portable, msix, situs, deploy
python tools/check-store-package.py # validasi paket Store
python tools/verify-all.py          # 42 checker
```
