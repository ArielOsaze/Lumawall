#!/usr/bin/env node
/**
 * Panggil jembatan LumaWall langsung dan cetak balasan lengkapnya.
 *
 * Dijalankan di server NexShop, memakai kredensial dari .env server itu.
 * Tujuannya: melihat pesan asli dari iPaymu tanpa lapisan-lapisan di antaranya.
 *
 * Versi pertama uji ini dijalankan dari laptop dan hanya menghasilkan "HTTP 400"
 * dari sisi LumaWall - tidak cukup untuk tahu apa yang salah, karena pesan
 * sebenarnya dari iPaymu ada di dalam body, bukan di status HTTP.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-jembatan.js
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
if (!RAHASIA) {
  console.log('  GAGAL: LUMAWALL_BRIDGE_SECRET tidak ada di .env');
  process.exit(1);
}

const ts = String(Date.now());
const tandaTangan = crypto.createHmac('sha256', RAHASIA).update('payment:' + ts).digest('hex');

const muatan = {
  product: 'LumaWall - lisensi lifetime',
  amount: 10000,
  returnUrl: 'https://lumawall.xinet.id/sukses?order=UJI-JEMBATAN',
  cancelUrl: 'https://lumawall.xinet.id/beli?batal=1',
  notifyUrl: 'https://lumawall.xinet.id/api/ipaymu-callback',
  referenceId: 'UJI-' + Date.now().toString(36).toUpperCase(),
  buyerName: 'Uji Jembatan',
  buyerEmail: 'uji@lumawall.invalid',
  buyerPhone: '081234567890',
};

console.log('  referenceId :', muatan.referenceId);
console.log('  amount      :', muatan.amount);
console.log();

fetch('http://127.0.0.1:3000/api/lumawall/payment', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-lumawall-ts': ts,
    'x-lumawall-signature': tandaTangan,
  },
  body: JSON.stringify(muatan),
})
  .then(async (r) => {
    const teks = await r.text();
    console.log('  HTTP', r.status);
    console.log();
    try {
      const d = JSON.parse(teks);
      console.log('  balasan lengkap:');
      console.log(JSON.stringify(d, null, 2).split('\n').map((l) => '    ' + l).join('\n'));
      const url = d && d.data && d.data.Data && d.data.Data.Url;
      if (url) {
        console.log();
        console.log('  HASIL: BERHASIL - tautan pembayaran dibuat');
        console.log('         ' + String(url).slice(0, 80) + '...');
      } else {
        console.log();
        console.log('  HASIL: iPaymu menolak. Pesan di atas adalah alasannya.');
      }
    } catch (e) {
      console.log('  balasan bukan JSON:', teks.slice(0, 400));
    }
  })
  .catch((e) => {
    console.log('  GAGAL menghubungi jembatan:', e.message);
  });
