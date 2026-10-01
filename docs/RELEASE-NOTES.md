# Catatan rilis LumaWall

Setiap versi punya satu bagian per bahasa. Yang ditulis hanya perubahan yang
dirasakan pemakai — bukan daftar berkas yang disentuh, dan bukan angka commit.

Nomor versi di sini harus sama dengan yang ada di `LumaWall/Properties/AssemblyInfo.cs`,
`msix/AppxManifest.xml`, dan nama berkas di `outputs/`.

---

## 4.5.13.0

### Bahasa Indonesia

**Jam sekarang benar-benar seperti iOS**

Ada dua sebab jamnya tidak seperti iOS, dan keduanya sudah diperbaiki.

Pertama, jamnya digambar dengan **halo gelap delapan arah** di sekeliling huruf.
Pada huruf tipis, halo itu menutupi area yang jauh lebih luas daripada goresan
hurufnya, sehingga mata membaca bayangannya sebagai bentuk huruf dan huruf
aslinya hanya tampak sebagai garis tipis di tengah - hasilnya jam terlihat
**berongga**, seperti huruf yang hanya digambar tepinya. Gaya yang justru paling
mirip iOS (ioslight) tidak masuk daftar gaya tipis, jadi gaya itulah yang paling
parah. Sekarang gaya tipis memakai bayangan rapat satu arah, dan hurufnya
tergambar penuh. Terukur dari pikselnya: kepadatan huruf naik dari berongga
menjadi 10-17%, sesuai huruf solid.

Kedua, jam gaya iOS **tidak pernah menampilkan detik** - jam layar kunci
menunjukkan jam dan menit saja. Sebelumnya detik ikut tampil karena pilihan
"Show seconds" masih dihormati untuk gaya iOS. Sekarang gaya iOS selalu
menampilkan jam:menit, sementara gaya lain (stopwatch, timer, papan skor) tetap
bisa menampilkan detik.

Seluruh gaya juga memakai satu keluarga font - Inter - dengan ketebalan yang
berbeda: ExtraLight untuk ioslarge, Light untuk ioslight dan iosstack, Medium
untuk iosdate. Terverifikasi dari aplikasinya sendiri, bukan dari nama berkas.

**Sakelar di Luma Studio sekarang berfungsi dan terbaca**

Sakelar on/off di halaman Studio tidak terbaca oleh alat bantu maupun alat
pemeriksa, karena jendela utamanya muncul di pohon aksesibilitas sebagai
"Hidden Window", bukan "LumaWall". Jendela yang tidak bisa ditemukan berarti
seluruh isinya tidak bisa diperiksa. Sekarang jendelanya punya nama aksesibilitas
yang benar, dan keenam sakelar terbaca lengkap dengan keadaannya.

Sakelarnya juga tidak lagi berupa kotak centang: template bawaannya diganti
sehingga yang tergambar hanya track dan knob, sementara status dan polanya tetap
dibawa - jadi screen reader tetap bisa membacanya.

**Halaman Studio tidak lagi berkedip saat sakelar diubah**

Sebelumnya setiap sakelar yang diubah membangun ulang seluruh halaman: seluruh
pohon elemen dibuang dan dibuat lagi, halaman berkedip, dan posisi gulir harus
dipulihkan. Untuk sakelar yang hanya mengubah nilai - tanggal, format 12 jam,
ping-pong, HDR - tidak ada satu pun elemen yang berubah, jadi membangun ulang
hanya menghasilkan kedipan. Sekarang halaman hanya dibangun ulang kalau
susunannya memang berubah.

**Tata letak dirapikan, terukur**

Ada 269 cacat tata letak yang ditemukan dan diperbaiki, diukur pada tiga lebar
jendela (920, 1200, 1580 piksel) untuk keenam halaman. Yang paling terlihat:

- Pratinjau wallpaper meluber keluar kartunya dan menutupi kartu di sebelahnya,
  karena gambar sengaja lebih besar daripada kotaknya tetapi tidak dipotong.
- Nama wallpaper panjang terpotong di tengah huruf tanpa tanda apa pun. Sekarang
  dipendekkan dengan elipsis, sehingga jelas namanya memang dipendekkan.
- "PRIMARY" pada kartu monitor terpotong menjadi "PRIMAR"; sekarang lencananya
  ditumpuk sehingga selalu utuh.
- Baris profil di halaman Displays memaksa semua isinya muat dalam satu baris;
  sekarang bisa turun ke baris berikutnya.
- Catatan di halaman Performa keluar dari kotaknya pada jendela sempit; sekarang
  mengisi lebar yang tersedia.
- Dua kolom Luma Studio tidak seimbang; sekarang kolom kiri sedikit lebih lebar
  sehingga keduanya selesai pada ketinggian yang hampir sama.

Tata letak diperiksa dengan alat baru (`--periksa-ui`) yang membaca ukuran
sebenarnya dari pohon elemen di dalam aplikasi, karena tangkapan layar tidak bisa
dipakai untuk jendela ini.

### English

**The clock now genuinely looks like iOS**

There were two reasons it did not, and both are fixed.

First, the clock was drawn with an **eight-direction dark halo** around the
glyphs. On thin letters that halo covers a far larger area than the strokes
themselves, so the eye reads the shadow as the letter shape and the real letter
only as a thin line down the middle - the clock looked **hollow**, like text
drawn as an outline. The style closest to iOS (ioslight) was missing from the
thin-style list, so it was the worst affected. Thin styles now use a single
tight shadow and the letters render solid. Measured from the pixels: glyph
density rose from hollow to 10-17%, matching solid text.

Second, an iOS-style clock **never shows seconds** - the lock screen shows hours
and minutes. Seconds used to appear because the "Show seconds" option was still
honoured for iOS styles. iOS styles now always show hours:minutes, while other
styles (stopwatch, timer, scoreboard) can still show seconds.

Every style also uses one font family - Inter - at different weights: ExtraLight
for ioslarge, Light for ioslight and iosstack, Medium for iosdate. Verified from
the running application, not from filenames.

**The switches in Luma Studio now work and can be read**

The on/off switches on the Studio page could not be read by assistive tools or
checkers, because the main window appeared in the accessibility tree as
"Hidden Window" rather than "LumaWall". A window that cannot be found means
everything inside it cannot be inspected. The window now carries the correct
accessibility name, and all six switches read back fully with their state.

They are also no longer checkboxes: the built-in template is replaced so only
the track and knob are drawn, while the state and pattern are still carried - so
a screen reader can still read them.

**The Studio page no longer flickers when a switch changes**

Every switch used to rebuild the whole page: the entire element tree was thrown
away and rebuilt, the page flickered, and the scroll position had to be restored.
For a switch that only changes a value - date, 12-hour format, ping-pong, HDR -
nothing in the layout changes, so rebuilding only produced a flicker. The page is
now rebuilt only when the layout genuinely changes.

**Layout tidied, measured**

269 layout defects were found and fixed, measured at three window widths (920,
1200, 1580 pixels) across all six pages. The most visible:

- Wallpaper previews overflowed their cards and covered the card next to them,
  because the image is deliberately larger than its box but was not clipped.
- Long wallpaper names were cut mid-letter with no indication. They are now
  shortened with an ellipsis, so it is clear the name was abbreviated.
- "PRIMARY" on the monitor card was cut to "PRIMAR"; the badge is now stacked so
  it always fits.
- The profile row on the Displays page forced everything onto one line; it can
  now wrap.
- The note on the Performance page escaped its box at narrow widths; it now
  fills the available width.
- Luma Studio's two columns were unbalanced; the left column is now slightly
  wider so both finish at nearly the same height.

Layout is checked by a new tool (`--periksa-ui`) that reads real measurements
from the element tree inside the application, because screenshots cannot be used
for this window.

---

## 4.5.12.0

### Bahasa Indonesia

**Video disesuaikan dengan tiap monitor**

Video yang jauh lebih besar daripada layarnya sekarang diperkecil otomatis
untuk monitor itu. Sebuah video 4K di layar 1080p memaksa GPU men-decode empat
kali piksel yang bisa ditampilkan, lalu membuang tiga perempatnya saat
menskalakan - dan itulah yang membuat satu layar terasa berat sementara layar
lain ringan. Berkas asli Anda tidak pernah disentuh; salinannya dibuat di folder
cache. Terukur: 4K menjadi 1920p, dan pemakaian decoder turun dari 22% menjadi
di bawah 5%.

**Font jam seperti iOS**

Seluruh gaya jam sekarang memakai satu keluarga font - Inter - dengan ketebalan
yang berbeda-beda, dari ExtraLight yang tipis seperti layar kunci iOS sampai
SemiBold untuk kartu widget. Sebelumnya setiap gaya memakai font sistem yang
berbeda, sehingga terlihat seperti beberapa font yang ditempel menjadi satu.

**Halaman Monitor sekarang jelas**

Dulu hanya ada "Apply" dan "Stop" tanpa keterangan. Sekarang: pilih wallpaper
untuk monitor ini, jeda monitor ini saja (layar lain tetap berjalan), atur warna
dan bentuk, dan lepas dengan konfirmasi. Setiap tombol menjelaskan dirinya.

**Perbaikan lain**

Berkas halaman yang menumpuk (1099 berkas) sekarang dibersihkan otomatis, dan
sisa proses WebView2 dari restart lama (761 MB) tidak lagi tertinggal.

### English

**Videos matched to each monitor**

A video far larger than its screen is now scaled down for that monitor. A 4K
video on a 1080p display forces the GPU to decode four times the pixels it can
show, then discard three quarters of them rescaling - which is why one screen
felt heavy while the others stayed light. Your original file is never touched;
a copy is made in a cache folder. Measured: 4K becomes 1920p, and decoder usage
drops from 22% to under 5%.

**iOS-style clock font**

Every clock style now uses one font family - Inter - at different weights, from
ExtraLight as thin as the iOS lock screen up to SemiBold for the widget card.
Previously each style used a different system font, which read as several fonts
pasted together.

**The Displays page is now clear**

It used to have "Apply" and "Stop" with no explanation. Now: choose a wallpaper
for this display, pause just this display (the others keep running), tune colour
and framing, and detach with a confirmation. Each button explains itself.

**Other fixes**

Accumulated page files (1099 of them) are now cleaned up automatically, and
leftover WebView2 processes from old restarts (761 MB) are no longer left behind.

---

## 4.5.11.0

### Bahasa Indonesia

**Wallpaper berhenti saat aplikasi fullscreen, dan lanjut seketika saat keluar**

Pemutaran sekarang benar-benar berhenti saat ada aplikasi fullscreen, dan lanjut
dalam hitungan milidetik begitu aplikasinya tidak fullscreen lagi. Diukur dari
aplikasinya sendiri: perintah jeda tercatat, tidak ada putaran video yang selesai
selama jeda, dan frame pertama muncul 3-29 milidetik setelah perintah lanjut.
Sebelumnya jeda ini bisa tertunda sampai 40 detik.

**Halaman Displays menunjukkan keadaan sebenarnya**

Setiap monitor sekarang menampilkan status (Active/Empty) dan ringkasan
pengaturannya sendiri - filter, kecerahan, saturasi, fit, kecepatan. Pengaturan
itu sudah ada dan bisa diubah di Luma Studio, tetapi tidak terlihat di halaman
yang memang tentang satu monitor. Nama wallpaper yang panjang kini punya
tooltip, dan kartu monitor tidak lagi memotong baris statusnya.

### English

**The wallpaper stops when an app goes fullscreen, and resumes the moment it leaves**

Playback now truly stops while an app is fullscreen, and resumes within
milliseconds of it leaving. Measured from the app itself: the pause is recorded,
no video loop completes during the pause, and the first frame arrives 3-29 ms
after the resume. Previously this could be delayed by up to 40 seconds.

**The Displays page shows what is actually happening**

Each monitor now shows its state (Active/Empty) and a summary of its own
settings - filter, brightness, saturation, fit, speed. Those settings existed and
were editable in Luma Studio, but were invisible on the one page about a single
monitor. Long wallpaper names now have a tooltip, and the monitor card no longer
clips its status row.

### 中文

**应用全屏时壁纸停止，退出时立即恢复**

应用全屏时播放会真正停止，退出后几毫秒内恢复。测量数据来自应用本身：暂停被记录，暂停期间没有任何视频循环完成，恢复后第一帧在 3-29 毫秒内出现。此前这一延迟最长可达 40 秒。

**显示器页面显示真实状态**

每个显示器现在都会显示状态（Active/Empty）及其自身设置的摘要——滤镜、亮度、饱和度、适配方式、速度。这些设置本就存在并可在 Luma Studio 中修改，却在这个专门针对单个显示器的页面上不可见。长壁纸名称现在有提示框，显示器卡片也不再裁切状态行。

### 日本語

**アプリが全画面のとき壁紙は停止し、解除した瞬間に再開します**

全画面中は再生が本当に停止し、解除後は数ミリ秒で再開します。アプリ自身の記録による測定：一時停止が記録され、一時停止中に動画ループが一度も完了せず、再開後 3〜29 ミリ秒で最初のフレームが表示されます。以前は最大 40 秒遅れることがありました。

**ディスプレイページが実際の状態を表示**

各モニターに状態（Active/Empty）とその設定の要約（フィルター、明るさ、彩度、フィット、速度）が表示されるようになりました。これらの設定は以前から存在し Luma Studio で編集できましたが、モニター単体についてのこのページでは見えませんでした。長い壁紙名にはツールチップが付き、カードが状態行を切り取ることもなくなりました。

---

## 4.5.10.0

### Bahasa Indonesia

**Wallpaper kembali seketika setelah keluar dari aplikasi fullscreen**

Setelah menutup game atau aplikasi fullscreen, desktop bisa tetap hitam sampai
**40 detik**. Penyebabnya bukan lambatnya memuat ulang: saat wallpaper dijeda,
Chromium diminta melepas memorinya, dan halaman videonya ikut kehilangan
kemampuan menjalankan skrip. Perintah "lanjut" yang dikirim setelah itu tidak
dijalankan oleh apa pun.

Yang membuatnya lama adalah cara aplikasi mengetahuinya. Pemeriksaan kesehatan
halaman berjalan setiap 20 detik dan baru membangun ulang halaman setelah **dua**
kegagalan berturut-turut — jadi halaman yang mati saat fullscreen menunggu 40
detik sebelum ada yang memperbaikinya.

Sekarang:

- memori dikembalikan **sebelum** perintah lanjut dikirim, bukan sesudahnya
- halaman diperiksa **tepat pada saat lanjut**, bukan menunggu jadwal
- satu kegagalan sudah cukup pada saat itu, karena tidak ada pergantian halaman
  yang sedang berlangsung

Hasilnya: wallpaper kembali dalam **0,2 detik**.

**Perbaikan lain**

- Halaman pembelian dan status pesanan punya menu navigasi di layar kecil.
  Sebelumnya seluruh tautan hilang di HP, sehingga halaman pembayaran tidak punya
  jalan kembali ke halaman utama.
- Bilah navigasi dirapikan: enam tautan datar menjadi dua menu bertingkat dan
  satu tautan, sehingga tidak lagi penuh.

### English

**The wallpaper comes back immediately after leaving a fullscreen app**

After closing a game or a fullscreen app, the desktop could stay black for up to
**40 seconds**. The cause was not slow loading: while the wallpaper is stopped,
Chromium is asked to release memory, and the video page loses the ability to run
its own script. The "resume" command sent afterwards is then carried out by
nothing at all.

What made it slow was how the app found out. The page's health check runs every
20 seconds and only rebuilds the page after **two** consecutive failures — so a
page that died during fullscreen waited 40 seconds before anything repaired it.

Now:

- memory is restored **before** the resume command is sent, not after
- the page is checked **at the moment of resume**, not on the next scheduled pass
- a single failure is enough at that moment, because no page change is in flight

The result: the wallpaper returns in **0.2 seconds**.

**Other fixes**

- The checkout and order-status pages have a navigation menu on small screens.
  Previously every link disappeared on a phone, leaving the payment page with no
  way back to the main page.
- The navigation bar was tidied: six flat links became two grouped menus and one
  link, so it is no longer crowded.

---

## 4.5.9.0

### Bahasa Indonesia

**Wallpaper tidak lagi menghitam saat dihentikan lalu dipasang ulang**

Menghentikan wallpaper lalu memasangnya kembali menyisakan layar hitam yang
lumayan lama. Penyebabnya bukan lambatnya pemuatan: tombol Hentikan menutup
jendela wallpaper, dan jendela itu satu-satunya yang menggambar di desktop. Jadi
layarnya benar-benar kosong sampai wallpaper berikutnya selesai dibangun.

Sekarang Hentikan tidak menutup jendelanya. Videonya dijeda dan frame terakhir
tetap di layar, sehingga tidak ada satu pun saat desktop dibiarkan kosong.
Memasang ulang wallpaper yang sama juga langsung melanjutkan pemutaran, bukan
membiarkannya beku.

**Wallpaper gambar tidak lagi hilang di Windows 11**

Wallpaper berupa gambar tidak muncul sama sekali di Windows 11 — layarnya hitam,
sementara semua catatan di log menyebut wallpaper sudah siap. Ada tiga sebab
yang bertumpuk, dan ketiganya sudah diperbaiki:

- Desktop Windows 11 adalah desktop "raised", yang hanya mau menampilkan jendela
  dengan gaya berlapis. Gaya itu sebelumnya dipasang hanya pada satu jalur yang
  cuma berjalan sekali; sekarang dipasang setiap kali dan dilepas lagi saat
  wallpaper video mengambil alih, karena jendela berlapis mengganggu WebView2.
- Jendela berlapis tanpa nilai transparansi bersifat tembus pandang sepenuhnya,
  jadi gambar yang sudah dilukis dengan benar tetap tidak terlihat. Nilainya kini
  ditetapkan.
- Penjagaan yang seharusnya memutuskan "sudah siap dipasang" hanya berlaku untuk
  wallpaper video, sehingga untuk wallpaper gambar tidak pernah dijalankan sama
  sekali — jendelanya tetap berukuran 16x16 di luar layar.

**Wallpaper tidak lagi terpotong di layar 1366x768**

Jendela wallpaper yang sudah menempel ke desktop tidak pernah diperiksa ukurannya
lagi. Kalau ukurannya menyimpang, ukuran yang salah itu bertahan selamanya, dan
di layar 1366x768 hasilnya terlihat sebagai wallpaper yang terpotong. Ukurannya
sekarang ditegakkan pada setiap pemeriksaan.

**Perpindahan antara wallpaper gambar dan video tidak lagi menghitam**

Saat beralih dari gambar ke video, gambar lama dibuang lebih dulu, dan jendela
video belum sempat dibangun — jadi layarnya kosong selama beberapa detik.
Sebaliknya juga sama. Sekarang yang lama tetap dipertahankan sampai yang baru
benar-benar punya sesuatu untuk ditampilkan.

### English

**Wallpapers no longer go black when stopped and applied again**

Stopping a wallpaper and applying one again left the screen black for a
noticeably long time. The cause was not slow loading: the Stop button closed the
wallpaper window, and that window is the only thing drawing on the desktop — so
the screen was genuinely empty until the next wallpaper finished building.

Stop no longer closes the window. Playback pauses and the last frame stays on
screen, so the desktop is never left uncovered. Applying the same wallpaper again
also resumes playback immediately instead of leaving it frozen.

**Image wallpapers no longer disappear on Windows 11**

Image wallpapers did not appear at all on Windows 11 — the screen stayed black
while every log line said the wallpaper was ready. Three causes were stacked on
top of each other, and all three are fixed:

- The Windows 11 desktop is a "raised" desktop, which only composites layered
  windows. That style was applied on a single path that runs once; it is now
  applied on every pass, and removed again when a video wallpaper takes over,
  because a layered window interferes with WebView2.
- A layered window with no transparency value is fully see-through, so a
  correctly painted image stayed invisible. The value is now set.
- The guard that decides "ready to attach" only ever held for video wallpapers,
  so for images it never ran at all — the window stayed 16x16 and off-screen.

**Wallpapers are no longer cropped on 1366x768 screens**

A wallpaper window that was already attached to the desktop was never checked
for size again. Once its size drifted, the wrong size persisted forever, which on
a 1366x768 screen shows up as a cropped wallpaper. The size is now enforced on
every check.

**Switching between image and video wallpapers no longer goes black**

Switching from an image to a video threw the image away first, before the video
window existed — leaving the screen empty for several seconds. The reverse was
the same. The old content is now kept until the new content actually has
something to show.

---

## 4.5.8.0

### Bahasa Indonesia

**Wallpaper tidak lagi hitam setelah keluar dari aplikasi fullscreen**

Ini perbaikan yang paling lama ditunggu. Setelah menutup game atau aplikasi
fullscreen, desktop sempat hitam selama satu sampai dua menit. Yang hitam bukan
videonya — videonya tetap didekode, dan log mencatat setiap frame kembali
normal. Yang berhenti bekerja adalah komposisi desktop Windows.

Selama aplikasi fullscreen berjalan, Windows berhenti mengomposisi desktop sama
sekali. Saat aplikasi ditutup, Windows meminta jendela desktop menggambar ulang,
dan permintaan itulah yang tidak pernah dijawab. Penyebabnya satu pilihan di
mesin browser: LumaWall mematikannya agar Chromium tidak menganggap wallpaper
sedang tersembunyi dan memperlambatnya sendiri — tetapi pilihan yang sama juga
membuat Chromium tidak melihat ada perubahan untuk ditanggapi.

Sekarang LumaWall yang memaksa gambar ulang itu sendiri, pada saat wallpaper
dilanjutkan. Hasilnya: wallpaper kembali dalam **0,4 detik**, bukan satu sampai
dua menit. Perbaikannya dijalankan dua kali — sekali segera, sekali 450 ms
kemudian — karena percobaan pertama bisa mendarat saat Windows masih berpindah
mode.

Hanya wallpaper yang benar-benar dijeda yang digambar ulang. Wallpaper yang
sedang berjalan tidak terusik.

**Perbaikan lain**

- Layar utama kembali beranimasi saat nama berkas wallpaper mengandung karakter
  tidak biasa. Sebelumnya monitor itu dilewati tanpa satu baris log pun.
- Widget jam tidak pernah menutupi aplikasi lagi. Ia menempel di desktop,
  setara dengan wallpaper.
- Pemilih penempatan jam tidak lagi menendang halaman ke atas saat dipilih.
- Tepi jendela tidak berkedip saat berpindah dari aplikasi fullscreen.

### English

**The wallpaper no longer goes black after closing a fullscreen app**

This is the fix that has been waited for the longest. After closing a game or a
fullscreen app, the desktop used to stay black for a minute or two. The video was
not the problem — it kept decoding, and the log recorded every frame returning to
normal. What stopped working was Windows' desktop composition.

While a fullscreen app runs, Windows stops compositing the desktop at all. When
the app closes, Windows asks the windows on the desktop to repaint — and that
request was never answered. The cause was one option in the browser engine:
LumaWall disables it so Chromium does not decide the wallpaper is hidden and
throttle itself, but the same option means Chromium sees no change to react to.

LumaWall now forces that repaint itself, at the moment the wallpaper resumes. The
wallpaper comes back in **0.4 seconds** instead of one to two minutes. The fix
runs twice — once immediately, once 450 ms later — because the first attempt can
land while Windows is still switching modes.

Only wallpapers that were actually paused are repainted. One that is already
running is never disturbed.

**Other fixes**

- The primary display animates again when a wallpaper filename contains unusual
  characters. It used to be skipped without a single log line.
- The clock widget never covers your apps. It is parented to the desktop, level
  with the wallpaper.
- The clock placement picker no longer throws the page to the top when chosen.
- Window edges no longer flicker when leaving a fullscreen app.

### 简体中文

**关闭全屏应用后，壁纸不再变黑**

这是等待最久的修复。关闭游戏或全屏应用后，桌面会黑上一到两分钟。问题不在
视频——视频一直在解码，日志记录每一帧都恢复正常。停止工作的是 Windows 的桌面
合成。

全屏应用运行时，Windows 完全停止合成桌面。应用关闭时，Windows 会请求桌面上的
窗口重绘——而这个请求从未得到响应。原因出在浏览器引擎的一个选项：LumaWall 关
闭它是为了不让 Chromium 认为壁纸被隐藏而自我限速，但同一个选项也让 Chromium
看不到任何需要响应的变化。

现在由 LumaWall 自己在壁纸恢复时强制重绘。壁纸在 **0.4 秒**内回来，而不是一到
两分钟。修复执行两次——一次立即，一次在 450 毫秒后——因为第一次可能落在 Windows
仍在切换模式的时刻。

只有真正被暂停的壁纸才会重绘。正在运行的壁纸不受影响。

**其他修复**

- 当壁纸文件名包含特殊字符时，主显示器恢复动画。此前该显示器会被跳过，连一行
  日志都没有。
- 时钟小组件不再遮挡你的应用。它附着在桌面上，与壁纸同级。
- 选择时钟位置时，页面不再跳到顶部。
- 离开全屏应用时，窗口边缘不再闪烁。

---

## 4.5.7.0

### Bahasa Indonesia

- Paket tervalidasi untuk pengiriman ke Microsoft Store.
- Layar utama kembali beranimasi saat nama berkas wallpaper mengandung karakter
  tidak biasa.
- Widget jam menempel di desktop, jadi tidak pernah menutupi aplikasi.
- Sepuluh gaya jam dengan font bergaya iOS yang berbeda.
- Peluncuran pertama lebih mulus dan pemakaian CPU saat menganggur lebih rendah.
- Tata letak Luma Studio lebih seimbang dan pemilih penempatan lebih jelas.

### English

- Package validated for Microsoft Store submission.
- The primary display animates again when a wallpaper filename contains unusual
  characters.
- The clock widget is parented to the desktop, so it never covers your apps.
- Ten clock styles with distinct iOS-style fonts.
- Smoother first launch and lower idle CPU usage.
- Balanced Luma Studio layout and a clearer placement picker.

### 简体中文

- 软件包已通过 Microsoft Store 提交验证。
- 修复壁纸文件名包含特殊字符时主显示器不动画的问题。
- 时钟小组件附着在桌面上，不会遮挡你的应用。
- 十种时钟样式，采用不同的 iOS 风格字体。
- 首次启动更流畅，空闲 CPU 占用更低。
- Luma Studio 布局更均衡，位置选择更清晰。
