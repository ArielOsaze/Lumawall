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

  // Pemeriksaan di peramban hanya untuk memberi balasan cepat. Pemeriksaan yang
  // benar-benar mengikat ada di server: apa pun yang dikirim dari sini bisa
  // dimanipulasi, jadi server memeriksa ulang semuanya.
  function validate() {
    var ok = true;
    var nama = fields.nama.input.value.trim();
    var email = fields.email.input.value.trim();
    var wa = fields.wa.input.value.trim();

    if (nama.length < 2) { showError('nama', 'Nama minimal 2 huruf.'); ok = false; }
    else showError('nama', '');

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      showError('email', 'Alamat email belum benar.');
      ok = false;
    } else showError('email', '');

    if (wa) {
      var digits = wa.replace(/[^\d]/g, '');
      if (digits.length < 9 || digits.length > 15) {
        showError('wa', 'Nomor WhatsApp belum benar.');
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

  function bukaQr(data) {
    orderCode = data.order;
    qrOrder.textContent = data.order;

    // Total ditampilkan lengkap dengan biaya layanan kalau ada. Pembeli yang
    // melihat angka berbeda antara halaman ini dan aplikasi banknya akan
    // mengira dirinya dikenai biaya tersembunyi.
    var total = data.total || data.amount;
    qrTotal.textContent = rupiah(total);
    if (data.fee && data.fee > 0) {
      qrTotal.textContent += ' (+' + rupiah(data.fee) + ' biaya)';
    }

    qrExpired.textContent = formatWaktu(data.expiredAt);

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
      // Sebagian kanal hanya mengembalikan string QR, bukan gambar. Stringnya
      // tetap ditampilkan supaya pembeli bisa menunjukkannya ke kasir.
      qrLoading.hidden = true;
      qrImg.hidden = true;
      qrStatusText.textContent = 'Tunjukkan kode ini ke kasir: ' + data.qrString;
    } else {
      qrLoading.textContent = 'Kode QR tidak tersedia. Hubungi dukungan dengan kode pesananmu.';
    }

    tampilkan(qrCard);
    mulaiPeriksa = Date.now();
    jadwalkan();
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
      wa: fields.wa.input.value.trim()
    };

    submit.disabled = true;
    submit.textContent = 'Menyiapkan QR\u2026';
    note.textContent = 'Menghubungi penyedia pembayaran, mohon tunggu sebentar.';

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
          submit.textContent = 'Bayar sekarang';
          note.textContent = 'Pembayaran lewat situs ini sedang disiapkan.';
          showAlert(
            'Pembayaran lewat situs ini belum aktif. Sementara itu kamu bisa ' +
            'membeli di Microsoft Store dengan harga Rp18.000 - lebih murah ' +
            'Rp2.000 dan tidak perlu menunggu. Buka Microsoft Store di tab baru.',
            false
          );
          window.open('https://apps.microsoft.com/detail/9PN82QJLV05B', '_blank', 'noopener');
          return;
        }

        if (!data.ok || !data.order) {
          throw new Error(data.error || 'Pembayaran tidak bisa dibuka. Coba lagi.');
        }

        // Panel QR dipakai kalau ada QR. Kalau iPaymu mengembalikan tautan
        // (kanal lama), tautan itu tetap dihormati - lebih baik pembeli sampai
        // ke halaman pembayaran daripada tidak bisa membayar sama sekali.
        if (data.qrImage || data.qrString) {
          bukaQr(data);
          return;
        }
        if (data.paymentUrl) {
          showAlert('Mengalihkan ke halaman pembayaran\u2026', true);
          window.location.href = data.paymentUrl;
          return;
        }

        throw new Error('Pembayaran tidak mengembalikan kode QR. Coba lagi.');
      })
      .catch(function (err) {
        submit.disabled = false;
        submit.textContent = 'Bayar sekarang';
        note.textContent = 'Pembayaran lewat QRIS, langsung di halaman ini.';
        showAlert(err.message || 'Terjadi kesalahan. Coba lagi.', false);
      });
  });

  // Kalau pembeli kembali dengan ?batal=1, beri tahu dengan tenang bahwa tidak
  // ada yang terpotong - kekhawatiran pertama orang yang membatalkan bayar.
  try {
    var params = new URLSearchParams(window.location.search);
    if (params.get('batal') === '1') {
      showAlert('Pembayaran dibatalkan. Tidak ada biaya yang terpotong. Kamu bisa mencoba lagi kapan saja.', false);
    }
  } catch (e) { /* URLSearchParams tidak ada: abaikan */ }
})();
