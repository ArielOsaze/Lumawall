/* Harga promo di halaman.

   Angka di HTML adalah tampilan, bukan kebenaran. Yang menagih adalah server,
   dan server bisa berubah tanpa deploy ulang - begitu tanggal promo lewat,
   /api/price langsung menjawab Rp18.000 sementara HTML masih berisi Rp10.000.

   Karena itu halaman ini mengambil harga yang berlaku dari server dan menimpa
   tampilannya. Tanpa langkah ini, pembeli yang membuka halaman pada 16 Oktober
   akan melihat Rp10.000 lalu ditagih Rp18.000 - dan itu alasan yang sah untuk
   marah, sekaligus alasan yang sah untuk menuntut harga yang tertera.

   Kalau permintaan gagal, angka di HTML dibiarkan apa adanya. Itu pilihan
   sadar: halaman yang menampilkan harga sedikit basi lebih baik daripada
   halaman yang menampilkan "Rp—" karena satu permintaan gagal. */

(function () {
  'use strict';

  // Semua elemen yang menampilkan harga promo diberi atribut data-price-promo,
  // dan yang menampilkan harga normal data-price-normal. Atributnya dipakai
  // alih-alih kelas CSS supaya perubahan harga tidak bergantung pada nama kelas
  // yang bisa berubah saat desainnya dirapikan.
  function formatRupiah(n) {
    return 'Rp' + Number(n).toLocaleString('id-ID');
  }

  function terapkan(h) {
    var promo = formatRupiah(h.promoPrice);
    var normal = formatRupiah(h.normalPrice);

    // Harga yang berlaku sekarang.
    document.querySelectorAll('[data-price]').forEach(function (el) {
      el.textContent = formatRupiah(h.amount);
    });

    // Harga normal - hanya ditampilkan sebagai pembanding selama promo.
    document.querySelectorAll('[data-price-normal]').forEach(function (el) {
      el.textContent = normal;
    });

    // Harga Microsoft Store tidak ikut promo; ia selalu Rp18.000.
    document.querySelectorAll('[data-price-store]').forEach(function (el) {
      el.textContent = formatRupiah(h.storePrice);
    });

    // Bagian yang hanya relevan selama promo (label "PROMO", hitungan hari).
    document.querySelectorAll('[data-promo-only]').forEach(function (el) {
      el.hidden = !h.promo;
    });

    // Bagian yang hanya relevan setelah promo berakhir.
    document.querySelectorAll('[data-after-promo]').forEach(function (el) {
      el.hidden = h.promo;
    });

    // Sisa hari promo, kalau elemennya ada.
    document.querySelectorAll('[data-promo-days]').forEach(function (el) {
      if (!h.promo) { el.textContent = ''; return; }
      var sisa = Math.ceil((new Date(h.promoEndsAt).getTime() - Date.now()) / 86400000);
      el.textContent = sisa > 0 ? String(sisa) : '0';
    });

    // Judul halaman ikut menyebut harga, jadi harus ikut berubah - kalau tidak,
    // hasil pencarian dan tab peramban menampilkan harga yang sudah lewat.
    document.title = document.title.replace(/Rp\s?[\d.,]+/g, formatRupiah(h.amount));
  }

  // Harga ditampilkan secepat mungkin. Menunggu DOMContentLoaded berarti
  // pembeli sempat melihat angka lama berkedip sebelum ditimpa.
  fetch('/api/price', { headers: { Accept: 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (h) {
      if (!h || !h.ok) return;
      terapkan(h);
    })
    .catch(function () {
      // Biarkan angka di HTML. Halaman tetap berfungsi; checkout tetap memakai
      // harga yang benar dari server.
    });
})();
