# Catatan rilis LumaWall

Setiap versi punya satu bagian per bahasa. Yang ditulis hanya perubahan yang
dirasakan pemakai — bukan daftar berkas yang disentuh, dan bukan angka commit.

Nomor versi di sini harus sama dengan yang ada di `LumaWall/Properties/AssemblyInfo.cs`,
`msix/AppxManifest.xml`, dan nama berkas di `outputs/`.

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
