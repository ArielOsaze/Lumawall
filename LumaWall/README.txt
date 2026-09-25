LUMAWALL 4.0.1

Cara pakai:
1. Jalankan LumaWall.exe.
2. Klik "Tambah wallpaper" lalu pilih video atau gambar pribadi.
3. Klik "Terapkan" pada kartu wallpaper, kemudian pilih Monitor 1, Monitor 2, atau Semua monitor. Tidak perlu membuka halaman lain.
4. Pilih target FPS di Performa. Untuk benar-benar mengurangi decode/render, pilih video lalu klik "Optimalkan".
5. Di Katalog, cari karakter/seri, klik Unduh, lalu pilih monitor tujuan.
6. Simpan susunan beberapa monitor sebagai profil agar dapat dipulihkan dengan satu klik.
7. Menutup jendela hanya memindahkan aplikasi ke area notifikasi. Pilih Keluar dari ikon tray untuk benar-benar menutup.

Format feed katalog (JSON):
[
  {
    "title": "Judul wallpaper",
    "videoUrl": "https://alamat/file.mp4",
    "thumbnailUrl": "https://alamat/preview.jpg",
    "license": "CC0",
    "sourceUrl": "https://alamat/sumber"
  }
]

Catatan:
- Gunakan hanya video yang Anda miliki atau yang lisensinya mengizinkan pengunduhan.
- Kolom URL katalog menerima feed JSON HTTPS dari penyedia/komunitas yang mengizinkan direct download; item akan tampil langsung di aplikasi.
- Katalog bawaan memuat tepat 2.000 pilihan: 1.723 video loop dan 277 wallpaper statis. Koleksi terdiri dari 900 Anime Loop, 220 Anime Girls, 57 Anime-style, 275 pilihan age-gated, dan 548 loop dinamis umum.
- Tidak ada entri Wikipedia/Wikimedia. Wallpaper online tetap berada di penyedia asal dan baru diunduh setelah pengguna memilihnya.
- Antarmuka monitor-wall memakai galeri asimetris, filter horizontal, inspector wallpaper permanen, dan navigation rail ringkas.
- Antarmuka tersedia dalam Indonesia, English, 简体中文, dan 日本語 melalui pemilih bahasa di bar atas.
- Kategori Mature 18+ hanya berisi ilustrasi sugestif non-eksplisit dan dilindungi peringatan umur sebelum thumbnail dimuat.
- Anime Loop berasal dari file MP4 live-wallpaper asli; bukan gambar berita dan bukan efek zoom otomatis.
- Setiap unduhan online menyimpan file .license.txt berisi kreator, lisensi, dan tautan sumber.
- Video selalu memerlukan proses decode. LumaWall men-decode video di GPU (hardware decode) dan mengomposit lewat GPU, sehingga pemakaian CPU tetap rendah; pause otomatis saat fullscreen, saat aplikasi lain dimaksimalkan (opsional), atau saat memakai baterai menekan beban lebih jauh.
- Jika driver GPU bermasalah, mesin video otomatis jatuh ke render CPU sebagai cadangan; pada kondisi normal GPU process memakai ANGLE/D3D11 dan bukan WARP.
- Wallpaper ditempatkan pada lapisan desktop Windows (WorkerW), sehingga ikon desktop dan aplikasi normal tetap berada di atasnya; ini bukan jendela overlay/topmost.
- Loop tetap berjalan saat jendela LumaWall diminimalkan, ditutup ke tray, atau saat desktop tampil penuh tanpa aplikasi terbuka.
- Pause bekerja per monitor: aplikasi fullscreen atau maximized hanya menghentikan wallpaper pada monitor yang tertutup itu, sedangkan monitor lain tetap beranimasi.
- Keluar dari aplikasi fullscreen langsung memulihkan animasi tanpa perlu klik; pemulihan dipicu event sistem, bukan menunggu pemeriksaan berkala.
- Antarmuka desktop gaming memakai navigation rail vertikal, panel properti langsung, status wallpaper faktual, dan kontrol performa khusus tanpa indikator online dekoratif.
- Memilih wallpaper di bagian bawah katalog tidak membangun ulang halaman; posisi scroll galeri tetap dipertahankan.
- Tombol Tampilkan lainnya menambah isi di galeri yang sama dan tidak mengembalikan scroll ke atas.
- Ukuran jendela mengikuti working area Windows dan DPI. Maximize menghormati taskbar pada setiap monitor; pada jendela sempit inspector disembunyikan agar katalog tetap dapat digunakan.
- Pergantian wallpaper saat aplikasi masih terbuka memakai halaman playback unik dan memasang ulang WorkerW secara otomatis; force-close tidak diperlukan.
- Pergantian wallpaper menggunakan staged swap: wallpaper lama tetap tampil sampai media baru benar-benar siap, sehingga tidak ada frame hitam saat Apply.
- Jika video atau gambar baru gagal dimuat, pergantian dibatalkan dan wallpaper lama tetap dipertahankan.
- LumaWall hanya menjalankan satu proses. Membuka aplikasi lagi mengaktifkan jendela yang sudah ada dan meneruskan perintah Apply ke proses utama.
- Pemeriksaan monitor bersifat stabil dan idempoten: wallpaper yang sama tidak dibongkar/pasang ulang hanya karena urutan monitor dari Windows berubah.
- Konfigurasi disimpan dengan file sementara dan cadangan; pada folder Windows terenkripsi aplikasi memakai penulisan aman yang kompatibel dengan EFS.
- Mesin video menggunakan Microsoft Edge WebView2 Runtime. Runtime ini sudah tersedia pada kebanyakan pemasangan Windows 10/11 modern.
- Untuk penggunaan paling ringan, pilih MP4 H.264 1080p 30 fps atau lebih rendah.
- Optimasi FPS memerlukan FFmpeg. LumaWall otomatis memakai FFmpeg dari PATH atau ffmpeg.exe yang diletakkan di folder aplikasi.
- Opsi startup menjalankan LumaWall setelah pengguna masuk Windows dan membuka aplikasi secara tersembunyi di system tray.
