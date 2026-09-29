#!/usr/bin/env node
/**
 * Cari kanal pembayaran mana saja yang tersedia untuk akun iPaymu LumaWall.
 *
 * iPaymu mendukung dua metode direct: `qris` dan `va`. Untuk `va`, nama bank
 * dipilih lewat `paymentChannel`, dan tidak semua bank tersedia untuk semua
 * akun. Yang tersedia harus dicari dengan mencoba, karena pesan penolakannya
 * tidak menyebutkan daftar yang benar.
 *
 * Dijalankan di server karena hanya dari IP ini iPaymu menerima permintaan.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-kanal.js
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

// Bank yang mungkin didukung iPaymu. Daftar ini dari dokumentasi mereka, dan
// yang benar-benar aktif untuk akun ini akan terlihat dari hasilnya.
const BANK = ['bni', 'bca', 'bri', 'mandiri', 'permata', 'cimb', 'bsi', 'muamalat',
              'danamon', 'panin', 'maybank', 'ocbc', 'artha', 'sampoerna'];

async function coba(metode, kanal) {
  const ref = 'KN-' + Math.random().toString(36).slice(2, 9).toUpperCase();
  const badan = JSON.stringify({
    name: 'Uji Kanal',
    phone: '081234567890',
    email: 'uji-kanal@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: ref,
    paymentMethod: metode,
    ...(kanal ? { paymentChannel: kanal } : {}),
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
    const ok = String(d.Status) === '200';
    const isi = (d && d.Data) || {};
    const no = isi.PaymentNo || isi.Va || isi.VirtualAccount || isi.PaymentCode || '';
    const nama = isi.PaymentName || isi.BankName || isi.Name || '';
    const kanalBalik = isi.Channel || isi.PaymentChannel || '';

    if (ok) {
      console.log('  \u2713 %-10s %-10s -> %s | %s | %s',
        metode, kanal || '(tanpa kanal)',
        kanalBalik || '-', nama || '-',
        no ? String(no).slice(0, 22) : '(tanpa nomor)');
    } else {
      console.log('  \u2717 %-10s %-10s -> %s', metode, kanal || '(tanpa kanal)',
        d.Message || d.message || ('HTTP ' + r.status));
    }
    return { ok, metode, kanal, nama, no, kanalBalik };
  } catch (e) {
    console.log('  \u2717 %-10s %-10s -> GAGAL: %s', metode, kanal || '(tanpa kanal)', e.message);
    return { ok: false, metode, kanal };
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 kanal pembayaran yang tersedia untuk akun ini \u2550\u2550');
  console.log();

  const tersedia = [];

  console.log('  \u2500\u2500 QRIS \u2500\u2500');
  const q = await coba('qris', 'qris');
  if (q.ok) tersedia.push(q);
  await new Promise((r) => setTimeout(r, 1000));

  console.log();
  console.log('  \u2500\u2500 Virtual Account \u2500\u2500');
  for (const bank of BANK) {
    const h = await coba('va', bank);
    if (h.ok) tersedia.push(h);
    await new Promise((r) => setTimeout(r, 1000));
  }

  console.log();
  console.log('  \u2500\u2500 VA tanpa menyebut bank (apakah ada bawaan?) \u2500\u2500');
  const v = await coba('va', null);
  if (v.ok) tersedia.push(v);

  console.log();
  console.log('  \u2550\u2550 HASIL \u2550\u2550');
  if (!tersedia.length) {
    console.log('  Tidak ada kanal yang berhasil.');
  } else {
    for (const t of tersedia) {
      console.log('  %-8s %-10s %s', t.metode, t.kanal || '-', t.nama || '(tanpa nama)');
    }
    console.log();
    console.log('  %d kanal tersedia.', tersedia.length);
  }
})();
