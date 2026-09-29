// GET /api/download?t=<token> — pintu unduhan.
//
// Aturan yang ditegakkan di sini, semuanya sekaligus:
//
//   • Token harus ada di database (artinya sudah dibayar - hanya webhook yang
//     membuat barisnya).
//   • Belum kedaluwarsa (72 jam).
//   • Pemakaian belum habis (3 kali).
//   • Terikat pada SATU alamat IP, dikunci saat pemakaian pertama.
//
// Pengikatan IP terjadi pada pemakaian pertama, bukan penerbitan, karena
// pembeli sering membayar dari satu jaringan (WiFi kantor, data seluler) dan
// mengunduh dari jaringan lain. Mengunci saat penerbitan akan mengunci orang
// yang salah. Setelah pemakaian pertama, tautan itu mati untuk alamat lain.
//
// Klaim token dilakukan lewat fungsi SQL `claim_download_token` yang memakai
// SELECT ... FOR UPDATE. Itu penting: tanpa kunci baris, dua permintaan yang
// datang bersamaan bisa dua-duanya membaca uses=0 dan dua-duanya lolos,
// sehingga satu tautan terpakai lebih dari batasnya.
//
// Berkasnya sendiri di-stream dari GitHub Releases, jadi berkas besar tidak
// perlu ikut ke dalam repositori atau ke bundel fungsi.

const crypto = require('crypto');
const { config, clientIp, supabase, rpc, json, fail } = require('./_lib');

function hashToken(t) {
  return crypto.createHash('sha256').update(String(t), 'utf8').digest('hex');
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return json(res, 405, { ok: false, error: 'Gunakan GET.' });
  }

  let tokenHash = null;
  try {
    const cfg = config();
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const token = (url.searchParams.get('t') || '').trim();

    if (!token || token.length < 20 || token.length > 200) {
      return json(res, 400, { ok: false, error: 'Tautan unduhan tidak lengkap.' });
    }

    tokenHash = hashToken(token);
    const ip = clientIp(req);

    // Klaim atomik: semua pemeriksaan + pencatatan pemakaian dalam satu transaksi.
    const result = await rpc('claim_download_token', {
      p_token_hash: tokenHash,
      p_ip: ip,
    });

    const row = Array.isArray(result) ? result[0] : result;
    const ok = row && (row.ok === true || row.ok === 't');
    const reason = row && row.alasan ? String(row.alasan) : 'ditolak';

    const logAttempt = (hasil, keterangan) =>
      supabase('download_attempts', {
        method: 'POST',
        body: [{
          token_hash: tokenHash,
          ip,
          user_agent: String(req.headers['user-agent'] || '').slice(0, 300),
          hasil,
          keterangan: String(keterangan).slice(0, 400),
        }],
      }).catch(() => {});

    if (!ok) {
      await logAttempt('ditolak', reason);

      const friendly = {
        'token tidak dikenal': 'Tautan unduhan ini tidak dikenal. Pastikan tautannya disalin utuh dari halaman pembelian.',
        'token kedaluwarsa': 'Tautan unduhan ini sudah kedaluwarsa. Hubungi dukungan dengan kode pesananmu.',
        'batas pemakaian tercapai': 'Tautan unduhan ini sudah dipakai sampai batasnya. Hubungi dukungan dengan kode pesananmu.',
        'token terikat ke alamat IP lain': 'Tautan ini sudah dipakai dari jaringan lain dan tidak bisa dipindahkan. Hubungi dukungan kalau kamu berganti jaringan.',
      }[reason] || 'Tautan unduhan ini tidak bisa dipakai lagi.';

      return json(res, 403, { ok: false, error: friendly, reason });
    }

    await logAttempt('diterima', `sisa ${row.sisa} pemakaian`);

    // ── kirim berkasnya ───────────────────────────────────────────────────────
    // Berkas diambil dari bucket PRIVAT, memakai service key yang hanya ada di
    // server. Ini yang membuat gerbangnya berarti: tidak ada alamat publik yang
    // bisa diketik langsung untuk mendapatkan installer tanpa melewati
    // pemeriksaan token di atas.
    //
    // Nama berkas dan bucket datang dari konfigurasi server, bukan dari
    // parameter permintaan - kalau datang dari klien, siapa pun bisa menyuruh
    // server mengambil objek apa pun di dalam bucket.
    const upstream = await fetchInstaller(cfg);
    if (!upstream || !upstream.ok || !upstream.body) {
      await logAttempt('gagal', `upstream ${upstream ? upstream.status : 'tidak ada sumber'}`);
      return json(res, 502, {
        ok: false,
        error: 'Berkas installer sedang tidak bisa diambil. Coba lagi sebentar lagi.',
      });
    }

    const total = upstream.headers.get('content-length');
    const filename = cfg.installerObject || `LumaWall-Setup-${cfg.version}.exe`;

    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
    res.setHeader('X-Download-Uses-Left', String(row.sisa));
    if (total) res.setHeader('Content-Length', total);

    // Stream, bukan buffer: berkas 15 MB per permintaan akan menghabiskan
    // memori fungsi kalau ditampung dulu di RAM.
    const reader = upstream.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!res.write(Buffer.from(value))) {
        await new Promise((resolve) => res.once('drain', resolve));
      }
    }
    res.end();
    return undefined;
  } catch (err) {
    // Kalau header sudah terkirim, tidak ada lagi yang bisa dilakukan selain
    // menutup koneksi - mengirim JSON di tengah unduhan justru merusak berkasnya.
    if (res.headersSent) {
      try { res.end(); } catch { /* sudah tertutup */ }
      console.error('[lumawall] unduhan terputus', err && err.message);
      return undefined;
    }
    return fail(res, err);
  }
};

// Ambil installer dari bucket privat. Mengembalikan objek Response (agar bisa
// di-stream) atau null kalau tidak ada sumber yang dikonfigurasi.
async function fetchInstaller(cfg) {
  if (cfg.storageUrl && cfg.storageKey && cfg.installerObject) {
    const url = `${cfg.storageUrl.replace(/\/$/, '')}/storage/v1/object/authenticated/` +
      `${encodeURIComponent(cfg.installerBucket)}/${encodeURIComponent(cfg.installerObject)}`;
    return fetch(url, {
      headers: {
        apikey: cfg.storageKey,
        Authorization: `Bearer ${cfg.storageKey}`,
      },
      redirect: 'follow',
    });
  }

  // Cadangan untuk pemasangan yang belum memakai penyimpanan.
  if (cfg.installerUrl) {
    return fetch(cfg.installerUrl, {
      headers: { 'User-Agent': 'LumaWall-Download/1.0' },
      redirect: 'follow',
    });
  }

  return null;
}
