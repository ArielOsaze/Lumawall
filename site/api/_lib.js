const crypto = require('crypto');

// Konfigurasi bersama untuk seluruh endpoint pembayaran LumaWall.
//
// Prinsip: TIDAK ADA rahasia di dalam berkas ini atau di repositori. Semua
// kredensial dibaca dari environment variable Vercel pada saat request, dan
// permintaan ditolak dengan jelas kalau ada yang belum dipasang - lebih baik
// gagal terang-terangan daripada diam-diam memakai kunci kosong.

// ── Harga ────────────────────────────────────────────────────────────────────
//
// Promo web: Rp10.000 sampai 15 Oktober 2026, lalu naik otomatis ke Rp18.000.
//
// Harga TIDAK ditulis di HTML sebagai kebenaran. HTML hanya menampilkan; yang
// menagih adalah berkas ini. Alasannya: kalau harga di halaman dan harga di
// checkout bisa berbeda, cepat atau lambat ada yang membayar Rp10.000 untuk
// produk yang seharusnya Rp18.000 - atau sebaliknya, ditagih lebih mahal
// daripada yang tertera. Dua angka yang harus cocok sebaiknya berasal dari satu
// tempat, dan tempat itu harus yang tidak bisa diubah pembeli.
//
// Batas tanggalnya memakai waktu Indonesia (WIB, UTC+7), bukan UTC: promo yang
// berakhir "15 Oktober" bagi pembeli di Jakarta harus berakhir saat tengah
// malam di Jakarta, bukan pukul 07.00 pagi keesokan harinya.
const PRICE_PROMO_IDR = 10000;
const PRICE_NORMAL_IDR = 18000;
const PROMO_ENDS_AT = '2026-10-15T23:59:59+07:00';

// Microsoft Store selalu Rp18.000. Promo Rp10.000 hanya berlaku di web, dan
// itu disengaja: Store memotong biaya distribusi, jadi menurunkan harganya di
// sana berarti memotong margin yang sudah tipis. Justru sebaliknya yang
// berlaku sekarang - web lebih murah selama promo.
const STORE_PRICE_IDR = 18000;
const STORE_URL = 'https://apps.microsoft.com/detail/9PN82QJLV05B';
const PRODUCT_CODE = 'lumawall';
const PRODUCT_NAME = 'LumaWall';

// Batas pemakaian token. Tiga kali, bukan satu, karena pembeli yang sah sering
// gagal pada percobaan pertama: unduhan terputus, antivirus memblokir, atau
// salah simpan berkas. Satu kali pakai membuat mereka harus menghubungi
// dukungan padahal sudah membayar; tiga kali tetap tidak berguna untuk
// dibagikan karena token juga terikat pada satu alamat IP.
const TOKEN_MAX_USES = 3;
const TOKEN_TTL_HOURS = 72;

function env(name, { required = true } = {}) {
  const v = process.env[name];
  if (required && (!v || !String(v).trim())) {
    const err = new Error(`Konfigurasi server belum lengkap: ${name} belum diisi.`);
    err.statusCode = 503;
    err.code = 'CONFIG_MISSING';
    throw err;
  }
  return v ? String(v).trim() : '';
}

// Harga yang berlaku saat ini. Dipanggil setiap request, bukan disimpan saat
// modul dimuat: instance fungsi serverless bisa hidup berjam-jam atau berhari-
// hari, dan harga yang disimpan di memori akan tetap promo setelah tanggalnya
// lewat.
function currentPrice(now = new Date()) {
  const promoAktif = now.getTime() <= new Date(PROMO_ENDS_AT).getTime();
  return {
    amount: promoAktif ? PRICE_PROMO_IDR : PRICE_NORMAL_IDR,
    promo: promoAktif,
    promoPrice: PRICE_PROMO_IDR,
    normalPrice: PRICE_NORMAL_IDR,
    promoEndsAt: PROMO_ENDS_AT,
    storePrice: STORE_PRICE_IDR,
  };
}

function config() {
  const version = env('LUMAWALL_VERSION', { required: false }) || '4.5.7.0';
  const harga = currentPrice();
  return {
    price: harga.amount,
    promo: harga.promo,
    promoPrice: harga.promoPrice,
    normalPrice: harga.normalPrice,
    promoEndsAt: harga.promoEndsAt,
    storePrice: STORE_PRICE_IDR,
    storeUrl: STORE_URL,
    productCode: PRODUCT_CODE,
    productName: PRODUCT_NAME,
    tokenMaxUses: TOKEN_MAX_USES,
    tokenTtlHours: TOKEN_TTL_HOURS,
    supabaseUrl: env('SUPABASE_URL'),
    supabaseKey: env('SUPABASE_SERVICE_KEY'),
    ipaymuVa: env('IPAYMU_VA'),
    ipaymuKey: env('IPAYMU_API_KEY'),
    ipaymuMode: env('IPAYMU_MODE', { required: false }) || 'production',
    bridgeSecret: env('LUMAWALL_BRIDGE_SECRET'),

    // Alamat jembatan pembayaran di server NexShop. Panggilan ke iPaymu
    // dialihkan lewat sini karena IP server itu sudah terdaftar di iPaymu,
    // sedangkan IP Vercel tidak.
    bridgeUrl: env('LUMAWALL_BRIDGE_URL', { required: false }) ||
      'https://nexshop.cloud/api/lumawall',
    siteUrl: env('SITE_URL', { required: false }) || 'https://lumawall.xinet.id',

    // Berkas installer disimpan di bucket privat milik proyek Supabase NexShop,
    // terpisah dari proyek yang menyimpan pesanan. Alasannya sederhana: bucket
    // penyimpanan sudah ada di sana beserta kredensialnya, dan tidak ada
    // gunanya membuat infrastruktur kedua hanya untuk satu berkas.
    //
    // Kuncinya dibaca dari variabel terpisah supaya kunci service proyek pesanan
    // tidak perlu punya akses ke penyimpanan, dan sebaliknya.
    storageUrl: env('INSTALLER_SUPABASE_URL', { required: false }) || env('SUPABASE_URL'),
    storageKey: env('INSTALLER_SUPABASE_KEY', { required: false }) || env('SUPABASE_SERVICE_KEY'),
    installerBucket: env('INSTALLER_BUCKET', { required: false }) || 'lumawall',
    installerObject: env('INSTALLER_OBJECT', { required: false }) || null,

    // Cadangan: kalau installer tidak ada di penyimpanan, alamat langsung ini
    // yang dipakai. Dibiarkan kosong secara default supaya tidak ada berkas
    // yang bisa diunduh tanpa melewati gerbang pembayaran.
    installerUrl: env('LUMAWALL_INSTALLER_URL', { required: false }) || null,
    version,
  };
}

// Alamat IP pemanggil. Vercel menaruh IP asli di x-forwarded-for sebagai daftar;
// entri pertama adalah klien. Nilai ini dipakai untuk mengikat token, jadi ia
// harus dinormalkan dulu supaya ::ffff:1.2.3.4 dan 1.2.3.4 tidak dianggap dua
// alamat berbeda.
function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  let ip = '';
  if (typeof fwd === 'string' && fwd.length) {
    ip = fwd.split(',')[0].trim();
  } else if (Array.isArray(fwd) && fwd.length) {
    ip = String(fwd[0]).split(',')[0].trim();
  }
  if (!ip) {
    ip = (req.socket && req.socket.remoteAddress) || (req.connection && req.connection.remoteAddress) || '';
  }
  return normaliseIp(ip);
}

function normaliseIp(ip) {
  let v = String(ip || '').trim();
  if (!v) return 'tidak-diketahui';
  // IPv4-mapped IPv6 -> IPv4
  if (v.toLowerCase().startsWith('::ffff:')) v = v.slice(7);
  // IPv6 loopback dan localhost diperlakukan sama supaya pengujian lokal tidak
  // menghasilkan alamat yang berbeda-beda.
  if (v === '::1' || v === '127.0.0.1' || v === 'localhost') return '127.0.0.1';
  return v;
}

async function supabase(path, { method = 'GET', body, headers = {} } = {}) {
  const cfg = config();
  const url = `${cfg.supabaseUrl}/rest/v1/${path}`;
  const res = await fetch(url, {
    method,
    headers: {
      apikey: cfg.supabaseKey,
      Authorization: `Bearer ${cfg.supabaseKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!res.ok) {
    const err = new Error(`Supabase ${res.status}: ${typeof data === 'string' ? data.slice(0, 200) : JSON.stringify(data).slice(0, 200)}`);
    err.statusCode = 502;
    throw err;
  }
  return data;
}

// Panggil fungsi RPC di Supabase (untuk klaim token yang atomik).
async function rpc(fnName, args) {
  const cfg = config();
  const res = await fetch(`${cfg.supabaseUrl}/rest/v1/rpc/${fnName}`, {
    method: 'POST',
    headers: {
      apikey: cfg.supabaseKey,
      Authorization: `Bearer ${cfg.supabaseKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(args),
  });
  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!res.ok) {
    const err = new Error(`Supabase RPC ${res.status}: ${typeof data === 'string' ? data.slice(0, 200) : JSON.stringify(data).slice(0, 200)}`);
    err.statusCode = 502;
    throw err;
  }
  return data;
}

// Panggil jembatan pembayaran di server NexShop.
//
// Jembatan ini ada karena iPaymu membatasi permintaan berdasarkan alamat IP
// pengirim, dan Vercel keluar dari IP dinamis yang tidak terdaftar. Server
// NexShop punya IP tetap yang sudah terdaftar di akun iPaymu yang sama.
//
// Tanda tangan yang dipakai adalah HMAC atas "tindakan:cap-waktu", BUKAN atas
// body. Alasannya teknis: menandatangani body mengharuskan kedua sisi
// menghasilkan string JSON yang identik byte per byte, dan urutan kunci bisa
// berbeda antara pembuat dan pemeriksa - begitu berbeda, tanda tangannya tidak
// pernah cocok, dan kegagalannya sulit dilacak karena isinya terlihat benar.
//
// Cap waktu dikirim dalam milidetik. Jembatan menolak tanda tangan yang lebih
// tua dari 5 menit, sehingga permintaan yang sempat terekam tidak bisa dipakai
// ulang.
async function panggilJembatan(cfg, tindakan, muatan) {
  const bridgeUrl = cfg.bridgeUrl;
  if (!bridgeUrl) {
    return { ok: false, status: 0, data: null, error: 'Alamat jembatan belum diisi.' };
  }

  const ts = String(Date.now());
  const tandaTangan = crypto
    .createHmac('sha256', cfg.bridgeSecret)
    .update(`${tindakan}:${ts}`)
    .digest('hex');

  const url = `${bridgeUrl.replace(/\/$/, '')}/${tindakan}`;

  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'x-lumawall-ts': ts,
        'x-lumawall-signature': tandaTangan,
      },
      body: JSON.stringify(muatan),
      // Jembatan meneruskan ke iPaymu yang kadang lambat. 20 detik lebih
      // pendek daripada batas fungsi serverless, sehingga kegagalan jembatan
      // dilaporkan sebagai pesan yang jelas alih-alih timeout platform.
      signal: AbortSignal.timeout(20000),
    });
  } catch (err) {
    const pesan = err && err.name === 'TimeoutError'
      ? 'Jembatan tidak menjawab dalam 20 detik.'
      : `Tidak bisa menghubungi jembatan: ${err && err.message}`;
    return { ok: false, status: 0, data: null, error: pesan };
  }

  const teks = await res.text();
  let data = null;
  try { data = JSON.parse(teks); } catch { /* biarkan null */ }

  // Jembatan membungkus balasan iPaymu dalam bentuk { ok, status, data }.
  // Yang dibutuhkan pemanggil adalah isi iPaymu-nya, jadi lapisan pembungkus
  // itu dibuka di sini - di SATU tempat.
  //
  // Ini bukan kerapian belaka. Versi pertama membiarkan pemanggil membukanya
  // sendiri, dan checkout.js memeriksa `data.Status` padahal yang benar
  // `data.data.Status`. Akibatnya iPaymu menjawab "200 Success" tetapi
  // checkout melaporkan gagal, dan pesanan tercatat gagal padahal tautan
  // pembayarannya sudah tercipta - pembeli tidak bisa membayar, dan tidak ada
  // yang tahu kenapa. Membukanya sekali di sini membuat kesalahan seperti itu
  // tidak mungkin terjadi lagi.
  if (data && typeof data === 'object' && !Array.isArray(data)
      && 'ok' in data && 'data' in data) {
    data = data.data;
  }

  return { ok: res.ok, status: res.status, data };
}

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.end(JSON.stringify(payload));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    if (req.body && typeof req.body === 'object') return resolve(req.body);
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 100000) {
        reject(Object.assign(new Error('Body terlalu besar'), { statusCode: 413 }));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); }
      catch { reject(Object.assign(new Error('Body bukan JSON yang sah'), { statusCode: 400 })); }
    });
    req.on('error', reject);
  });
}

function fail(res, err) {
  const status = err && err.statusCode ? err.statusCode : 500;
  const message = status >= 500 && !(err && err.code === 'CONFIG_MISSING')
    ? 'Terjadi kesalahan di server. Coba lagi sebentar lagi.'
    : (err && err.message) || 'Terjadi kesalahan.';
  // Log lengkap di sisi server, pesan aman ke klien: jangan pernah bocorkan
  // detail internal (nama env, isi respons Supabase) ke peramban.
  console.error('[lumawall]', status, err && err.stack ? err.stack : err);
  json(res, status, { ok: false, error: message });
}

module.exports = {
  config,
  currentPrice,
  panggilJembatan,
  clientIp,
  normaliseIp,
  supabase,
  rpc,
  json,
  readBody,
  fail,
};
