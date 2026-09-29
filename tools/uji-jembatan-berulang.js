#!/usr/bin/env node
/**
 * Uji cabang payment-direct di jembatan, berulang kali, dengan dan tanpa nomor
 * telepon.
 *
 * Kenapa uji ini perlu: pengujian langsung ke iPaymu berhasil 15 kali dari 15,
 * tetapi lewat jembatan sebagian permintaan ditolak "unauthorized signature".
 * Perbedaannya harus ada di jembatan, bukan di iPaymu - dan satu-satunya
 * perbedaan yang terlihat antara uji langsung dan permintaan dari situs adalah
 * ada tidaknya nomor telepon.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-jembatan-berulang.js
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

async function lewatJembatan(no, denganTelepon) {
  const ref = 'JB' + no + '-' + Math.random().toString(36).slice(2, 7).toUpperCase();
  const ts = String(Date.now());
  const tandaTangan = crypto.createHmac('sha256', RAHASIA).update('payment-direct:' + ts).digest('hex');

  const muatan = {
    amount: 10000,
    referenceId: ref,
    buyerName: 'Uji Jembatan',
    buyerEmail: 'uji-jembatan@lumawall.invalid',
    paymentMethod: 'qris',
    paymentChannel: 'qris',
  };
  if (denganTelepon) muatan.buyerPhone = '081234567890';

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
    const dalam = d && d.data ? d.data : {};
    const ok = String(dalam.Status) === '200';
    console.log('  %s #%-3d %-14s %s',
      ok ? '\u2713' : '\u2717', no,
      denganTelepon ? 'ada telepon' : 'tanpa telepon',
      ok ? 'OK' : (dalam.Message || dalam.message || 'HTTP ' + r.status));
    return ok;
  } catch (e) {
    console.log('  \u2717 #%-3d %-14s GAGAL: %s', no, denganTelepon ? 'ada telepon' : 'tanpa telepon', e.message);
    return false;
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 uji jembatan payment-direct berulang \u2550\u2550');
  console.log();

  let a = 0;
  let b = 0;

  console.log('  \u2500\u2500 dengan nomor telepon \u2500\u2500');
  for (let i = 1; i <= 5; i += 1) {
    if (await lewatJembatan(i, true)) a += 1;
    await new Promise((r) => setTimeout(r, 900));
  }

  console.log();
  console.log('  \u2500\u2500 tanpa nomor telepon \u2500\u2500');
  for (let i = 6; i <= 10; i += 1) {
    if (await lewatJembatan(i, false)) b += 1;
    await new Promise((r) => setTimeout(r, 900));
  }

  console.log();
  console.log('  ada telepon   : %d dari 5 berhasil', a);
  console.log('  tanpa telepon : %d dari 5 berhasil', b);
  console.log();
  if (a === 5 && b === 0) {
    console.log('  SEBABNYA: nomor telepon kosong. iPaymu menolaknya dengan pesan');
    console.log('  "unauthorized signature" yang menyesatkan.');
  } else if (a === 5 && b === 5) {
    console.log('  Nomor telepon bukan penyebabnya. Periksa hal lain.');
  }
})();
