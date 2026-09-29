#!/usr/bin/env node
/**
 * Ukur berapa lama tiap bank butuh, dan apakah transaksinya tetap terbuat
 * ketika kita menyerah menunggu.
 *
 * Ini pertanyaan yang penting dan mudah terlewat. Kalau iPaymu membutuhkan 60
 * detik sementara jembatan menyerah di 40 detik, dua hal buruk terjadi
 * sekaligus:
 *
 *   1. Pembeli melihat "gagal" padahal transaksinya sedang diproses.
 *   2. Kalau ia mencoba lagi, ada DUA transaksi untuk satu pembelian - dan
 *      salah satunya bisa dibayar, sehingga uang masuk tanpa pesanan yang
 *      cocok.
 *
 * Karena itu yang diukur bukan hanya lamanya, melainkan juga apakah permintaan
 * yang kita batalkan tetap menghasilkan transaksi di sisi iPaymu.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-waktu.js
 */
const fs = require('fs');
const crypto = require('crypto');
const https = require('https');

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

// Batas waktu yang diuji. 120 detik cukup jauh di atas apa pun yang mungkin
// dibutuhkan iPaymu, jadi kalau masih habis, masalahnya bukan kecepatan.
const BATAS_MS = 120000;

function panggil(badan) {
  return new Promise((resolve) => {
    const mulai = Date.now();
    const req = https.request(
      {
        hostname: 'my.ipaymu.com',
        path: '/api/v2/payment/direct',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          va: VA,
          signature: tandaTangan(badan),
          timestamp: capWaktuJakarta(),
          'Content-Length': Buffer.byteLength(badan),
        },
        timeout: BATAS_MS,
      },
      (res) => {
        let teks = '';
        res.on('data', (c) => { teks += c; });
        res.on('end', () => {
          let d = null;
          try { d = JSON.parse(teks); } catch (e) { /* biarkan null */ }
          resolve({ ms: Date.now() - mulai, status: res.statusCode, data: d, dibatalkan: false });
        });
      }
    );
    req.on('timeout', () => {
      req.destroy();
      resolve({ ms: Date.now() - mulai, status: 0, data: null, dibatalkan: true });
    });
    req.on('error', (e) => {
      resolve({ ms: Date.now() - mulai, status: 0, data: null, error: e.message, dibatalkan: false });
    });
    req.write(badan);
    req.end();
  });
}

// Periksa apakah transaksi dengan referenceId tertentu ada di iPaymu.
async function periksaAda(referenceId) {
  const badan = JSON.stringify({ referenceId });
  try {
    const r = await fetch('https://my.ipaymu.com/api/v2/transaction', {
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
    return d;
  } catch (e) {
    return { error: e.message };
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 berapa lama tiap bank, dan apakah transaksinya terbuat \u2550\u2550');
  console.log();
  console.log('  batas waktu: %d detik', BATAS_MS / 1000);
  console.log();

  for (const kanal of ['bri', 'permata', 'bca', 'bni']) {
    const ref = 'WK-' + Math.random().toString(36).slice(2, 9).toUpperCase();
    const badan = JSON.stringify({
      name: 'Uji Waktu',
      phone: '081200000000',
      email: 'uji-waktu@lumawall.invalid',
      amount: 10000,
      notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
      referenceId: ref,
      paymentMethod: 'va',
      paymentChannel: kanal,
    });

    const h = await panggil(badan);
    const isi = (h.data && h.data.Data) || {};
    const ok = String(h.data && h.data.Status) === '200';

    console.log('  %-9s %6.1f detik  %s',
      kanal.toUpperCase(), h.ms / 1000,
      h.dibatalkan ? 'DIBATALKAN (batas waktu habis)'
        : ok ? ('OK  VA ' + String(isi.PaymentNo || '').slice(0, 18))
        : ('GAGAL  ' + ((h.data && h.data.Message) || h.error || ('HTTP ' + h.status))));

    // Kalau kita menyerah, apakah transaksinya tetap ada?
    if (h.dibatalkan) {
      await new Promise((r) => setTimeout(r, 5000));
      const cek = await periksaAda(ref);
      const ada = cek && cek.Data;
      console.log('            transaksi tetap terbuat? %s',
        ada ? ('YA - ' + JSON.stringify(ada).slice(0, 90)) : 'tidak');
      if (ada) {
        console.log('            \u26a0 pembeli melihat gagal, padahal VA-nya ada di iPaymu');
      }
    }

    await new Promise((r) => setTimeout(r, 1500));
  }
})();
