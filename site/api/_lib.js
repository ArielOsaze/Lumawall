// Konfigurasi bersama untuk seluruh endpoint pembayaran LumaWall.
//
// Prinsip: TIDAK ADA rahasia di dalam berkas ini atau di repositori. Semua
// kredensial dibaca dari environment variable Vercel pada saat request, dan
// permintaan ditolak dengan jelas kalau ada yang belum dipasang - lebih baik
// gagal terang-terangan daripada diam-diam memakai kunci kosong.

const PRICE_IDR = 20000;
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

function config() {
  const version = env('LUMAWALL_VERSION', { required: false }) || '4.5.7.0';
  return {
    price: PRICE_IDR,
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
  clientIp,
  normaliseIp,
  supabase,
  rpc,
  json,
  readBody,
  fail,
};
