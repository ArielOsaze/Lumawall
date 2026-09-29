#!/usr/bin/env bash
# Ambil kunci proyek LumaWall dari Supabase CLI dan pasang ke Vercel.
#
# Tidak pernah mencetak nilai kunci. Kunci ditulis ke berkas di luar repositori,
# lalu dikirim ke Vercel lewat stdin supaya tidak muncul di daftar proses mesin.
#
# Catatan penting soal path: skrip ini memanggil `python` versi Windows, dan
# python itu TIDAK mengerti path gaya MSYS seperti "/tmp/x". Path yang
# diteruskan ke python harus gaya Windows ("C:/..."), kalau tidak ia
# membacanya sebagai path relatif dari akar drive dan gagal FileNotFoundError.
set -u

cd "$(dirname "$0")/.." || exit 1

REF="qqefvysewtugajsrqvsu"
WINHOME="C:/Users/ariel/.supabase"
TMP="$WINHOME/lumawall-keys.json"
ENVF="$WINHOME/lumawall-keys.env"
TOKEN_FILE="/c/Users/ariel/.supabase/access-token"

export SUPABASE_ACCESS_TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"

say() { printf '  %s\n' "$*"; }

say "mengambil kunci proyek $REF"
if ! npx --yes supabase@latest projects api-keys --project-ref "$REF" --output json > "$TMP" 2>/dev/null; then
  say "GAGAL mengambil kunci"
  exit 1
fi

say "membaca kunci"
if ! python - "$TMP" "$ENVF" <<'PY'
import json, sys
from pathlib import Path

sumber = Path(sys.argv[1])
tujuan = Path(sys.argv[2])

data = json.loads(sumber.read_text(encoding='utf-8'))

# Bentuk keluaran CLI berbeda antar versi: kadang {"keys": [...]}, kadang
# langsung [...]. Menangani keduanya lebih murah daripada menebak versinya.
if isinstance(data, dict):
    daftar = data.get('keys', [])
elif isinstance(data, list):
    daftar = data
else:
    daftar = []

keys = {}
for k in daftar:
    if isinstance(k, dict):
        nama = k.get('id') or k.get('name') or ''
        nilai = k.get('api_key') or ''
        if nama and nilai:
            keys[nama] = nilai

service = keys.get('service_role', '')
anon = keys.get('anon', '')

if not service:
    print('  ! service_role tidak ada. Yang tersedia: %s'
          % ', '.join(sorted(keys.keys())))
    sys.exit(1)

tujuan.write_text(
    'SUPABASE_URL=https://qqefvysewtugajsrqvsu.supabase.co\n'
    'SUPABASE_SERVICE_KEY=%s\n'
    'SUPABASE_ANON_KEY=%s\n' % (service, anon),
    encoding='utf-8')

print('  service_role : %d karakter' % len(service))
print('  anon         : %d karakter' % len(anon))
PY
then
  say "GAGAL membaca kunci"
  exit 1
fi

SUPA_URL="https://$REF.supabase.co"
SERVICE_KEY="$(grep '^SUPABASE_SERVICE_KEY=' "$ENVF" | cut -d= -f2-)"

say ""
say "memasang ke Vercel (nilai lewat stdin)"
for scope in production preview development; do
  printf '%s' "$SUPA_URL" | vercel env add SUPABASE_URL "$scope" --force >/dev/null 2>&1 \
    && say "  SUPABASE_URL ($scope)  ok" || say "  SUPABASE_URL ($scope)  GAGAL"
  printf '%s' "$SERVICE_KEY" | vercel env add SUPABASE_SERVICE_KEY "$scope" --force >/dev/null 2>&1 \
    && say "  SUPABASE_SERVICE_KEY ($scope)  ok" || say "  SUPABASE_SERVICE_KEY ($scope)  GAGAL"
done

say ""
say "SELESAI. Masih perlu diisi manual di Vercel:"
say "  IPAYMU_VA, IPAYMU_API_KEY, LUMAWALL_BRIDGE_SECRET"
say ""
say "hapus berkas sementara setelah selesai:"
say "  rm \"$ENVF\" \"$TMP\""
