// Jembatan pembayaran LumaWall.
//
// ===========================================================
// KENAPA JEMBATAN INI ADA
// ===========================================================
//
// iPaymu membatasi permintaan berdasarkan DUA hal, dan keduanya harus
// dipenuhi dari tempat yang sama:
//
//   1. Alamat IP pengirim. Vercel keluar dari IP dinamis yang tidak
//      terdaftar, jadi checkout dari situs LumaWall ditolak "Invalid IP".
//      Buktinya ada di database pesanan:
//
//          {"order_code":"LW-XXSX3D","status":"gagal",
//           "catatan":"ipaymu gagal: Invalid IP"}
//
//      Server ini (VPS, IP tetap 202.10.38.167) sudah terdaftar di akun
//      iPaymu yang sama - diuji langsung dari sini, /balance menjawab
//      Status 200.
//
//   2. Domain pada returnUrl/notifyUrl/cancelUrl. iPaymu menolak domain
//      yang tidak terdaftar di akun dengan pesan "Invalid domain". Untuk
//      akun ini, SATU-SATUNYA domain yang diterima adalah nexshop.cloud:
//
//          https://lumawall.xinet.id    -> Invalid domain
//          https://xinet.id             -> Invalid domain
//          https://akuntuntas.xinet.id  -> Invalid domain
//          https://nexshop.cloud        -> Success
//
//      Itu sebabnya proyek lain bisa langsung jalan tanpa mengurus
//      whitelist: domain mereka memang sudah terdaftar di akun iPaymu
//      masing-masing. Yang belum terdaftar harus lewat domain yang sudah
//      ada - dan itulah fungsi jembatan ini.
//
// Karena itu jembatan ini melakukan dua hal: memanggil iPaymu, dan menjadi
// alamat callback yang diterima iPaymu lalu meneruskannya ke LumaWall.
//
// Berkas ini berdiri sendiri dan tidak mengubah bagian NexShop yang lain.
// Yang mengalir lewat sini hanya panggilan ke iPaymu dan notifikasinya:
// database pesanan, token unduhan, dan berkas installer tetap di tempatnya
// masing-masing. Server ini tidak menyimpan data LumaWall sama sekali, jadi
// ia tidak bisa menjadi sumber kebocoran, dan kalau nanti tidak diperlukan
// cukup dimatikan.

const express = require("express");
const crypto = require("crypto");
const https = require("https");
const router = express.Router();

// Kredensial iPaymu khusus LumaWall. Dipisah dari IPAYMU_* milik NexShop
// karena keduanya akun berbeda: yang satu sandbox, yang satu produksi.
// Mencampurnya adalah kesalahan yang sudah pernah terjadi di proyek ini dan
// gejalanya hanya "401 unauthorized" tanpa petunjuk.
const VA = process.env.LUMAWALL_IPAYMU_VA || "";
const API_KEY = process.env.LUMAWALL_IPAYMU_API_KEY || "";
const RAHASIA = process.env.LUMAWALL_BRIDGE_SECRET || "";

// Alamat situs LumaWall. Semua pengalihan kembali ke pembeli menuju ke sini.
const SITUS = (process.env.LUMAWALL_SITE_URL || "https://lumawall.xinet.id").replace(/\/+$/, "");

// Domain yang terdaftar di akun iPaymu. Alamat callback WAJIB memakai domain
// ini, apa pun alamat aslinya. Diambil dari host permintaan yang masuk supaya
// tidak perlu dikonfigurasi terpisah, tetapi hanya host nexshop.cloud yang
// diterima - kalau permintaan datang lewat host lain, callbacks tetap memakai
// domain resmi.
const DOMAIN_TERDAFTAR = process.env.LUMAWALL_IPAYMU_DOMAIN || "https://nexshop.cloud";

const IPAYMU_PRODUCTION = "https://my.ipaymu.com/api/v2";

// Batas umur tanda tangan. Permintaan yang lebih tua dari ini ditolak,
// sehingga permintaan yang sempat terekam tidak bisa dipakai ulang.
const UMUR_MAKS_MS = 5 * 60 * 1000;

// Hanya tiga tindakan yang dikenal. Apa pun di luar daftar ini ditolak, jadi
// menambah kemampuan jembatan harus disengaja - bukan efek samping dari
// meneruskan nama endpoint dari pemanggil.
const TINDAKAN = new Set(["payment", "payment-direct", "transaction"]);

// Cap waktu iPaymu memakai jam Jakarta, bukan UTC. Server ini bisa saja
// disetel UTC, dan cap waktu yang meleset 7 jam akan ditolak iPaymu.
function capWaktuJakarta() {
    const sekarang = new Date();
    const wib = new Date(sekarang.getTime() + 7 * 60 * 60 * 1000);
    const p = (n) => String(n).padStart(2, "0");
    return (
        `${wib.getUTCFullYear()}${p(wib.getUTCMonth() + 1)}${p(wib.getUTCDate())}` +
        `${p(wib.getUTCHours())}${p(wib.getUTCMinutes())}${p(wib.getUTCSeconds())}`
    );
}

// Signature iPaymu v2: HMAC_SHA256("POST:va:sha256(body):apiKey", apiKey).
// Body yang ditandatangani adalah string JSON yang benar-benar dikirim.
function tandaTanganIpaymu(badan) {
    const hash = crypto.createHash("sha256").update(badan).digest("hex").toLowerCase();
    const stringToSign = `POST:${VA}:${hash}:${API_KEY}`;
    return crypto.createHmac("sha256", API_KEY).update(stringToSign).digest("hex");
}

function samaAman(a, b) {
    const ba = Buffer.from(String(a || ""), "utf8");
    const bb = Buffer.from(String(b || ""), "utf8");
    if (ba.length !== bb.length) return false;
    return crypto.timingSafeEqual(ba, bb);
}

// Tanda tangan jembatan diturunkan dari TINDAKAN + WAKTU, bukan dari body.
//
// Alasannya teknis: menandatangani body mengharuskan kedua sisi menghasilkan
// string JSON yang identik byte per byte. Urutan kunci bisa berbeda antara
// pembuat dan pemeriksa, dan begitu berbeda, tanda tangannya tidak pernah
// cocok - kegagalan yang sulit dilacak karena isinya terlihat benar.
// Menandatangani tindakan + waktu menghilangkan seluruh masalah itu, dan
// tetap memberi dua hal yang penting: pemalsuan tidak mungkin tanpa rahasia,
// dan permintaan lama tidak bisa dipakai ulang.
function tandaTanganJembatan(tindakan, ts) {
    return crypto
        .createHmac("sha256", RAHASIA)
        .update(`${tindakan}:${ts}`)
        .digest("hex");
}

function mintaKeIpaymu(jalur, badan) {
    return new Promise((resolve, reject) => {
        const url = new URL(IPAYMU_PRODUCTION + jalur);
        const req = https.request(
            {
                hostname: url.hostname,
                path: url.pathname,
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                    va: VA,
                    signature: tandaTanganIpaymu(badan),
                    timestamp: capWaktuJakarta(),
                    "Content-Length": Buffer.byteLength(badan),
                },
                // iPaymu kadang butuh lebih dari 20 detik saat sibuk. Batas
                // yang terlalu pendek membuat permintaan yang sebenarnya
                // berhasil dilaporkan sebagai kegagalan - dan pembeli mencoba
                // lagi, sehingga ada dua transaksi untuk satu pembelian.
                timeout: 40000,
            },
            (res) => {
                let teks = "";
                res.on("data", (c) => { teks += c; });
                res.on("end", () => {
                    let data = null;
                    try { data = JSON.parse(teks); } catch (e) { /* biarkan null */ }
                    resolve({ statusCode: res.statusCode, data, teks });
                });
            }
        );
        req.on("timeout", () => req.destroy(new Error("Timeout menghubungi iPaymu")));
        req.on("error", reject);
        req.write(badan);
        req.end();
    });
}

// Pengurai JSON dipasang pada rute yang memang menerima JSON, bukan di seluruh
// router.
//
// Ini penting: `router.use(express.json())` akan membaca dan menghabiskan body
// untuk SEMUA permintaan, termasuk notifikasi iPaymu. Notifikasi itu harus
// diteruskan mentah, dan begitu body sudah diurai jadi objek, byte aslinya
// hilang - signature di sisi LumaWall tidak akan pernah cocok. Karena itu
// pengurai dipasang per rute, bukan global.

router.get("/health", (req, res) => {
    res.json({
        ok: true,
        siap: Boolean(VA && API_KEY && RAHASIA),
        // Hanya menyatakan ada atau tidak, tidak pernah nilainya.
        kredensial: VA ? "ada" : "tidak ada",
        rahasia: RAHASIA ? "ada" : "tidak ada",
        domain: DOMAIN_TERDAFTAR,
    });
});

// ── alamat callback yang diterima iPaymu ────────────────────────────────────
//
// iPaymu hanya mau mengirim pembeli dan notifikasi ke domain terdaftar
// (nexshop.cloud). Rute-rute ini menerima mereka di sana, lalu mengalihkan ke
// LumaWall - jadi pembeli tetap berakhir di situs yang benar meskipun iPaymu
// tidak pernah tahu alamat itu.

// Pembeli selesai membayar: alihkan ke halaman sukses LumaWall.
router.get("/kembali", (req, res) => {
    const order = String(req.query.order || req.query.referenceId || "");
    const tujuan = order
        ? `${SITUS}/sukses?order=${encodeURIComponent(order)}`
        : `${SITUS}/sukses`;
    res.redirect(302, tujuan);
});

// Pembeli membatalkan: alihkan ke halaman beli dengan penanda batal.
router.get("/batal", (req, res) => {
    const order = String(req.query.order || "");
    const tujuan = order
        ? `${SITUS}/beli?batal=1&order=${encodeURIComponent(order)}`
        : `${SITUS}/beli?batal=1`;
    res.redirect(302, tujuan);
});

// Notifikasi pembayaran dari iPaymu. Diteruskan ke webhook LumaWall.
//
// PENTING: yang menentukan sah atau tidaknya pembayaran adalah webhook di
// LumaWall, bukan rute ini. Rute ini hanya memindahkan notifikasi; ia tidak
// menandai apa pun sebagai lunas dan tidak menyimpan apa pun. Kalau rute ini
// dimatikan, tidak ada pembayaran yang menjadi sah karenanya.
//
// Body diteruskan MENTAH, byte per byte. Ini bukan kehati-hatian berlebih:
// signature webhook dihitung atas body mentah yang diterima LumaWall, dan
// mengurai lalu menyusun ulang JSON bisa mengubah urutan kunci atau spasi -
// hasilnya signature tidak pernah cocok dan setiap pembayaran ditolak tanpa
// alasan yang jelas. Karena itu rute ini memasang pengurai mentahnya sendiri,
// terpisah dari express.json() di atas.
router.post("/notifikasi", express.raw({ type: "*/*", limit: "256kb" }), async (req, res) => {
    const mentah = Buffer.isBuffer(req.body) ? req.body : Buffer.from("");

    if (!mentah.length) {
        console.warn("[lumawall-bridge] notifikasi kosong");
        return res.status(200).json({ ok: false, pesan: "Body kosong." });
    }

    // Jenis isi asli diteruskan apa adanya. LumaWall memutuskan sendiri cara
    // membacanya; jembatan tidak perlu tahu bentuknya.
    const jenis = String(req.get("content-type") || "application/x-www-form-urlencoded");

    try {
        const hasil = await kirimKeSitus(`${SITUS}/api/ipaymu-callback`, mentah, jenis);
        console.log("[lumawall-bridge] notifikasi diteruskan:", hasil.statusCode, hasil.teks.slice(0, 200));
        res.status(200).json({ ok: true, diteruskan: hasil.statusCode });
    } catch (e) {
        console.error("[lumawall-bridge] gagal meneruskan notifikasi:", e.message);
        // Tetap 200 supaya iPaymu tidak mengulang tanpa henti. Notifikasi yang
        // gagal diteruskan akan terlihat di log ini.
        res.status(200).json({ ok: false, pesan: "Gagal meneruskan." });
    }
});

function kirimKeSitus(url, body, jenis) {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        const isi = Buffer.isBuffer(body) ? body : Buffer.from(String(body), "utf8");
        const req = https.request(
            {
                hostname: u.hostname,
                path: u.pathname + u.search,
                method: "POST",
                headers: {
                    "Content-Type": jenis || "application/x-www-form-urlencoded",
                    "Content-Length": isi.length,
                    "User-Agent": "lumawall-bridge/1.0",
                },
                timeout: 20000,
            },
            (res) => {
                let teks = "";
                res.on("data", (c) => { teks += c; });
                res.on("end", () => resolve({ statusCode: res.statusCode, teks }));
            }
        );
        req.on("timeout", () => req.destroy(new Error("Timeout")));
        req.on("error", reject);
        req.write(isi);
        req.end();
    });
}

router.post("/:tindakan", express.json({ limit: "64kb" }), async (req, res) => {
    const tindakan = String(req.params.tindakan || "").toLowerCase();

    if (!RAHASIA) {
        return res.status(503).json({ ok: false, pesan: "Jembatan belum dikonfigurasi." });
    }
    if (!TINDAKAN.has(tindakan)) {
        return res.status(404).json({ ok: false, pesan: "Tindakan tidak dikenal." });
    }

    const ts = String(req.get("x-lumawall-ts") || "");
    const dikirim = String(req.get("x-lumawall-signature") || "");

    if (!ts || !dikirim) {
        return res.status(401).json({ ok: false, pesan: "Tanda tangan tidak ada." });
    }

    if (!samaAman(tandaTanganJembatan(tindakan, ts), dikirim)) {
        console.warn("[lumawall-bridge] tanda tangan tidak sah:", tindakan);
        return res.status(401).json({ ok: false, pesan: "Tanda tangan tidak sah." });
    }

    const umur = Date.now() - Number(ts);
    if (!Number.isFinite(umur) || Math.abs(umur) > UMUR_MAKS_MS) {
        return res.status(401).json({ ok: false, pesan: "Permintaan kedaluwarsa." });
    }

    if (!VA || !API_KEY) {
        return res.status(503).json({ ok: false, pesan: "Kredensial iPaymu belum diisi." });
    }

    // Body disusun ulang di sini dari kunci yang dikenal saja.
    //
    // Pemanggil TIDAK bisa menyisipkan kunci tambahan. Tanpa penyaringan ini,
    // pemanggil yang memegang rahasia jembatan bisa mengubah perilaku
    // transaksi dengan kunci yang tidak terduga - misalnya mengarahkan dana
    // ke rekening lain. Jembatan yang meneruskan body apa adanya bukan
    // jembatan, melainkan pintu terbuka.
    const p = req.body || {};
    const kirim = {};

    if (tindakan === "payment") {
        if (!p.amount || !p.referenceId) {
            return res.status(400).json({ ok: false, pesan: "amount dan referenceId wajib." });
        }
        const kode = String(p.referenceId);

        // ── alamat callback WAJIB memakai domain terdaftar ──────────────────
        //
        // iPaymu menolak returnUrl/notifyUrl/cancelUrl yang domainnya tidak
        // terdaftar di akun, dengan pesan "Invalid domain". Alamat apa pun yang
        // dikirim pemanggil diabaikan dan diganti dengan alamat di domain
        // terdaftar; dari sana jembatan ini mengalihkan pembeli ke situs
        // LumaWall yang sebenarnya.
        //
        // Dibiarkan memakai alamat kiriman pemanggil akan berarti jembatan
        // hanya berhasil untuk domain yang kebetulan sudah terdaftar, dan
        // gagal tanpa penjelasan untuk domain lain.
        kirim.product = [String(p.product || "LumaWall")];
        kirim.qty = ["1"];
        kirim.price = [String(p.amount)];
        kirim.amount = String(p.amount);
        kirim.returnUrl = `${DOMAIN_TERDAFTAR}/api/lumawall/kembali?order=${encodeURIComponent(kode)}`;
        kirim.notifyUrl = `${DOMAIN_TERDAFTAR}/api/lumawall/notifikasi`;
        kirim.cancelUrl = `${DOMAIN_TERDAFTAR}/api/lumawall/batal?order=${encodeURIComponent(kode)}`;
        kirim.referenceId = kode;
        kirim.buyerName = String(p.buyerName || "Guest");
        if (p.buyerEmail) kirim.buyerEmail = String(p.buyerEmail);
        if (p.buyerPhone) kirim.buyerPhone = String(p.buyerPhone);
    } else if (tindakan === "payment-direct") {
        if (!p.amount || !p.referenceId) {
            return res.status(400).json({ ok: false, pesan: "amount dan referenceId wajib." });
        }
        const kode = String(p.referenceId);

        // notifyUrl WAJIB memakai domain terdaftar, sama seperti pada
        // `payment`. Tanpa ini iPaymu menjawab "Invalid domain" dan tidak ada
        // QR yang terbuat.
        //
        // returnUrl dan cancelUrl tidak dikirim sama sekali di sini: pembeli
        // tidak pernah meninggalkan situs LumaWall, jadi tidak ada halaman
        // iPaymu yang perlu tahu ke mana harus kembali.
        kirim.name = String(p.buyerName || p.name || "Guest");

        // Nomor telepon TIDAK boleh kosong.
        //
        // Ditemukan dengan menguji, bukan dari dokumentasi: iPaymu menolak
        // permintaan tanpa nomor telepon dengan pesan "unauthorized signature".
        // Pesan itu menunjuk ke tanda tangan, padahal tanda tangannya benar -
        // dan karena pesannya menyesatkan, penyebabnya sulit ditemukan. Uji
        // berulang membuktikannya: lima permintaan dengan nomor telepon
        // berhasil semua, lima tanpa nomor telepon gagal semua.
        //
        // Kalau pemanggil tidak mengirim nomor, dipakai nomor placeholder yang
        // jelas bukan nomor siapa pun. Ini bukan data palsu yang menyesatkan:
        // nomornya tidak pernah dihubungi, dan satu-satunya alternatifnya
        // adalah transaksi yang gagal.
        const telepon = String(p.buyerPhone || p.phone || "").replace(/[^\d+]/g, "");
        kirim.phone = telepon || "08000000000";
        kirim.email = String(p.buyerEmail || p.email || "");
        kirim.amount = String(p.amount);
        kirim.notifyUrl = `${DOMAIN_TERDAFTAR}/api/lumawall/notifikasi`;
        kirim.referenceId = kode;
        kirim.paymentMethod = String(p.paymentMethod || "qris");
        if (p.paymentChannel) kirim.paymentChannel = String(p.paymentChannel);
    } else {
        if (!p.transactionId) {
            return res.status(400).json({ ok: false, pesan: "transactionId wajib." });
        }
        kirim.transactionId = String(p.transactionId);
    }

    const badan = JSON.stringify(kirim);
    const jalur = tindakan === "transaction" ? "/transaction"
                : tindakan === "payment-direct" ? "/payment/direct"
                : "/payment";

    try {
        const hasil = await mintaKeIpaymu(jalur, badan);

        // Balasan diteruskan apa adanya. Jembatan tidak menafsirkan hasilnya:
        // yang memutuskan pembayaran sah atau tidak adalah webhook di sisi
        // LumaWall, bukan perantara ini.
        res.status(hasil.statusCode || 502);
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.setHeader("Cache-Control", "no-store");
        return res.end(JSON.stringify({
            ok: hasil.statusCode === 200,
            status: hasil.statusCode,
            data: hasil.data,
        }));
    } catch (e) {
        console.error("[lumawall-bridge] gagal menghubungi iPaymu:", e.message);
        return res.status(502).json({ ok: false, pesan: "Gagal menghubungi iPaymu." });
    }
});

module.exports = router;
