#!/usr/bin/env node
/**
 * Cari bedanya payload situs dan payload jembatan untuk BRI dan Permata.
 *
 * Keadaannya: lewat situs, BRI dan Permata SELALU gagal "Failed to generate
 * VA" (4 dari 4 percobaan). Lewat jembatan, keduanya SELALU berhasil (9 dari 9
 * kanal). Keduanya memanggil iPaymu dari server yang sama, dengan kredensial
 * yang sama.
 *
 * Satu perbedaan yang terlihat: situs mengirim nomor WhatsApp hanya kalau
 * pembeli mengisinya, dan uji situs tidak mengisinya - jadi jembatan memakai
 * nomor placeholder. Uji jembatan mengirim nomor sungguhan.
 *
 * Kalau hipotesis itu benar, hanya kanal yang meneruskan nomor ke bank yang
 * terpengaruh, dan itu menjelaskan kenapa hanya dua bank yang gagal.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-beda-payload.js
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

const RAHASIA = env.LUMAWALL_BRIDGE_SECRET || '';

// Nomor yang diuji. Yang pertama adalah placeholder yang dipakai jembatan
// sekarang; sisanya nomor sungguhan dengan prefix operator yang berbeda.
const NOMOR = [
  ['08000000000', 'placeholder sekarang'],
  ['081234567890', 'nomor sungguhan'],
  ['08123456789', '10 digit'],
  ['6281234567890', 'format 62'],
];

async function lewatJembatan(kanal, telepon, keterangan) {
  const ts = String(Date.now());
  const tandaTangan = crypto.createHmac('sha256', RAHASIA)
    .update('payment-direct:' + ts).digest('hex');

  const muatan = {
    amount: 10000,
    referenceId: 'BD-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
    buyerName: 'Uji Beda Payload',
    buyerEmail: 'uji-beda@lumawall.invalid',
    buyerPhone: telepon,
    paymentMethod: 'va',
    paymentChannel: kanal,
  };

  try {
    const r = await fetch('http://127.0.0.1:3000/api/lumawall/payment-direct', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-lumawall-ts': ts,
        'x-lumawall-signature': tandaTangan,
      },
      body: JSON.stringify(muatan),
    });
    const d = await r.json().catch(() => ({}));
    const dalam = (d && d.data) || {};
    const ok = String(dalam.Status) === '200';
    const isi = dalam.Data || {};
    return {
      ok,
      pesan: ok ? String(isi.PaymentNo || '').slice(0, 20) : (dalam.Message || dalam.message || 'HTTP ' + r.status),
      keterangan,
      telepon,
    };
  } catch (e) {
    return { ok: false, pesan: 'jaringan: ' + e.message, keterangan, telepon };
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 pengaruh nomor telepon pada tiap bank \u2550\u2550');
  console.log();

  for (const kanal of ['bri', 'permata', 'bca']) {
    console.log('  \u2500\u2500 %s \u2500\u2500', kanal.toUpperCase());
    for (const [telepon, keterangan] of NOMOR) {
      const h = await lewatJembatan(kanal, telepon, keterangan);
      console.log('     %s %-16s %-20s %s',
        h.ok ? '\u2713' : '\u2717', telepon, keterangan,
        h.ok ? ('VA ' + h.pesan) : h.pesan);
      await new Promise((r) => setTimeout(r, 1200));
    }
    console.log();
  }

  console.log('  Kalau hanya nomor placeholder yang gagal, penyebabnya nomor itu -');
  console.log('  dan nomor pengganti harus dipilih yang diterima semua bank.');
})();
