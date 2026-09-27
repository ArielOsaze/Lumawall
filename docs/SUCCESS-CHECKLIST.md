# Checklist keberhasilan — LumaWall

Setiap baris punya angka yang diukur, bukan klaim. Perintah di kolom kanan bisa dijalankan
ulang kapan saja; kalau checker-nya tidak bisa gagal, ia tidak dipakai.

Terakhir diperbarui: rilis 4.4.9.0. Semua 40 checker PASS.

---

## Fitur yang diminta

| # | Fitur | Status | Angka terukur | Perintah |
|---|---|---|---|---|
| 1 | Widget timer **tidak boleh menimpa aplikasi** | ✅ | timer Z-index 78/81, `WS_EX_TOPMOST: False`; aplikasi di Z 2 | `tools/check-timer-zorder.ps1` |
| 2 | Timer **kadang tidak muncul** | ✅ diperbaiki | Rect setinggi font → GDI+ gambar **0 piksel**; +4px → **1986 piksel**. Semua 10 gaya sekarang menggambar | `tools/check-timer-styles.py` |
| 3 | Timer **bergaya iOS lock screen**, beberapa pilihan | ✅ | 10 gaya, masing-masing dengan muka font berbeda. Tebal goresan (mean run / tinggi jam): **ioslarge 11.6%** (paling tipis), ioslight 16.7%, iosdate 18.4%, minimal 23.7% | `tools/check-timer-styles.py` |
| 3b | **Font tiap gaya beda** | ✅ diperbaiki | Sebelumnya `iosdate` menggambar dengan font **sama persis** dengan `minimal` (kondisi pemilih font tidak pernah cocok). Sekarang tiap gaya menyebut mukanya sendiri dan checker memverifikasi muka yang benar-benar dipakai | `tools/check-timer-styles.py` |
| 4 | Timer **background transparan** | ✅ | wallpaper tembus **69–99%** per gaya | `tools/check-timer-styles.py` |
| 5 | **Placement tidak bikin bingung** | ✅ diperbaiki | Tanda jam terukur di **0.17/0.17**, **0.83/0.83**, **0.50/0.50** sesuai posisi | `tools/check-placement-mark.py` |
| 6 | Pilih placement **tidak scroll ke atas** | ✅ | Offset dipulihkan; pad persegi 126x126, sel 42x42, drift label **0.0px** | `tools/test-studio-scroll.ps1`, `tools/measure-placement-pad.ps1` |
| 7 | **Cold start tidak ngelag** | ✅ diperbaiki | Parse katalog 288 ms dipindah ke worker thread; startup **1.66s** (limit 4.0s) | `tools/check-startup.py` |
| 8 | **Update apa pun otomatis update installer di web** | ✅ | `python tools/release.py <versi>` — 11 langkah: build, installer, portable, msix, stage, cache-bust, manifest, install, verify | `tools/release.py` |
| 9 | **Tile hitam di katalog** | ✅ diperbaiki | **22.879** entri, **0** tanpa `thumbnailUrl`; 50/50 sampel live adalah JPEG/PNG asli | `tools/check-catalog.py` |
| 10 | **Favicon logo lama** | ✅ | `/favicon.ico` HTTP 200, ICO 3 ukuran (16/32/48), tinta gelap = logo L | `curl -D - https://lumawall.xinet.id/favicon.ico` |
| 11 | **Scrollbar gelap** | ✅ | Isi 11785px dalam 700px → bar 10px, kecerahan app **8** (dari ~240) | `tools/check-scrollbar-site.mjs` |
| 12 | **Katalog besar, kategori benar** | ✅ | **22.879** entri · 100% dinamis · 100% HD · 58.8% 2K/4K · 0 duplikat · 0 AI · 16 kategori · mature 249 | `tools/check-catalog.py`, `tools/audit-categories.py` |
| 13 | **Dua bahasa (ID/EN)** | ✅ | Kedua halaman ada, saling terhubung `hreflang`; semua kunci terjemahan lengkap 4 bahasa | `tools/verify-claims.py` |

---

## Optimisasi

| # | Optimisasi | Sebelum | Sesudah | Perintah |
|---|---|---|---|---|
| 1 | **CPU idle** | 7.3% | **2.6%** (limit 3.0%) | `tools/check-idle-cpu.py` |
| 2 | Pemindaian jendela | 2× `EnumWindows` penuh tiap 2s (~1.000 panggilan lintas-proses) | **1 lintasan** per tick, filter murah dulu, nama kelas di-cache | — |
| 3 | Spam log | 309 baris / 10 menit | **0 baris** saat idle | `tools/check-idle-cpu.py` |
| 4 | **Cold start** | parse 288 ms memblokir UI thread | worker thread, **paralel** dengan pemulihan wallpaper | `tools/check-startup.py` |
| 5 | **RAM** | — | **215 MB** dengan 3 monitor aktif | `tools/check-idle-cpu.py` |
| 6 | GPU vs CPU | — | Wallpaper didekode WebView2 (GPU); proses UI **2.6%**, tiap WebView2 ~0.5% | `tools/check-idle-cpu.py` |

---

## Zero bug

| # | Yang diperiksa | Status |
|---|---|---|
| 1 | Tidak ada flicker hitam saat ganti wallpaper | ✅ "Wallpaper swap committed without blank frame" |
| 2 | Tidak ada exception saat jalan | ✅ 0 exception |
| 3 | Timer tidak menimpa aplikasi | ✅ terbukti positif **dan** negatif |
| 4 | Semua gaya timer menggambar | ✅ 10/10, diuji sabotase (kotak solid & kosong dua-duanya FAIL) |
| 5 | Placement mencatat klik **dan** menggambar ulang | ✅ dua-duanya diperiksa terpisah |
| 6 | Installer di web = biner yang dibuild | ✅ sha256 cocok (`497d9bd6…`) |
| 7 | Deploy tidak mematikan situs | ✅ `rootDirectory=site` utuh, domain menyajikan situs asli |
| 8 | Semua 40 checker | ✅ **all 40 checks passed** | `tools/verify-all.py` |

---

## Pelajaran yang menentukan (kenapa checker ini ada)

1. **`UniformGrid` mengabaikan `Grid.SetRow`/`Grid.SetColumn`.** Ia menempatkan anak
   berdasarkan urutan. Tanda jam adalah anak ke-10, jadi selalu mendarat di kiri-bawah dan
   **tidak pernah bisa dipindah** — berapa pun posisi yang dipilih. Config tersimpan benar,
   halaman di-reload, tapi yang terlihat tidak berubah. Itulah "placement bikin bingung".

2. **Kondisi pemilih font yang tidak pernah bisa cocok.** Gaya iOS meminta muka tipis dengan
   `light.Name == family.Name || light.Name.StartsWith("Segoe UI Light")`. Entri pertama
   daftar adalah `"Segoe UI Variable Display Light"` — nama itu tidak sama dengan
   `"Segoe UI Variable Display"` dan tidak diawali `"Segoe UI Light"`, jadi kondisi itu
   **melewatinya** dan jatuh ke muka 57% lebih tebal. `iosdate` tidak ada di daftar sama
   sekali, jadi digambar dengan font **sama persis** dengan `minimal`. Itulah "font timernya
   gada bedanya". Sekarang tiap gaya menyebut mukanya sendiri, dan checker memverifikasi
   muka yang benar-benar dipakai — bukan sekadar ada piksel.

3. **Rect setinggi font membuat GDI+ menggambar nol piksel.** Tanpa exception, tanpa
   peringatan. Gaya ber-font besar (`ioslarge` 93px) kena, yang kecil lolos — itu bug
   "timer ada ga muncul". Diukur: 0 piksel vs 1986 piksel.

4. **Checker yang tidak bisa gagal tidak berguna.** `check-timer-styles.py` versi pertama
   memotret widget di atas wallpaper, jadi yang terukur adalah wallpaper: semua gaya
   dilaporkan "93% ink" dan lolos. Versi sekarang membaca alpha dari `DrawFrame` itu sendiri,
   memeriksa muka font, dan sudah diuji dengan sabotase (kotak solid, gambar kosong, dan
   font yang dikembalikan ke bug lama — ketiganya FAIL).

5. **Membangun ulang halaman pada setiap klik membuat klik berikutnya meleset.** Setiap
   pilih posisi memanggil `ReloadCurrentPage()`, yang membangun ulang seluruh halaman Studio.
   Klik kedua mendarat saat halaman setengah jadi. Terukur: klik di pad+0, +10, +20, +30
   mencatat middle-left, top-left, middle-left, middle-center — empat jawaban berbeda untuk
   satu sel. Sekarang memilih posisi hanya memindahkan tanda dan mengganti label.

6. **Vision tidak bisa dipercaya untuk verifikasi.** Ia menyebut "Kaspro/Sakuku" (konten
   yang tidak ada di app), dan bilang semua bar ada di kiri-bawah padahal tidak. Setiap
   klaim visual di dokumen ini berasal dari pengukuran piksel.

7. **Jangan mengukur dari asumsi.** Offset pad dari label salah tiga kali berturut-turut.
   Checker yang benar mengkalibrasi dari objeknya sendiri (tanda jam) dan memverifikasi
   setiap langkah lewat efek samping yang bisa dibaca (file config).

8. **`SetForegroundWindow` tidak cukup untuk menggerakkan aplikasi.** Windows menolaknya
   bila proses pemanggil bukan proses foreground — persis kasus checker yang dijalankan dari
   terminal. Kliknya mendarat di terminal, app tidak mencatat apa pun, dan checker menyalahkan
   app. Perlu `ShowWindow(SW_RESTORE)` + `SetWindowPos(HWND_TOPMOST)` +
   `SetWindowPos(HWND_NOTOPMOST)`.

9. **Verifikasi tiap URL, jangan percaya polanya.** Backfill thumbnail motionbgs: pola
   `.jpg` 78%, `.WxH.jpg` 22% — ternyata keduanya dipakai, entri lama dan baru. Setiap still
   diverifikasi lewat HTTP sebelum ditulis.

10. **Cache-bust harus mencakup file logo.** Tanpa itu browser menyimpan favicon lama
    selamanya, dan `favicon.ico` yang tidak ada membuat browser tidak pernah memperbaruinya.

11. **Parse berat tidak boleh di jalur kritis.** 288 ms di UI thread antara window muncul dan
    wallpaper naik = lag yang terasa di setiap cold start.
