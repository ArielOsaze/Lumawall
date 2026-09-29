#!/usr/bin/env bash
# Cari kredensial Supabase milik proyek AkunTuntas (cumirppxywzkbrzlvknr).
#
# Tujuannya: fungsi serverless di Vercel perlu service key proyek itu untuk
# menulis pesanan dan token unduhan. Tanpa kunci itu, gerbang pembayaran tidak
# bisa jalan.
#
# Skrip ini HANYA melaporkan di mana kuncinya berada dan panjangnya - tidak
# pernah mencetak nilainya, karena keluaran ini masuk ke log percakapan.
set -u

PROJECT="cumirppxywzkbrzlvknr"
echo "  ══ mencari referensi proyek $PROJECT ══"

# Lokasi yang masuk akal: konfigurasi aplikasi AkunTuntas, folder Cadangan,
# dan proyek NexShop (jembatan ke AkunTuntas).
SEARCH_DIRS=(
  "/c/Users/ariel/AkunTuntas"
  "/c/Users/ariel/AppData/Local/AkunTuntas"
  "/c/Users/ariel/AppData/Roaming/AkunTuntas"
  "/c/Users/ariel/Documents/Cadangan AkunTuntas"
  "/c/Users/ariel/Documents/AkunTuntas Beta Version 1.0.0"
  "/c/Users/ariel/Documents/NexShop 1.2"
  "/c/Users/ariel/Documents/Backup"
)

for d in "${SEARCH_DIRS[@]}"; do
  [ -d "$d" ] || continue
  hits=$(grep -rl "$PROJECT" "$d" 2>/dev/null | grep -v node_modules | head -5)
  if [ -n "$hits" ]; then
    echo "  di $d:"
    echo "$hits" | while read -r f; do echo "     $f"; done
  fi
done

echo
echo "  ══ nama variabel kunci di file .env yang ditemukan ══"
find /c/Users/ariel/Documents /c/Users/ariel/AkunTuntas -maxdepth 4 -name ".env*" 2>/dev/null | head -20 | while read -r f; do
  echo "  $f"
  grep -oE "^[A-Z_]+" "$f" 2>/dev/null | sed 's/^/     /'
done

echo
echo "  ══ berkas konfigurasi AkunTuntas ══"
ls -la /c/Users/ariel/AppData/Local/AkunTuntas/ 2>/dev/null | head -20
