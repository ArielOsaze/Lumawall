/* Form pembelian LumaWall, dengan QRIS tampil di halaman ini sendiri.

   Yang penting di berkas ini: tidak ada kunci rahasia apa pun. Seluruh
   panggilan iPaymu terjadi di server (/api/checkout), dan halaman ini hanya
   mengirim nama + email + nomor WA lalu menerima kode QR untuk ditampilkan.

   Kenapa QR di sini, bukan pengalihan ke halaman iPaymu:

   Begitu pembeli berpindah ke situs lain, halaman ini kehilangan
   kemampuannya memberi tahu apa pun. Pembeli yang sudah membayar tidak tahu
   pembayarannya sudah masuk, dan ia hanya bisa menebak sambil memuat ulang
   halaman sukses. Dengan QR di sini, halaman bisa memeriksa sendiri dan
   menampilkan tautan unduhan begitu pembayaran terkonfirmasi - tanpa pembeli
   perlu melakukan apa pun selain membayar. */

(function () {
  'use strict';

  var form = document.getElementById('buy-form');
  if (!form) return;

  var submit = document.getElementById('buy-submit');
  var alertBox = document.getElementById('buy-alert');
  var note = document.getElementById('buy-note');

  var formCard = document.getElementById('form-card');
  var qrCard = document.getElementById('qr-card');
  var doneCard = document.getElementById('done-card');

  var qrImg = document.getElementById('qr-img');
  var qrLoading = document.getElementById('qr-loading');
  var qrTotal = document.getElementById('qr-total');
  var qrOrder = document.getElementById('qr-order');
  var qrExpired = document.getElementById('qr-expired');
  var qrStatusText = document.getElementById('qr-status-text');
  var qrStatus = document.getElementById('qr-status');
  var doneDownload = document.getElementById('done-download');

  // Panel pembayaran: QR untuk QRIS, nomor Virtual Account untuk transfer bank.
  var qrPanel = document.getElementById('qr-panel');
  var vaPanel = document.getElementById('va-panel');
  var qrJudul = document.getElementById('qr-judul');
  var vaBank = document.getElementById('va-bank');
  var vaNomor = document.getElementById('va-nomor');
  var vaAtasNama = document.getElementById('va-atas-nama');
  var vaJumlah = document.getElementById('va-jumlah');
  var vaSalin = document.getElementById('va-salin');

  // Pemilih cara bayar. Kanal disimpan di sini supaya nilainya ikut terkirim
  // bersama formulir.
  var kanalGrid = document.getElementById('kanal-grid');
  var bankField = document.getElementById('bank-field');
  var bankGrid = document.getElementById('bank-grid');
  var kanalDipilih = 'qris';
  var bankDipilih = 'bca';

  var fields = {
    nama: { input: document.getElementById('f-nama'), err: document.getElementById('e-nama') },
    email: { input: document.getElementById('f-email'), err: document.getElementById('e-email') },
    wa: { input: document.getElementById('f-wa'), err: document.getElementById('e-wa') }
  };

  // Pemeriksaan status berjalan berkala. Intervalnya 4 detik: cukup cepat
  // supaya pembeli tidak menunggu setelah membayar, cukup jarang supaya tidak
  // membebani server kalau halaman dibiarkan terbuka lama.
  var JEDA_PERIKSA_MS = 4000;

  // Batas waktu pemeriksaan otomatis. Setelah ini halaman berhenti bertanya
  // sendiri dan menampilkan tombol periksa manual - halaman yang bertanya
  // selamanya adalah halaman yang membebani server tanpa hasil.
  var BATAS_PERIKSA_MS = 30 * 60 * 1000;

  var timer = null;
  var mulaiPeriksa = 0;
  var orderCode = null;

  function rupiah(n) {
    var angka = Number(n) || 0;
    return 'Rp' + angka.toLocaleString('id-ID');
  }

  function showError(key, message) {
    var f = fields[key];
    if (!f) return;
    if (message) {
      f.err.textContent = message;
      f.err.hidden = false;
      f.input.setAttribute('aria-invalid', 'true');
    } else {
      f.err.textContent = '';
      f.err.hidden = true;
      f.input.removeAttribute('aria-invalid');
    }
  }

  function clearErrors() {
    Object.keys(fields).forEach(function (k) { showError(k, ''); });
    alertBox.hidden = true;
  }

  function showAlert(message, ok) {
    alertBox.textContent = message;
    alertBox.className = ok ? 'buy-alert ok' : 'buy-alert';
    alertBox.hidden = false;
  }

  // ── pemilih cara bayar ─────────────────────────────────────────────────────
  //
  // Tombol dipakai, bukan <input type="radio">, karena tampilannya perlu
  // menampilkan ikon dan dua baris teks. Atribut role dan aria-checked dipasang
  // supaya pembaca layar tetap membacanya sebagai pilihan, bukan sebagai tombol
  // biasa yang tidak menjelaskan apa yang sedang dipilih.

  function tandaiRadio(kumpulan, terpilih) {
    for (var i = 0; i < kumpulan.length; i++) {
      var aktif = kumpulan[i] === terpilih;
      kumpulan[i].classList.toggle('aktif', aktif);
      kumpulan[i].setAttribute('aria-checked', aktif ? 'true' : 'false');
    }
  }

  function pilihKanal(nilai) {
    kanalDipilih = nilai;
    tandaiRadio(kanalGrid.querySelectorAll('.kanal'),
                kanalGrid.querySelector('[data-kanal="' + nilai + '"]'));

    // Daftar bank hanya muncul untuk transfer bank. Menampilkannya sejak awal
    // membuat pembeli mengira bank harus dipilih meskipun ia memakai QRIS.
    var transfer = nilai !== 'qris';
    bankField.hidden = !transfer;
    if (transfer) {
      // Bank yang dipilih mengikuti tombol "Transfer Bank" yang ditekan: yang
      // pertama kali terpilih adalah BCA, kecuali pembeli sudah memilih bank
      // lain sebelumnya.
      pilihBank(bankDipilih);
    }
  }

  function pilihBank(nilai) {
    bankDipilih = nilai;
    tandaiRadio(bankGrid.querySelectorAll('.bank'),
                bankGrid.querySelector('[data-bank="' + nilai + '"]'));
  }

  if (kanalGrid) {
    kanalGrid.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('.kanal') : null;
      if (t) pilihKanal(t.getAttribute('data-kanal'));
    });
    // Tombol harus bisa dipilih dengan papan ketik, karena tidak semua orang
    // memakai tetikus - dan pembaca layar menggerakkan fokus dengan panah.
    kanalGrid.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      var semua = Array.prototype.slice.call(kanalGrid.querySelectorAll('.kanal'));
      var i = semua.indexOf(document.activeElement);
      if (i === -1) return;
      e.preventDefault();
      var berikut = semua[(i + (e.key === 'ArrowRight' ? 1 : semua.length - 1)) % semua.length];
      berikut.focus();
      pilihKanal(berikut.getAttribute('data-kanal'));
    });
  }

  if (bankGrid) {
    bankGrid.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('.bank') : null;
      if (t) pilihBank(t.getAttribute('data-bank'));
    });
  }

  // Pemeriksaan di peramban hanya untuk memberi balasan cepat. Pemeriksaan yang
  // benar-benar mengikat ada di server: apa pun yang dikirim dari sini bisa
  // dimanipulasi, jadi server memeriksa ulang semuanya.
  function validate() {
    var ok = true;
    var nama = fields.nama.input.value.trim();
    var email = fields.email.input.value.trim();
    var wa = fields.wa.input.value.trim();

    if (nama.length < 2) { showError('nama', 'Name must be at least 2 characters.'); ok = false; }
    else showError('nama', '');

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      showError('email', 'That email address does not look right.');
      ok = false;
    } else showError('email', '');

    if (wa) {
      var digits = wa.replace(/[^\d]/g, '');
      if (digits.length < 9 || digits.length > 15) {
        showError('wa', 'That WhatsApp number does not look right.');
        ok = false;
      } else showError('wa', '');
    } else showError('wa', '');

    return ok;
  }

  // ── tampilkan panel ────────────────────────────────────────────────────────
  //
  // Hanya satu panel yang terlihat pada satu waktu. Kartu formulir, kartu QR,
  // dan kartu selesai tidak pernah muncul bersamaan - kalau muncul bersamaan,
  // pembeli melihat dua instruksi yang saling bertentangan.

  function tampilkan(panel) {
    [formCard, qrCard, doneCard].forEach(function (kartu) {
      if (kartu) kartu.hidden = (kartu !== panel);
    });
  }

  function formatWaktu(nilai) {
    if (!nilai) return '\u2014';
    // iPaymu mengirim "2026-10-01 00:06:22" (waktu Jakarta, tanpa zona).
    // Ditampilkan apa adanya dengan penanda WIB, bukan dikonversi: mengubahnya
    // ke zona peramban bisa membuat waktunya terlihat mundur beberapa jam, dan
    // pembeli yang melihat waktunya sudah lewat akan mengira QR-nya mati.
    var m = String(nilai).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
    if (!m) return String(nilai);
    var bulan = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    return parseInt(m[3], 10) + ' ' + bulan[parseInt(m[2], 10) - 1] + ' ' + m[4] + ':' + m[5] + ' WIB';
  }

  function bukaPembayaran(data) {
    orderCode = data.order;
    qrOrder.textContent = data.order;

    // Harga dan biaya dipisah, bukan digabung di sebelah total.
    //
    // Versi pertama menulis "Rp10.249 (+Rp249 biaya)" di sebelah kanan judul,
    // dan di layar sempit teks itu melipat sehingga kata "total" jatuh ke baris
    // berikutnya - terlihat berantakan tepat di angka yang paling diperhatikan
    // pembeli. Sekarang totalnya sendirian di atas, dan rinciannya turun ke
    // daftar di bawah, tempat baris baru tidak merusak apa pun.
    //
    // Pembeli yang melihat angka berbeda antara halaman ini dan aplikasi
    // banknya akan mengira dirinya dikenai biaya tersembunyi, jadi rinciannya
    // tetap harus ada - hanya tempatnya yang dipindah.
    qrTotal.textContent = rupiah(data.total || data.amount);

    var hargaEl = document.getElementById('qr-harga');
    if (hargaEl) hargaEl.textContent = rupiah(data.amount);

    var biayaBaris = document.getElementById('qr-biaya-baris');
    var biayaEl = document.getElementById('qr-biaya');
    if (biayaBaris && biayaEl) {
      if (data.fee && data.fee > 0) {
        biayaEl.textContent = rupiah(data.fee);
        biayaBaris.hidden = false;
      } else {
        biayaBaris.hidden = true;
      }
    }

    qrExpired.textContent = formatWaktu(data.expiredAt);

    // ── dua jenis pembayaran, satu kartu ─────────────────────────────────────
    //
    // QRIS dan transfer bank meminta hal yang berbeda dari pembeli, jadi
    // panelnya berbeda. Yang ditentukan bukan tebakan dari ada-tidaknya nilai,
    // melainkan `jenis` dari server: kalau server bilang ini transfer bank,
    // yang ditampilkan adalah nomor rekening meskipun kebetulan ada juga nilai
    // QR di balasannya.
    var jenisVa = data.jenis === 'va';

    qrJudul.textContent = jenisVa
      ? 'Transfer to ' + (data.kanalLabel || 'bank')
      : 'Pay by QRIS';

    if (jenisVa) {
      qrPanel.hidden = true;
      vaPanel.hidden = false;

      vaBank.textContent = 'Virtual Account ' + (data.kanalLabel || '');
      vaNomor.textContent = data.nomorVa || '\u2014';
      vaAtasNama.textContent = data.namaVa || '\u2014';
      vaJumlah.textContent = rupiah(data.total || data.amount);

      // Nomor yang tidak ada berarti pembeli tidak punya cara membayar. Lebih
      // baik mengatakannya daripada menampilkan kotak kosong yang membuatnya
      // menunggu.
      if (!data.nomorVa) {
        vaNomor.textContent = 'Number unavailable';
        qrStatusText.textContent = 'The destination number was not received. Reload this page.';
      }
    } else {
      vaPanel.hidden = true;
      qrPanel.hidden = false;

      if (data.qrImage) {
        qrImg.onload = function () {
          qrLoading.hidden = true;
          qrImg.hidden = false;
        };
        // Kalau gambarnya gagal dimuat, jangan biarkan kotak kosong: pembeli
        // tidak punya cara membayar dan tidak tahu kenapa.
        qrImg.onerror = function () {
          qrLoading.textContent = 'Kode QR gagal dimuat. Muat ulang halaman ini.';
        };
        qrImg.src = data.qrImage;
        qrImg.hidden = true;
      } else if (data.qrString) {
        // Sebagian kanal hanya mengembalikan string QR, bukan gambar.
        qrLoading.hidden = true;
        qrImg.hidden = true;
        qrStatusText.textContent = 'Tunjukkan kode ini ke kasir: ' + data.qrString;
      } else {
        qrLoading.textContent = 'Kode QR tidak tersedia. Hubungi dukungan dengan kode pesananmu.';
      }
    }

    tampilkan(qrCard);
    mulaiPeriksa = Date.now();
    jadwalkan();
  }

  // Tombol salin nomor Virtual Account.
  //
  // Nomornya 16 digit dan harus diketik di aplikasi lain, jadi menyalinnya
  // adalah hal pertama yang dilakukan pembeli. Tanpa tombol ini ia mengetik
  // manual sambil berpindah aplikasi - dan satu digit salah berarti uangnya
  // masuk ke rekening orang lain.
  if (vaSalin) {
    vaSalin.addEventListener('click', function () {
      var teks = (vaNomor.textContent || '').trim();
      if (!teks || teks === '\u2014' || teks === 'Number unavailable') return;

      // API papan klip hanya tersedia di konteks aman (HTTPS atau localhost),
      // dan bisa ditolak izinnya. Keduanya ditangani: kalau gagal, nomornya
      // dipilih otomatis supaya pembeli bisa menekan Ctrl+C sendiri.
      var beres = function () {
        var label = vaSalin.querySelector('span');
        var asli = label.textContent;
        label.textContent = 'Copied';
        vaSalin.classList.add('berhasil');
        setTimeout(function () {
          label.textContent = asli;
          vaSalin.classList.remove('berhasil');
        }, 2000);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(teks).then(beres).catch(pilihManual);
      } else {
        pilihManual();
      }

      function pilihManual() {
        try {
          var r = document.createRange();
          r.selectNodeContents(vaNomor);
          var s = window.getSelection();
          s.removeAllRanges();
          s.addRange(r);
        } catch (e) { /* tidak bisa memilih: nomornya tetap terlihat */ }
      }
    });
  }

  function jadwalkan() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(periksa, JEDA_PERIKSA_MS);
  }

  function periksa() {
    if (!orderCode) return;

    if (Date.now() - mulaiPeriksa > BATAS_PERIKSA_MS) {
      qrStatus.classList.add('lama');
      qrStatusText.textContent =
        'Pemeriksaan otomatis berhenti setelah 30 menit. Kalau kamu sudah membayar, muat ulang halaman ini.';
      return;
    }

    fetch('/api/status-pembayaran?order=' + encodeURIComponent(orderCode), {
      headers: { Accept: 'application/json' }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.paid && data.downloadUrl) {
          selesai(data.downloadUrl);
          return;
        }
        jadwalkan();
      })
      .catch(function () {
        // Kegagalan jaringan bukan alasan untuk berhenti memeriksa: koneksi
        // yang tersendat sebentar akan pulih sendiri, dan pembayaran yang
        // sudah masuk tetap harus terlihat.
        jadwalkan();
      });
  }

  function selesai(downloadUrl) {
    if (timer) clearTimeout(timer);
    timer = null;

    // Kode pesanan disimpan supaya halaman sukses tetap bisa memuat status
    // kalau pembeli membuka tautannya di tab yang sama nanti.
    try { sessionStorage.setItem('lumawall_order', orderCode); } catch (e) { /* mode privat */ }

    doneDownload.href = downloadUrl;
    tampilkan(doneCard);

    // Fokus dipindahkan ke tautan unduhan. Pembeli yang memakai pembaca layar
    // tidak akan tahu panelnya berubah kalau fokusnya dibiarkan di tempat lama.
    doneDownload.focus();
  }

  // ── kirim formulir ─────────────────────────────────────────────────────────

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    clearErrors();

    if (!validate()) {
      var firstBad = form.querySelector('[aria-invalid="true"]');
      if (firstBad) firstBad.focus();
      return;
    }

    var payload = {
      nama: fields.nama.input.value.trim(),
      email: fields.email.input.value.trim(),
      wa: fields.wa.input.value.trim(),
      // Untuk transfer bank, yang dikirim adalah kode banknya. Untuk QRIS,
      // 'qris'. Server memvalidasi ulang nilai ini - kanal yang tidak dikenal
      // jatuh ke QRIS, bukan membuat transaksi gagal.
      kanal: kanalDipilih === 'qris' ? 'qris' : bankDipilih
    };

    submit.disabled = true;
    submit.textContent = 'Preparing QR\u2026';
    note.textContent = 'Contacting the payment provider, please wait a moment.';

    fetch('/api/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (data) { return { status: res.status, data: data }; });
      })
      .then(function (result) {
        var data = result.data || {};

        // Server belum dikonfigurasi (503). Ini terjadi selama pemasangan awal
        // dan bukan kesalahan pembeli - jadi jangan tampilkan pesan kesalahan
        // yang membuat mereka mengira situsnya rusak. Arahkan ke Microsoft
        // Store, yang menjual produk yang sama dan tidak bergantung pada
        // konfigurasi server ini.
        if (result.status === 503) {
          submit.disabled = false;
          submit.textContent = 'Pay now';
          note.textContent = 'Payment on this site is being set up.';
          showAlert(
            'Payment on this site is not active yet. In the meantime you can ' +
            'buy from the Microsoft Store for Rp18,000 - Rp2,000 cheaper ' +
            'and no waiting. Opening the Microsoft Store in a new tab.',
            false
          );
          window.open('https://apps.microsoft.com/detail/9PN82QJLV05B', '_blank', 'noopener');
          return;
        }

        if (!data.ok || !data.order) {
          throw new Error(data.error || 'Could not open the payment page. Please try again.');
        }

        // Panel pembayaran dipakai kalau ada yang bisa ditampilkan: kode QR
        // untuk QRIS, nomor Virtual Account untuk transfer bank. Kalau iPaymu
        // mengembalikan tautan (kanal lama), tautan itu tetap dihormati - lebih
        // baik pembeli sampai ke halaman pembayaran daripada tidak bisa
        // membayar sama sekali.
        if (data.jenis === 'va' || data.qrImage || data.qrString) {
          bukaPembayaran(data);
          return;
        }
        if (data.paymentUrl) {
          showAlert('Redirecting to the payment page\u2026', true);
          window.location.href = data.paymentUrl;
          return;
        }

        throw new Error('Pembayaran tidak mengembalikan cara bayar. Coba lagi.');
      })
      .catch(function (err) {
        submit.disabled = false;
        submit.textContent = 'Pay now';
        note.textContent = 'Payment happens right on this page.';
        showAlert(err.message || 'Something went wrong. Please try again.', false);
      });
  });

  // Kalau pembeli kembali dengan ?batal=1, beri tahu dengan tenang bahwa tidak
  // ada yang terpotong - kekhawatiran pertama orang yang membatalkan bayar.
  try {
    var params = new URLSearchParams(window.location.search);
    if (params.get('batal') === '1') {
      showAlert('Payment cancelled. Nothing was charged. You can try again any time.', false);
    }
  } catch (e) { /* URLSearchParams tidak ada: abaikan */ }
})();
