#!/usr/bin/env node
/**
 * Cari tahu kenapa sebagian permintaan ditolak "unauthorized signature".
 *
 * Gejalanya: dua transaksi pertama berhasil, lalu yang berikutnya ditolak. Pola
 * seperti itu menunjuk ke salah satu dari tiga hal, dan ketiganya harus
 * dibedakan sebelum diperbaiki:
 *
 *   1. Batas laju (rate limit). Permintaan yang berdekatan ditolak, yang
 *      berjarak diterima.
 *   2. Cap waktu. Kalau jam server meleset dari jam iPaymu, tanda tangan
 *      dianggap kedaluwarsa.
 *   3. Cap waktu berulang. Kalau dua permintaan dalam detik yang sama memakai
 *      cap waktu identik, iPaymu bisa menganggapnya pengiriman ulang.
 *
 * Uji ini mengirim permintaan dengan jarak berbeda dan mencatat mana yang
 * diterima, jadi penyebabnya terlihat dari polanya.
 *
 * Pemakaian (di server):
 *   node /tmp/uji-laju.js
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

function capWaktuJakarta(geserDetik) {
  const wib = new Date(Date.now() + 7 * 60 * 60 * 1000 + (geserDetik || 0) * 1000);
  const p = (n) => String(n).padStart(2, '0');
  return (
    wib.getUTCFullYear() + p(wib.getUTCMonth() + 1) + p(wib.getUTCDate()) +
    p(wib.getUTCHours()) + p(wib.getUTCMinutes()) + p(wib.getUTCSeconds())
  );
}

function tandaTangan(badan, cap) {
  const hash = crypto.createHash('sha256').update(badan).digest('hex').toLowerCase();
  return crypto.createHmac('sha256', KEY).update(`POST:${VA}:${hash}:${KEY}`).digest('hex');
}

async function kirim(no, capGeser, keterangan) {
  const ref = 'LAJU' + no + '-' + Math.random().toString(36).slice(2, 7).toUpperCase();
  const badan = JSON.stringify({
    name: 'Uji Laju',
    phone: '081234567890',
    email: 'uji-laju@lumawall.invalid',
    amount: 10000,
    notifyUrl: 'https://nexshop.cloud/api/lumawall/notifikasi',
    referenceId: ref,
    paymentMethod: 'qris',
    paymentChannel: 'qris',
  });
  const cap = capWaktuJakarta(capGeser);

  const mulai = Date.now();
  try {
    const r = await fetch('https://my.ipaymu.com/api/v2/payment/direct', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        va: VA,
        signature: tandaTangan(badan, cap),
        timestamp: cap,
      },
      body: badan,
    });
    const d = await r.json().catch(() => ({}));
    const ok = String(d.Status) === '200';
    console.log('  %s #%d %-34s %s  %sms',
      ok ? '\u2713' : '\u2717', no, keterangan,
      ok ? 'OK' : (d.Message || d.message || 'HTTP ' + r.status),
      Date.now() - mulai);
    return ok;
  } catch (e) {
    console.log('  \u2717 #%d %-34s GAGAL: %s', no, keterangan, e.message);
    return false;
  }
}

(async () => {
  console.log();
  console.log('  \u2550\u2550 mencari penyebab "unauthorized signature" \u2550\u2550');
  console.log();
  console.log('  Jam server (WIB) : %s', capWaktuJakarta());
  console.log();

  // ── uji 1: berurutan cepat, 5 kali ──────────────────────────────────────
  console.log('  \u2500\u2500 uji 1: lima permintaan berurutan cepat \u2500\u2500');
  let berhasil = 0;
  for (let i = 1; i <= 5; i += 1) {
    if (await kirim(i, 0, 'berurutan')) berhasil += 1;
  }
  console.log('  %d dari 5 berhasil', berhasil);
  console.log();

  // ── uji 2: berjarak 3 detik ─────────────────────────────────────────────
  console.log('  \u2500\u2500 uji 2: tiga permintaan berjarak 3 detik \u2500\u2500');
  let berhasil2 = 0;
  for (let i = 1; i <= 3; i += 1) {
    if (await kirim(10 + i, 0, 'berjarak 3 detik')) berhasil2 += 1;
    if (i < 3) await new Promise((r) => setTimeout(r, 3000));
  }
  console.log('  %d dari 3 berhasil', berhasil2);
  console.log();

  // ── uji 3: cap waktu digeser ────────────────────────────────────────────
  //
  // Kalau jam server meleset, hanya geseran tertentu yang diterima. Geseran
  // yang diterima menunjukkan besar selisihnya, dan arahnya menunjukkan jam
  // server terlalu cepat atau terlalu lambat.
  console.log('  \u2500\u2500 uji 3: cap waktu digeser dari jam server \u2500\u2500');
  for (const geser of [-300, -60, -10, 0, 10, 60, 300]) {
    await kirim(20 + Math.abs(geser), geser, 'geser ' + (geser >= 0 ? '+' : '') + geser + 's');
    await new Promise((r) => setTimeout(r, 1200));
  }
})();
