#!/usr/bin/env bash
# Pasang variabel lingkungan ke project Vercel yang BENAR (lumawall).
#
# Kesalahan yang diperbaiki di sini: `vercel env add` memasang variabel ke
# project yang tertaut di direktori kerja saat itu. Repositori ini punya
# .vercel/ di akar (project "work") DAN di site/ (project "lumawall"), jadi
# menjalankan perintah dari akar memasang variabel ke "work" - project yang
# tidak melayani situs LumaWall sama sekali. Gejalanya membingungkan: variabel
# terlihat terpasang, tetapi endpoint di situs live tetap menjawab
# "SUPABASE_URL belum diisi".
#
# Skrip ini selalu menargetkan project "lumawall" lewat --cwd site.
set -u

cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"

WINHOME="C:/Users/ariel/.supabase"
ENVF="$WINHOME/lumawall-keys.env"
IPAYMU="$WINHOME/lumawall-ipaymu.env"
PROJECT="lumawall"

say() { printf '  %s\n' "$*"; }

for f in "$ENVF" "$IPAYMU"; do
  if [ ! -f "$f" ]; then
    say "GAGAL: berkas kredensial tidak ada: $f"
    exit 1
  fi
done

SUPA_URL="$(grep '^SUPABASE_URL=' "$ENVF" | cut -d= -f2-)"
SUPA_KEY="$(grep '^SUPABASE_SERVICE_KEY=' "$ENVF" | cut -d= -f2-)"
IPAYMU_VA="$(grep '^IPAYMU_VA=' "$IPAYMU" | cut -d= -f2- | tr -d '[:space:]')"
IPAYMU_KEY="$(grep '^IPAYMU_API_KEY=' "$IPAYMU" | cut -d= -f2- | tr -d '[:space:]')"
IPAYMU_MODE="$(grep '^IPAYMU_MODE=' "$IPAYMU" | cut -d= -f2- | tr -d '[:space:]')"
BRIDGE="$(grep '^LUMAWALL_BRIDGE_SECRET=' "$IPAYMU" | cut -d= -f2- | tr -d '[:space:]')"

say "target project: $PROJECT  (lewat --cwd site)"
say ""
say "nilai yang akan dipasang (panjang saja):"
say "  SUPABASE_URL            ${#SUPA_URL}"
say "  SUPABASE_SERVICE_KEY    ${#SUPA_KEY}"
say "  IPAYMU_VA               ${#IPAYMU_VA}"
say "  IPAYMU_API_KEY          ${#IPAYMU_KEY}"
say "  IPAYMU_MODE             ${#IPAYMU_MODE}"
say "  LUMAWALL_BRIDGE_SECRET  ${#BRIDGE}"
say ""

pasang() {
  # $1 = nama, $2 = nilai
  local nama="$1" nilai="$2" scope
  for scope in production preview development; do
    if printf '%s' "$nilai" | vercel env add "$nama" "$scope" --force --cwd site >/dev/null 2>&1; then
      say "  $nama ($scope)  ok"
    else
      say "  $nama ($scope)  GAGAL"
    fi
  done
}

pasang SUPABASE_URL "$SUPA_URL"
pasang SUPABASE_SERVICE_KEY "$SUPA_KEY"
pasang IPAYMU_VA "$IPAYMU_VA"
pasang IPAYMU_API_KEY "$IPAYMU_KEY"
pasang IPAYMU_MODE "${IPAYMU_MODE:-production}"
pasang LUMAWALL_BRIDGE_SECRET "$BRIDGE"

say ""
say "bersihkan yang salah tempat di project 'work'"
for nama in SUPABASE_URL SUPABASE_SERVICE_KEY IPAYMU_VA IPAYMU_API_KEY IPAYMU_MODE LUMAWALL_BRIDGE_SECRET; do
  for scope in production preview development; do
    vercel env rm "$nama" "$scope" --yes >/dev/null 2>&1 && say "  $nama ($scope) dihapus dari work" || true
  done
done

say ""
say "selesai. Variabel di project 'work' sudah dibersihkan."
say "Deploy ulang:  git commit --allow-empty -m redeploy && git push"
