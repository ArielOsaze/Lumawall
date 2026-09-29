#!/usr/bin/env node
/**
 * Uji ulang setiap kanal beberapa kali, untuk memisahkan kanal yang benar-benar
 * tidak tersedia dari yang hanya gagal sesaat.
 *
 * Ini pembedaan yang penting dan tidak bisa dilakukan dengan satu percobaan.
 * "Invalid payment channel" berarti kanalnya tidak ada untuk akun ini. "Failed
 * to generate VA" berarti kanalnya ada tetapi pembuatan nomornya gagal - dan
 * itu bisa berarti gangguan sesaat di sisi bank, atau memang tidak pernah
 * bekerja.
 *
 * Kalau kanal yang gagal sesaat ikut dibuang dari daftar, pembeli kehilangan
 * pilihan yang sebenarnya bekerja. Kalau kanal yang selalu gagal tetap
 * dicantumkan, pembeli memilihnya dan tidak bisa membayar. Karena itu setiap
 * kanal dicoba beberapa kali, dan yang berhasil minimal sekali tetap dipakai.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-kanal-ulang.js
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

const KANAL = ['qris', 'bni', 'bca', 'bri', 'mandiri', 'permata', 'cimb', 'bsi', 'danamon'];
const PERCOBAAN = 3;

async function coba(kanal) {
  const metode = kanal === 'qris' ? 'qris' : 'va';
  const badan = JSON.stringify({
    name: 'Uji Ulang',
    phone: '081234567890',
    email: 'uji-ulang@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: 'UL-' + Math.random().toString(36).slice(2, 9).toUpperCase(),
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
    if (String(d.Status) === '200') return { ok: true };
    return { ok: false, pesan: d.Message || d.message || ('HTTP ' + r.status) };
  } catch (e) {
    return { ok: false, pesan: 'jaringan: ' + e.message };
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 setiap kanal dicoba %d kali \u2550\u2550', PERCOBAAN);
  console.log();

  const hasil = {};

  for (const kanal of KANAL) {
    let berhasil = 0;
    let pesanTerakhir = '';
    for (let i = 0; i < PERCOBAAN; i += 1) {
      const h = await coba(kanal);
      if (h.ok) berhasil += 1;
      else pesanTerakhir = h.pesan;
      await new Promise((r) => setTimeout(r, 1200));
    }
    hasil[kanal] = { berhasil, pesanTerakhir };

    const tanda = berhasil === PERCOBAAN ? '\u2713' : (berhasil > 0 ? '~' : '\u2717');
    console.log('  %s %-9s %d/%d berhasil%s',
      tanda, kanal, berhasil, PERCOBAAN,
      berhasil < PERCOBAAN ? '  (' + pesanTerakhir + ')' : '');
  }

  console.log();
  console.log('  \u2550\u2550 kesimpulan \u2550\u2550');
  const selalu = Object.entries(hasil).filter(([, h]) => h.berhasil === PERCOBAAN).map(([k]) => k);
  const kadang = Object.entries(hasil).filter(([, h]) => h.berhasil > 0 && h.berhasil < PERCOBAAN).map(([k]) => k);
  const tidak = Object.entries(hasil).filter(([, h]) => h.berhasil === 0).map(([k]) => k);

  console.log('  selalu berhasil : %s', selalu.join(', ') || '(tidak ada)');
  console.log('  kadang berhasil : %s', kadang.join(', ') || '(tidak ada)');
  console.log('  tidak pernah    : %s', tidak.join(', ') || '(tidak ada)');
  console.log();
  if (tidak.length) {
    console.log('  Kanal yang tidak pernah berhasil harus DIBUANG dari daftar:');
    console.log('  pembeli yang memilihnya tidak akan bisa membayar.');
  }
})();
