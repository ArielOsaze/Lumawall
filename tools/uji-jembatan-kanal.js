#!/usr/bin/env node
/**
 * Uji kanal lewat JEMBATAN, bukan langsung ke iPaymu.
 *
 * Perbedaan ini penting: lewat situs, BRI dan Permata selalu gagal "Failed to
 * generate VA", padahal langsung ke iPaymu keduanya berhasil tiga kali dari
 * tiga. Artinya masalahnya ada di antara keduanya - dan satu-satunya yang ada
 * di antara keduanya adalah jembatan.
 *
 * Yang diuji sama persis dengan yang dikirim situs: kanal yang sama, jumlah
 * yang sama, dan lewat rute jembatan yang sama.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-jembatan-kanal.js
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

const KANAL = [
  ['qris', 'qris'],
  ['bni', 'va'],
  ['bca', 'va'],
  ['bri', 'va'],
  ['mandiri', 'va'],
  ['permata', 'va'],
  ['cimb', 'va'],
  ['bsi', 'va'],
  ['danamon', 'va'],
];

async function lewatJembatan(kanal, metode) {
  const ts = String(Date.now());
  const tandaTangan = crypto.createHmac('sha256', RAHASIA)
    .update('payment-direct:' + ts).digest('hex');

  const muatan = {
    amount: 10000,
    referenceId: 'JB-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
    buyerName: 'Uji Jembatan Kanal',
    buyerEmail: 'uji-jb@lumawall.invalid',
    buyerPhone: '081234567890',
    paymentMethod: metode,
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
    if (String(dalam.Status) === '200') {
      const isi = dalam.Data || {};
      return {
        ok: true,
        nomor: isi.PaymentNo || isi.Va || '(tanpa nomor)',
        kanal: isi.Channel || isi.PaymentChannel || '-',
      };
    }
    return { ok: false, pesan: dalam.Message || dalam.message || ('HTTP ' + r.status) };
  } catch (e) {
    return { ok: false, pesan: 'jaringan: ' + e.message };
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 kanal lewat jembatan \u2550\u2550');
  console.log();

  const gagal = [];

  for (const [kanal, metode] of KANAL) {
    const h = await lewatJembatan(kanal, metode);
    if (h.ok) {
      console.log('  \u2713 %-9s %-4s  %s', kanal, h.kanal, String(h.nomor).slice(0, 24));
    } else {
      console.log('  \u2717 %-9s %s', kanal, h.pesan);
      gagal.push(kanal);
    }
    await new Promise((r) => setTimeout(r, 1200));
  }

  console.log();
  if (gagal.length) {
    console.log('  Gagal lewat jembatan: %s', gagal.join(', '));
    console.log();
    console.log('  Kalau kanal yang sama BERHASIL saat dipanggil langsung ke iPaymu,');
    console.log('  perbedaannya ada di jembatan - dan itu yang harus diperiksa.');
  } else {
    console.log('  semua kanal berhasil lewat jembatan.');
  }
})();
