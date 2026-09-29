// POST /api/checkout — memulai pembelian LumaWall.
//
// Alur lengkapnya:
//   1. Pembeli mengisi nama + email + WhatsApp di halaman /beli
//   2. Endpoint ini membuat baris `orders` berstatus 'menunggu'
//   3. Endpoint ini memanggil iPaymu untuk membuat sesi pembayaran
//   4. Pembeli membayar lewat QRIS / VA / e-wallet
//   5. iPaymu memanggil /api/ipaymu-callback (webhook)
//   6. Webhook memverifikasi, menandai lunas, dan menerbitkan token unduhan
//   7. Halaman /sukses menampilkan tautan sekali pakai
//
// Yang TIDAK dilakukan endpoint ini: menerbitkan token. Token hanya lahir dari
// webhook yang sudah terverifikasi, sehingga tidak ada cara mendapatkan tautan
// unduhan tanpa pembayaran yang benar-benar tercatat di iPaymu.

const crypto = require('crypto');
const { config, clientIp, supabase, json, readBody, fail, panggilJembatan } = require('./_lib');

// Kanal pembayaran yang tersedia untuk akun iPaymu ini.
//
// Daftarnya hasil pengujian, bukan dari dokumentasi: iPaymu hanya menjawab
// "Invalid payment channel" tanpa menyebutkan mana yang benar. Yang dicoba dan
// berhasil: QRIS, dan Virtual Account untuk delapan bank. Yang ditolak:
// Muamalat, Panin, Maybank, OCBC, Artha, Sampoerna.
//
// `metode` menentukan jenis pembayarannya di iPaymu, `channel` menentukan
// banknya. Keduanya dikirim terpisah karena iPaymu menolak permintaan yang
// menyebut metode tanpa kanal yang cocok.
//
// Nama bank ditulis seperti yang dikenali iPaymu (huruf kecil), sedangkan label
// adalah yang dilihat pembeli.
const KANAL = {
  qris: { metode: 'qris', channel: 'qris', label: 'QRIS', jenis: 'qr' },
  bni: { metode: 'va', channel: 'bni', label: 'BNI', jenis: 'va' },
  bca: { metode: 'va', channel: 'bca', label: 'BCA', jenis: 'va' },
  bri: { metode: 'va', channel: 'bri', label: 'BRI', jenis: 'va' },
  mandiri: { metode: 'va', channel: 'mandiri', label: 'Mandiri', jenis: 'va' },
  permata: { metode: 'va', channel: 'permata', label: 'Permata', jenis: 'va' },
  cimb: { metode: 'va', channel: 'cimb', label: 'CIMB Niaga', jenis: 'va' },
  bsi: { metode: 'va', channel: 'bsi', label: 'BSI', jenis: 'va' },
  danamon: { metode: 'va', channel: 'danamon', label: 'Danamon', jenis: 'va' },
};

function newOrderCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // tanpa I,O,0,1 yang mudah tertukar
  let tail = '';
  const bytes = crypto.randomBytes(6);
  for (let i = 0; i < 6; i += 1) tail += alphabet[bytes[i] % alphabet.length];
  return `LW-${tail}`;
}

// Signature iPaymu v2 sekarang dihitung di jembatan (server NexShop), bukan di
// sini. Fungsi `sign` dan `timestamp` dipindahkan ke jembatan bersama seluruh
// panggilan iPaymu, karena hanya dari sana IP-nya terdaftar. Keduanya sengaja
// dihapus dari berkas ini supaya tidak ada dua salinan logika tanda tangan yang
// bisa saling menyimpang.

function validEmail(v) {
  return typeof v === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) && v.length <= 200;
}

function validName(v) {
  return typeof v === 'string' && v.trim().length >= 2 && v.trim().length <= 120;
}

function validPhone(v) {
  if (v === undefined || v === null || v === '') return true; // opsional
  const digits = String(v).replace(/[^\d]/g, '');
  return digits.length >= 9 && digits.length <= 15;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return json(res, 405, { ok: false, error: 'Gunakan POST.' });
  }

  try {
    const cfg = config();
    const body = await readBody(req);

    const nama = typeof body.nama === 'string' ? body.nama.trim() : '';
    const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
    const wa = typeof body.wa === 'string' ? body.wa.trim() : '';

    if (!validName(nama)) {
      return json(res, 400, { ok: false, error: 'Nama minimal 2 huruf.' });
    }
    if (!validEmail(email)) {
      return json(res, 400, { ok: false, error: 'Alamat email tidak sah.' });
    }
    if (!validPhone(wa)) {
      return json(res, 400, { ok: false, error: 'Nomor WhatsApp tidak sah.' });
    }

    const ip = clientIp(req);
    const orderCode = newOrderCode();
    const amount = cfg.price;

    // Simpan order lebih dulu. Kalau iPaymu gagal, baris ini tetap ada sebagai
    // jejak percobaan, dan statusnya tidak pernah naik ke 'dibayar' tanpa webhook.
    const inserted = await supabase('orders', {
      method: 'POST',
      headers: { Prefer: 'return=representation' },
      body: [{
        order_code: orderCode,
        product_code: cfg.productCode,
        nama_pembeli: nama,
        email_pembeli: email,
        whatsapp: wa || null,
        jumlah: amount,
        status: 'menunggu',
        catatan: `ip=${ip}`,
        kedaluwarsa_pada: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      }],
    });

    if (!Array.isArray(inserted) || !inserted.length) {
      throw Object.assign(new Error('Gagal menyimpan pesanan.'), { statusCode: 502 });
    }

    // ── panggil iPaymu lewat jembatan ─────────────────────────────────────────
    //
    // TIDAK langsung ke iPaymu. Ada dua alasan, dan keduanya ditemukan dengan
    // menguji, bukan dengan membaca dokumentasi:
    //
    //   1. iPaymu membatasi permintaan berdasarkan alamat IP pengirim, dan
    //      Vercel keluar dari IP dinamis yang tidak terdaftar. Permintaan
    //      langsung ditolak "Invalid IP".
    //   2. iPaymu juga membatasi DOMAIN pada returnUrl/notifyUrl/cancelUrl.
    //      Untuk akun ini hanya nexshop.cloud yang diterima; lumawall.xinet.id
    //      ditolak "Invalid domain". Jembatan mengganti alamat itu dengan
    //      domainnya sendiri lalu mengalihkan pembeli ke sini.
    //
    // Yang dipakai adalah `payment-direct`, BUKAN `payment`. Bedanya penting:
    // `payment` mengembalikan tautan ke halaman iPaymu dan pembeli meninggalkan
    // situs ini; `payment-direct` mengembalikan kode QR atau nomor Virtual
    // Account yang bisa ditampilkan di halaman ini sendiri. Pembeli tidak pernah
    // berpindah situs, jadi tidak ada halaman pihak ketiga yang bisa
    // membingungkan atau kehilangan jejak pesanannya.
    //
    // Kanal yang tersedia untuk akun ini dicari dengan menguji satu per satu,
    // karena iPaymu hanya menjawab "Invalid payment channel" tanpa menyebutkan
    // mana yang benar. Yang berhasil: QRIS, dan Virtual Account untuk BNI, BCA,
    // BRI, Mandiri, Permata, CIMB, BSI, dan Danamon. Muamalat, Panin, Maybank,
    // OCBC, Artha, dan Sampoerna ditolak.
    const kanal = KANAL[body.kanal] || KANAL.qris;

    const muatan = {
      amount: amount,
      referenceId: orderCode,
      buyerName: nama,
      buyerEmail: email,
      paymentMethod: kanal.metode,
      paymentChannel: kanal.channel,
    };
    // iPaymu menolak body yang memuat kunci bernilai undefined, jadi nomor
    // WhatsApp hanya ditambahkan kalau memang diisi.
    if (wa) muatan.buyerPhone = wa;

    const upstream = await panggilJembatan(cfg, 'payment-direct', muatan);

    if (!upstream.ok || !upstream.data || String(upstream.data.Status) !== '200') {
      // Detailnya diambil selengkap mungkin. Versi pertama hanya menyimpan
      // "HTTP 400", dan itu tidak cukup untuk tahu apa yang salah - pesan
      // sebenarnya dari iPaymu ada di dalam `data`, bukan di status HTTP.
      const detail = upstream.data
        ? (upstream.data.Message || upstream.data.message
           || (upstream.data.data && (upstream.data.data.Message || upstream.data.data.message))
           || JSON.stringify(upstream.data).slice(0, 300))
        : (upstream.error || `HTTP ${upstream.status}`);
      await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
        method: 'PATCH',
        body: { status: 'gagal', catatan: `ipaymu gagal: ${detail}`.slice(0, 500) },
      }).catch(() => {});
      return json(res, 502, {
        ok: false,
        error: 'Gagal membuka sesi pembayaran. Coba lagi sebentar lagi.',
        order: orderCode,
      });
    }

    const data = upstream.data;
    const sesi = data.Data || {};

    // Nomor transaksi dipakai untuk memeriksa status nanti. Tanpa ini halaman
    // tidak bisa tahu pembayaran sudah masuk, dan pembeli harus menunggu
    // halaman sukses memuat ulang sendiri.
    const transactionId = sesi.TransactionId || sesi.transactionId || null;
    let qrImage = sesi.QrImage || sesi.qrImage || null;
    const qrString = sesi.QrString || sesi.qrString || null;

    // Nomor Virtual Account, untuk pembayaran lewat transfer bank.
    //
    // iPaymu memakai beberapa nama berbeda untuk nilai yang sama, dan mana yang
    // muncul bergantung pada banknya - jadi semuanya diperiksa. Tanpa ini,
    // pembeli yang memilih transfer bank sampai di halaman tanpa nomor tujuan,
    // dan satu-satunya cara ia bisa membayar adalah menebak.
    const nomorVa = sesi.PaymentNo || sesi.paymentNo || sesi.Va || sesi.va
      || sesi.VaNumber || sesi.vaNumber || sesi.VirtualAccount || sesi.virtualAccount
      || sesi.AccountNumber || sesi.accountNumber || sesi.PaymentCode || sesi.paymentCode
      || null;

    // ── QrImage bukan berkas gambar ──────────────────────────────────────────
    //
    // iPaymu mengembalikan ALAMAT yang, kalau dibuka, berisi halaman HTML dengan
    // gambar PNG tertanam sebagai data URL - bukan berkas PNG. Memasangnya
    // langsung ke atribut `src` sebuah <img> menghasilkan gambar yang tidak
    // pernah muncul: peramban menerima HTML, bukan gambar, dan tidak ada pesan
    // kesalahan yang terlihat di halaman.
    //
    // Jadi isinya diambil di sini dan data URL-nya dikembalikan. Dikerjakan di
    // server, bukan di peramban, karena permintaan dari peramban ke domain
    // iPaymu akan ditolak oleh aturan lintas-asal.
    //
    // Kalau pengambilan gagal, QR dibuat ulang dari QrString di sini. QrString
    // adalah isi QR-nya sendiri, jadi kode yang dihasilkan identik dengan yang
    // akan ditampilkan iPaymu - dan itu jauh lebih baik daripada halaman yang
    // memberitahu pembeli "kode QR gagal dimuat".
    if (qrImage) {
      try {
        const r = await fetch(qrImage, { signal: AbortSignal.timeout(8000) });
        const teks = await r.text();
        const m = teks.match(/src="(data:image\/[a-z]+;base64,[^"]+)"/i);
        if (m) {
          qrImage = m[1];
        } else if (teks.trim().startsWith('data:image/')) {
          qrImage = teks.trim();
        }
      } catch (e) {
        console.error('[lumawall] gagal mengambil gambar QR', e && e.message);
      }
    }

    if (!qrImage && qrString) {
      try {
        const QRCode = require('qrcode');
        qrImage = await QRCode.toDataURL(String(qrString), {
          errorCorrectionLevel: 'M',
          margin: 2,
          width: 450,
        });
      } catch (e) {
        console.error('[lumawall] gagal membuat QR dari QrString', e && e.message);
      }
    }

    if (!transactionId) {
      await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
        method: 'PATCH',
        body: { status: 'gagal', catatan: 'ipaymu tidak mengembalikan TransactionId' },
      }).catch(() => {});
      return json(res, 502, {
        ok: false,
        error: 'iPaymu tidak mengembalikan nomor transaksi.',
        order: orderCode,
      });
    }

    await supabase(`orders?order_code=eq.${encodeURIComponent(orderCode)}`, {
      method: 'PATCH',
      body: {
        sesi_pembayaran: sesi.SessionId || null,
        // Nomor transaksi disimpan di sini supaya halaman status bisa
        // memeriksanya tanpa memanggil iPaymu lagi dari sisi peramban - dan
        // tanpa membocorkan kredensial ke peramban.
        acuan_pembayaran: String(transactionId),
      },
    }).catch(() => {});

    return json(res, 200, {
      ok: true,
      order: orderCode,
      amount,
      // Jumlah yang benar-benar dibayar pembeli, termasuk biaya layanan kalau
      // ada. Ditampilkan terpisah supaya tidak ada kejutan di halaman QR.
      total: sesi.Total || amount,
      fee: sesi.Fee || 0,
      // `jenis` memberi tahu halaman apa yang harus ditampilkan: kode QR atau
      // nomor Virtual Account. Halaman tidak perlu menebak dari ada-tidaknya
      // salah satu nilainya.
      jenis: kanal.jenis,
      kanal: kanal.channel,
      kanalLabel: kanal.label,
      qrImage,
      qrString,
      // Nomor tujuan transfer. Hanya ada untuk pembayaran lewat bank.
      nomorVa,
      namaVa: sesi.PaymentName || sesi.paymentName || sesi.BankName || sesi.bankName || kanal.label,
      channel: sesi.Channel || kanal.label,
      expiredAt: sesi.Expired || null,
    });
  } catch (err) {
    return fail(res, err);
  }
};
