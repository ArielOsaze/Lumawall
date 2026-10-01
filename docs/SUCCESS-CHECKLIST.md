# Checklist keberhasilan — LumaWall

Setiap baris punya angka yang diukur, bukan klaim. Perintah di kolom kanan bisa dijalankan
ulang kapan saja; kalau checker-nya tidak bisa gagal, ia tidak dipakai.

Terakhir diperbarui: rilis 4.5.7.0 + gerbang pembayaran web.

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
| 19 | **Wallpaper hitam setelah keluar dari app fullscreen** | ✅ diperbaiki (2 tahap) | Tahap 1: komposisi desktop - `ForceRepaint()` pada transisi resume. Tahap 2 (4.5.11.0): halaman yang mati saat fullscreen baru dibangun ulang setelah **40 detik** (`LivenessCheckSeconds=20` × `DeadPageStrikes=2`); sekarang liveness diperiksa tepat saat resume dan satu strike cukup → **3–29 ms**. Terukur dari log aplikasi, bukan dari piksel layar (piksel tidak bisa membedakan wallpaper yang dijeda dari wallpaper yang tertutup jendela lain) | `python tools/check-pause-resume.py` |
| 20 | **Installer di web ikut ter-update otomatis** | ✅ diperbaiki | Dulu installer disalin ke `site/assets/downloads/` — artinya berkasnya bisa diunduh siapa pun yang menebak alamatnya, **gratis, tanpa membayar**. Sekarang setiap rilis mengunggah installer ke bucket **privat**; server yang mengambilnya setelah token diverifikasi. URL lama dialihkan ke halaman beli | `python tools/release.py <versi>` (langkah 7) |
| 21 | **Pembayaran berhasil, tidak sekadar terpasang** | ✅ | Tautan bayar sungguhan dari iPaymu: `Status: 200 Success`. Lewat jembatan, **10/10 permintaan** berhasil; langsung ke iPaymu **15/15** | `python tools/test-live-checkout.py` |
| 22 | **Bayar tanpa pindah situs (snap)** | ✅ baru | QRIS tampil di halaman beli sendiri lewat `payment-direct`. QR asli **450×450** muncul di halaman pada **280×280 px**, sumbernya data URL. Tidak ada pengalihan ke iPaymu | `python tools/check-snap-qr-asli.py` |
| 23 | **Halaman memeriksa pembayaran sendiri** | ✅ baru | `/api/status-pembayaran` memeriksa database lalu iPaymu sebagai cadangan; jumlah diperiksa, bukan dipercaya. Kode pesanan tidak sah ditolak: `{"ok":false,"error":"Kode pesanan tidak sah."}` | `curl "https://lumawall.xinet.id/api/status-pembayaran/?order=HACK"` |
| 24 | **Promo Rp10.000 naik otomatis ke Rp18.000** | ✅ | 11 kasus diuji termasuk 15 Okt 23:59:59 (masih promo) dan 16 Okt 00:00:00 (sudah naik), serta dua kasus dalam UTC. Batasnya jam Jakarta, bukan UTC | `python tools/check-price-schedule.py` |
| 25 | **Harga tidak pernah bertentangan di halaman** | ✅ diperbaiki | Blok promo dan blok setelah-promo pernah tampil bersamaan (`[hidden]` kalah dari `display:flex`) sehingga halaman menyatakan dua harga sekaligus. Sekarang: promo 5/5 terlihat, setelah-promo 0/1 | `python tools/check-promo-display.py` |
| 26 | **Harga di web = harga yang ditagih** | ✅ | Halaman mengambil harga dari `/api/price`, jadi angka yang ditampilkan selalu sama dengan yang ditagih server. `Rp20.000` sudah **0 kemunculan** di seluruh situs | `curl https://lumawall.xinet.id/api/price/` |
| 27 | **Ganti bahasa tidak error** | ✅ diperbaiki | `/en/beli/` tidak pernah ada — tombol ID di `/en/buy/` dan `/en/success/` naik **satu** tingkat, seharusnya **dua** → 404. Tombol EN di `/sukses/` malah menuju halaman beli. Sekarang 6/6 tombol menuju halaman yang benar, **158 tautan diperiksa, 0 rusak** | `python tools/check-links.py` |
| 28 | **Tombol bahasa punya gaya** | ✅ diperbaiki | Tidak ada aturan `.lang` di berkas CSS mana pun: tautan EN/ID muncul sebagai teks biru bergaris bawah, terlihat seperti halaman yang belum selesai | `python tools/check-links.py` |
| 29 | **Pilihan cara bayar, bukan cuma QRIS** | ✅ baru | **9 kanal**: QRIS + Virtual Account BNI, BCA, BRI, Mandiri, Permata, CIMB, BSI, Danamon. Ditolak akun ini: Muamalat, Panin, Maybank, OCBC, Artha, Sampoerna | `python tools/uji-kanal.js` (di server) |
| 30 | **Biaya layanan terlihat sebelum memilih** | ✅ diperbaiki | QRIS Rp249 (2,5%), BCA Rp4.500 (45%), Mandiri Rp4.000, bank lain Rp3.500 — semuanya ditanggung pembeli. Dulu pembeli melihat Rp10.000 lalu diminta transfer Rp14.500. Sekarang biaya ada di tombol pemilih, dan total dipecah tiga baris | `python tools/check-kanal.py` |
| 31 | **Panel menampilkan nilai yang sama dengan server** | ✅ | QRIS: QR 450×450 sebagai data URL, total Rp10.249. BCA: nomor 16 digit, total Rp14.500. Dibandingkan nilai per nilai | `python tools/check-kanal.py` |
| 32 | **BRI dan Permata tidak lagi selalu gagal** | ✅ diperbaiki | Nomor placeholder `081200000000` ditolak BRI dan Permata ("Failed to generate VA") tetapi diterima bank lain — dan nomor WhatsApp opsional di formulir. Diuji 11 kandidat; `081211111111` diterima ketiganya. Sekarang **9/9 kanal berhasil** tanpa nomor WhatsApp | `python tools/uji-nomor.js` (di server) |

| 33 | **Wallpaper berhenti saat app fullscreen, lanjut seketika saat keluar** | ✅ diperbaiki | Dulu halaman wallpaper bisa mati saat fullscreen dan baru dibangun ulang setelah **40 detik** (`LivenessCheckSeconds=20` × `DeadPageStrikes=2`). Sekarang pemeriksaan liveness diminta **tepat saat resume** dan satu strike cukup. Terukur dari log aplikasi: jeda tercatat, **0 putaran video selesai selama jeda** (video yang dijeda tidak mungkin menyelesaikan putaran, jadi ini tidak bisa dipalsukan oleh frame beku), dan frame pertama **3–29 ms** setelah perintah lanjut | `python tools/check-pause-resume.py` |
| 34 | **Checker pause/resume bisa gagal** | ✅ baru | 15 kasus: `paused [DISPLAY1]` dengan DISPLAY2/DISPLAY3 hanya disebut di bagian depan harus **tidak** dianggap dijeda. Pencocokan yang mencari nama di seluruh baris pernah membuat uji lulus/gagal karena alasan yang tidak ada hubungannya dengan wallpaper | `python tools/check-pause-resume-bisa-gagal.py` |
| 35 | **Halaman Displays menampilkan keadaan sebenarnya** | ✅ diperbaiki | Dulu hanya tombol Apply/Stop tanpa keterangan. Sekarang tiap monitor menampilkan status (Active/Empty) dan ringkasan pengaturannya sendiri. Chip statusnya dulu **ada di pohon UI tetapi jatuh di luar kartu** (tinggi 262 px) - terlihat benar sampai diperiksa | `python tools/shoot-displays.py` |
| 36 | **Pemeriksaan tidak menutup jendela pengguna** | ✅ diperbaiki | Semua checker kini **meminimalkan** jendela yang menghalangi lalu memulihkannya. Hanya Chrome yang diluncurkan checker sendiri yang ditutup, dan dikenali dari **profil**-nya, bukan dari judul jendela | `tools/chrome_uji.py` |

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
| 11 | Jam gaya iOS **solid**, bukan berongga | ✅ kepadatan piksel huruf 10-17% (huruf berongga 3-6%). Bayangan halo delapan arah diganti bayangan rapat untuk semua gaya tipis | `LumaWall.exe --render-timer` + hitung kepadatan |
| 12 | Jam gaya iOS **memakai Inter**, bukan Segoe | ✅ render melaporkan `ioslarge -> Inter ExtraLight`, `ioslight -> Inter Light`, `iosdate -> Inter Medium` | `LumaWall.exe --render-timer` |
| 13 | Jam gaya iOS **tidak menampilkan detik** | ✅ `ShowSeconds` diabaikan untuk ioslarge/ioslight/iosstack/iosdate | baca `Format()` di `DesktopTimer.cs` |
| 14 | Sakelar Studio **bisa dibaca alat bantu** | ✅ 6/6 sakelar ditemukan, `toggle=True`, ukuran 42×23. Sebelumnya 0 ditemukan karena jendela bernama "Hidden Window" | `python tools/periksa-toggle.py` |
| 15 | Tata letak **rapi di semua lebar** | ✅ 0 masalah pada 6 halaman × 3 lebar (920/1200/1580 px). Sebelumnya 269 masalah | `LumaWall.exe --periksa-ui <folder>` |
| 16 | Sakelar **tidak membangun ulang halaman** | ✅ hanya sakelar yang mengubah susunan (jam on/off) yang memicu muat ulang | baca `StudioToggle` di `FeaturesPage.cs` |
| 17 | Installer terpasang = versi yang dibuild | ✅ 4.5.13.0 terpasang, situs juga menyajikan 4.5.13.0 | `python tools/release.py --verify-only` |
| 18 | Jalankan/pause saat fullscreen | ✅ jeda terdeteksi, tidak ada putaran selesai selama jeda, frame pertama setelah 25 ms, video benar berjalan (putaran selesai 11.4 s) | `python tools/check-pause-resume.py` |
| 19 | Jam memakai **Inter Display**, bukan Inter teks | ✅ `ioslarge/ioslight/iosstack/iosdate -> Inter Display Light`. Inter Display dirancang untuk ukuran besar, seperti SF Pro Display milik Apple | `LumaWall.exe --render-timer` |
| 20 | Tanggal di **atas** jam, untuk semua gaya iOS | ✅ susunan yang Apple pakai; sebelumnya tiga gaya menaruhnya di bawah | `LumaWall.exe --render-timer` + lihat gambar |
| 21 | Jam dan tanggal **satu keluarga font** | ✅ jam Inter Display Light, tanggal Inter Light - sebelumnya tanggal memakai Segoe | `LumaWall.exe --render-timer` |
| 22 | Pemilih gaya menggambar susunan yang sebenarnya | ✅ keempat gaya iOS menggambar tanggal kecil di atas jam besar | buka Luma Studio → Jam desktop |
| 23 | Halaman Monitor tidak menampilkan nama perangkat internal | ✅ `\\.\DISPLAY2 · LOOP` diganti jenis wallpaper + ukuran berkas | buka halaman Monitor |
| 24 | Katalog: kategori mature **sesuai**, tidak nyasar | ✅ 82 entri dipindahkan ke Mature, 25 entri tidak layak dikeluarkan | `python tools/check-catalog.py` |
| 25 | Katalog: tidak ada entri tanpa berkas video | ✅ 2.305 entri tanpa `videoUrl` dibuang - tidak bisa dipasang sama sekali | `python tools/check-catalog.py` |
| 26 | Katalog: 25.560 entri, semua HD, 0 duplikat, 0 AI | ✅ 100% dinamis, 100% resolusi terukur, 56,8% 2K+ | `python tools/check-catalog.py` |

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

14. **Jendela yang ter-occlude tidak otomatis digambar ulang.** Selama aplikasi fullscreen
    berjalan, Windows berhenti mengomposisi desktop sama sekali. Saat aplikasi ditutup, DWM
    meminta jendela desktop menggambar ulang — dan permintaan itulah yang tidak pernah
    dijawab. Penyebabnya satu flag: `--disable-features=CalculateNativeWinOcclusion` membuat
    Chromium tidak melacak occlusion, jadi ia tidak melihat ada transisi untuk ditanggapi.
    Flag itu sendiri benar (ia mencegah Chromium membatasi wallpaper yang dikiranya
    tersembunyi), jadi perbaikannya bukan menghapus flag, melainkan memaksa repaint sendiri
    pada transisi resume: `RedrawWindow` + satu nudge di sisi halaman. Dijalankan **dua kali**
    (segera + 450 ms) karena percobaan pertama bisa mendarat saat DWM masih berpindah mode.

15. **Berkas yang bisa diunduh publik membatalkan gerbang pembayaran.** Installer pernah
    di-commit ke `site/assets/downloads/` supaya tidak 404. Itu memperbaiki satu masalah dan
    menciptakan yang lebih besar: `curl` ke alamat itu mengembalikan **206** — siapa pun bisa
    mengunduh tanpa membayar, dan seluruh sistem token jadi hiasan. Aturan yang berlaku:
    berkas berbayar tidak boleh berada di folder yang disajikan publik, sebagus apa pun
    sistem token di atasnya.

16. **Uji yang tidak bisa gagal lebih buruk daripada tidak ada uji.** Versi pertama
    `check-fullscreen-recovery.py` melaporkan "LULUS 0,5 detik" sementara kecerahan layar
    tidak berubah sama sekali (48,4 → 48,4) — jendela ujinya tidak pernah menutupi layar,
    jadi tidak ada yang diuji. Sekarang uji itu **memeriksa dulu bahwa keadaannya benar**
    (kecerahan harus turun ke ~0 saat fullscreen) dan menyatakan **TIDAK VALID**, bukan lulus,
    kalau tidak. Uji yang sama juga membaca log untuk memastikan jalur resume benar-benar
    terpicu, karena "layar terlihat benar" bisa saja berarti wallpaper tidak pernah dijeda.

17. **iPaymu menandatangani HASH body, bukan body mentah.** Tanda tangan
    `HMAC_SHA256(method:va:body:key)` dengan body apa adanya ditolak (`unauthorized
    signature`); bentuk yang diterima adalah `HMAC_SHA256(method:va:sha256(body):key)`.
    Bedanya satu langkah hash, dan gejalanya hanya "401 unauthorized" tanpa petunjuk.

18. **Kredensial sandbox tidak berlaku di endpoint produksi.** Kunci di `.env` NexShop
    bertanda `sandbox` dan ditolak di `my.ipaymu.com`; kunci produksi di proyek lain diterima
    (`Status: 200`). Menyalin kunci antar lingkungan adalah kesalahan yang tampak seperti
    "kunci sudah kedaluwarsa".

19. **Skrip konversi harus dikelompokkan per berkas tujuan.** Versi pertama
    `make_en_pages.py` menerapkan **semua** pasangan frasa ke **setiap** berkas, lalu
    melaporkan 182 "frasa tidak ditemukan" — padahal sebagian besar frasa itu memang milik
    halaman lain. Laporan yang penuh kebisingan membuat masalah yang sungguhan tidak
    terlihat.

20. **iPaymu membatasi DUA hal, bukan satu: alamat IP dan domain.** "Invalid IP" adalah
    masalah pertama, dan setelah itu diperbaiki muncul "Invalid domain" — `returnUrl`
    harus memakai domain yang terdaftar di akun, dan untuk akun ini hanya **satu** domain
    yang diterima. Diuji satu per satu: `lumawall.xinet.id`, `xinet.id`,
    `akuntuntas.xinet.id`, dan versi `www` semuanya ditolak; hanya `nexshop.cloud` diterima.
    Itulah jawaban dari "kenapa proyek lain bisa langsung tanpa whitelist" — domain mereka
    memang sudah terdaftar di akun masing-masing.

21. **iPaymu menolak nomor telepon kosong dengan pesan yang menyesatkan.** Pesannya
    `unauthorized signature`, yang menunjuk ke tanda tangan — padahal tanda tangannya benar.
    Dibuktikan dengan uji berulang: lima permintaan dengan nomor telepon berhasil semua,
    lima tanpa nomor gagal semua. Pesan yang menunjuk ke tempat yang salah membuat
    penyebabnya sulit ditemukan; satu-satunya cara adalah menguji variabelnya satu per satu.

22. **`QrImage` dari iPaymu bukan berkas gambar.** Alamat itu mengembalikan halaman **HTML**
    dengan PNG tertanam sebagai data URL. Memasangnya ke `src` sebuah `<img>` menghasilkan
    gambar yang **tidak pernah muncul**, tanpa satu pun pesan kesalahan di halaman. Karena
    itu isinya harus diambil dan data URL-nya yang dipakai — dan pengambilannya harus di
    server, karena permintaan dari peramban ke domain iPaymu ditolak aturan lintas-asal.

23. **Batas waktu yang terlalu pendek mengubah keberhasilan menjadi kegagalan.** iPaymu
    terukur 4,4 detik untuk permintaan normal dan pernah melewati 20 detik. Satu pesanan
    tercatat gagal karena itu, padahal transaksinya mungkin sedang diproses — dan pembeli
    yang mencoba lagi menghasilkan **dua transaksi untuk satu pembelian**.

24. **Teks yang "terpotong" di tangkapan layar sering artefak Chrome, bukan bug halaman.**
    `--window-size` punya lebar minimum sekitar 500px, jadi tangkapan "390px" sebenarnya
    mewakili lebar desktop. Diukur dengan iframe yang lebarnya bisa disetel bebas: viewport
    320/360/390/414/768/1200 semuanya sama dengan lebar dokumen — tidak ada yang meluber.
    Sebelum memperbaiki tampilan karena tangkapan layar, ukur dulu angkanya.

25. **Halaman yang tidak didaftarkan di `cache-bust.py` akan tertinggal menunjuk berkas
    yang sudah diganti nama.** Halaman privasi memuat CSS yang sama dengan halaman lain
    tetapi tidak ada di daftar `PAGES`, jadi tautannya rusak setiap kali cache-bust
    dijalankan — dan baru terlihat kalau diperiksa terpisah. Checker tautan menangkapnya
    seketika; sebelumnya tidak ada yang memeriksanya.

26. **Biaya pembayaran berbeda jauh antar kanal, dan itu harus terlihat sebelum
    memilih.** QRIS Rp249 (2,5% dari harga) versus transfer BCA Rp4.500 (45%). Semuanya
    ditanggung pembeli. Membiarkan biaya baru muncul setelah memilih berarti pembeli
    melihat Rp10.000 di formulir lalu diminta mentransfer Rp14.500 — dan ia tidak salah
    mengira ada biaya tersembunyi, karena memang disembunyikan oleh halamannya sendiri.
    Ukur biaya setiap kanal untuk dua harga berbeda: QRIS mengikuti harga, semua bank
    tetap.

27. **Nomor telepon placeholder yang bentuknya tidak masuk akal ditolak sebagian bank.**
    `081200000000` ditolak BRI dan Permata dengan "Failed to generate VA" tetapi diterima
    BCA, BNI, dan yang lain. Karena nomor WhatsApp opsional di formulir, kasus ini nyata:
    pembeli yang tidak mengisinya menemukan dua bank yang selalu gagal. Diuji sebelas
    kandidat; yang diterima semua bank adalah nomor dengan digit berulang setelah prefix
    (`081211111111`). Pesan galatnya tidak menyebut nomor telepon sama sekali, jadi satu-
    satunya cara menemukannya adalah mengubah satu variabel pada satu waktu.

28. **Mengganti nilai tanpa mengujinya adalah kesalahan yang sama, satu langkah lebih
    jauh.** Nomor `081200000000` dipasang sebagai placeholder tanpa diuji ke BRI lebih
    dulu — dan ternyata juga ditolak, persis seperti nilai sebelumnya. Menguji satu
    kanal saja tidak cukup ketika masalahnya hanya muncul di kanal tertentu; uji harus
    mencakup kanal yang paling ketat.

29. **Pembacaan tangkapan layar tidak bisa dipercaya untuk angka.** Pada halaman yang
    sama, pembacaan itu melaporkan "Harga barang Rp12.000" dan kode pesanan
    "INV-BCCK2FM" — dua nilai yang tidak ada di proyek ini. Ia juga melaporkan teks
    pemilih cara bayar "terlalu gelap" padahal perhitungan kontras menunjukkan semua
    pasangan lulus WCAG AA (terendah 4,70:1). Angka yang salah lebih berbahaya daripada
    tidak ada angka, karena angkanya terlihat meyakinkan. Untuk nilai, baca DOM dan
    bandingkan dengan yang dikembalikan server; untuk kontras, hitung rasionya.

30. **Alamat `QrImage` dari iPaymu mengembalikan HTML, bukan gambar.** Isinya adalah
    halaman dengan PNG tertanam sebagai data URL. Memasangnya ke `src` sebuah `<img>`
    menghasilkan gambar yang tidak pernah muncul, tanpa pesan kesalahan apa pun. Isinya
    harus diambil dan data URL-nya yang dipakai — di server, karena permintaan dari
    peramban ke domain iPaymu ditolak aturan lintas-asal.
