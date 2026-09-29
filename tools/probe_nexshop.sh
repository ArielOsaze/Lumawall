#!/usr/bin/env bash
# Menyelidiki infrastruktur NexShop yang sudah live (tanpa mencetak rahasia).
set -u

echo "  ══ 1. endpoint bridge yang mungkin ada ══"
for p in \
  /api/akuntuntas/health \
  /api/akuntuntas/orders \
  /api/akuntuntas/license/verify \
  /api/bridge \
  /api/bridge/health \
  /api/digital \
  /api/digital/products \
  /api/products \
  /api/health
do
  code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "https://nexshop.cloud$p")
  printf "     %-38s -> %s\n" "$p" "$code"
done

echo
echo "  ══ 2. apakah situs NexShop menyebut produk digital ══"
curl -s -m 20 https://nexshop.cloud -o /tmp/nx.html 2>/dev/null
if [ -f /tmp/nx.html ]; then
  echo "     ukuran: $(wc -c < /tmp/nx.html) byte"
  grep -oE "(LumaWall|digital|lisensi|license|akuntuntas)" /tmp/nx.html 2>/dev/null | sort | uniq -c | head -10
else
  echo "     (gagal ambil)"
fi

echo
echo "  ══ 3. env NexShop: nama kunci saja ══"
ENVF="/c/Users/ariel/Documents/NexShop 1.2/nexshop-backend/.env"
if [ -f "$ENVF" ]; then
  grep -oE "^[A-Z_]+" "$ENVF" | sort | head -40
else
  echo "     (tidak ada)"
fi
