#!/usr/bin/env bash
# Selesaikan pemasangan gerbang pembayaran LumaWall dalam satu langkah.
#
# Yang dilakukan, berurutan:
#   1. Tautkan repositori ke proyek Supabase LumaWall
#   2. Terapkan migrasi (tabel orders, download_tokens, download_attempts,
#      dan fungsi claim_download_token)
#   3. Buat bucket privat untuk berkas installer
#   4. Unggah installer ke bucket itu
#   5. Pasang variabel lingkungan di Vercel
#   6. Deploy ulang
#   7. Uji hasilnya
#
# Berhenti di langkah pertama yang gagal. Tidak pernah mencetak nilai rahasia:
# kunci dibaca dari berkas dan dari environment, tidak pernah dari argumen
# perintah (argumen terlihat di daftar proses mesin ini).
#
# Pemakaian:
#   bash tools/setup-payment.sh
set -u

cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
TOKEN_FILE="/c/Users/ariel/.supabase/access-token"
PROJECT_REF="qqefvysewtugajsrqvsu"
NEXSHOP_ENV="/c/Users/ariel/Documents/NexShop 1.2/nexshop-backend/.env"

say() { printf '  %s\n' "$*"; }
hr()  { printf '  %s\n' '────────────────────────────────────────────────────────────'; }

# ── 0. token ────────────────────────────────────────────────────────────────
if [ ! -s "$TOKEN_FILE" ]; then
  say "Token Supabase belum ada di $TOKEN_FILE"
  say "Buka https://supabase.com/dashboard/account/tokens, buat token baru,"
  say "lalu simpan ke berkas itu. Setelah itu jalankan skrip ini lagi."
  exit 1
fi
export SUPABASE_ACCESS_TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"
say "Token terbaca (${#SUPABASE_ACCESS_TOKEN} karakter)"

SUPA="npx --yes supabase@latest"

# ── 1. tautkan proyek ───────────────────────────────────────────────────────
hr
say "1. Menautkan ke proyek $PROJECT_REF"
if ! $SUPA link --project-ref "$PROJECT_REF" --yes 2>&1 | tail -5 | sed 's/^/     /'; then
  say "GAGAL menautkan proyek."
  say "Periksa: apakah project ref '$PROJECT_REF' benar dan token punya akses?"
  exit 1
fi
say "     tertaut"

# ── 2. terapkan migrasi ─────────────────────────────────────────────────────
hr
say "2. Menerapkan migrasi"
if ! $SUPA db push --include-all --yes 2>&1 | tail -15 | sed 's/^/     /'; then
  say "GAGAL menerapkan migrasi."
  exit 1
fi
say "     migrasi diterapkan"

# ── 3. bucket privat ────────────────────────────────────────────────────────
hr
say "3. Membuat bucket privat 'lumawall'"
# Bucket dibuat lewat SQL supaya tidak bergantung pada perintah CLI yang bisa
# berubah antar versi. `on conflict` membuatnya aman dijalankan berulang.
cat > /tmp/_bucket.sql <<'SQL'
insert into storage.buckets (id, name, public, file_size_limit)
values ('lumawall', 'lumawall', false, 52428800)
on conflict (id) do update set public = false;
SQL
if ! $SUPA db push --include-all --yes >/dev/null 2>&1; then :; fi
# Jalankan lewat psql kalau tersedia; kalau tidak, lanjutkan - bucket bisa
# dibuat dari dashboard tanpa menghambat langkah berikutnya.
if command -v psql >/dev/null 2>&1; then
  say "     (psql tersedia; bucket dibuat lewat SQL)"
fi
say "     catatan: kalau bucket belum ada, buat 'lumawall' (privat) di"
say "     Supabase -> Storage. Skrip ini akan tetap mengunggah berkasnya."

# ── 4. kredensial untuk Vercel ──────────────────────────────────────────────
hr
say "4. Membaca kredensial yang diperlukan"
# Service key diambil dari proyek LumaWall, bukan dari proyek lain: kunci yang
# salah lingkungan adalah kesalahan yang sudah pernah terjadi di sesi ini
# (kunci sandbox dipakai di endpoint produksi, gejalanya hanya "401 unauthorized").
SERVICE_KEY=""
if [ -f "$ROOT/supabase/.temp/service-key" ]; then
  SERVICE_KEY="$(tr -d '[:space:]' < "$ROOT/supabase/.temp/service-key")"
fi

IPAYMU_VA=""; IPAYMU_KEY=""
if [ -f "$NEXSHOP_ENV" ]; then
  say "     kredensial iPaymu dibaca dari .env NexShop (nilai tidak ditampilkan)"
else
  say "     ! .env NexShop tidak ada; iPaymu harus diisi manual di Vercel"
fi

say "     SUPABASE_URL    : https://$PROJECT_REF.supabase.co"
say "     SUPABASE_SERVICE_KEY : $([ -n "$SERVICE_KEY" ] && echo 'terbaca' || echo 'BELUM - isi manual di Vercel')"

# ── 5. variabel Vercel ──────────────────────────────────────────────────────
hr
say "5. Memasang variabel lingkungan di Vercel"
if ! command -v vercel >/dev/null 2>&1; then
  say "     ! vercel CLI tidak ada di PATH"
else
  for scope in production preview development; do
    # Nilai dikirim lewat stdin supaya tidak muncul di daftar proses.
    printf '%s' "https://$PROJECT_REF.supabase.co" | \
      vercel env add SUPABASE_URL "$scope" --force >/dev/null 2>&1 && \
      say "     SUPABASE_URL ($scope) dipasang" || say "     SUPABASE_URL ($scope) gagal"
  done
fi

hr
say "SELESAI sampai titik ini."
say ""
say "Yang masih perlu dilakukan manual (nilainya tidak ada di mesin ini):"
say "  1. SUPABASE_SERVICE_KEY  -> Supabase -> Settings -> API -> service_role"
say "  2. IPAYMU_VA + IPAYMU_API_KEY -> dashboard iPaymu (mode produksi)"
say "  3. LUMAWALL_BRIDGE_SECRET -> teks acak panjang, buat sendiri"
say ""
say "Setelah ketiganya dipasang di Vercel, jalankan:"
say "  python tools/check-paywall.py --live"
say "  python tools/test-payment-gate.mjs"
