// Jembatan pembayaran LumaWall.
//
// ===========================================================
// KENAPA JEMBATAN INI ADA
// ===========================================================
//
// iPaymu membatasi permintaan berdasarkan alamat IP pengirim. Vercel keluar
// dari IP dinamis yang tidak terdaftar, jadi setiap checkout dari situs
// LumaWall ditolak. Buktinya ada di database pesanan:
//
//     {"order_code":"LW-XXSX3D","status":"gagal",
//      "catatan":"ipaymu gagal: Invalid IP"}
//
// Server ini (VPS, IP tetap 202.10.38.167) sudah terdaftar di akun iPaymu
// yang sama - diuji langsung dari sini, /balance menjawab Status 200. Jadi
// panggilan ke iPaymu dialihkan lewat server ini.
//
// Berkas ini berdiri sendiri dan tidak mengubah bagian NexShop yang lain.
// Yang mengalir lewat sini hanya panggilan ke iPaymu: database pesanan, token
// unduhan, dan berkas installer tetap di tempatnya masing-masing. Server ini
// tidak menyimpan data LumaWall sama sekali, jadi ia tidak bisa menjadi
// sumber kebocoran, dan kalau nanti tidak diperlukan cukup dimatikan.

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
                timeout: 20000,
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

router.use(express.json({ limit: "64kb" }));

router.get("/health", (req, res) => {
    res.json({
        ok: true,
        siap: Boolean(VA && API_KEY && RAHASIA),
        // Hanya menyatakan ada atau tidak, tidak pernah nilainya.
        kredensial: VA ? "ada" : "tidak ada",
        rahasia: RAHASIA ? "ada" : "tidak ada",
    });
});

router.post("/:tindakan", async (req, res) => {
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
        kirim.product = [String(p.product || "LumaWall")];
        kirim.qty = ["1"];
        kirim.price = [String(p.amount)];
        kirim.amount = String(p.amount);
        kirim.returnUrl = String(p.returnUrl || "");
        kirim.notifyUrl = String(p.notifyUrl || "");
        kirim.cancelUrl = String(p.cancelUrl || "");
        kirim.referenceId = String(p.referenceId);
        kirim.buyerName = String(p.buyerName || "Guest");
        if (p.buyerEmail) kirim.buyerEmail = String(p.buyerEmail);
        if (p.buyerPhone) kirim.buyerPhone = String(p.buyerPhone);
    } else if (tindakan === "payment-direct") {
        if (!p.amount || !p.referenceId) {
            return res.status(400).json({ ok: false, pesan: "amount dan referenceId wajib." });
        }
        kirim.name = String(p.name || "Guest");
        kirim.phone = String(p.phone || "");
        kirim.email = String(p.email || "");
        kirim.amount = String(p.amount);
        kirim.notifyUrl = String(p.notifyUrl || "");
        kirim.referenceId = String(p.referenceId);
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
