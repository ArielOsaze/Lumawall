# Checklist keberhasilan — LumaWall

Setiap baris punya angka yang diukur, bukan klaim. Perintah di kolom kanan bisa dijalankan
ulang kapan saja; kalau checker-nya tidak bisa gagal, ia tidak dipakai.

Terakhir diperbarui: rilis 4.5.5.0.

---

## Fitur yang diminta

| # | Fitur | Status | Angka terukur | Perintah |
|---|---|---|---|---|
| 1 | Widget timer **tidak boleh menimpa aplikasi** | ✅ | timer Z-index 28/30, `WS_EX_TOPMOST: False`; Paint di Z 3 | `tools/check-timer-zorder.ps1` |
| 2 | Timer **kadang tidak muncul** | ✅ diperbaiki | Rect setinggi font → GDI+ gambar **0 piksel**; +4px → **1986 piksel**. Semua 10 gaya sekarang menggambar | `tools/check-timer-styles.py` |
| 3 | Timer **bergaya iOS lock screen**, beberapa pilihan | ✅ | 10 gaya, masing-masing dengan muka font berbeda. Tebal goresan (mean run / tinggi jam): **ioslarge 11.6%** (paling tipis), ioslight 16.7%, iosdate 18.4%, minimal 23.7% | `tools/check-timer-styles.py` |
| 3b | **Font tiap gaya beda** | ✅ diperbaiki | Sebelumnya `iosdate` menggambar dengan font **sama persis** dengan `minimal`. Sekarang tiap gaya menyebut mukanya sendiri dan checker memverifikasi muka yang benar-benar dipakai | `tools/check-timer-styles.py` |
| 4 | Timer **background transparan** | ✅ | wallpaper tembus **69–99%** per gaya | `tools/check-timer-styles.py` |
| 5 | **Placement tidak bikin bingung** | ✅ diperbaiki | Tanda jam terukur di **0.17/0.17**, **0.84/0.84**, **0.50/0.50** sesuai posisi | `tools/check-placement-mark.py` |
| 6 | Pilih placement **tidak scroll ke atas** | ✅ | Offset dipulihkan; pad persegi 126x126, drift label **0.0px** | `tools/test-studio-scroll.ps1` |
| 7 | **Cold start tidak ngelag** | ✅ diperbaiki | Parse katalog 273 ms **di luar UI thread**; jendela dibangun **0.20–0.34s**; wallpaper pertama **1.27s** (limit 4.0s) | `tools/check-startup.py` |
| 8 | **Update apa pun otomatis update installer di web** | ✅ | `python tools/release.py <versi>` — 11 langkah, berhenti kalau ada yang gagal | `tools/release.py` |
| 9 | **Tile hitam di katalog** | ✅ diperbaiki | **22.879** entri, **0** tanpa `thumbnailUrl` | `tools/check-catalog.py` |
| 10 | **Favicon logo lama** | ✅ | `/favicon.ico` HTTP 200, ICO 3 ukuran, tinta = logo L | `curl -D - https://lumawall.xinet.id/favicon.ico` |
| 11 | **Scrollbar gelap** | ✅ | Isi 11785px dalam 700px → bar 10px, kecerahan app **8** | `tools/check-scrollbar-site.mjs` |
| 12 | **Katalog besar, kategori benar** | ✅ | **22.879** entri · 100% dinamis · 100% HD · 58.8% 2K/4K · 0 duplikat · 0 AI · 16 kategori · mature 249 | `tools/check-catalog.py` |
| 13 | **Dua bahasa (ID/EN)** | ✅ | Kedua halaman ada, `hreflang` **per halaman**; semua kunci terjemahan lengkap 4 bahasa | `tools/check-seo.py`, `tools/check-translations.py` |
| 14 | **Primary display ikut beranimasi** | ✅ diperbaiki | Nama berkas dengan huruf Сirilik tersimpan sebagai `Ð¡` → `File.Exists` false → monitor **dilewati tanpa pesan**. Sekarang path dipulihkan: **2 renderer → 3 renderer** | `tools/check-wallpaper-alive.ps1` |
| 15 | **Timer bisa pindah layar** | ✅ baru | Dulu `Place()` membaca `Screen.PrimaryScreen` tanpa syarat. Sekarang ada pemilih layar; checker mengklik chip dan membaca persegi jendela widget: pindah ke DISPLAY3, **bertahan lintas repaint**, kembali ke DISPLAY1 | `tools/check-timer-display.py` |
| 16 | **Switch bisa dioperasikan screen reader** | ✅ diperbaiki | Dulu app mengekspos **0 CheckBox** (switch adalah `Border` + handler klik). Sekarang **4 CheckBox** dengan `TogglePattern` dan nama | `tools/ui_buttons.py --kind CheckBox` |
| 17 | **Pengujian tidak mengganggu layar utama** | ✅ baru | Semua checker berbasis jendela pindah ke monitor non-primary terkecil (DISPLAY3 1366x768); posisi dan ukuran dipulihkan di `finally` | `python tools/test_screen.py` |
| 18 | **Paket MS Store** | ✅ | `outputs/LumaWall_4.5.5.0_x64.msix`; BadgeLogo = glyph putih di transparansi (22% opaque), bukan kotak putih | `tools/check-store-package.py` |

---

## Optimisasi

| # | Optimisasi | Sebelum | Sesudah | Perintah |
|---|---|---|---|---|
| 1 | **CPU idle** | 7.3% | **2.6%** (limit 3.0%) | `tools/check-idle-cpu.py` |
| 2 | Pemindaian jendela | 2× `EnumWindows` penuh tiap 2s | **1 lintasan** per tick, filter murah dulu, nama kelas di-cache | — |
| 3 | Spam log | 309 baris / 10 menit | **0 baris** saat idle | `tools/check-idle-cpu.py` |
| 4 | **Cold start** | parse 288 ms memblokir UI thread | worker thread, **paralel** dengan pemulihan wallpaper | `tools/check-startup.py` |
| 5 | **RAM** | — | **215 MB** dengan 3 monitor aktif | `tools/check-idle-cpu.py` |
| 6 | GPU vs CPU | — | Wallpaper didekode WebView2 (GPU); proses UI **2.6%**, tiap WebView2 ~0.5% | `tools/check-idle-cpu.py` |
| 7 | **Boot proses dipisah dari kerja app** | 1.81s dilaporkan sebagai "langkah app" dan menuduh 0x052C | boot 0.21s hangat / 1.8s dingin (antivirus memindai exe baru) dilaporkan terpisah; kerja app **0.20–0.34s** | `tools/check-startup.py` |

---

## Zero bug

| # | Yang diperiksa | Status |
|---|---|---|
| 1 | Tidak ada flicker hitam saat ganti wallpaper | ✅ "Wallpaper swap committed without blank frame" |
| 2 | Tidak ada exception saat jalan | ✅ 0 exception |
| 3 | Timer tidak menimpa aplikasi | ✅ terbukti positif **dan** negatif |
| 4 | Semua gaya timer menggambar | ✅ 10/10, diuji sabotase (kotak solid & kosong dua-duanya FAIL) |
| 5 | Placement mencatat klik **dan** menggambar ulang | ✅ dua-duanya diperiksa terpisah |
| 6 | Installer di web = biner yang dibuild | ✅ sha256 cocok |
| 7 | Deploy tidak mematikan situs | ✅ `rootDirectory=site` utuh |
| 8 | Timer benar-benar pindah layar | ✅ dibaca dari persegi jendela widget, bukan dari klaim app |
| 9 | Hover tombol terlihat | ✅ 3/3 tombol, hover merah di close `(255, 46, 67)`, **tidak ada Aero blue** |
| 10 | Semua checker | ✅ `tools/verify-all.py` |

---

## Pelajaran yang menentukan (kenapa checker ini ada)

1. **`UniformGrid` mengabaikan `Grid.SetRow`/`Grid.SetColumn`.** Ia menempatkan anak
   berdasarkan urutan. Tanda jam adalah anak ke-10, jadi selalu mendarat di kiri-bawah dan
   **tidak pernah bisa dipindah**. Itulah "placement bikin bingung".

2. **Kondisi pemilih font yang tidak pernah bisa cocok.** Gaya iOS meminta muka tipis dengan
   `light.Name == family.Name || light.Name.StartsWith("Segoe UI Light")`. Entri pertama
   daftar adalah `"Segoe UI Variable Display Light"` — nama itu tidak sama dan tidak diawali
   `"Segoe UI Light"`, jadi kondisi itu **melewatinya** dan jatuh ke muka 57% lebih tebal.
   `iosdate` tidak ada di daftar sama sekali. Itulah "font timernya gada bedanya".

3. **Rect setinggi font membuat GDI+ menggambar nol piksel.** Tanpa exception, tanpa
   peringatan. Diukur: 0 piksel vs 1986 piksel.

4. **Berkas yang tidak ditemukan tidak boleh dilewati diam-diam.** Nama berisi huruf Сirilik
   tersimpan sebagai `Ð¡` (UTF-8 dibaca Latin-1). `File.Exists` bilang tidak ada, monitor
   **dilewati tanpa satu baris log pun**, desktop kosong. Itu keluhan "primary display ga
   jalan animasinya". Sekarang path dipulihkan dengan kedua arah salah-encoding dan
   kecocokan nyata terhadap isi folder.

5. **Checker yang tidak bisa gagal tidak berguna** — dan **checker yang bisa PASS palsu lebih
   buruk lagi.** `check-timer-styles.py` versi pertama mengukur wallpaper. `verify-hover.py`
   pernah PASS di atas jendela minimized 160x28: strip yang dibandingkan adalah desktop
   kosong, jadi setiap tombol "bereaksi".

6. **`Write-Output` di dalam delegate PowerShell tidak sampai ke pemanggil.** Callback
   `EnumWindows` berjalan di luar pipeline, jadi outputnya dibuang diam-diam. Checker
   melaporkan "the timer is on no monitor" padahal widgetnya ada di layar. Kumpulkan ke
   array, tulis setelah enumerasi.

7. **PowerShell 5.1 membaca `.ps1` tanpa BOM sebagai ANSI.** Literal CJK di dalam skrip
   datang sebagai mojibake dan seluruh skrip gagal parse ("Unexpected token"). Label CJK
   dibangun dari code point.

8. **`ShowWindow(SW_RESTORE)` tidak cukup untuk jendela ber-`WindowChrome`.** Jendela kembali
   dengan sentinel `-32000,-32000` / `160x28` (diukur berulang). `SetWindowPlacement` yang
   bekerja, dan sekaligus memperbaiki ukuran normal tersimpan — jendela minimized menyimpan
   sentinel di `rcNormalPosition`.

9. **Jangan mengubah ukuran jendela di tengah pengukuran.** `park()` menempatkan jendela,
   lalu `_measure` mengecilkannya lagi — UI Automation tetap melaporkan tombol dari lebar
   **lama**, dua tombol jadi di luar jendela. Ukur pada geometri yang sama.

10. **Offset tetap hanya benar untuk satu ukuran jendela.** Tombol title bar dibaca lewat UI
    Automation (`Minimize`, `Maximize`, `Close to tray`), bukan `right-110/66/22`.

11. **Boot proses bukan kerja app.** 1.8s pada start pertama setelah build adalah antivirus
    memindai exe baru; 0.21s saat hangat. Melaporkannya sebagai langkah app membuat checker
    gagal tepat setelah setiap rilis dengan alasan yang salah.

12. **Checker harus memulihkan keadaan pengguna.** Timer yang dinyalakan dikembalikan mati;
    jendela yang dipindah dikembalikan ke posisi dan ukuran semula; switch yang di-toggle
    dicocokkan lewat **label**, bukan "yang pertama mati" (itu menyalakan Tone mapping).

13. **Proses anak Chrome harus dibunuh sebagai pohon.** `chrome.kill()` hanya memberi sinyal
    ke peluncur; 61 proses yatim menumpuk sampai checker browser berikutnya gagal.
