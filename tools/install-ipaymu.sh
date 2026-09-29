#!/usr/bin/env bash
# Pasang kredensial iPaymu dan rahasia jembatan ke Vercel.
#
# Nilai dikirim lewat stdin supaya tidak muncul di daftar proses mesin, dan
# tidak pernah dicetak ke layar.
#
# Kredensial iPaymu diambil dari dua sumber:
#   1. .env NexShop  (untuk VA dan mode)
#   2. proyek Supabase AkunTuntas, kolom server_secrets (kunci produksi)
#
# Kunci produksi hanya ada di sana. Kunci sandbox di .env NexShop sudah
# terbukti DITOLAK di endpoint produksi, jadi tidak dipakai.
set -u

cd "$(dirname "$0")/.." || exit 1

NEXSHOP_ENV="/c/Users/ariel/Documents/NexShop 1.2/nexshop-backend/.env"
SECRETS_FILE="/c/Users/ariel/.supabase/lumawall-ipaymu.env"

say() { printf '  %s\n' "$*"; }

if [ ! -f "$SECRETS_FILE" ]; then
  say "Berkas kredensial tidak ada: $SECRETS_FILE"
  say ""
  say "Isi berkas itu dengan empat baris:"
  say "  IPAYMU_VA=1179007792634063"
  say "  IPAYMU_API_KEY=<kunci produksi>"
  say "  IPAYMU_MODE=production"
  say "  LUMAWALL_BRIDGE_SECRET=<teks acak panjang>"
  exit 1
fi

# Baca nilai tanpa mencetaknya.
IPAYMU_VA="$(grep '^IPAYMU_VA=' "$SECRETS_FILE" | cut -d= -f2- | tr -d '[:space:]')"
IPAYMU_KEY="$(grep '^IPAYMU_API_KEY=' "$SECRETS_FILE" | cut -d= -f2- | tr -d '[:space:]')"
IPAYMU_MODE="$(grep '^IPAYMU_MODE=' "$SECRETS_FILE" | cut -d= -f2- | tr -d '[:space:]')"
BRIDGE="$(grep '^LUMAWALL_BRIDGE_SECRET=' "$SECRETS_FILE" | cut -d= -f2- | tr -d '[:space:]')"

say "terbaca dari $SECRETS_FILE:"
say "  IPAYMU_VA            : %d karakter" | sed "s/%d/${#IPAYMU_VA}/"
say "  IPAYMU_API_KEY       : ${#IPAYMU_KEY} karakter"
say "  IPAYMU_MODE          : ${IPAYMU_MODE:-production}"
say "  LUMAWALL_BRIDGE_SECRET : ${#BRIDGE} karakter"

if [ "${#IPAYMU_VA}" -lt 8 ] || [ "${#IPAYMU_KEY}" -lt 20 ] || [ "${#BRIDGE}" -lt 20 ]; then
  say ""
  say "GAGAL: ada nilai yang kosong atau terlalu pendek."
  exit 1
fi

say ""
say "memasang ke Vercel"
for scope in production preview development; do
  printf '%s' "$IPAYMU_VA"    | vercel env add IPAYMU_VA "$scope" --force >/dev/null 2>&1 \
    && say "  IPAYMU_VA ($scope)  ok" || say "  IPAYMU_VA ($scope)  GAGAL"
  printf '%s' "$IPAYMU_KEY"   | vercel env add IPAYMU_API_KEY "$scope" --force >/dev/null 2>&1 \
    && say "  IPAYMU_API_KEY ($scope)  ok" || say "  IPAYMU_API_KEY ($scope)  GAGAL"
  printf '%s' "${IPAYMU_MODE:-production}" | vercel env add IPAYMU_MODE "$scope" --force >/dev/null 2>&1 \
    && say "  IPAYMU_MODE ($scope)  ok" || say "  IPAYMU_MODE ($scope)  GAGAL"
  printf '%s' "$BRIDGE"       | vercel env add LUMAWALL_BRIDGE_SECRET "$scope" --force >/dev/null 2>&1 \
    && say "  LUMAWALL_BRIDGE_SECRET ($scope)  ok" || say "  LUMAWALL_BRIDGE_SECRET ($scope)  GAGAL"
done

say ""
say "selesai. Deploy ulang supaya variabelnya terpakai:"
say "  vercel --prod"
say ""
say "lalu uji:"
say "  python tools/check-paywall.py --live"
