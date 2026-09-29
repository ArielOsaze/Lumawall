// GET /api/price — harga yang berlaku sekarang.
//
// Halaman beli memanggil ini supaya angka yang ditampilkan selalu sama dengan
// angka yang ditagih. Tanpa endpoint ini, harga di HTML dan harga di checkout
// adalah dua angka terpisah yang harus dijaga tetap cocok dengan tangan - dan
// begitu tanggal promo lewat, halaman akan tetap menampilkan Rp10.000
// sementara checkout sudah menagih Rp18.000.
//
// Jawabannya di-cache sangat singkat (60 detik). Tidak lebih lama dari itu:
// kalau cache-nya berumur jam, halaman bisa menampilkan harga promo sesaat
// setelah promo berakhir - dan pembeli yang melihat Rp10.000 lalu ditagih
// Rp18.000 punya alasan sah untuk marah.

const { currentPrice, json, fail } = require('./_lib');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return json(res, 405, { ok: false, error: 'Gunakan GET.' });
  }

  try {
    const h = currentPrice();

    res.setHeader('Cache-Control', 'public, max-age=60, s-maxage=60');

    return json(res, 200, {
      ok: true,
      // Harga yang berlaku sekarang, dalam rupiah.
      amount: h.amount,
      promo: h.promo,
      // Kedua angka selalu dikirim, bukan hanya yang berlaku: halaman perlu
      // menampilkan "Rp10.000, normal Rp18.000" selama promo, dan "Rp18.000"
      // saja setelahnya. Mengirim keduanya membuat halaman tidak perlu tahu
      // tanggalnya sendiri.
      promoPrice: h.promoPrice,
      normalPrice: h.normalPrice,
      storePrice: h.storePrice,
      promoEndsAt: h.promoEndsAt,
    });
  } catch (err) {
    return fail(res, err);
  }
};
