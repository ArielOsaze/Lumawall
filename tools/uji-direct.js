#!/usr/bin/env node
/**
 * Cari tahu bentuk balasan /payment/direct iPaymu.
 *
 * Tujuannya: menampilkan pembayaran DI SITUS SENDIRI, tanpa mengalihkan
 * pembeli ke halaman iPaymu. Untuk itu kita perlu daftar kanal pembayaran
 * (QRIS, VA bank, e-wallet) beserta datanya.
 *
 * Dijalankan di server NexShop karena hanya dari IP ini iPaymu menerima
 * permintaan.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-direct.js
 */
const fs = require('fs');
const crypto = require('crypto');

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

const VA = env.LUMAWALL_IPAYMU_VA || '';
const KEY = env.LUMAWALL_IPAYMU_API_KEY || '';

function capWaktuJakarta() {
  const sekarang = new Date();
  const wib = new Date(sekarang.getTime() + 7 * 60 * 60 * 1000);
  const p = (n) => String(n).padStart(2, '0');
  return (
    wib.getUTCFullYear() + p(wib.getUTCMonth() + 1) + p(wib.getUTCDate()) +
    p(wib.getUTCHours()) + p(wib.getUTCMinutes()) + p(wib.getUTCSeconds())
  );
}

function tandaTangan(badan) {
  const hash = crypto.createHash('sha256').update(badan).digest('hex').toLowerCase();
  return crypto.createHmac('sha256', KEY).update(`POST:${VA}:${hash}:${KEY}`).digest('hex');
}

async function kirim(jalur, muatan, keterangan) {
  const badan = JSON.stringify(muatan);
  console.log('\n  ══ %s ══', keterangan);
  console.log('  POST %s', jalur);
  try {
    const r = await fetch('https://my.ipaymu.com/api/v2' + jalur, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        va: VA,
        signature: tandaTangan(badan),
        timestamp: capWaktuJakarta(),
      },
      body: badan,
    });
    const d = await r.json().catch(() => ({}));
    console.log('  HTTP %s  Status %s  %s', r.status, d.Status, d.Message || '');
    console.log('  balasan lengkap:');
    console.log(JSON.stringify(d, null, 2).split('\n').map((l) => '    ' + l).join('\n'));
    return d;
  } catch (e) {
    console.log('  GAGAL: %s', e.message);
    return null;
  }
}

(async () => {
  console.log();
  console.log('  ══ mencari bentuk API pembayaran langsung iPaymu ══');
  console.log();
  console.log('  VA : %s', VA);

  const ref = 'DIR-' + Date.now().toString(36).toUpperCase();

  // Langkah 1: minta daftar kanal pembayaran yang tersedia.
  await kirim('/payment/direct', {
    name: 'Uji Direct',
    phone: '081234567890',
    email: 'uji-direct@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: ref,
  }, 'langkah 1: daftar kanal pembayaran');

  await new Promise((r) => setTimeout(r, 800));

  // Langkah 2: pilih satu kanal dan lihat data yang dikembalikan.
  //
  // Kode kanal berbeda-beda per akun, jadi ini hanya contoh. Kalau langkah 1
  // mengembalikan daftar, kode yang benar diambil dari sana.
  for (const [kanal, ket] of [['qris', 'QRIS'], ['bag', 'VA BAG'], ['bca', 'VA BCA']]) {
    await kirim('/payment/direct', {
      name: 'Uji Direct',
      phone: '081234567890',
      email: 'uji-direct@lumawall.invalid',
      amount: 10000,
      notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
      referenceId: ref,
      paymentMethod: 'qris',
      paymentChannel: kanal,
    }, `langkah 2: pilih kanal ${ket}`);
    await new Promise((r) => setTimeout(r, 800));
  }
})();
