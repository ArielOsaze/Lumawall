/* Form pembelian LumaWall.

   Yang penting di berkas ini: tidak ada kunci rahasia apa pun. Seluruh
   panggilan iPaymu terjadi di server (/api/checkout), dan halaman ini hanya
   mengirim nama + email + nomor WA lalu menerima tautan pembayaran. Kunci
   iPaymu yang bocor ke peramban sama dengan membiarkan siapa pun membuat
   transaksi atas namamu. */

(function () {
  'use strict';

  var form = document.getElementById('buy-form');
  if (!form) return;

  var submit = document.getElementById('buy-submit');
  var alertBox = document.getElementById('buy-alert');
  var note = document.getElementById('buy-note');

  var fields = {
    nama: { input: document.getElementById('f-nama'), err: document.getElementById('e-nama') },
    email: { input: document.getElementById('f-email'), err: document.getElementById('e-email') },
    wa: { input: document.getElementById('f-wa'), err: document.getElementById('e-wa') }
  };

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
    submit.textContent = 'Membuka pembayaran\u2026';
    note.textContent = 'Menghubungi iPaymu, mohon tunggu sebentar.';

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

        if (!data.ok || !data.paymentUrl) {
          throw new Error(data.error || 'Pembayaran tidak bisa dibuka. Coba lagi.');
        }

        // Simpan kode pesanan supaya halaman sukses tetap bisa memuat status
        // walau pengalihan iPaymu kehilangan parameter.
        try {
          sessionStorage.setItem('lumawall_order', data.order);
        } catch (e) { /* mode privat: tidak apa-apa, parameter URL masih ada */ }

        showAlert('Mengalihkan ke halaman pembayaran\u2026', true);
        window.location.href = data.paymentUrl;
      })
      .catch(function (err) {
        submit.disabled = false;
        submit.textContent = 'Bayar sekarang';
        note.textContent = 'Kamu akan diarahkan ke halaman pembayaran iPaymu.';
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
