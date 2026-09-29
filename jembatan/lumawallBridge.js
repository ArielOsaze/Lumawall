/**
 * Jembatan pembayaran LumaWall.
 *
 * ===========================================================
 * KENAPA JEMBATAN INI ADA
 * ===========================================================
 *
 * iPaymu membatasi permintaan berdasarkan alamat IP pengirim. Vercel keluar
 * dari IP dinamis yang tidak terdaftar, jadi setiap permintaan checkout dari
 * situs LumaWall ditolak dengan "Invalid IP" - terbukti dari log pesanan:
 *
 *     {"order_code":"LW-XXSX3D","status":"gagal",
 *      "catatan":"ipaymu gagal: Invalid IP"}
 *
 * Server ini (VPS dengan IP tetap 202.10.38.167) sudah terdaftar di akun
 * iPaymu yang sama. Diuji langsung dari sini: /balance menjawab Status 200.
 * Jadi permintaan checkout LumaWall dialihkan lewat server ini.
 *
 * Yang mengalir lewat jembatan ini HANYA panggilan ke iPaymu. Database
 * pesanan, token unduhan, dan berkas installer tetap di tempatnya masing-
 * masing - server ini tidak menyimpan data LumaWall sama sekali. Itu disengaja:
 * jembatan yang tidak menyimpan apa pun tidak bisa menjadi sumber kebocoran,
 * dan kalau nanti tidak diperlukan lagi, ia cukup dimatikan.
 *
 * ===========================================================
 * KEAMANAN
 * ===========================================================
 *
 * Jembatan ini bisa memanggil iPaymu dengan kredensial produksi, jadi ia
 * TIDAK boleh terbuka. Tiga lapis:
 *
 *   1. Rahasia bersama (HMAC). Setiap permintaan ditandatangani dengan
 *      LUMAWALL_BRIDGE_SECRET. Tanpa rahasia itu, permintaan ditolak sebelum
 *      apa pun terjadi.
 *
 *   2. Waktu. Tanda tangan yang lebih tua dari 5 menit ditolak, sehingga
 *      permintaan yang sempat terekam tidak bisa dipakai ulang besok.
 *
 *   3. Daftar putih tindakan. Hanya tiga tindakan yang dikenal: membuat
 *      pembayaran, membuat pembayaran langsung, dan mengecek status. Tidak
 *      ada cara memanggil endpoint iPaymu sembarangan lewat jembatan ini.
 *
 * Yang TIDAK dilakukan jembatan ini: memutuskan apakah pembayaran sah.
 * Keputusan itu tetap di webhook di sisi LumaWall, yang memverifikasi
 * signature iPaymu dan mencocokkan jumlahnya. Jembatan ini hanya perantara.
 */

const express = require('express');
const crypto = require('crypto');
const router = express.Router();

const IPAYMU_PRODUCTION = 'https://my.ipaymu.com/api/v2';
const IPAYMU_SANDBOX = 'https://sandbox.ipaymu.com/api/v2';

const MAX_AGE_MS = 5 * 60 * 1000; // 5 menit

// Tindakan yang diizinkan. Apa pun di luar daftar ini ditolak, jadi menambah
// kemampuan jembatan harus disengaja - bukan efek samping dari meneruskan
// nama endpoint dari pemanggil.
const TINDAKAN = new Set(['payment', 'payment-direct', 'transaction']);

function bacaEnv(nama) {
  const v = process.env[nama];
  return v ? String(v).trim() : '';
}

function timestamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`
       + `${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

// Signature iPaymu v2: HMAC_SHA256("POST:va:sha256(body):apiKey", apiKey)
// Body yang ditandatangani adalah string JSON yang benar-benar dikirim.
function tandaTanganIpaymu(va, apiKey, body) {
  const bodyHash = crypto.createHash('sha256').update(body).digest('hex').toLowerCase();
  const stringToSign = `POST:${va}:${bodyHash}:${apiKey}`;
  return crypto.createHmac('sha256', apiKey).update(stringToSign).digest('hex');
}

// Perbandingan waktu-tetap: perbandingan biasa membocorkan berapa banyak
// karakter awal yang sudah benar lewat selisih waktu, dan rahasia bersama
// adalah satu-satunya yang melindungi jembatan ini.
function samaAman(a, b) {
  const ba = Buffer.from(String(a || ''), 'utf8');
  const bb = Buffer.from(String(b || ''), 'utf8');
  if (ba.length !== bb.length) return false;
  return crypto.timingSafeEqual(ba, bb);
}

// Tanda tangan jembatan: HMAC(secret, "tindakan:timestamp:sha256(body)")
function tandaTanganJembatan(secret, tindakan, ts, body) {
  const bodyHash = crypto.createHash('sha256').update(body).digest('hex');
  const payload = `${tindakan}:${ts}:${bodyHash}`;
  return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

// Express perlu body mentah untuk memverifikasi tanda tangan. Kalau body sudah
// di-parse jadi objek, JSON.stringify ulang bisa menghasilkan urutan kunci yang
// berbeda dan tanda tangannya tidak akan pernah cocok. Karena itu rute ini
// memakai express.raw dan mengurai sendiri setelah verifikasi.
router.use(express.raw({ type: '*/*', limit: '64kb' }));

router.post('/:tindakan', async (req, res) => {
  const tindakan = String(req.params.tindakan || '').toLowerCase();

  const rahasia = bacaEnv('LUMAWALL_BRIDGE_SECRET');
  if (!rahasia) {
    console.error('[lumawall-bridge] LUMAWALL_BRIDGE_SECRET belum diisi');
    return res.status(503).json({ ok: false, error: 'Jembatan belum dikonfigurasi.' });
  }

  if (!TINDAKAN.has(tindakan)) {
    return res.status(404).json({ ok: false, error: 'Tindakan tidak dikenal.' });
  }

  const bodyMentah = Buffer.isBuffer(req.body) ? req.body.toString('utf8') : String(req.body || '');
  const ts = String(req.get('x-lumawall-ts') || '');
  const tandaTangan = String(req.get('x-lumawall-signature') || '');

  // ── lapis 1: tanda tangan ──────────────────────────────────────────────
  if (!ts || !tandaTangan) {
    return res.status(401).json({ ok: false, error: 'Tanda tangan tidak ada.' });
  }

  const diharapkan = tandaTanganJembatan(rahasia, tindakan, ts, bodyMentah);
  if (!samaAman(diharapkan, tandaTangan)) {
    console.warn('[lumawall-bridge] tanda tangan tidak sah, tindakan:', tindakan);
    return res.status(401).json({ ok: false, error: 'Tanda tangan tidak sah.' });
  }

  // ── lapis 2: waktu ─────────────────────────────────────────────────────
  const umur = Date.now() - Number(ts);
  if (!Number.isFinite(umur) || Math.abs(umur) > MAX_AGE_MS) {
    return res.status(401).json({ ok: false, error: 'Permintaan kedaluwarsa.' });
  }

  // ── lapis 3: teruskan ke iPaymu ────────────────────────────────────────
  let muatan;
  try {
    muatan = JSON.parse(bodyMentah || '{}');
  } catch (e) {
    return res.status(400).json({ ok: false, error: 'Body bukan JSON.' });
  }

  const va = bacaEnv('IPAYMU_VA');
  const apiKey = bacaEnv('IPAYMU_API_KEY');
  const mode = String(bacaEnv('IPAYMU_MODE') || 'production').toLowerCase();
  const produksi = !['sandbox', '0', 'false'].includes(mode);

  if (!va || !apiKey) {
    console.error('[lumawall-bridge] kredensial iPaymu tidak ada di .env server');
    return res.status(503).json({ ok: false, error: 'Kredensial iPaymu tidak ada di server.' });
  }

  // Body yang dikirim ke iPaymu disusun di sini, dari muatan yang sudah
  // diverifikasi. Pemanggil TIDAK bisa menyisipkan kunci tambahan: hanya
  // kunci yang dikenal di bawah ini yang diteruskan. Tanpa penyaringan ini,
  // pemanggil bisa mengubah perilaku transaksi dengan kunci yang tidak
  // terduga (misalnya menyalurkan dana ke rekening lain).
  const kirim = {};

  if (tindakan === 'payment') {
    const p = muatan;
    kirim.product = [String(p.product || 'LumaWall')];
    kirim.qty = ['1'];
    kirim.price = [String(p.amount)];
    kirim.amount = String(p.amount);
    kirim.returnUrl = String(p.returnUrl || '');
    kirim.notifyUrl = String(p.notifyUrl || '');
    kirim.cancelUrl = String(p.cancelUrl || '');
    kirim.referenceId = String(p.referenceId || '');
    kirim.buyerName = String(p.buyerName || 'Guest');
    if (p.buyerEmail) kirim.buyerEmail = String(p.buyerEmail);
    if (p.buyerPhone) kirim.buyerPhone = String(p.buyerPhone);
  } else if (tindakan === 'payment-direct') {
    const p = muatan;
    kirim.name = String(p.name || 'Guest');
    kirim.phone = String(p.phone || '');
    kirim.email = String(p.email || '');
    kirim.amount = String(p.amount);
    kirim.notifyUrl = String(p.notifyUrl || '');
    kirim.referenceId = String(p.referenceId || '');
    kirim.paymentMethod = String(p.paymentMethod || 'qris');
    if (p.paymentChannel) kirim.paymentChannel = String(p.paymentChannel);
  } else {
    kirim.transactionId = String(muatan.transactionId || '');
  }

  const bodyIpaymu = JSON.stringify(kirim);
  const base = produksi ? IPAYMU_PRODUCTION : IPAYMU_SANDBOX;
  const jalur = tindakan === 'transaction' ? '/transaction'
              : tindakan === 'payment-direct' ? '/payment/direct'
              : '/payment';

  try {
    const upstream = await fetch(base + jalur, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        va,
        signature: tandaTanganIpaymu(va, apiKey, bodyIpaymu),
        timestamp: timestamp(),
      },
      body: bodyIpaymu,
    });

    const teks = await upstream.text();
    let data = null;
    try { data = JSON.parse(teks); } catch (e) { /* biarkan null */ }

    // Balasan diteruskan apa adanya. Jembatan tidak menafsirkan hasilnya:
    // yang memutuskan pembayaran sah atau tidak adalah webhook di sisi
    // LumaWall, bukan perantara ini.
    res.status(upstream.status);
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    return res.end(JSON.stringify({
      ok: upstream.ok,
      status: upstream.status,
      data,
      mode: produksi ? 'production' : 'sandbox',
    }));
  } catch (err) {
    console.error('[lumawall-bridge] gagal menghubungi iPaymu:', err && err.message);
    return res.status(502).json({
      ok: false,
      error: 'Gagal menghubungi iPaymu dari server.',
    });
  }
});

// Pemeriksaan sederhana: tidak membocorkan apa pun, hanya menyatakan hidup.
router.get('/health', (req, res) => {
  const va = bacaEnv('IPAYMU_VA');
  res.json({
    ok: true,
    siap: Boolean(va && bacaEnv('IPAYMU_API_KEY') && bacaEnv('LUMAWALL_BRIDGE_SECRET')),
  });
});

module.exports = router;
