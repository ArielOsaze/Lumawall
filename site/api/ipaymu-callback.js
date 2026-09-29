// POST /api/ipaymu-callback — webhook dari iPaymu.
//
// Ini satu-satunya tempat token unduhan diterbitkan. Tidak ada endpoint lain
// yang boleh membuat token, karena satu-satunya bukti yang sah bahwa seseorang
// sudah membayar adalah panggilan ini, yang datang dari server iPaymu dan
// membawa signature yang bisa diverifikasi.
//
// Tiga lapis pemeriksaan, berurutan:
//
//   1. Signature HMAC. Dihitung ulang di sini memakai API key rahasia. Tanpa
//      kunci itu, penyerang tidak bisa memalsukan payload yang lolos.
//   2. Jumlah yang dibayar harus sama dengan harga produk. Tanpa ini, seseorang
//      bisa membayar Rp1 lewat halaman iPaymu lain dan mengirim order code kita.
//   3. Status harus 'berhasil'. iPaymu mengirim notifikasi untuk beberapa
//      keadaan (pending, expired, gagal), dan hanya yang berhasil yang boleh
//      menerbitkan token.
//
// Setelah lolos ketiganya, order ditandai lunas dan token dibuat. Operasi
// penandaan bersifat idempoten: webhook yang dikirim ulang (iPaymu memang
// mengulang kalau tidak menerima 200) tidak menerbitkan token kedua.

const crypto = require('crypto');
const { config, supabase, rpc, json, readBody } = require('./_lib');

// iPaymu mengirim body sebagai form-urlencoded.
function parseForm(raw) {
  const out = {};
  for (const pair of String(raw).split('&')) {
    if (!pair) continue;
    const idx = pair.indexOf('=');
    const k = idx === -1 ? pair : pair.slice(0, idx);
    const v = idx === -1 ? '' : pair.slice(idx + 1);
    out[decodeURIComponent(k.replace(/\+/g, ' '))] = decodeURIComponent(v.replace(/\+/g, ' '));
  }
  return out;
}

function readRaw(req) {
  return new Promise((resolve, reject) => {
    if (typeof req.body === 'string') return resolve(req.body);
    if (req.body && typeof req.body === 'object') {
      return resolve(new URLSearchParams(req.body).toString());
    }
    let raw = '';
    req.on('data', (c) => { raw += c; if (raw.length > 200000) { reject(new Error('too big')); req.destroy(); } });
    req.on('end', () => resolve(raw));
    req.on('error', reject);
  });
}

function safeEqual(a, b) {
  const ba = Buffer.from(String(a || ''), 'utf8');
  const bb = Buffer.from(String(b || ''), 'utf8');
  if (ba.length !== bb.length) return false;
  return crypto.timingSafeEqual(ba, bb);
}

// Verifikasi signature iPaymu. Dua bentuk diterima karena dokumentasi mereka
// berubah antar versi: ada yang menandatangani nilai mentah, ada yang
// menandatangani hash body. Menerima keduanya TIDAK melemahkan keamanan -
// keduanya sama-sama butuh API key rahasia, jadi penyerang tetap tidak bisa
// memalsukannya.
function verifySignature(apiKey, body, signature) {
  const candidates = [];
  const bodyHash = crypto.createHash('sha256').update(body, 'utf8').digest('hex');
  candidates.push(bodyHash);
  candidates.push(body);

  for (const subject of candidates) {
    const mac = crypto.createHmac('sha256', apiKey).update(subject, 'utf8').digest('hex');
    if (safeEqual(mac, signature)) return true;
    const macUpper = crypto.createHmac('sha256', apiKey).update(subject, 'utf8').digest('hex').toUpperCase();
    if (safeEqual(macUpper, signature)) return true;
  }
  return false;
}

function asInt(v) {
  const n = parseInt(String(v === undefined || v === null ? '' : v).replace(/[^\d-]/g, ''), 10);
  return Number.isFinite(n) ? n : NaN;
}

function newToken() {
  return crypto.randomBytes(32).toString('base64url');
}

function hashToken(t) {
  return crypto.createHash('sha256').update(t, 'utf8').digest('hex');
}

// Token diturunkan dari kode order + rahasia server, bukan disimpan.
//
// Alasannya: kalau token acak disimpan di database, isi database yang bocor
// langsung berarti tautan unduhan yang bisa dipakai. Dengan menurunkannya,
// yang tersimpan hanya hash-nya, dan token aslinya bisa dihitung ulang kapan
// saja oleh server tanpa pernah ditulis ke mana pun.
//
// Ini juga membuat halaman /sukses bisa menampilkan tautan tanpa menyimpan
// salinan: server menghitungnya dari kode order yang dikirim pembeli.
function deriveToken(secret, orderCode) {
  return crypto
    .createHmac('sha256', secret)
    .update(`lumawall:${orderCode}`, 'utf8')
    .digest('base64url');
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return json(res, 405, { ok: false });
  }

  // iPaymu mengharapkan balasan cepat; apa pun yang terjadi kita jawab 200
  // supaya mereka tidak mengulang tanpa henti. Kegagalan dicatat di tabel
  // download_attempts agar bisa diperiksa, bukan dibalas dengan error.
  try {
    const cfg = config();
    const raw = await readRaw(req);
    const form = parseForm(raw);

    const orderCode = form.referenceId || form.reference_id || form.merchantReferenceId || '';
    const status = String(form.status || form.Status || '').toLowerCase();
    const paidAmount = asInt(form.amount || form.total || form.nominal);
    const trxId = form.trxId || form.trx_id || form.transactionId || '';
    const signature = form.signature || form.Signature || '';

    const logAttempt = (hasil, keterangan, tokenHash) =>
      supabase('download_attempts', {
        method: 'POST',
        body: [{
          token_hash: tokenHash || null,
          ip: 'ipaymu',
          user_agent: 'webhook',
          hasil,
          keterangan: String(keterangan).slice(0, 500),
        }],
      }).catch(() => {});

    if (!orderCode) {
      await logAttempt('webhook-ditolak', 'referenceId kosong');
      return json(res, 200, { ok: false, reason: 'no-reference' });
    }

    // ── lapis 1: signature ────────────────────────────────────────────────────
    if (!signature || !verifySignature(cfg.ipaymuKey, raw, signature)) {
      await logAttempt('webhook-ditolak', `signature tidak sah untuk ${orderCode}`);
      console.error('[lumawall] webhook signature ditolak', orderCode);
      return json(res, 200, { ok: false, reason: 'bad-signature' });
    }

    // ── lapis 2: order harus ada ──────────────────────────────────────────────
    const rows = await supabase(
      `orders?order_code=eq.${encodeURIComponent(orderCode)}&select=order_code,status,jumlah,email_pembeli,nama_pembeli,license_id`
    );
    if (!Array.isArray(rows) || !rows.length) {
      await logAttempt('webhook-ditolak', `order ${orderCode} tidak ditemukan`);
      return json(res, 200, { ok: false, reason: 'unknown-order' });
    }
    const order = rows[0];

    // ── lapis 3: jumlah harus cocok ───────────────────────────────────────────
    if (!Number.isFinite(paidAmount) || paidAmount < cfg.price) {
      await logAttempt('webhook-ditolak',
        `jumlah tidak cocok untuk ${orderCode}: dibayar ${paidAmount}, seharusnya ${cfg.price}`);
      console.error('[lumawall] jumlah tidak cocok', orderCode, paidAmount, cfg.price);
      return json(res, 200, { ok: false, reason: 'amount-mismatch' });
    }

    // ── lapis 4: status harus berhasil ────────────────────────────────────────
    const paidStatuses = ['berhasil', 'success', 'paid', 'settlement', 'capture', 'sukses'];
    if (!paidStatuses.includes(status)) {
      await logAttempt('webhook-diabaikan', `${orderCode} status=${status || '(kosong)'}`);
      return json(res, 200, { ok: true, ignored: true, status });
    }

    // ── idempoten: order yang sudah lunas tidak menerbitkan token kedua ───────
    if (order.status === 'dibayar' && order.license_id) {
      await logAttempt('webhook-diulang', `${orderCode} sudah lunas`);
      return json(res, 200, { ok: true, already: true });
    }

    const token = deriveToken(cfg.bridgeSecret, orderCode);
    const tokenHash = hashToken(token);

    await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
      method: 'PATCH',
      body: {
        status: 'dibayar',
        dibayar_pada: new Date().toISOString(),
        trx_pembayaran: trxId || null,
        diperbarui_pada: new Date().toISOString(),
      },
    });

    // Token hanya diterbitkan sekali per order. Kalau baris sudah ada (webhook
    // diulang), token yang sama dipakai kembali - `ignore-duplicates` membuat
    // pengulangan tidak menimpa pemakaian yang sudah tercatat.
    await supabase('download_tokens?on_conflict=token_hash', {
      method: 'POST',
      headers: { Prefer: 'resolution=ignore-duplicates,return=minimal' },
      body: [{
        token_hash: tokenHash,
        order_code: orderCode,
        product_code: cfg.productCode,
        pemilik_email: order.email_pembeli || null,
        max_uses: cfg.tokenMaxUses,
        kedaluwarsa: new Date(Date.now() + cfg.tokenTtlHours * 3600 * 1000).toISOString(),
        catatan: 'diterbitkan oleh webhook iPaymu',
      }],
    });

    await logAttempt('webhook-diterima', `${orderCode} lunas, token diterbitkan`, tokenHash);

    return json(res, 200, { ok: true });
  } catch (err) {
    console.error('[lumawall] webhook error', err && err.stack ? err.stack : err);
    // Tetap 200: percobaan ulang tidak akan memperbaiki kesalahan konfigurasi,
    // dan kegagalan sudah tercatat di log server.
    return json(res, 200, { ok: false });
  }
};
