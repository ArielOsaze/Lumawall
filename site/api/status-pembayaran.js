// GET /api/status-pembayaran?order=LW-XXXXXX — memeriksa apakah sudah dibayar.
//
// Kenapa endpoint ini ada, padahal sudah ada webhook:
//
// Webhook memberi tahu SERVER kalau pembayaran masuk, tetapi pembeli yang masih
// membuka halaman QR tidak tahu apa-apa sampai ia memuat ulang halaman. Kalau
// ia menutup peramban sebelum webhook diproses, ia tidak pernah melihat tautan
// unduhannya meskipun sudah membayar. Jadi halaman perlu cara bertanya.
//
// Yang diperiksa endpoint ini adalah DATABASE, bukan iPaymu. Alasannya:
// webhook sudah menuliskan status ke database begitu pembayaran masuk, jadi
// database adalah sumber yang lebih cepat dan tidak membebani iPaymu. Kalau
// webhook belum sampai (iPaymu kadang terlambat beberapa detik), endpoint ini
// memeriksa langsung ke iPaymu lewat jembatan sebagai cadangan - dan begitu
// terbukti lunas, ia menandai pesanan lunas lewat jalur yang sama dengan
// webhook, sehingga token unduhan terbit.
//
// Yang TIDAK dilakukan endpoint ini: menerbitkan token sendiri tanpa bukti.
// Untuk memakai jalur cadangan, status harus datang dari iPaymu dengan nomor
// transaksi yang cocok dan jumlah yang benar.

const crypto = require('crypto');
const { config, supabase, json, panggilJembatan } = require('./_lib');

// Token unduhan diturunkan dari kode pesanan + rahasia server, sama persis
// seperti di webhook. Fungsi yang sama ada di dua berkas karena keduanya harus
// menghasilkan token yang identik; kalau salah satu diubah, tautan yang
// diterbitkan webhook tidak akan cocok dengan yang ditampilkan halaman ini.
function deriveToken(secret, orderCode) {
  return crypto
    .createHmac('sha256', secret)
    .update(`lumawall:${orderCode}`, 'utf8')
    .digest('base64url');
}

function hashToken(t) {
  return crypto.createHash('sha256').update(t, 'utf8').digest('hex');
}

function asInt(v) {
  const n = parseInt(String(v === undefined || v === null ? '' : v).replace(/[^\d-]/g, ''), 10);
  return Number.isFinite(n) ? n : NaN;
}

// Status yang dianggap sudah dibayar. iPaymu memakai beberapa istilah berbeda
// antar endpoint, dan hanya satu di antaranya yang benar-benar berarti uangnya
// sudah masuk.
function sudahDibayar(status) {
  return ['berhasil', 'success', 'paid', 'settlement', 'capture', 'sukses']
    .includes(String(status || '').toLowerCase());
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return json(res, 405, { ok: false, error: 'Gunakan GET.' });
  }

  try {
    const cfg = config();

    // Kode pesanan datang dari query string, jadi harus dibersihkan dulu.
    // Tanpa pembersihan ini, kode yang memuat karakter khusus bisa menyusup ke
    // dalam query Supabase di bawah.
    const url = new URL(req.url, 'https://lumawall.invalid');
    const orderCode = String(url.searchParams.get('order') || '').trim().toUpperCase();

    if (!/^LW-[A-Z0-9]{4,12}$/.test(orderCode)) {
      return json(res, 400, { ok: false, error: 'Kode pesanan tidak sah.' });
    }

    const rows = await supabase(
      `orders?order_code=eq.${encodeURIComponent(orderCode)}` +
      '&select=order_code,status,jumlah,acuan_pembayaran,email_pembeli,nama_pembeli'
    );

    if (!Array.isArray(rows) || !rows.length) {
      return json(res, 404, { ok: false, error: 'Pesanan tidak ditemukan.' });
    }

    const order = rows[0];

    // ── jalur utama: database sudah bilang lunas ─────────────────────────────
    if (order.status === 'dibayar') {
      const token = deriveToken(cfg.bridgeSecret, orderCode);
      return json(res, 200, {
        ok: true,
        order: orderCode,
        status: 'dibayar',
        paid: true,
        amount: order.jumlah,
        downloadUrl: `${cfg.siteUrl.replace(/\/$/, '')}/api/download?t=${encodeURIComponent(token)}`,
      });
    }

    // ── jalur cadangan: tanya iPaymu ─────────────────────────────────────────
    //
    // Dipakai saat webhook belum sampai. Hasilnya harus lolos dua pemeriksaan
    // sebelum dipercaya: nomor transaksinya cocok dengan yang tersimpan saat
    // checkout, dan jumlah yang dibayar tidak kurang dari harga.
    if (!order.acuan_pembayaran) {
      return json(res, 200, { ok: true, order: orderCode, status: order.status, paid: false });
    }

    const upstream = await panggilJembatan(cfg, 'transaction', {
      transactionId: Number(order.acuan_pembayaran),
    });

    const data = upstream && upstream.data ? upstream.data : null;
    const isi = data && data.Data ? data.Data : null;
    const statusIpaymu = isi ? (isi.Status || isi.status) : null;
    const dibayar = isi ? (isi.Paid === true || sudahDibayar(statusIpaymu)) : false;

    // Jumlah diperiksa, bukan dipercaya. Tanpa ini, pesanan yang dibayar
    // sebagian akan dianggap lunas.
    const dibayarJumlah = isi ? asInt(isi.Amount || isi.amount || isi.Total) : NaN;
    const jumlahCukup = Number.isFinite(dibayarJumlah) && dibayarJumlah >= order.jumlah;

    if (!dibayar || !jumlahCukup) {
      return json(res, 200, {
        ok: true,
        order: orderCode,
        status: order.status,
        paid: false,
        // Dikirim apa adanya supaya halaman bisa menampilkan "menunggu
        // pembayaran" alih-alih pesan yang membingungkan kalau iPaymu
        // mengembalikan status yang tidak dikenal.
        ipaymuStatus: statusIpaymu || null,
      });
    }

    // ── tandai lunas, terbitkan token ────────────────────────────────────────
    //
    // Ditulis dengan bentuk yang sama seperti webhook, dan idempoten: kalau
    // webhook datang belakangan, ia melihat status 'dibayar' dan tidak
    // menerbitkan token kedua.
    const token = deriveToken(cfg.bridgeSecret, orderCode);
    const tokenHash = hashToken(token);
    const now = new Date().toISOString();

    await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
      method: 'PATCH',
      body: { status: 'dibayar', dibayar_pada: now, diperbarui_pada: now },
    }).catch(() => {});

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
        catatan: 'diterbitkan oleh pemeriksaan status',
      }],
    }).catch(() => {});

    return json(res, 200, {
      ok: true,
      order: orderCode,
      status: 'dibayar',
      paid: true,
      amount: order.jumlah,
      downloadUrl: `${cfg.siteUrl.replace(/\/$/, '')}/api/download?t=${encodeURIComponent(token)}`,
    });
  } catch (err) {
    console.error('[lumawall] status-pembayaran error', err && err.stack ? err.stack : err);
    // 502 supaya halaman tahu ini kegagalan sementara dan bisa mencoba lagi,
    // bukan "belum dibayar" yang akan membuat pembeli menunggu selamanya.
    return json(res, 502, { ok: false, error: 'Tidak bisa memeriksa status sekarang.' });
  }
};
