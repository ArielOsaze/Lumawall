// POST /api/checkout — memulai pembelian LumaWall.
//
// Alur lengkapnya:
//   1. Pembeli mengisi nama + email + WhatsApp di halaman /beli
//   2. Endpoint ini membuat baris `orders` berstatus 'menunggu'
//   3. Endpoint ini memanggil iPaymu untuk membuat sesi pembayaran
//   4. Pembeli membayar lewat QRIS / VA / e-wallet
//   5. iPaymu memanggil /api/ipaymu-callback (webhook)
//   6. Webhook memverifikasi, menandai lunas, dan menerbitkan token unduhan
//   7. Halaman /sukses menampilkan tautan sekali pakai
//
// Yang TIDAK dilakukan endpoint ini: menerbitkan token. Token hanya lahir dari
// webhook yang sudah terverifikasi, sehingga tidak ada cara mendapatkan tautan
// unduhan tanpa pembayaran yang benar-benar tercatat di iPaymu.

const crypto = require('crypto');
const { config, clientIp, supabase, json, readBody, fail, panggilJembatan } = require('./_lib');

function newOrderCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // tanpa I,O,0,1 yang mudah tertukar
  let tail = '';
  const bytes = crypto.randomBytes(6);
  for (let i = 0; i < 6; i += 1) tail += alphabet[bytes[i] % alphabet.length];
  return `LW-${tail}`;
}

// Signature iPaymu v2 sekarang dihitung di jembatan (server NexShop), bukan di
// sini. Fungsi `sign` dan `timestamp` dipindahkan ke jembatan bersama seluruh
// panggilan iPaymu, karena hanya dari sana IP-nya terdaftar. Keduanya sengaja
// dihapus dari berkas ini supaya tidak ada dua salinan logika tanda tangan yang
// bisa saling menyimpang.

function validEmail(v) {
  return typeof v === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) && v.length <= 200;
}

function validName(v) {
  return typeof v === 'string' && v.trim().length >= 2 && v.trim().length <= 120;
}

function validPhone(v) {
  if (v === undefined || v === null || v === '') return true; // opsional
  const digits = String(v).replace(/[^\d]/g, '');
  return digits.length >= 9 && digits.length <= 15;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return json(res, 405, { ok: false, error: 'Gunakan POST.' });
  }

  try {
    const cfg = config();
    const body = await readBody(req);

    const nama = typeof body.nama === 'string' ? body.nama.trim() : '';
    const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
    const wa = typeof body.wa === 'string' ? body.wa.trim() : '';

    if (!validName(nama)) {
      return json(res, 400, { ok: false, error: 'Nama minimal 2 huruf.' });
    }
    if (!validEmail(email)) {
      return json(res, 400, { ok: false, error: 'Alamat email tidak sah.' });
    }
    if (!validPhone(wa)) {
      return json(res, 400, { ok: false, error: 'Nomor WhatsApp tidak sah.' });
    }

    const ip = clientIp(req);
    const orderCode = newOrderCode();
    const amount = cfg.price;

    // Simpan order lebih dulu. Kalau iPaymu gagal, baris ini tetap ada sebagai
    // jejak percobaan, dan statusnya tidak pernah naik ke 'dibayar' tanpa webhook.
    const inserted = await supabase('orders', {
      method: 'POST',
      headers: { Prefer: 'return=representation' },
      body: [{
        order_code: orderCode,
        product_code: cfg.productCode,
        nama_pembeli: nama,
        email_pembeli: email,
        whatsapp: wa || null,
        jumlah: amount,
        status: 'menunggu',
        catatan: `ip=${ip}`,
        kedaluwarsa_pada: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      }],
    });

    if (!Array.isArray(inserted) || !inserted.length) {
      throw Object.assign(new Error('Gagal menyimpan pesanan.'), { statusCode: 502 });
    }

    // ── panggil iPaymu lewat jembatan ─────────────────────────────────────────
    //
    // TIDAK langsung ke iPaymu. Ada dua alasan, dan keduanya ditemukan dengan
    // menguji, bukan dengan membaca dokumentasi:
    //
    //   1. iPaymu membatasi permintaan berdasarkan alamat IP pengirim, dan
    //      Vercel keluar dari IP dinamis yang tidak terdaftar. Permintaan
    //      langsung ditolak "Invalid IP".
    //   2. iPaymu juga membatasi DOMAIN pada returnUrl/notifyUrl/cancelUrl.
    //      Untuk akun ini hanya nexshop.cloud yang diterima; lumawall.xinet.id
    //      ditolak "Invalid domain". Jembatan mengganti alamat itu dengan
    //      domainnya sendiri lalu mengalihkan pembeli ke sini.
    //
    // Yang dipakai adalah `payment-direct`, BUKAN `payment`. Bedanya penting:
    // `payment` mengembalikan tautan ke halaman iPaymu dan pembeli meninggalkan
    // situs ini; `payment-direct` mengembalikan kode QR yang bisa ditampilkan di
    // halaman ini sendiri. Pembeli tidak pernah berpindah situs, jadi tidak ada
    // halaman pihak ketiga yang bisa membingungkan atau kehilangan jejak
    // pesanannya.
    const muatan = {
      amount: amount,
      referenceId: orderCode,
      buyerName: nama,
      buyerEmail: email,
      // QRIS dipilih karena satu-satunya kanal yang tidak butuh pembeli memilih
      // bank dulu, dan sudah diuji bekerja untuk akun ini.
      paymentMethod: 'qris',
      paymentChannel: 'qris',
    };
    // iPaymu menolak body yang memuat kunci bernilai undefined, jadi nomor
    // WhatsApp hanya ditambahkan kalau memang diisi.
    if (wa) muatan.buyerPhone = wa;

    const upstream = await panggilJembatan(cfg, 'payment-direct', muatan);

    if (!upstream.ok || !upstream.data || String(upstream.data.Status) !== '200') {
      // Detailnya diambil selengkap mungkin. Versi pertama hanya menyimpan
      // "HTTP 400", dan itu tidak cukup untuk tahu apa yang salah - pesan
      // sebenarnya dari iPaymu ada di dalam `data`, bukan di status HTTP.
      const detail = upstream.data
        ? (upstream.data.Message || upstream.data.message
           || (upstream.data.data && (upstream.data.data.Message || upstream.data.data.message))
           || JSON.stringify(upstream.data).slice(0, 300))
        : (upstream.error || `HTTP ${upstream.status}`);
      await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
        method: 'PATCH',
        body: { status: 'gagal', catatan: `ipaymu gagal: ${detail}`.slice(0, 500) },
      }).catch(() => {});
      return json(res, 502, {
        ok: false,
        error: 'Gagal membuka sesi pembayaran. Coba lagi sebentar lagi.',
        order: orderCode,
      });
    }

    const data = upstream.data;
    const sesi = data.Data || {};

    // Nomor transaksi dipakai untuk memeriksa status nanti. Tanpa ini halaman
    // tidak bisa tahu pembayaran sudah masuk, dan pembeli harus menunggu
    // halaman sukses memuat ulang sendiri.
    const transactionId = sesi.TransactionId || sesi.transactionId || null;
    const qrImage = sesi.QrImage || sesi.qrImage || null;
    const qrString = sesi.QrString || sesi.qrString || null;

    if (!transactionId) {
      await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
        method: 'PATCH',
        body: { status: 'gagal', catatan: 'ipaymu tidak mengembalikan TransactionId' },
      }).catch(() => {});
      return json(res, 502, {
        ok: false,
        error: 'iPaymu tidak mengembalikan nomor transaksi.',
        order: orderCode,
      });
    }

    await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
      method: 'PATCH',
      body: {
        sesi_pembayaran: sesi.SessionId || null,
        // Nomor transaksi disimpan di sini supaya halaman status bisa
        // memeriksanya tanpa memanggil iPaymu lagi dari sisi peramban - dan
        // tanpa membocorkan kredensial ke peramban.
        acuan_pembayaran: String(transactionId),
      },
    }).catch(() => {});

    return json(res, 200, {
      ok: true,
      order: orderCode,
      amount,
      // Jumlah yang benar-benar dibayar pembeli, termasuk biaya layanan kalau
      // ada. Ditampilkan terpisah supaya tidak ada kejutan di halaman QR.
      total: sesi.Total || amount,
      fee: sesi.Fee || 0,
      qrImage,
      qrString,
      channel: sesi.Channel || 'QRIS',
      expiredAt: sesi.Expired || null,
    });
  } catch (err) {
    return fail(res, err);
  }
};
