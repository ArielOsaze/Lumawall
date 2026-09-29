#!/usr/bin/env node
/**
 * Cari tahu variabel mana yang membuat BRI dan Permata gagal.
 *
 * Keadaannya sekarang:
 *   - BRI dan Permata selalu gagal "Failed to generate VA"
 *   - BCA, BNI, Mandiri, CIMB, BSI, Danamon selalu berhasil
 *   - Lewat jembatan, BRI dan Permata BERHASIL kalau nomor teleponnya sungguhan
 *
 * Jadi ada satu variabel yang berbeda antara dua jalur itu. Yang sudah dicoba
 * dan bukan penyebabnya: batas waktu (iPaymu menjawab dalam 1,5 detik).
 *
 * Uji ini mengubah SATU variabel pada satu waktu dan melihat pengaruhnya.
 * Mengubah beberapa sekaligus akan menghasilkan tebakan, bukan jawaban.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-variabel.js
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

function panggil(muatan) {
  return new Promise((resolve) => {
    const badan = JSON.stringify(muatan);
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
        timeout: 60000,
      },
      (res) => {
        let teks = '';
        res.on('data', (c) => { teks += c; });
        res.on('end', () => {
          let d = null;
          try { d = JSON.parse(teks); } catch (e) { /* biarkan null */ }
          const ok = String(d && d.Status) === '200';
          const isi = (d && d.Data) || {};
          resolve({
            ok,
            pesan: ok ? String(isi.PaymentNo || '') : ((d && d.Message) || ('HTTP ' + res.status)),
          });
        });
      }
    );
    req.on('timeout', () => { req.destroy(); resolve({ ok: false, pesan: 'timeout' }); });
    req.on('error', (e) => resolve({ ok: false, pesan: 'jaringan: ' + e.message }));
    req.write(badan);
    req.end();
  });
}

// Payload dasar, sama seperti yang dikirim jembatan.
function dasar(kanal, ubah) {
  const m = {
    name: 'Uji Variabel',
    phone: '081200000000',
    email: 'uji-variabel@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: 'VR-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
    paymentMethod: 'va',
    paymentChannel: kanal,
  };
  return Object.assign(m, ubah || {});
}

// Setiap kasus: keterangan + fungsi yang mengubah payload.
const KASUS = [
  ['dasar (nomor 081200000000)', () => ({})],
  ['tanpa nomor telepon', () => ({ phone: undefined })],
  ['nomor 081234567890', () => ({ phone: '081234567890' })],
  ['tanpa email', () => ({ email: undefined })],
  ['email @gmail.com', () => ({ email: 'uji@gmail.com' })],
  ['jumlah 18000', () => ({ amount: 18000 })],
  ['jumlah 50000', () => ({ amount: 50000 })],
  ['tanpa name', () => ({ name: undefined })],
  ['name panjang', () => ({ name: 'Nama Pembeli Yang Panjang Sekali Untuk Uji' })],
];

(async () => {
  console.log();
  console.log('  \u2550\u2550 variabel mana yang membuat BRI gagal \u2550\u2550');
  console.log();

  for (const [keterangan, ubah] of KASUS) {
    const muatan = dasar('bri', ubah());
    // Kunci bernilai undefined dibuang: iPaymu menolak body yang memuatnya.
    for (const k of Object.keys(muatan)) {
      if (muatan[k] === undefined) delete muatan[k];
    }

    const h = await panggil(muatan);
    console.log('  %s %-34s %s',
      h.ok ? '\u2713' : '\u2717', keterangan,
      h.ok ? ('VA ' + h.pesan.slice(0, 20)) : h.pesan);
    await new Promise((r) => setTimeout(r, 1200));
  }
})();
