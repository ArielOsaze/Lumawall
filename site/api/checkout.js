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
const { config, clientIp, supabase, json, readBody, fail } = require('./_lib');

const IPAYMU_PRODUCTION = 'https://my.ipaymu.com/api/v2';
const IPAYMU_SANDBOX = 'https://sandbox.ipaymu.com/api/v2';

function newOrderCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // tanpa I,O,0,1 yang mudah tertukar
  let tail = '';
  const bytes = crypto.randomBytes(6);
  for (let i = 0; i < 6; i += 1) tail += alphabet[bytes[i] % alphabet.length];
  return `LW-${tail}`;
}

// Signature iPaymu v2. Yang ditandatangani adalah HASH SHA-256 dari body, bukan
// body mentah - ini yang membuat verifikasi gagal kalau memakai body apa adanya.
// Sudah diuji langsung ke endpoint produksi: bentuk inilah yang diterima.
function sign(method, va, body, apiKey) {
  const bodyHash = crypto.createHash('sha256').update(body, 'utf8').digest('hex');
  const payload = `${method}:${va}:${bodyHash}:${apiKey}`;
  return crypto.createHmac('sha256', apiKey).update(payload, 'utf8').digest('hex');
}

function timestamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return (
    `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}` +
    `${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
  );
}

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

    // ── panggil iPaymu ────────────────────────────────────────────────────────
    const isSandbox = String(cfg.ipaymuMode).toLowerCase() === 'sandbox';
    const base = isSandbox ? IPAYMU_SANDBOX : IPAYMU_PRODUCTION;
    const site = cfg.siteUrl.replace(/\/$/, '');

    const payload = {
      product: [`${cfg.productName} - lisensi lifetime`],
      qty: ['1'],
      price: [String(amount)],
      amount: String(amount),
      returnUrl: `${site}/sukses?order=${encodeURIComponent(orderCode)}`,
      cancelUrl: `${site}/beli?batal=1`,
      notifyUrl: `${site}/api/ipaymu-callback`,
      referenceId: orderCode,
      buyerName: nama,
      buyerEmail: email,
    };
    // iPaymu menolak body yang memuat kunci bernilai undefined, jadi nomor
    // WhatsApp hanya ditambahkan kalau memang diisi.
    if (wa) payload.buyerPhone = wa;

    const rawBody = JSON.stringify(payload);
    const ts = timestamp();
    const signature = sign('POST', cfg.ipaymuVa, rawBody, cfg.ipaymuKey);

    const upstream = await fetch(`${base}/payment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        va: cfg.ipaymuVa,
        signature,
        timestamp: ts,
      },
      body: rawBody,
    });

    const text = await upstream.text();
    let data = null;
    try { data = JSON.parse(text); } catch { data = null; }

    if (!upstream.ok || !data || String(data.Status) !== '200') {
      const detail = data && (data.Message || data.message) ? String(data.Message || data.message) : `HTTP ${upstream.status}`;
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
