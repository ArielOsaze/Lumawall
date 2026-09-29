#!/usr/bin/env node
/**
 * Ukur biaya layanan tiap kanal pembayaran.
 *
 * Ini penting dan mudah terlewat: pembeli melihat "Rp10.000" di formulir, lalu
 * di panel transfer bank diminta mentransfer jumlah yang berbeda. Biaya VA di
 * iPaymu jauh lebih besar daripada QRIS, dan kalau jumlahnya baru muncul setelah
 * pembeli memilih, ia merasa dikenai biaya tersembunyi - di halaman yang
 * seharusnya menjelaskan harga lebih jujur daripada toko lain.
 *
 * Yang dicatat: biaya, total, dan siapa yang menanggungnya (FeeDirection).
 * Kalau yang menanggung adalah PENJUAL, biaya itu tidak boleh ditambahkan ke
 * jumlah yang diminta dari pembeli.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-biaya.js
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

const KANAL = [
  ['qris', 'qris', 'QRIS'],
  ['va', 'bni', 'BNI'],
  ['va', 'bca', 'BCA'],
  ['va', 'bri', 'BRI'],
  ['va', 'mandiri', 'Mandiri'],
  ['va', 'permata', 'Permata'],
  ['va', 'cimb', 'CIMB'],
  ['va', 'bsi', 'BSI'],
  ['va', 'danamon', 'Danamon'],
];

// Harga yang diuji. Dipakai dua nilai supaya terlihat apakah biayanya tetap
// (flat) atau mengikuti persentase - dan itu menentukan cara menuliskannya di
// halaman.
const HARGA = [10000, 18000];

async function ukur(metode, kanal, nama, harga) {
  const badan = JSON.stringify({
    name: 'Uji Biaya',
    phone: '081234567890',
    email: 'uji-biaya@lumawall.invalid',
    amount: harga,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: 'BY-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
    paymentMethod: metode,
    paymentChannel: kanal,
  });

  try {
    const r = await fetch('https://my.ipaymu.com/api/v2/payment/direct', {
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
    if (String(d.Status) !== '200') return null;
    const isi = d.Data || {};
    return {
      nama,
      kanal,
      metode,
      harga,
      biaya: Number(isi.Fee || 0),
      total: Number(isi.Total || 0),
      arah: isi.FeeDirection || '(tidak disebut)',
    };
  } catch (e) {
    return null;
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 biaya layanan tiap kanal \u2550\u2550');
  console.log();
  console.log('  %-10s %-9s %-9s %-9s %-9s %s', 'kanal', 'harga', 'biaya', 'total', '%', 'ditanggung');
  console.log('  ' + '\u2500'.repeat(62));

  const hasil = [];

  for (const [metode, kanal, nama] of KANAL) {
    for (const harga of HARGA) {
      const h = await ukur(metode, kanal, nama, harga);
      if (!h) {
        console.log('  %-10s %-9s GAGAL', nama, harga);
      } else {
        const persen = h.harga ? ((h.biaya / h.harga) * 100).toFixed(2) : '0';
        console.log('  %-10s %-9s %-9s %-9s %-9s %s',
          h.nama, h.harga, h.biaya, h.total, persen + '%', h.arah);
        hasil.push(h);
      }
      await new Promise((r) => setTimeout(r, 900));
    }
    console.log();
  }

  // Ringkasan: apakah biayanya tetap atau mengikuti harga?
  console.log('  \u2550\u2550 ringkasan \u2550\u2550');
  const perKanal = {};
  for (const h of hasil) {
    if (!perKanal[h.nama]) perKanal[h.nama] = [];
    perKanal[h.nama].push(h);
  }
  for (const [nama, daftar] of Object.entries(perKanal)) {
    const biaya = daftar.map((d) => d.biaya);
    const tetap = biaya.length === 2 && biaya[0] === biaya[1];
    const arah = daftar[0].arah;
    console.log('  %-10s biaya %s  %s  ditanggung %s',
      nama,
      tetap ? 'TETAP' : 'MENGIKUTI HARGA',
      biaya.join(' / '),
      arah);
  }
})();
