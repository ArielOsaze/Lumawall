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
    // TIDAK langsung ke iPaymu. Alasannya: iPaymu membatasi permintaan
    // berdasarkan alamat IP pengirim, dan Vercel keluar dari IP dinamis yang
    // tidak terdaftar. Permintaan langsung dari sini ditolak dengan
    // "Invalid IP" - terbukti dari log pesanan:
    //
    //     {"order_code":"LW-XXSX3D","status":"gagal",
    //      "catatan":"ipaymu gagal: Invalid IP"}
    //
    // Jembatan di server NexShop punya IP tetap yang sudah terdaftar, dan
    // sudah diuji dari sana: /balance menjawab Status 200.
    const site = cfg.siteUrl.replace(/\/$/, '');

    const muatan = {
      product: `${cfg.productName} - lisensi lifetime`,
      amount: amount,
      returnUrl: `${site}/sukses?order=${encodeURIComponent(orderCode)}`,
      cancelUrl: `${site}/beli?batal=1`,
      notifyUrl: `${site}/api/ipaymu-callback`,
      referenceId: orderCode,
      buyerName: nama,
      buyerEmail: email,
    };
    // iPaymu menolak body yang memuat kunci bernilai undefined, jadi nomor
    // WhatsApp hanya ditambahkan kalau memang diisi.
    if (wa) muatan.buyerPhone = wa;

    const upstream = await panggilJembatan(cfg, 'payment', muatan);

    if (!upstream.ok || !upstream.data || String(upstream.data.Status) !== '200') {
      const detail = upstream.data && (upstream.data.Message || upstream.data.message)
        ? String(upstream.data.Message || upstream.data.message)
        : `HTTP ${upstream.status}`;
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
    const session = (data.Data) || {};
    const sessionId = session.SessionID || session.sessionId || null;
    const paymentUrl = session.Url || session.url || null;

    if (!paymentUrl) {
      return json(res, 502, {
        ok: false,
        error: 'iPaymu tidak mengembalikan tautan pembayaran.',
        order: orderCode,
      });
    }

    await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
      method: 'PATCH',
      body: {
        sesi_pembayaran: sessionId,
        acuan_pembayaran: session.ReferenceId || orderCode,
      },
    }).catch(() => {});

    return json(res, 200, {
      ok: true,
      order: orderCode,
      amount,
      paymentUrl,
      sessionId,
    });
  } catch (err) {
    return fail(res, err);
  }
};
