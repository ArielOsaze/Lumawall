#!/usr/bin/env node
/**
 * Cari bentuk balasan /transaction untuk memeriksa status pembayaran.
 *
 * Halaman pembayaran di situs harus tahu kapan pembeli sudah membayar, dan itu
 * berarti memeriksa status ke iPaymu. Tanpa ini, satu-satunya cara pembeli
 * mendapat tautan unduhan adalah menunggu notifikasi yang mungkin tidak sampai
 * kalau ia menutup peramban.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-status.js
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
  const wib = new Date(Date.now() + 7 * 60 * 60 * 1000);
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
    console.log(JSON.stringify(d, null, 2).split('\n').map((l) => '    ' + l).join('\n'));
    return d;
  } catch (e) {
    console.log('  GAGAL: %s', e.message);
    return null;
  }
}

(async () => {
  console.log();
  console.log('  ══ memeriksa bentuk API status transaksi ══');

  const ref = 'ST-' + Date.now().toString(36).toUpperCase();

  // Buat transaksi dulu supaya ada yang diperiksa.
  const buat = await kirim('/payment/direct', {
    name: 'Uji Status',
    phone: '081234567890',
    email: 'uji-status@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: ref,
    paymentMethod: 'qris',
    paymentChannel: 'qris',
  }, 'membuat transaksi ' + ref);

  const trxId = buat && buat.Data && buat.Data.TransactionId;
  const sesiId = buat && buat.Data && buat.Data.SessionId;
  console.log('\n  TransactionId: %s   SessionId: %s', trxId, sesiId);

  await new Promise((r) => setTimeout(r, 1200));

  // Berbagai bentuk permintaan status yang mungkin diterima.
  await kirim('/transaction', { transactionId: trxId }, 'status lewat transactionId');
  await new Promise((r) => setTimeout(r, 800));
  await kirim('/transaction', { referenceId: ref }, 'status lewat referenceId');
  await new Promise((r) => setTimeout(r, 800));
  await kirim('/transaction', { id: trxId }, 'status lewat id');

  // Daftar kanal pembayaran yang tersedia untuk akun ini.
  await new Promise((r) => setTimeout(r, 800));
  await kirim('/payment-channel', {}, 'daftar kanal pembayaran (payment-channel)');
  await new Promise((r) => setTimeout(r, 800));
  await kirim('/payment/direct', {
    name: 'Uji Kanal',
    phone: '081234567890',
    email: 'uji-kanal@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: 'KNL-' + Date.now().toString(36).toUpperCase(),
  }, 'payment/direct tanpa kanal - apakah mengembalikan daftar?');
})();
