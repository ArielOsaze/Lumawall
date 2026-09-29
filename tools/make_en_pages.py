#!/usr/bin/env python3
"""Buat versi Inggris dari halaman beli + sukses, beserta skripnya.

Pendekatan: salin berkas Indonesia lalu ganti teksnya. Bukan tulis ulang dari
nol, karena struktur, kelas CSS, dan atribut keamanan harus identik di kedua
bahasa - kalau ditulis ulang, cepat atau lambat keduanya menyimpang dan salah
satu versi kehilangan perbaikan.

Dua hal yang ditangani di sini:

  1. Teks di HTML terpotong baris, jadi spasi di dalam berkas tidak sama dengan
     spasi di frasa. Pencocokan menormalkan setiap rentetan spasi menjadi satu
     spasi lebih dulu.
  2. Sebagian teks ada di berkas JavaScript. Berkas itu ikut dikonversi, karena
     kalau tidak halaman Inggris menampilkan pesan kesalahan berbahasa Indonesia.

Pasangan frasa dikelompokkan per berkas tujuan. Sebelumnya semuanya diterapkan
ke setiap berkas, sehingga frasa milik halaman sukses dilaporkan "tidak
ditemukan" saat memproses halaman beli - padahal itu wajar. Pengelompokan ini
membuat laporan benar-benar berarti: yang dilaporkan hanya frasa yang seharusnya
ada di berkas itu tetapi hilang.

Jalankan: python tools/make_en_pages.py
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent / 'site'

# ══════════════════════════════════════════════════════════════════════════════
# Halaman beli (site/beli/index.html)
# ══════════════════════════════════════════════════════════════════════════════
BUY = [
    ('<title>Beli LumaWall - Rp20.000 sekali bayar</title>',
     '<title>Buy LumaWall - Rp20,000 one-time</title>'),
    ('Beli LumaWall Rp20.000 sekali bayar, lisensi lifetime. Bayar lewat QRIS, transfer bank, atau e-wallet. Tautan unduhan terbit otomatis setelah pembayaran.',
     'Buy LumaWall for Rp20,000 one-time, lifetime licence. Pay with QRIS, bank transfer, or e-wallet. Your download link is issued automatically after payment.'),
    ('Beli LumaWall - Rp20.000 sekali bayar', 'Buy LumaWall - Rp20,000 one-time'),
    ('Lisensi lifetime, tanpa langganan. Tautan unduhan terbit otomatis setelah pembayaran.',
     'Lifetime licence, no subscription. Your download link is issued automatically after payment.'),
    ('Rp20.000 sekali bayar, lisensi lifetime. Lebih murah Rp18.000 di Microsoft Store.',
     'Rp20,000 one-time, lifetime licence. Rp18,000 on the Microsoft Store.'),
    ('<a href="../#features">Fitur</a>', '<a href="../#features">Features</a>'),
    ('<a href="../#performance">Performa</a>', '<a href="../#performance">Performance</a>'),
    ('<a href="../#download">Unduh</a>', '<a href="../#download">Download</a>'),
    ('<a href="../#download" class="btn btn-ghost btn-sm">Lihat dulu</a>',
     '<a href="../#download" class="btn btn-ghost btn-sm">See it first</a>'),
    ('<a href="../en/buy/" class="lang">EN</a>', '<a href="../beli/" class="lang">ID</a>'),
    ('<span class="eyebrow">Pembelian</span>', '<span class="eyebrow">Checkout</span>'),
    ('Satu kali bayar,<br>dipakai selamanya', 'Pay once,<br>keep it forever'),
    ('Rp20.000 untuk lisensi lifetime. Tanpa langganan, tanpa iklan, tanpa batas jumlah wallpaper maupun monitor. Tautan unduhan terbit otomatis begitu pembayaran terkonfirmasi.',
     'Rp20,000 for a lifetime licence. No subscription, no ads, no limit on the number of wallpapers or monitors. Your download link is issued the moment your payment is confirmed.'),
    ('22.233 wallpaper, 100% bergerak dan HD', '22,233 wallpapers, 100% animated and HD'),
    ('Video diproses GPU, CPU tetap di bawah 1%', 'Video decoded on the GPU, CPU stays under 1%'),
    ('Berhenti sendiri saat game fullscreen', 'Stops itself when a game goes fullscreen'),
    ('Timer &amp; Luma Studio, bebas diatur', 'Timer &amp; Luma Studio, fully adjustable'),
    ('Pembaruan versi berikutnya gratis', 'Every future version included'),
    ('<b>Lebih murah Rp18.000</b> kalau memasang dari Microsoft Store &mdash; hemat Rp2.000. Windows yang mengurus pemasangan dan pembaruannya.',
     '<b>Rp18,000 cheaper</b> if you install from the Microsoft Store &mdash; save Rp2,000. Windows handles the install and the updates for you.'),
    ('>Buka Microsoft Store &rarr;</a>', '>Open Microsoft Store &rarr;</a>'),
    ('<span class="buy-amount">Rp20.000</span>', '<span class="buy-amount">Rp20,000</span>'),
    ('<span class="buy-per">sekali bayar</span>', '<span class="buy-per">one-time</span>'),
    ('<span class="field-label">Nama lengkap</span>', '<span class="field-label">Full name</span>'),
    ('placeholder="Nama kamu"', 'placeholder="Your name"'),
    ('<span class="field-hint">Untuk mencocokkan pesananmu kalau tautan unduhan perlu diterbitkan ulang.</span>',
     '<span class="field-hint">Used to match your order if the download link ever needs to be reissued.</span>'),
    ('<span class="field-label">Nomor WhatsApp <span class="opt">(opsional)</span></span>',
     '<span class="field-label">WhatsApp number <span class="opt">(optional)</span></span>'),
    ('<b>Rp20.000</b>', '<b>Rp20,000</b>'),
    ('Bayar sekarang\n        </button>', 'Pay now\n        </button>'),
    ('Kamu akan diarahkan ke halaman pembayaran iPaymu. QRIS, transfer bank, dan e-wallet tersedia.',
     'You will be taken to the iPaymu payment page. QRIS, bank transfer, and e-wallet are all available.'),
    ('<span class="eyebrow">Cara kerjanya</span>', '<span class="eyebrow">How it works</span>'),
    ('Empat langkah, selesai', 'Four steps, done'),
    ('<h3 class="h3">Isi data</h3>', '<h3 class="h3">Enter your details</h3>'),
    ('<p>Nama dan email. Tidak perlu membuat akun.</p>',
     '<p>Name and email. No account to create.</p>'),
    ('<h3 class="h3">Bayar Rp20.000</h3>', '<h3 class="h3">Pay Rp20,000</h3>'),
    ('<p>QRIS, transfer bank, atau e-wallet lewat iPaymu.</p>',
     '<p>QRIS, bank transfer, or e-wallet through iPaymu.</p>'),
    ('<h3 class="h3">Tautan terbit otomatis</h3>', '<h3 class="h3">Link issued automatically</h3>'),
    ('<p>Begitu pembayaran terkonfirmasi, halaman unduhan terbuka sendiri.</p>',
     '<p>The moment payment clears, the download page opens by itself.</p>'),
    ('<h3 class="h3">Pasang dan pakai</h3>', '<h3 class="h3">Install and go</h3>'),
    ('<p>Satu berkas installer, sekitar satu menit.</p>',
     '<p>One installer file, about a minute.</p>'),
    ('<span class="eyebrow">Pertanyaan</span>', '<span class="eyebrow">Questions</span>'),
    ('Yang sering ditanyakan', 'Frequently asked'),
    ('Kenapa Rp20.000 di sini, tapi Rp18.000 di Microsoft Store?',
     'Why Rp20,000 here but Rp18,000 on the Microsoft Store?'),
    ('Microsoft Store memotong biaya distribusi yang lebih kecil daripada biaya pemrosesan pembayaran di situs ini, jadi kami bisa menjual lebih murah di sana. Kalau tidak masalah memasang lewat Store, ambil yang Rp18.000 &mdash; produknya persis sama.',
     'The Microsoft Store takes a smaller cut than this site\u2019s payment processing costs, so we can sell it cheaper there. If installing through the Store is fine for you, take the Rp18,000 one &mdash; it is the exact same product.'),
    ('Apakah ada biaya bulanan?', 'Is there a monthly fee?'),
    ('Tidak. Sekali bayar Rp20.000 untuk lisensi lifetime, termasuk semua pembaruan versi berikutnya.',
     'No. Rp20,000 once for a lifetime licence, including every future version.'),
    ('Berapa kali tautan unduhannya bisa dipakai?', 'How many times can the download link be used?'),
    ('Tiga kali, selama 72 jam, dan hanya dari satu alamat IP. Batasnya longgar untuk pemakaian wajar (unduhan terputus, antivirus memblokir, salah simpan) tetapi tidak cukup untuk dibagikan ke orang lain. Kalau kamu berganti jaringan atau butuh tautan baru, hubungi dukungan dengan kode pesananmu.',
     'Three times, within 72 hours, and only from one IP address. That is roomy for normal use (an interrupted download, an antivirus block, a mis-saved file) but not enough to share around. If you change networks or need a fresh link, contact support with your order code.'),
    ('Metode pembayaran apa saja yang tersedia?', 'Which payment methods are available?'),
    ('QRIS, transfer bank (virtual account), dan e-wallet seperti GoPay, OVO, dan DANA. Semuanya lewat iPaymu.',
     'QRIS, bank transfer (virtual account), and e-wallets such as GoPay, OVO and DANA. All handled by iPaymu.'),
    ('Bagaimana kalau saya butuh bantuan?', 'What if I need help?'),
    ('Hubungi <a href="https://wa.me/6282224293639" target="_blank" rel="noopener">WhatsApp dukungan</a> dengan menyertakan kode pesanan (format <code>LW-XXXXXX</code>).',
     'Message <a href="https://wa.me/6282224293639" target="_blank" rel="noopener">support on WhatsApp</a> and include your order code (format <code>LW-XXXXXX</code>).'),
]

# ══════════════════════════════════════════════════════════════════════════════
# Halaman sukses (site/sukses/index.html)
# ══════════════════════════════════════════════════════════════════════════════
SUCCESS = [
    ('<title>Pesanan LumaWall</title>', '<title>Your LumaWall order</title>'),
    ('Status pesanan LumaWall dan tautan unduhannya.',
     'Your LumaWall order status and download link.'),
    ('<a href="../#features">Fitur</a>', '<a href="../#features">Features</a>'),
    ('<a href="../#performance">Performa</a>', '<a href="../#performance">Performance</a>'),
    ('<a href="../#download">Unduh</a>', '<a href="../#download">Download</a>'),
    ('<a href="../en/buy/" class="lang">EN</a>', '<a href="../beli/" class="lang">ID</a>'),
    ('<a href="../" class="btn btn-ghost btn-sm">Beranda</a>',
     '<a href="../" class="btn btn-ghost btn-sm">Home</a>'),
    ('Memeriksa pesanan&hellip;', 'Checking your order&hellip;'),
    ('Sebentar, kami sedang mencocokkan pembayaranmu dengan iPaymu.',
     'One moment while we match your payment with iPaymu.'),
    ('Pembayaran belum terkonfirmasi', 'Payment not confirmed yet'),
    ('Kalau kamu baru saja membayar, tunggu sebentar lalu muat ulang halaman ini. Konfirmasi dari bank biasanya masuk dalam beberapa detik, tetapi bisa sampai satu menit pada jam sibuk.',
     'If you have just paid, give it a moment and reload this page. Bank confirmations usually land within seconds, but can take up to a minute at busy times.'),
    ('id="btn-reload">Periksa lagi</button>', 'id="btn-reload">Check again</button>'),
    ('class="btn btn-ghost" target="_blank" rel="noopener">Hubungi dukungan</a>',
     'class="btn btn-ghost" target="_blank" rel="noopener">Contact support</a>'),
    ('Kode pesanan: <code id="order-waiting">&mdash;</code>',
     'Order code: <code id="order-waiting">&mdash;</code>'),
    ('Pembayaran diterima', 'Payment received'),
    ('Terima kasih! Tautan unduhanmu sudah siap. Simpan halaman ini sebelum menutup tab, karena tautannya tidak dikirim lewat email.',
     'Thank you! Your download link is ready. Keep this page before you close the tab, because the link is not sent by email.'),
    ('Unduh LumaWall', 'Download LumaWall'),
    ('Salin tautan unduhan', 'Copy download link'),
    ('>Tersalin<', '>Copied<'),
    ('Tautan ini hanya berlaku dari jaringan yang kamu pakai sekarang, maksimal <b id="warn-uses">3</b> kali unduh dalam <b id="warn-hours">72</b> jam. Kalau berpindah jaringan atau tautannya sudah habis, hubungi dukungan dengan kode pesanan di bawah.',
     'This link only works from the network you are on now, for up to <b id="warn-uses">3</b> downloads within <b id="warn-hours">72</b> hours. If you change networks or the link runs out, contact support with the order code below.'),
    ('Kode pesanan: <code id="order-paid">&mdash;</code>',
     'Order code: <code id="order-paid">&mdash;</code>'),
    ('Sudah pernah mengunduh dan butuh bantuan?', 'Already downloaded and need help?'),
    ('Tautan unduhan tidak bisa dipindahkan ke perangkat atau jaringan lain. Kalau kamu ganti jaringan, atau unduhanmu terputus sampai batasnya habis, hubungi <a href="https://wa.me/6282224293639" target="_blank" rel="noopener">WhatsApp dukungan</a> dengan kode pesanan di atas &mdash; kami terbitkan tautan baru.',
     'The download link cannot be moved to another device or network. If you change networks, or your download was interrupted until the limit ran out, message <a href="https://wa.me/6282224293639" target="_blank" rel="noopener">support on WhatsApp</a> with the order code above &mdash; we will issue a new link.'),
    ('Pesanan tidak ditemukan', 'Order not found'),
    ('Kami tidak menemukan pesanan dengan kode itu. Pastikan tautannya utuh, atau hubungi dukungan dengan kode pesananmu.',
     'We could not find an order with that code. Check that the link is complete, or contact support with your order code.'),
    ('<a href="../beli/" class="btn btn-primary">Coba beli lagi</a>',
     '<a href="../buy/" class="btn btn-primary">Try buying again</a>'),
    ('<a href="../privacy/">Privasi</a>', '<a href="../privacy/">Privacy</a>'),
    ('Rp20.000 sekali bayar, lisensi lifetime. Lebih murah Rp18.000 di Microsoft Store.',
     'Rp20,000 one-time, lifetime licence. Rp18,000 on the Microsoft Store.'),
]

# ══════════════════════════════════════════════════════════════════════════════
# assets/js/buy.js
# ══════════════════════════════════════════════════════════════════════════════
BUY_JS = [
    ("submit.textContent = 'Membuka pembayaran\\u2026';", "submit.textContent = 'Opening payment\\u2026';"),
    ("note.textContent = 'Menghubungi iPaymu, mohon tunggu sebentar.';",
     "note.textContent = 'Contacting iPaymu, one moment.';"),
    ("showError('nama', 'Nama minimal 2 huruf.');", "showError('nama', 'Name must be at least 2 characters.');"),
    ("showError('email', 'Alamat email belum benar.');", "showError('email', 'That email address does not look right.');"),
    ("showError('wa', 'Nomor WhatsApp belum benar.');", "showError('wa', 'That WhatsApp number does not look right.');"),
    ("data.error || 'Pembayaran tidak bisa dibuka. Coba lagi.'",
     "data.error || 'Could not open the payment page. Please try again.'"),
    ("showAlert('Mengalihkan ke halaman pembayaran\\u2026', true);",
     "showAlert('Redirecting to the payment page\\u2026', true);"),
    ("submit.textContent = 'Bayar sekarang';", "submit.textContent = 'Pay now';"),
    ("note.textContent = 'Kamu akan diarahkan ke halaman pembayaran iPaymu.';",
     "note.textContent = 'You will be taken to the iPaymu payment page.';"),
    ("err.message || 'Terjadi kesalahan. Coba lagi.'", "err.message || 'Something went wrong. Please try again.'"),
    ("showAlert('Pembayaran dibatalkan. Tidak ada biaya yang terpotong. Kamu bisa mencoba lagi kapan saja.', false);",
     "showAlert('Payment cancelled. Nothing was charged. You can try again any time.', false);"),
]

# ══════════════════════════════════════════════════════════════════════════════
# assets/js/success.js
# ══════════════════════════════════════════════════════════════════════════════
SUCCESS_JS = [
    ("fail('Tautan ini tidak memuat kode pesanan. Buka tautan yang diberikan iPaymu setelah pembayaran, atau hubungi dukungan.');",
     "fail('This link has no order code in it. Open the link iPaymu gave you after payment, or contact support.');"),
    ("d.error || 'Pesanan dengan kode itu tidak ditemukan.'", "d.error || 'No order found with that code.'"),
    ("d.error || 'Kode pesanan tidak sah.'", "d.error || 'That order code is not valid.'"),
    ("d.error || 'Kami tidak bisa memeriksa pesananmu sekarang. Coba muat ulang halaman ini.'",
     "d.error || 'We cannot check your order right now. Try reloading this page.'"),
    ("fail('Tidak bisa menghubungi server. Periksa koneksimu lalu muat ulang halaman ini.');",
     "fail('Could not reach the server. Check your connection and reload this page.');"),
    ("'LumaWall-Setup.exe \\u00b7 versi terbaru'", "'LumaWall-Setup.exe \\u00b7 latest version'"),
    ("setText('meta-uses', 'Tautan sudah kedaluwarsa');", "setText('meta-uses', 'Link expired');"),
    ("setText('meta-uses', 'Batas unduhan sudah habis');", "setText('meta-uses', 'Download limit reached');"),
    ("'Sisa ' + d.usesLeft + ' dari ' + d.maxUses + ' unduhan'", "'Uses left: ' + d.usesLeft + ' of ' + d.maxUses"),
    ("btn.textContent = d.expired ? 'Tautan kedaluwarsa' : 'Batas unduhan habis';",
     "btn.textContent = d.expired ? 'Link expired' : 'Download limit reached';"),
    ("window.prompt('Salin tautan ini:', url)", "window.prompt('Copy this link:', url)"),
]

# Sisa kata Indonesia yang menandakan konversi belum tuntas.
SISA = ['Rp20.000', 'sekali bayar', 'Bayar sekarang', 'Kode pesanan', 'Hubungi dukungan',
        'Pembelian', 'Cara kerjanya', 'Pertanyaan', 'Unduh', 'Fitur', 'Performa',
        'Nama kamu', 'Memeriksa pesanan', 'Pembayaran diterima', 'Tersalin',
        'Beranda', 'Lihat dulu', 'Tautan kedaluwarsa']

# (sumber, tujuan, pasangan, jalankan-pemeriksa-sisa, skrip-pengganti)
JOBS = [
    (ROOT / 'beli' / 'index.html', ROOT / 'en' / 'buy' / 'index.html', BUY, True,
     ('buy', 'buy-en')),
    (ROOT / 'sukses' / 'index.html', ROOT / 'en' / 'success' / 'index.html', SUCCESS, True,
     ('success', 'success-en')),
    (ROOT / 'assets' / 'js' / 'buy.js', ROOT / 'assets' / 'js' / 'buy-en.js', BUY_JS, False, None),
    (ROOT / 'assets' / 'js' / 'success.js', ROOT / 'assets' / 'js' / 'success-en.js', SUCCESS_JS, False, None),
]

# Kata yang sama di kedua bahasa, jadi bukan tanda konversi belum tuntas.
SAMA = {'Performa', 'Total', 'Email'}


def normalize(s):
    return re.sub(r'\s+', ' ', s).strip()


def replace_normalized(text, old, new):
    """Ganti `old` di `text`, tahan terhadap perbedaan spasi dan pemotongan baris."""
    target = normalize(old)
    if not target:
        return text, 0
    parts = [re.escape(p) for p in re.split(r'\s+', target)]
    pattern = re.compile(r'\s+'.join(parts))
    count = 0
    result = text
    while count < 50:
        m = pattern.search(result)
        if not m:
            break
        result = result[:m.start()] + new + result[m.end():]
        count += 1
    return result, count


def main():
    problems = 0

    for src, dst, pairs, check_leftover, script_swap in JOBS:
        if not src.exists():
            print('  ! sumber tidak ada: %s' % src)
            problems += 1
            continue

        text = src.read_text(encoding='utf-8')
        missed = []

        for old, new in pairs:
            text, n = replace_normalized(text, old, new)
            if n == 0:
                missed.append(normalize(old)[:72])

        # Halaman Inggris harus memuat skrip Inggris: kalau tidak, pesan
        # kesalahan dan tombolnya kembali berbahasa Indonesia.
        #
        # Nama berkasnya ber-hash (buy.bee1420957.js), jadi pencocokan harus
        # memakai pola, bukan nama tetap. Versi pertama mencari
        # "../assets/js/buy.js" - nama yang tidak ada lagi setelah cache-bust,
        # sehingga penggantiannya dilewati diam-diam dan halaman Inggris
        # memakai skrip Indonesia.
        if script_swap:
            base_old, base_new = script_swap  # mis. ('buy', 'buy-en')
            pola = re.compile(
                r'(/assets/js/)' + re.escape(base_old) + r'(\.[0-9a-f]{10})?\.js')
            if pola.search(text):
                # Ambil hash dari berkas versi Inggris yang ada di disk supaya
                # halaman menunjuk berkas yang benar-benar ada.
                js_dir = ROOT / 'site' / 'assets' / 'js'
                kandidat = sorted(js_dir.glob('%s.*.js' % base_new))
                if kandidat:
                    hash_baru = kandidat[0].name[len(base_new):-3]  # '.cc6df5b331'
                    text = pola.sub(r'\g<1>' + base_new + hash_baru + '.js', text)
                else:
                    text = pola.sub(r'\g<1>' + base_new + '.js', text)
            elif ('/assets/js/%s' % base_new) not in text:
                missed.append('tag skrip tidak ditemukan: %s' % base_old)

        # ── path aset harus absolut ──────────────────────────────────────────
        # Halaman Indonesia ada di /beli/ (satu tingkat), jadi "../assets/"
        # benar. Halaman Inggris ada di /en/buy/ (dua tingkat), jadi
        # "../assets/" menunjuk ke /en/assets/ yang tidak ada - dan hasilnya
        # halaman tanpa CSS sama sekali: teks polos, logo rusak, tata letak
        # hilang. Persis itu yang terjadi sebelum baris ini ada.
        #
        # Semua halaman Inggris lain di situs ini memakai path absolut
        # ("/assets/..."), jadi versi Inggris di sini disamakan. Itu juga
        # membuat kedalaman folder tidak lagi menjadi soal.
        if dst.parts and 'en' in dst.parts:
            before = text
            text = text.replace('"../assets/', '"/assets/')
            text = text.replace("'../assets/", "'/assets/")
            # Tautan antar-halaman juga ikut: dari /en/buy/ ke /en/ bukan "../".
            text = text.replace('href="../#', 'href="/en/#')
            text = text.replace('href="../"', 'href="/en/"')
            if text == before and '"/assets/' not in text:
                missed.append('tidak ada path aset yang perlu diperbaiki')

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding='utf-8')

        print('  %s -> %s' % (src.relative_to(ROOT), dst.relative_to(ROOT)))
        for m in missed:
            print('      ! tidak ditemukan: %s' % m)
        problems += len(missed)

        if check_leftover:
            for phrase in SISA:
                if phrase in SAMA:
                    continue
                if phrase in text:
                    print('      ! masih berbahasa Indonesia: %s' % phrase)
                    problems += 1

    print()
    if problems:
        print('  %d masalah - periksa daftar di atas.' % problems)
        return 1
    print('  semua halaman + skrip Inggris dibuat tanpa sisa teks Indonesia.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
