#!/usr/bin/env node
/**
 * Cari tahu domain mana yang diterima akun iPaymu LumaWall.
 *
 * iPaymu menolak transaksi dengan "Invalid domain" kalau returnUrl/notifyUrl
 * tidak cocok dengan domain yang terdaftar di akun. Pesan itu tidak menyebut
 * domain mana yang benar, jadi satu-satunya cara adalah mencoba beberapa
 * kandidat dan melihat mana yang lolos.
 *
 * Ini dijalankan DI SERVER karena hanya dari IP server ini iPaymu menerima
 * permintaan.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-domain.js
 */
const fs = require('fs');

const ENV = '/var/www/NEXSHOP_ALL/nexshop-backend/.env';
const env = {};
for (const baris of fs.readFileSync(ENV, 'utf8').split('\n')) {
  const t = baris.trim();
  if (!t || t.startsWith('#') || !t.includes('=')) continue;
  const i = t.indexOf('=');
  let v = t.slice(i + 1).trim();
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
  env[t.slice(0, i).trim()] = v;
}

// Kredensial LumaWall diambil dari .env server (sudah diisi sebelumnya).
const VA = env.LUMAWALL_IPAYMU_VA || '';
const KEY = env.LUMAWALL_IPAYMU_API_KEY || '';

if (!VA || !KEY) {
  console.log('  GAGAL: LUMAWALL_IPAYMU_VA / LUMAWALL_IPAYMU_KEY tidak ada di .env');
  console.log('  ada:', Object.keys(env).filter((k) => k.startsWith('LUMAWALL')).join(', ') || '(tidak ada)');
  process.exit(1);
}

const crypto = require('crypto');

// Kandidat domain, dari yang paling mungkin ke paling tidak.
const KANDIDAT = [
  ['https://lumawall.xinet.id', 'domain LumaWall (dipakai sekarang)'],
  ['https://nexshop.cloud', 'domain server jembatan'],
  ['https://xinet.id', 'domain induk'],
  ['https://akuntuntas.xinet.id', 'domain proyek lain yang sudah jalan'],
  ['https://www.lumawall.xinet.id', 'dengan www'],
  ['http://lumawall.xinet.id', 'http, bukan https'],
];

async function coba(domain, keterangan) {
  const badan = {
    product: ['LumaWall - lisensi lifetime'],
    qty: [1],
    price: [10000],
    description: ['LumaWall - lisensi lifetime'],
    returnUrl: domain + '/sukses',
    notifyUrl: domain + '/api/ipaymu-callback',
    cancelUrl: domain + '/beli?batal=1',
    referenceId: 'DOM-' + Math.random().toString(36).slice(2, 10).toUpperCase(),
    buyerName: 'Uji Domain',
    buyerEmail: 'uji@lumawall.invalid',
    buyerPhone: '081234567890',
  };

  const teks = JSON.stringify(badan);
  const hash = crypto.createHash('sha256').update(teks).digest('hex').toLowerCase();

  // Kunci API ikut masuk ke dalam string yang ditandatangani. Ini terlihat
  // ganjil - kunci yang sama dipakai sebagai kunci HMAC dan sebagai bagian
  // pesan - tapi begitulah bentuk yang diterima iPaymu, dan itu sudah terbukti
  // dari jembatan yang berhasil membuat transaksi.
  const stringToSign = 'POST:' + VA + ':' + hash + ':' + KEY;
  const tandaTangan = crypto.createHmac('sha256', KEY).update(stringToSign).digest('hex');

  // Cap waktu memakai jam Jakarta. Server bisa saja disetel UTC, dan cap waktu
  // yang meleset 7 jam akan ditolak sebagai tanda tangan tidak sah.
  const sekarang = new Date();
  const wib = new Date(sekarang.getTime() + 7 * 60 * 60 * 1000);
  const p2 = (n) => String(n).padStart(2, '0');
  const capWaktu =
    wib.getUTCFullYear() + p2(wib.getUTCMonth() + 1) + p2(wib.getUTCDate()) +
    p2(wib.getUTCHours()) + p2(wib.getUTCMinutes()) + p2(wib.getUTCSeconds());

  try {
    const r = await fetch('https://my.ipaymu.com/api/v2/payment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        va: VA,
        signature: tandaTangan,
        timestamp: capWaktu,
      },
      body: teks,
    });
    const d = await r.json().catch(() => ({}));
    const pesan = d.Message || d.message || '';
    const url = d.Data && d.Data.Url ? String(d.Data.Url) : '';
    const berhasil = String(d.Status) === '200' && url;

    console.log('  %s %-38s %s', berhasil ? '\u2713' : '\u2717', domain, keterangan);
    console.log('      Status %s  %s', d.Status, pesan || (berhasil ? 'OK' : '-'));
    if (berhasil) {
      console.log('      tautan: %s', url.slice(0, 90));
    }
    return berhasil;
  } catch (e) {
    console.log('  \u2717 %-38s %s', domain, 'gagal menghubungi: ' + e.message);
    return false;
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 mencari domain yang diterima iPaymu \u2550\u2550');
  console.log();
  console.log('  VA : %s', VA);
  console.log();

  const menang = [];
  for (const [domain, ket] of KANDIDAT) {
    if (await coba(domain, ket)) menang.push(domain);
    await new Promise((r) => setTimeout(r, 600));
  }

  console.log();
  if (menang.length === 0) {
    console.log('  TIDAK ADA kandidat yang diterima.');
    console.log('  Artinya domain harus didaftarkan dulu di dashboard iPaymu');
    console.log('  (Pengaturan -> Domain), atau akun ini belum punya domain terdaftar.');
  } else {
    console.log('  DITERIMA: %s', menang.join(', '));
    console.log();
    console.log('  Pakai domain ini untuk returnUrl/notifyUrl/cancelUrl.');
  }
})();
