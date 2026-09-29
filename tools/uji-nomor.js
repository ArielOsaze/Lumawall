#!/usr/bin/env node
/**
 * Cari nomor telepon placeholder yang diterima SEMUA bank.
 *
 * Yang sudah diketahui:
 *   - BRI dan Permata menolak nomor yang bentuknya tidak masuk akal, dengan
 *     "Failed to generate VA". Bank lain menerimanya.
 *   - 081234567890 diterima BRI.
 *   - 081200000000 ditolak BRI.
 *
 * Bedanya: 081234567890 berawalan 0812, yang memang prefix Telkomsel yang
 * benar-benar ada. 081200000000 juga berawalan 0812 tetapi angka berikutnya
 * nol semua, dan BRI tampaknya memeriksa lebih dari sekadar panjang.
 *
 * Nomor placeholder yang dipakai harus diterima semua bank, karena pembeli
 * yang tidak mengisi nomor WhatsApp tidak boleh kehilangan pilihan bank.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-nomor.js
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

function panggil(kanal, telepon) {
  return new Promise((resolve) => {
    const badan = JSON.stringify({
      name: 'Uji Nomor',
      phone: telepon,
      email: 'uji-nomor@lumawall.invalid',
      amount: 10000,
      notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
      referenceId: 'NM-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
      paymentMethod: 'va',
      paymentChannel: kanal,
    });
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
        timeout: 30000,
      },
      (res) => {
        let teks = '';
        res.on('data', (c) => { teks += c; });
        res.on('end', () => {
          let d = null;
          try { d = JSON.parse(teks); } catch (e) { /* biarkan null */ }
          resolve(String(d && d.Status) === '200');
        });
      }
    );
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
    req.write(badan);
    req.end();
  });
}

// Kandidat nomor. Yang diuji: prefix operator yang benar-benar ada, dengan
// angka yang jelas tidak mungkin milik siapa pun.
const KANDIDAT = [
  '081200000001',
  '081211111111',
  '081222222222',
  '081299999999',
  '081311111111',
  '081511111111',
  '081711111111',
  '081811111111',
  '082111111111',
  '085711111111',
  '087711111111',
];

// Bank yang paling ketat, plus satu bank longgar sebagai pembanding.
const BANK = ['bri', 'permata', 'bca'];

(async () => {
  console.log();
  console.log('  \u2550\u2550 nomor mana yang diterima semua bank \u2550\u2550');
  console.log();
  console.log('  %-16s %s', 'nomor', BANK.map((b) => b.toUpperCase().padEnd(8)).join(''));
  console.log('  ' + '\u2500'.repeat(48));

  const diterimaSemua = [];

  for (const nomor of KANDIDAT) {
    const hasil = [];
    for (const bank of BANK) {
      const ok = await panggil(bank, nomor);
      hasil.push(ok);
      await new Promise((r) => setTimeout(r, 900));
    }
    const semua = hasil.every(Boolean);
    if (semua) diterimaSemua.push(nomor);
    console.log('  %-16s %s %s',
      nomor,
      hasil.map((h) => (h ? '\u2713' : '\u2717').padEnd(8)).join(''),
      semua ? '\u2190 diterima semua' : '');
  }

  console.log();
  if (diterimaSemua.length) {
    console.log('  Nomor yang bisa dipakai sebagai placeholder:');
    for (const n of diterimaSemua) console.log('    %s', n);
  } else {
    console.log('  Tidak ada kandidat yang diterima semua bank.');
    console.log('  Berarti nomor telepon tidak bisa dikosongkan di formulir:');
    console.log('  pembeli HARUS mengisinya, atau dua bank harus dibuang.');
  }
})();
