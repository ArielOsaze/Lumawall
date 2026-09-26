// site-copy.js — the marketing site's copy, in both languages.
//
// ── why two files and not one page that swaps text ───────────────────────────
//
// A single page that swaps its text with JavaScript is one URL. A search engine
// indexes one language, and the other is invisible - so half the work of writing it is
// thrown away.
//
// So the site is built as two pages: `/` in Indonesian and `/en/` in English, each a
// real document with its own title, description and structured data, linked by
// hreflang so a search engine knows they are the same page in two languages rather
// than two pages competing with each other.
//
// tools/make-site-i18n.py generates the English page from the Indonesian one using
// this table. The Indonesian page is the source; the English is derived, so the two
// cannot drift in structure - only in words.
//
// ── what is NOT translated ───────────────────────────────────────────────────
//
// Numbers, units, format names, product names, and the version string. `14,5 MB`
// becomes `14.5 MB` because the decimal separator IS localised; `1920×1080` does not,
// because it is a specification.

export const ID = {
  // ── head ──
  'LumaWall - Wallpaper hidup untuk Windows': 'LumaWall - Wallpaper hidup untuk Windows',
  'Wallpaper video di setiap monitor, diproses chip grafis supaya CPU tetap di bawah 1%. Berhenti otomatis saat game fullscreen. Gratis, 5.000+ wallpaper.':
    'Wallpaper video di setiap monitor, diproses chip grafis supaya CPU tetap di bawah 1%. Berhenti otomatis saat game fullscreen. Gratis, 5.000+ wallpaper.',

  // ── nav ──
  'Performa': 'Performa',
  'Video': 'Video',
  'Tampilan': 'Tampilan',
  'FAQ': 'FAQ',
  'Unduh': 'Unduh',

  // ── hero ──
  'Video diproses chip grafis, jadi CPU tetap di bawah 1%.':
    'Video diproses chip grafis, jadi CPU tetap di bawah 1%.',
  'Lihat cara kerjanya': 'Lihat cara kerjanya',
  'wallpaper siap pakai': 'wallpaper siap pakai',
  'satu core, tiga wallpaper': 'satu core, tiga wallpaper',
  'Per layar': 'Per layar',
  'pause otomatis': 'pause otomatis',
  'Gratis': 'Gratis',
  'tanpa iklan': 'tanpa iklan',

  // ── features ──
  'Dibangun untuk dipakai bertahun-tahun': 'Dibangun untuk dipakai bertahun-tahun',
  'Enam hal yang biasanya bikin wallpaper bergerak ditinggalkan: CPU yang panas, game yang tersendat, ikon desktop yang tidak bisa diklik.':
    'Enam hal yang biasanya bikin wallpaper bergerak ditinggalkan: CPU yang panas, game yang tersendat, ikon desktop yang tidak bisa diklik.',
  'Video didecode chip grafis': 'Video didecode chip grafis',
  'Video diproses blok khusus di chip grafis (NVDEC atau DXVA2), lalu dikomposit lewat DWM. Saat tiga wallpaper 1080p berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%.':
    'Video diproses blok khusus di chip grafis (NVDEC atau DXVA2), lalu dikomposit lewat DWM. Saat tiga wallpaper 1080p berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%.',
  'Berhenti hanya di layar yang tertutup': 'Berhenti hanya di layar yang tertutup',
  'Game fullscreen di monitor kedua hanya menghentikan wallpaper monitor kedua. Monitor lain tetap beranimasi. Tidak ada lagi wallpaper yang ikut mati hanya karena ada aplikasi di layar sebelah.':
    'Game fullscreen di monitor kedua hanya menghentikan wallpaper monitor kedua. Monitor lain tetap beranimasi. Tidak ada lagi wallpaper yang ikut mati hanya karena ada aplikasi di layar sebelah.',
  'Reaksi dalam ratusan milidetik': 'Reaksi dalam ratusan milidetik',
  'Pause dan resume dipicu langsung oleh event sistem Windows. Saat game ditutup, animasi wallpaper kembali berjalan dalam ratusan milidetik, tanpa klik atau sentuhan.':
    'Pause dan resume dipicu langsung oleh event sistem Windows. Saat game ditutup, animasi wallpaper kembali berjalan dalam ratusan milidetik, tanpa klik atau sentuhan.',
  'Susunan berbeda tiap layar': 'Susunan berbeda tiap layar',
  'Pasang video berbeda di setiap monitor, lalu simpan seluruh susunan sebagai profil dan pulihkan dengan satu klik. Kalau tata letak monitor berubah, LumaWall menyesuaikan sendiri.':
    'Pasang video berbeda di setiap monitor, lalu simpan seluruh susunan sebagai profil dan pulihkan dengan satu klik. Kalau tata letak monitor berubah, LumaWall menyesuaikan sendiri.',
  'Katalog 5.000+ wallpaper': 'Katalog 5.000+ wallpaper',
  'Cari berdasarkan karakter atau suasana, lihat pratinjau, lalu unduh langsung dari dalam aplikasi. Setiap unduhan menyertakan file':
    'Cari berdasarkan karakter atau suasana, lihat pratinjau, lalu unduh langsung dari dalam aplikasi. Setiap unduhan menyertakan file',
  'Tidak mengganggu desktop': 'Tidak mengganggu desktop',
  'Wallpaper ditempatkan di lapisan desktop Windows, tepat di bawah ikon. Ini bukan jendela overlay, jadi ikon tetap bisa diklik, tidak muncul di Alt+Tab, dan tidak menghalangi aplikasi apa pun.':
    'Wallpaper ditempatkan di lapisan desktop Windows, tepat di bawah ikon. Ini bukan jendela overlay, jadi ikon tetap bisa diklik, tidak muncul di Alt+Tab, dan tidak menghalangi aplikasi apa pun.',

  // ── performance ──
  'Angkanya, bukan klaim': 'Angkanya, bukan klaim',
  'Diukur pada tiga monitor 1080p dengan tiga wallpaper video berjalan bersamaan. Kedua batang di bawah menunjukkan beban satu core, supaya perbandingannya sebanding.':
    'Diukur pada tiga monitor 1080p dengan tiga wallpaper video berjalan bersamaan. Kedua batang di bawah menunjukkan beban satu core, supaya perbandingannya sebanding.',
  'Video didecode software, semuanya di core CPU': 'Video didecode software, semuanya di core CPU',
  'Dengan LumaWall': 'Dengan LumaWall',
  'Decode dipindahkan ke blok khusus chip grafis': 'Decode dipindahkan ke blok khusus chip grafis',
  'Decode video': 'Decode video',
  'Ditangani blok khusus di GPU, bukan core CPU': 'Ditangani blok khusus di GPU, bukan core CPU',
  'Resume setelah game ditutup': 'Resume setelah game ditutup',
  'Dari game ditutup sampai wallpaper berjalan lagi': 'Dari game ditutup sampai wallpaper berjalan lagi',
  'Versi lama': 'Versi lama',
  'Cek tiap 2 detik': 'Cek tiap 2 detik',
  'Dipicu event Windows': 'Dipicu event Windows',
  'Wallpaper statis tanpa WebView': 'Wallpaper statis tanpa WebView',
  'Gambar diam dirender langsung, menghemat sekitar 75 MB RAM per monitor.':
    'Gambar diam dirender langsung, menghemat sekitar 75 MB RAM per monitor.',
  'Layar terkunci, layar mati, atau memakai baterai: decode dihentikan otomatis.':
    'Layar terkunci, layar mati, atau memakai baterai: decode dihentikan otomatis.',
  'Pergantian antar loop dirancang mulus, tanpa frame hitam di antaranya.':
    'Pergantian antar loop dirancang mulus, tanpa frame hitam di antaranya.',

  // ── video ──
  'LumaWall dalam 52 detik': 'LumaWall dalam 52 detik',
  'Seluruh isi video ini diambil dari aplikasi yang kamu unduh, bukan mockup.':
    'Seluruh isi video ini diambil dari aplikasi yang kamu unduh, bukan mockup.',
  'Browser kamu tidak mendukung pemutaran video.': 'Browser kamu tidak mendukung pemutaran video.',

  // ── tour ──
  'Semua yang kamu butuhkan, satu jendela': 'Semua yang kamu butuhkan, satu jendela',
  'Diambil langsung dari aplikasi, bukan dari rancangan.':
    'Diambil langsung dari aplikasi, bukan dari rancangan.',
  'Katalog': 'Katalog',
  'Cari, filter, dan unduh dari 5.000+ wallpaper tanpa keluar dari aplikasi':
    'Cari, filter, dan unduh dari 5.000+ wallpaper tanpa keluar dari aplikasi',
  'Semua koleksi kamu, rapi di satu tempat': 'Semua koleksi kamu, rapi di satu tempat',
  'Atur wallpaper tiap monitor dan simpan sebagai profil': 'Atur wallpaper tiap monitor dan simpan sebagai profil',
  'Pantau CPU, RAM, dan FPS secara langsung': 'Pantau CPU, RAM, dan FPS secara langsung',

  // ── comparison ──
  'Bersebelahan dengan bawaan Windows': 'Bersebelahan dengan bawaan Windows',
  'Bawaan Windows menangani gambar diam dengan baik. Untuk video, ada beberapa hal yang tidak bisa dilakukannya.':
    'Bawaan Windows menangani gambar diam dengan baik. Untuk video, ada beberapa hal yang tidak bisa dilakukannya.',
  'Fitur': 'Fitur',
  'LumaWall': 'LumaWall',
  'Wallpaper bawaan Windows': 'Wallpaper bawaan Windows',
  'Wallpaper video di setiap monitor': 'Wallpaper video di setiap monitor',
  'Ya': 'Ya',
  'Tidak': 'Tidak',
  'Hardware decode GPU': 'Hardware decode GPU',
  'Pause per monitor saat fullscreen': 'Pause per monitor saat fullscreen',
  'Otomatis': 'Otomatis',
  'Wallpaper berbeda tiap layar': 'Wallpaper berbeda tiap layar',
  'Terbatas': 'Terbatas',
  'Profil susunan multi-display': 'Profil susunan multi-display',
  'Satu klik': 'Satu klik',
  'Katalog wallpaper bawaan': 'Katalog wallpaper bawaan',
  'Pemulihan otomatis setelah Explorer restart': 'Pemulihan otomatis setelah Explorer restart',
  'Harga': 'Harga',
  'Angka performa diukur pada Windows 11 build 26200, Ryzen 5 5600, GeForce GTX 1080, tiga monitor 1080p dengan tiga wallpaper H.264 berjalan bersamaan. CPU dibaca dari Performance Monitor, waktu resume dari log aplikasi yang mencatat setiap perubahan status playback.':
    'Angka performa diukur pada Windows 11 build 26200, Ryzen 5 5600, GeForce GTX 1080, tiga monitor 1080p dengan tiga wallpaper H.264 berjalan bersamaan. CPU dibaca dari Performance Monitor, waktu resume dari log aplikasi yang mencatat setiap perubahan status playback.',

  // ── download ──
  'Pasang dalam satu menit': 'Pasang dalam satu menit',
  'Aplikasinya sama di ketiga format. Yang berbeda hanya cara memasangnya.':
    'Aplikasinya sama di ketiga format. Yang berbeda hanya cara memasangnya.',
  'Paling mudah': 'Paling mudah',
  'Installer': 'Installer',
  'Untuk pemakaian sehari-hari. Pasang seperti aplikasi Windows biasa, lengkap dengan pintasan Start Menu dan opsi berjalan otomatis saat Windows menyala.':
    'Untuk pemakaian sehari-hari. Pasang seperti aplikasi Windows biasa, lengkap dengan pintasan Start Menu dan opsi berjalan otomatis saat Windows menyala.',
  'Paket MSIX': 'Paket MSIX',
  'Kalau kamu ingin Windows yang mengurusnya: pasang lewat Microsoft Store atau sideload, dan pembaruan serta penghapusan ditangani sistem.':
    'Kalau kamu ingin Windows yang mengurusnya: pasang lewat Microsoft Store atau sideload, dan pembaruan serta penghapusan ditangani sistem.',
  'Portable': 'Portable',
  'Untuk mencoba dulu tanpa mengubah apa pun, atau dibawa di flashdisk. Ekstrak ke folder mana saja lalu jalankan; tidak ada yang ditulis ke registry.':
    'Untuk mencoba dulu tanpa mengubah apa pun, atau dibawa di flashdisk. Ekstrak ke folder mana saja lalu jalankan; tidak ada yang ditulis ke registry.',
  'tanpa registry': 'tanpa registry',
  'Windows dan prosesor 64-bit (x64)': 'Windows dan prosesor 64-bit (x64)',
  'WebView2 Runtime, sudah tersedia di Windows 11 dan Windows 10 yang terbarui':
    'WebView2 Runtime, sudah tersedia di Windows 11 dan Windows 10 yang terbarui',

  // ── FAQ ──
  'Pertanyaan yang paling sering masuk': 'Pertanyaan yang paling sering masuk',
  'Apakah LumaWall memberatkan komputer?': 'Apakah LumaWall memberatkan komputer?',
  'Tidak. Video didecode di GPU, bukan CPU. Pada tiga wallpaper 1080p yang berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%. Aplikasi juga berhenti melakukan decode saat layar terkunci, layar mati, atau saat komputer memakai baterai.':
    'Tidak. Video didecode di GPU, bukan CPU. Pada tiga wallpaper 1080p yang berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%. Aplikasi juga berhenti melakukan decode saat layar terkunci, layar mati, atau saat komputer memakai baterai.',
  'Bagaimana kalau saya membuka game fullscreen?': 'Bagaimana kalau saya membuka game fullscreen?',
  'Wallpaper di monitor yang tertutup game langsung berhenti, dan berjalan lagi begitu game ditutup atau diminimize. Pause bekerja per layar, jadi monitor lain tetap beranimasi seperti biasa.':
    'Wallpaper di monitor yang tertutup game langsung berhenti, dan berjalan lagi begitu game ditutup atau diminimize. Pause bekerja per layar, jadi monitor lain tetap beranimasi seperti biasa.',
  'Apakah ikon desktop saya masih bisa diklik?': 'Apakah ikon desktop saya masih bisa diklik?',
  'Bisa. LumaWall menempatkan wallpaper di lapisan desktop Windows, tepat di bawah ikon. Ia bukan jendela overlay, jadi tidak mencuri klik, tidak muncul di Alt+Tab, dan tidak menghalangi apa pun.':
    'Bisa. LumaWall menempatkan wallpaper di lapisan desktop Windows, tepat di bawah ikon. Ia bukan jendela overlay, jadi tidak mencuri klik, tidak muncul di Alt+Tab, dan tidak menghalangi apa pun.',
  'Bisa memakai video saya sendiri?': 'Bisa memakai video saya sendiri?',
  'Bisa. Klik Tambah lalu pilih file video atau gambar milikmu: mp4, m4v, wmv, avi, mov, webm, jpg, png, atau bmp. Untuk setiap unduhan dari katalog, LumaWall juga menyimpan file':
    'Bisa. Klik Tambah lalu pilih file video atau gambar milikmu: mp4, m4v, wmv, avi, mov, webm, jpg, png, atau bmp. Untuk setiap unduhan dari katalog, LumaWall juga menyimpan file',
  'Apakah LumaWall gratis?': 'Apakah LumaWall gratis?',
  'Gratis, tanpa iklan, dan tanpa versi berbayar. Tidak ada batas jumlah wallpaper maupun jumlah monitor.':
    'Gratis, tanpa iklan, dan tanpa versi berbayar. Tidak ada batas jumlah wallpaper maupun jumlah monitor.',
  'Bagaimana cara menghapusnya?': 'Bagaimana cara menghapusnya?',
  'Lewat Settings › Apps seperti aplikasi Windows biasa, atau lewat uninstaller di folder pemasangan. Semua berkas ada di satu folder dan bisa dihapus seluruhnya tanpa sisa di registry.':
    'Lewat Settings › Apps seperti aplikasi Windows biasa, atau lewat uninstaller di folder pemasangan. Semua berkas ada di satu folder dan bisa dihapus seluruhnya tanpa sisa di registry.',
  'Berapa monitor yang bisa dipakai sekaligus?': 'Berapa monitor yang bisa dipakai sekaligus?',
  'Tidak ada batas di sisi aplikasi. Setiap monitor yang terdeteksi Windows mendapat wallpaper, pengaturan, dan status pause-nya sendiri, dan susunannya bisa disimpan sebagai profil.':
    'Tidak ada batas di sisi aplikasi. Setiap monitor yang terdeteksi Windows mendapat wallpaper, pengaturan, dan status pause-nya sendiri, dan susunannya bisa disimpan sebagai profil.',
  'Bagaimana kalau Explorer restart atau crash?': 'Bagaimana kalau Explorer restart atau crash?',
  'LumaWall memeriksa kesehatannya setiap dua detik. Kalau jendela desktop hilang, wallpaper dibangun ulang dan dipasang kembali secara otomatis dalam waktu kurang dari empat detik, tanpa menjalankan ulang aplikasi.':
    'LumaWall memeriksa kesehatannya setiap dua detik. Kalau jendela desktop hilang, wallpaper dibangun ulang dan dipasang kembali secara otomatis dalam waktu kurang dari empat detik, tanpa menjalankan ulang aplikasi.',
  'Apakah ada iklan atau pelacakan?': 'Apakah ada iklan atau pelacakan?',
  'Tidak ada iklan, akun, maupun telemetri. Satu-satunya koneksi internet terjadi saat kamu sendiri mengunduh wallpaper dari katalog.':
    'Tidak ada iklan, akun, maupun telemetri. Satu-satunya koneksi internet terjadi saat kamu sendiri mengunduh wallpaper dari katalog.',
  'Bahasa apa saja yang didukung?': 'Bahasa apa saja yang didukung?',
  'Antarmuka tersedia dalam Bahasa Indonesia, English, 简体中文, dan 日本語. Kamu bisa menggantinya kapan saja lewat pemilih bahasa di bar atas.':
    'Antarmuka tersedia dalam Bahasa Indonesia, English, 简体中文, dan 日本語. Kamu bisa menggantinya kapan saja lewat pemilih bahasa di bar atas.',

  // ── close ──
  'Wallpaper yang bergerak, komputer yang tetap tenang': 'Wallpaper yang bergerak, komputer yang tetap tenang',
  'Gratis, tanpa iklan, dan kamu akan lupa kalau ini sedang berjalan.':
    'Gratis, tanpa iklan, dan kamu akan lupa kalau ini sedang berjalan.',
  'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB': 'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB',
  'Wallpaper hidup untuk Windows. Video diproses chip grafis, dan wallpaper berhenti sendiri saat kamu membuka aplikasi fullscreen.':
    'Wallpaper hidup untuk Windows. Video diproses chip grafis, dan wallpaper berhenti sendiri saat kamu membuka aplikasi fullscreen.',

  // ── footer ──
  'Xinet Group': 'Xinet Group',
  'Pertanyaan': 'Pertanyaan',
  'Kode sumber': 'Kode sumber',
  'Laporkan masalah': 'Laporkan masalah',
  'LumaWall adalah perangkat lunak gratis dan terbuka.': 'LumaWall adalah perangkat lunak gratis dan terbuka.',
  'Tanpa membebani komputer.': 'Tanpa membebani komputer.',
  'Buka game fullscreen, dan wallpaper di layar itu berhenti sendiri.':
    'Buka game fullscreen, dan wallpaper di layar itu berhenti sendiri.',
  'Kenapa LumaWall': 'Kenapa LumaWall',
  'Performa terukur': 'Performa terukur',
  'Tanpa LumaWall': 'Tanpa LumaWall',
  'Versi sekarang': 'Versi sekarang',
  'Hemat saat layar tidak terlihat': 'Hemat saat layar tidak terlihat',
  'Perpindahan loop tanpa kedip': 'Perpindahan loop tanpa kedip',
  'Tampilan asli': 'Tampilan asli',
  'NVDEC / DXVA2': 'NVDEC / DXVA2',
  'Microsoft Store': 'Microsoft Store',
  'Tanpa install': 'Tanpa install',
  'Syarat sistem': 'Syarat sistem',
  'Windows 10 versi 1809 atau lebih baru, atau Windows 11':
    'Windows 10 versi 1809 atau lebih baru, atau Windows 11',
  'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB': 'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB',
  'Unduh gratis': 'Unduh gratis',
  'Unduh installer': 'Unduh installer',
  'Unduh MSIX': 'Unduh MSIX',
  'Unduh portable': 'Unduh portable',
  'Unduh untuk Windows': 'Unduh untuk Windows',
  'Wallpaper hidup di setiap monitor.': 'Wallpaper hidup di setiap monitor.',
  'Wallpaper video diproses chip grafis, bukan CPU. Berhenti otomatis saat game fullscreen, jalan lagi begitu game ditutup. 5.000+ wallpaper, gratis, tanpa iklan.':
    'Wallpaper video diproses chip grafis, bukan CPU. Berhenti otomatis saat game fullscreen, jalan lagi begitu game ditutup. 5.000+ wallpaper, gratis, tanpa iklan.',
};


export const EN = {
  // ── head ──
  'LumaWall - Wallpaper hidup untuk Windows': 'LumaWall - Live Wallpaper for Windows',
  'Wallpaper video di setiap monitor, diproses chip grafis supaya CPU tetap di bawah 1%. Berhenti otomatis saat game fullscreen. Gratis, 5.000+ wallpaper.':
    'Video wallpaper on every monitor, decoded on the GPU so the CPU stays under 1%. Pauses itself when a game goes fullscreen. Free, 5,000+ wallpapers.',

  // ── nav ──
  'Performa': 'Performance',
  'Video': 'Video',
  'Tampilan': 'Screens',
  'FAQ': 'FAQ',
  'Unduh': 'Download',

  // ── hero ──
  'Video diproses chip grafis, jadi CPU tetap di bawah 1%.':
    'Video decoded on the GPU, so the CPU stays under 1%.',
  'Lihat cara kerjanya': 'See how it works',
  'wallpaper siap pakai': 'wallpapers ready to use',
  'satu core, tiga wallpaper': 'one core, three wallpapers',
  'Per layar': 'Per screen',
  'pause otomatis': 'automatic pause',
  'Gratis': 'Free',
  'tanpa iklan': 'no ads',

  // ── features ──
  'Dibangun untuk dipakai bertahun-tahun': 'Built to be used for years',
  'Enam hal yang biasanya bikin wallpaper bergerak ditinggalkan: CPU yang panas, game yang tersendat, ikon desktop yang tidak bisa diklik.':
    'Six reasons people give up on live wallpaper: a hot CPU, games that stutter, desktop icons you can no longer click.',
  'Video didecode chip grafis': 'Video decoded on the graphics chip',
  'Video diproses blok khusus di chip grafis (NVDEC atau DXVA2), lalu dikomposit lewat DWM. Saat tiga wallpaper 1080p berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%.':
    'Video is handled by a dedicated block on the graphics chip (NVDEC or DXVA2), then composited through DWM. With three 1080p wallpapers running at once, LumaWall\'s main process stays under 1% CPU.',
  'Berhenti hanya di layar yang tertutup': 'Stops only on the screen it covers',
  'Game fullscreen di monitor kedua hanya menghentikan wallpaper monitor kedua. Monitor lain tetap beranimasi. Tidak ada lagi wallpaper yang ikut mati hanya karena ada aplikasi di layar sebelah.':
    'A fullscreen game on your second monitor stops the second monitor\'s wallpaper and nothing else. The others keep animating. No more wallpapers dying because of an app on the screen next door.',
  'Reaksi dalam ratusan milidetik': 'Reacts in hundreds of milliseconds',
  'Pause dan resume dipicu langsung oleh event sistem Windows. Saat game ditutup, animasi wallpaper kembali berjalan dalam ratusan milidetik, tanpa klik atau sentuhan.':
    'Pause and resume are driven by Windows\' own system events. Close the game and the wallpaper is animating again within hundreds of milliseconds, with no click and no touch.',
  'Susunan berbeda tiap layar': 'A different setup for every screen',
  'Pasang video berbeda di setiap monitor, lalu simpan seluruh susunan sebagai profil dan pulihkan dengan satu klik. Kalau tata letak monitor berubah, LumaWall menyesuaikan sendiri.':
    'Put a different video on each monitor, then save the whole arrangement as a profile and restore it in one click. If your monitor layout changes, LumaWall adapts on its own.',
  'Katalog 5.000+ wallpaper': 'A catalog of 5,000+ wallpapers',
  'Cari berdasarkan karakter atau suasana, lihat pratinjau, lalu unduh langsung dari dalam aplikasi. Setiap unduhan menyertakan file':
    'Search by character or mood, preview it, then download it without leaving the app. Every download comes with its',
  'Tidak mengganggu desktop': 'It does not get in the desktop\'s way',
  'Wallpaper ditempatkan di lapisan desktop Windows, tepat di bawah ikon. Ini bukan jendela overlay, jadi ikon tetap bisa diklik, tidak muncul di Alt+Tab, dan tidak menghalangi aplikasi apa pun.':
    'The wallpaper sits on Windows\' desktop layer, directly beneath the icons. It is not an overlay window, so your icons stay clickable, it never appears in Alt+Tab, and it blocks nothing.',

  // ── performance ──
  'Angkanya, bukan klaim': 'Numbers, not claims',
  'Diukur pada tiga monitor 1080p dengan tiga wallpaper video berjalan bersamaan. Kedua batang di bawah menunjukkan beban satu core, supaya perbandingannya sebanding.':
    'Measured on three 1080p monitors with three video wallpapers running at once. Both bars show the load on a single core, so the comparison is like for like.',
  'Video didecode software, semuanya di core CPU': 'Video decoded in software, all of it on the CPU core',
  'Dengan LumaWall': 'With LumaWall',
  'Decode dipindahkan ke blok khusus chip grafis': 'Decoding moved to a dedicated block on the graphics chip',
  'Decode video': 'Video decoding',
  'Ditangani blok khusus di GPU, bukan core CPU': 'Handled by a dedicated block on the GPU, not the CPU core',
  'Resume setelah game ditutup': 'Resume after a game closes',
  'Dari game ditutup sampai wallpaper berjalan lagi': 'From the game closing to the wallpaper running again',
  'Versi lama': 'Older version',
  'Cek tiap 2 detik': 'Polls every 2 seconds',
  'Dipicu event Windows': 'Driven by Windows events',
  'Wallpaper statis tanpa WebView': 'Static wallpapers, no WebView',
  'Gambar diam dirender langsung, menghemat sekitar 75 MB RAM per monitor.':
    'Still images render directly, saving about 75 MB of RAM per monitor.',
  'Layar terkunci, layar mati, atau memakai baterai: decode dihentikan otomatis.':
    'Screen locked, display off, or running on battery: decoding stops on its own.',
  'Pergantian antar loop dirancang mulus, tanpa frame hitam di antaranya.':
    'Loop transitions are built to be seamless, with no black frame between them.',

  // ── video ──
  'LumaWall dalam 52 detik': 'LumaWall in 52 seconds',
  'Seluruh isi video ini diambil dari aplikasi yang kamu unduh, bukan mockup.':
    'Everything in this video is captured from the app you download, not a mockup.',
  'Browser kamu tidak mendukung pemutaran video.': 'Your browser does not support video playback.',

  // ── tour ──
  'Semua yang kamu butuhkan, satu jendela': 'Everything you need, in one window',
  'Diambil langsung dari aplikasi, bukan dari rancangan.':
    'Captured straight from the app, not from a design.',
  'Katalog': 'Catalog',
  'Cari, filter, dan unduh dari 5.000+ wallpaper tanpa keluar dari aplikasi':
    'Search, filter and download from 5,000+ wallpapers without leaving the app',
  'Semua koleksi kamu, rapi di satu tempat': 'Everything you have collected, in one place',
  'Atur wallpaper tiap monitor dan simpan sebagai profil': 'Set each monitor\'s wallpaper and save it as a profile',
  'Pantau CPU, RAM, dan FPS secara langsung': 'Watch CPU, RAM and FPS live',

  // ── comparison ──
  'Bersebelahan dengan bawaan Windows': 'Side by side with what Windows ships',
  'Bawaan Windows menangani gambar diam dengan baik. Untuk video, ada beberapa hal yang tidak bisa dilakukannya.':
    'Windows\' own wallpaper handles still images well. With video, there are things it simply cannot do.',
  'Fitur': 'Feature',
  'LumaWall': 'LumaWall',
  'Wallpaper bawaan Windows': 'Windows wallpaper',
  'Wallpaper video di setiap monitor': 'Video wallpaper on every monitor',
  'Ya': 'Yes',
  'Tidak': 'No',
  'Hardware decode GPU': 'GPU hardware decoding',
  'Pause per monitor saat fullscreen': 'Per-monitor pause when fullscreen',
  'Otomatis': 'Automatic',
  'Wallpaper berbeda tiap layar': 'A different wallpaper per screen',
  'Terbatas': 'Limited',
  'Profil susunan multi-display': 'Multi-display layout profiles',
  'Satu klik': 'One click',
  'Katalog wallpaper bawaan': 'Built-in wallpaper catalog',
  'Pemulihan otomatis setelah Explorer restart': 'Automatic recovery after an Explorer restart',
  'Harga': 'Price',
  'Angka performa diukur pada Windows 11 build 26200, Ryzen 5 5600, GeForce GTX 1080, tiga monitor 1080p dengan tiga wallpaper H.264 berjalan bersamaan. CPU dibaca dari Performance Monitor, waktu resume dari log aplikasi yang mencatat setiap perubahan status playback.':
    'Performance figures were measured on Windows 11 build 26200, Ryzen 5 5600, GeForce GTX 1080, with three 1080p monitors running three H.264 wallpapers at once. CPU was read from Performance Monitor; resume time from the app\'s own log, which records every playback state change.',

  // ── download ──
  'Pasang dalam satu menit': 'Installed in a minute',
  'Aplikasinya sama di ketiga format. Yang berbeda hanya cara memasangnya.':
    'The app is identical in all three formats. Only the way you install it differs.',
  'Paling mudah': 'Easiest',
  'Installer': 'Installer',
  'Untuk pemakaian sehari-hari. Pasang seperti aplikasi Windows biasa, lengkap dengan pintasan Start Menu dan opsi berjalan otomatis saat Windows menyala.':
    'For everyday use. Installs like any Windows application, with a Start Menu shortcut and the option to start automatically when Windows does.',
  'Paket MSIX': 'MSIX package',
  'Kalau kamu ingin Windows yang mengurusnya: pasang lewat Microsoft Store atau sideload, dan pembaruan serta penghapusan ditangani sistem.':
    'If you would rather Windows manage it: install from the Microsoft Store or sideload it, and updates and removal are handled by the system.',
  'Portable': 'Portable',
  'Untuk mencoba dulu tanpa mengubah apa pun, atau dibawa di flashdisk. Ekstrak ke folder mana saja lalu jalankan; tidak ada yang ditulis ke registry.':
    'To try it without changing anything, or to carry on a flash drive. Extract it anywhere and run it; nothing is written to the registry.',
  'tanpa registry': 'no registry',
  'Windows dan prosesor 64-bit (x64)': 'Windows and a 64-bit processor (x64)',
  'WebView2 Runtime, sudah tersedia di Windows 11 dan Windows 10 yang terbarui':
    'WebView2 Runtime, already present on Windows 11 and up-to-date Windows 10',

  // ── FAQ ──
  'Pertanyaan yang paling sering masuk': 'Questions we get most',
  'Apakah LumaWall memberatkan komputer?': 'Does LumaWall weigh down my computer?',
  'Tidak. Video didecode di GPU, bukan CPU. Pada tiga wallpaper 1080p yang berjalan bersamaan, proses utama LumaWall memakai CPU di bawah 1%. Aplikasi juga berhenti melakukan decode saat layar terkunci, layar mati, atau saat komputer memakai baterai.':
    'No. Video is decoded on the GPU, not the CPU. With three 1080p wallpapers running at once, LumaWall\'s main process stays under 1% CPU. It also stops decoding when the screen is locked, the display is off, or the machine is on battery.',
  'Bagaimana kalau saya membuka game fullscreen?': 'What happens when I open a fullscreen game?',
  'Wallpaper di monitor yang tertutup game langsung berhenti, dan berjalan lagi begitu game ditutup atau diminimize. Pause bekerja per layar, jadi monitor lain tetap beranimasi seperti biasa.':
    'The wallpaper on the monitor the game covers stops immediately, and runs again the moment the game closes or is minimised. Pause works per screen, so your other monitors keep animating as usual.',
  'Apakah ikon desktop saya masih bisa diklik?': 'Can I still click my desktop icons?',
  'Bisa. LumaWall menempatkan wallpaper di lapisan desktop Windows, tepat di bawah ikon. Ia bukan jendela overlay, jadi tidak mencuri klik, tidak muncul di Alt+Tab, dan tidak menghalangi apa pun.':
    'Yes. LumaWall puts the wallpaper on Windows\' desktop layer, directly beneath the icons. It is not an overlay window, so it never steals a click, never appears in Alt+Tab, and blocks nothing.',
  'Bisa memakai video saya sendiri?': 'Can I use my own videos?',
  'Bisa. Klik Tambah lalu pilih file video atau gambar milikmu: mp4, m4v, wmv, avi, mov, webm, jpg, png, atau bmp. Untuk setiap unduhan dari katalog, LumaWall juga menyimpan file':
    'Yes. Click Add and pick your own video or image: mp4, m4v, wmv, avi, mov, webm, jpg, png or bmp. For every catalog download, LumaWall also saves a',
  'Apakah LumaWall gratis?': 'Is LumaWall free?',
  'Gratis, tanpa iklan, dan tanpa versi berbayar. Tidak ada batas jumlah wallpaper maupun jumlah monitor.':
    'Free, with no ads and no paid tier. There is no limit on the number of wallpapers or monitors.',
  'Bagaimana cara menghapusnya?': 'How do I uninstall it?',
  'Lewat Settings › Apps seperti aplikasi Windows biasa, atau lewat uninstaller di folder pemasangan. Semua berkas ada di satu folder dan bisa dihapus seluruhnya tanpa sisa di registry.':
    'Through Settings › Apps, like any Windows application, or through the uninstaller in the install folder. Every file lives in one folder and can be removed completely, with nothing left in the registry.',
  'Berapa monitor yang bisa dipakai sekaligus?': 'How many monitors can I use at once?',
  'Tidak ada batas di sisi aplikasi. Setiap monitor yang terdeteksi Windows mendapat wallpaper, pengaturan, dan status pause-nya sendiri, dan susunannya bisa disimpan sebagai profil.':
    'There is no limit on the app\'s side. Every monitor Windows detects gets its own wallpaper, its own settings and its own pause state, and the arrangement can be saved as a profile.',
  'Bagaimana kalau Explorer restart atau crash?': 'What if Explorer restarts or crashes?',
  'LumaWall memeriksa kesehatannya setiap dua detik. Kalau jendela desktop hilang, wallpaper dibangun ulang dan dipasang kembali secara otomatis dalam waktu kurang dari empat detik, tanpa menjalankan ulang aplikasi.':
    'LumaWall checks its own health every two seconds. If the desktop window disappears, the wallpaper is rebuilt and reapplied automatically in under four seconds, without restarting the app.',
  'Apakah ada iklan atau pelacakan?': 'Are there ads or tracking?',
  'Tidak ada iklan, akun, maupun telemetri. Satu-satunya koneksi internet terjadi saat kamu sendiri mengunduh wallpaper dari katalog.':
    'No ads, no account, no telemetry. The only internet connection happens when you yourself download a wallpaper from the catalog.',
  'Bahasa apa saja yang didukung?': 'Which languages are supported?',
  'Antarmuka tersedia dalam Bahasa Indonesia, English, 简体中文, dan 日本語. Kamu bisa menggantinya kapan saja lewat pemilih bahasa di bar atas.':
    'The interface is available in English, Bahasa Indonesia, 简体中文 and 日本語. You can switch at any time from the language picker in the top bar.',

  // ── close ──
  'Wallpaper yang bergerak, komputer yang tetap tenang': 'Wallpaper that moves, a computer that stays quiet',
  'Gratis, tanpa iklan, dan kamu akan lupa kalau ini sedang berjalan.':
    'Free, no ads, and you will forget it is running.',
  'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB': 'Version 4.0.1 · Windows 10 / 11 · x64 · 14.5 MB',
  'Wallpaper hidup untuk Windows. Video diproses chip grafis, dan wallpaper berhenti sendiri saat kamu membuka aplikasi fullscreen.':
    'Live wallpaper for Windows. Video is decoded on the GPU, and the wallpaper pauses itself when you open a fullscreen app.',

  // ── footer ──
  'Xinet Group': 'Xinet Group',
  'Pertanyaan': 'Questions',
  'Kode sumber': 'Source code',
  'Laporkan masalah': 'Report an issue',
  'LumaWall adalah perangkat lunak gratis dan terbuka.': 'LumaWall is free and open-source software.',
  'Tanpa membebani komputer.': 'Without weighing down your PC.',
  'Buka game fullscreen, dan wallpaper di layar itu berhenti sendiri.':
    'Open a fullscreen game, and the wallpaper on that screen stops on its own.',
  'Kenapa LumaWall': 'Why LumaWall',
  'Performa terukur': 'Measured performance',
  'Tanpa LumaWall': 'Without LumaWall',
  'Versi sekarang': 'Current version',
  'Hemat saat layar tidak terlihat': 'Saves when the screen is not visible',
  'Perpindahan loop tanpa kedip': 'Loop transitions without a flicker',
  'Tampilan asli': 'Native display',
  'NVDEC / DXVA2': 'NVDEC / DXVA2',
  'Microsoft Store': 'Microsoft Store',
  'Tanpa install': 'No installation',
  'Syarat sistem': 'System requirements',
  'Windows 10 versi 1809 atau lebih baru, atau Windows 11':
    'Windows 10 version 1809 or newer, or Windows 11',
  'Versi 4.0.1 · Windows 10 / 11 · x64 · 14,5 MB': 'Version 4.0.1 · Windows 10 / 11 · x64 · 14.5 MB',
  'Unduh gratis': 'Download free',
  'Unduh installer': 'Download installer',
  'Unduh MSIX': 'Download MSIX',
  'Unduh portable': 'Download portable',
  'Unduh untuk Windows': 'Download for Windows',
  'Wallpaper hidup di setiap monitor.': 'Live wallpaper on every monitor.',
  'Wallpaper video diproses chip grafis, bukan CPU. Berhenti otomatis saat game fullscreen, jalan lagi begitu game ditutup. 5.000+ wallpaper, gratis, tanpa iklan.':
    'Video wallpaper decoded on the GPU, not the CPU. Pauses itself when a game goes fullscreen, resumes the moment it closes. 5,000+ wallpapers, free, no ads.',
};


export const TABLES = { id: ID, en: EN };

export function t(key, lang = 'id') {
  const table = TABLES[lang] || ID;
  return table[key] !== undefined ? table[key] : key;
}

export function keys() {
  return Object.keys(ID);
}
