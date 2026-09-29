// GET /api/order?code=LW-XXXXXX — status pesanan + tautan unduhan.
//
// Dipakai halaman /sukses setelah pembeli kembali dari iPaymu.
//
// Kenapa kode pesanan boleh menjadi kuncinya: kode itu dibuat acak dari 32
// huruf/angka sebanyak 6 karakter (lebih dari satu miliar kemungkinan), hanya
// pernah dikirim ke pembeli lewat pengalihan iPaymu, dan tidak pernah
// ditampilkan di halaman mana pun yang publik. Untuk menebaknya orang harus
// menebak satu dari miliaran, dan setiap percobaan gagal tercatat.
//
// Yang TIDAK dikembalikan endpoint ini: token mentah sebelum lunas. Status
// 'menunggu' hanya menjawab "belum dibayar", tanpa tautan apa pun.

const { config, supabase, json } = require('./_lib');
const crypto = require('crypto');

function deriveToken(secret, orderCode) {
  return crypto
    .createHmac('sha256', secret)
    .update(`lumawall:${orderCode}`, 'utf8')
    .digest('base64url');
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return json(res, 405, { ok: false, error: 'Gunakan GET.' });
  }

  try {
    const cfg = config();
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const code = (url.searchParams.get('code') || '').trim().toUpperCase();

    if (!/^LW-[A-Z0-9]{6}$/.test(code)) {
      return json(res, 400, { ok: false, error: 'Kode pesanan tidak sah.' });
    }

    const rows = await supabase(
      `orders?order_code=eq.${encodeURIComponent(code)}` +
      '&select=order_code,status,jumlah,email_pembeli,nama_pembeli,dibayar_pada,dibuat_pada'
    );

    if (!Array.isArray(rows) || !rows.length) {
      return json(res, 404, { ok: false, error: 'Pesanan tidak ditemukan.' });
    }

    const order = rows[0];
    const paid = order.status === 'dibayar';

    if (!paid) {
      return json(res, 200, {
        ok: true,
        paid: false,
        status: order.status,
        order: order.order_code,
        amount: order.jumlah,
        nama: order.nama_pembeli,
      });
    }

    // Cek sisa pemakaian supaya halaman bisa memberi tahu kalau tautannya sudah
    // habis, bukan menampilkan tombol yang pasti gagal.
    const tokenHash = crypto.createHash('sha256')
      .update(deriveToken(cfg.bridgeSecret, code), 'utf8').digest('hex');

    const tokens = await supabase(
      `download_tokens?token_hash=eq.${tokenHash}&select=uses,max_uses,kedaluwarsa,bound_ip`
    );
    const token = Array.isArray(tokens) && tokens.length ? tokens[0] : null;

    const expired = token ? new Date(token.kedaluwarsa).getTime() < Date.now() : false;
    const exhausted = token ? token.uses >= token.max_uses : false;

    return json(res, 200, {
      ok: true,
      paid: true,
      order: order.order_code,
      amount: order.jumlah,
      nama: order.nama_pembeli,
      paidAt: order.dibayar_pada,
      // Token diturunkan ulang di server dan hanya dikirim setelah lunas.
      downloadToken: deriveToken(cfg.bridgeSecret, code),
      downloadUrl: `/api/download?t=${encodeURIComponent(deriveToken(cfg.bridgeSecret, code))}`,
      usesLeft: token ? Math.max(0, token.max_uses - token.uses) : null,
      maxUses: token ? token.max_uses : null,
      expiresAt: token ? token.kedaluwarsa : null,
      expired,
      exhausted,
      // Alamat IP yang sudah mengunci tautan ini (null = belum dipakai).
      lockedTo: token && token.bound_ip ? token.bound_ip : null,
    });
  } catch (err) {
    const { fail } = require('./_lib');
    return fail(res, err);
  }
};
