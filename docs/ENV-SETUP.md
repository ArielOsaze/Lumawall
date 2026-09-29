# Konfigurasi server — LumaWall

Semua nilai di bawah dibaca dari environment variable Vercel pada saat request.
Tidak ada satu pun yang boleh ditulis ke dalam kode: kunci yang masuk ke
repositori harus dianggap sudah bocor, dan repositori ini publik.

Pasang lewat Vercel: **Project → Settings → Environment Variables**. Pasang
untuk **Production** dan **Preview** sekaligus, karena pratinjau juga menjalankan
fungsi yang sama.

---

## Wajib

| Nama | Isi | Dari mana |
|---|---|---|
| `SUPABASE_URL` | `https://qqefvysewtugajsrqvsu.supabase.co` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | kunci `service_role` | Supabase → Project Settings → API |
| `IPAYMU_VA` | nomor Virtual Account iPaymu | dashboard iPaymu |
| `IPAYMU_API_KEY` | API Key iPaymu | dashboard iPaymu |
| `LUMAWALL_BRIDGE_SECRET` | teks acak panjang | buat sendiri: `openssl rand -base64 48` |

`LUMAWALL_BRIDGE_SECRET` dipakai untuk menurunkan token unduhan dari kode
pesanan. Kalau nilai ini berubah, semua tautan unduhan yang sudah diterbitkan
berhenti berlaku — jadi simpan baik-baik dan jangan diganti tanpa alasan.

## Opsional

| Nama | Bawaan | Gunanya |
|---|---|---|
| `IPAYMU_MODE` | `production` | isi `sandbox` untuk menguji tanpa uang sungguhan |
| `SITE_URL` | `https://lumawall.xinet.id` | alamat yang dipakai untuk URL kembali dari iPaymu |
| `LUMAWALL_VERSION` | `4.5.7.0` | versi yang ditampilkan dan nama berkas unduhan |
| `INSTALLER_SUPABASE_URL` | ikut `SUPABASE_URL` | kalau berkas installer disimpan di proyek lain |
| `INSTALLER_SUPABASE_KEY` | ikut `SUPABASE_SERVICE_KEY` | idem |
| `INSTALLER_BUCKET` | `lumawall` | nama bucket penyimpanan installer |
| `INSTALLER_OBJECT` | `LumaWall-Setup-<versi>.exe` | nama objek di bucket |
| `LUMAWALL_INSTALLER_URL` | (kosong) | cadangan: alamat langsung ke berkas installer |

---

## Cara memeriksa sudah benar

```
python tools/check-paywall.py --live
```

Yang diperiksa: berkas installer tidak bisa diunduh tanpa token, endpoint
unduhan menolak token palsu, halaman status menolak kode pesanan palsu, dan
checkout menolak data yang tidak sah.

Kalau ada variabel yang belum dipasang, endpoint akan menjawab **503** dengan
pesan yang menyebut nama variabelnya. Itu disengaja: lebih baik gagal
terang-terangan daripada diam-diam memakai nilai kosong dan menerima
pembayaran yang tidak bisa dilacak.

---

## Yang TIDAK boleh dipasang

| Jangan | Kenapa |
|---|---|
| `SUPABASE_ANON_KEY` | Tidak dipakai di server. Kunci anon memang publik, tapi menaruhnya di sini mengundang seseorang memakainya untuk menulis kode sisi klien yang mengakses tabel. |
| Kunci iPaymu **sandbox** di `IPAYMU_MODE=production` | Sudah pernah terjadi: kunci sandbox ditolak di endpoint produksi, dan gejalanya hanya "401 unauthorized credential" — tampak seperti kunci kedaluwarsa padahal cuma salah lingkungan. |
| Kunci mana pun di dalam berkas `site/` | Berkas di sana disajikan ke peramban. `tools/check-paywall.py` memeriksa ini secara otomatis. |
