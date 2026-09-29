#!/usr/bin/env bash
# Pasang jembatan pembayaran LumaWall di server NexShop.
#
# Kenapa lewat skrip dan bukan diketik satu per satu: setiap langkah di sini
# pernah salah di sesi ini, dan kesalahannya tidak selalu kelihatan. Skrip yang
# berhenti di kegagalan pertama jauh lebih aman daripada mengedit berkas server
# dengan tangan sambil menebak.
#
# Idempoten: menjalankannya dua kali tidak merusak apa pun.
set -euo pipefail

HOST="${NEXSHOP_HOST:-nexshop}"
DIR="/var/www/NEXSHOP_ALL/nexshop-backend"

say() { printf '\n  === %s ===\n' "$1"; }

say "1. periksa berkas jembatan ada di server"
ssh -o BatchMode=yes "$HOST" "test -f '$DIR/routes/lumawallRoutes.js' && wc -l '$DIR/routes/lumawallRoutes.js'"

say "2. tambahkan require dan pemasangan rute kalau belum ada"
# Dijalankan di server, dan hanya menambahkan baris yang belum ada. Menulis
# ulang seluruh server.js berisiko menghapus perubahan yang tidak saya lihat.
ssh -o BatchMode=yes "$HOST" "cd '$DIR' && python3 - <<'PY'
from pathlib import Path
import re

p = Path('server.js')
t = p.read_text(encoding='utf-8')
asli = t

# 1) require, ditaruh tepat setelah require akuntuntasRoutes supaya
#    pengelompokan jembatan tetap terbaca.
if 'lumawallRoutes' not in t:
    pola = re.compile(r'^(const akuntuntasRoutes = require\(.*\);\s*)$', re.M)
    m = pola.search(t)
    if not m:
        raise SystemExit('GAGAL: baris require akuntuntasRoutes tidak ditemukan')
    tambahan = m.group(1) + '\nconst lumawallRoutes = require(\"./routes/lumawallRoutes\"); // jembatan pembayaran LumaWall'
    t = t[:m.end()] + '\nconst lumawallRoutes = require(\"./routes/lumawallRoutes\"); // jembatan pembayaran LumaWall' + t[m.end():]
    print('  require ditambahkan')
else:
    print('  require sudah ada')

# 2) pemasangan rute, tepat setelah pemasangan akuntuntasRoutes.
if 'app.use(\"/api/lumawall\"' not in t:
    pola = re.compile(r'^(app\.use\(\"/api/akuntuntas\", akuntuntasRoutes\);.*)$', re.M)
    m = pola.search(t)
    if not m:
        raise SystemExit('GAGAL: baris app.use akuntuntas tidak ditemukan')
    t = t[:m.end()] + '\napp.use(\"/api/lumawall\", lumawallRoutes); // jembatan pembayaran LumaWall' + t[m.end():]
    print('  rute ditambahkan')
else:
    print('  rute sudah ada')

if t != asli:
    p.write_text(t, encoding='utf-8')
    print('  server.js diperbarui')
else:
    print('  server.js tidak berubah')
PY"

say "3. periksa sintaks server.js sebelum me-restart"
ssh -o BatchMode=yes "$HOST" "cd '$DIR' && node --check server.js && echo '  sintaks OK'"

say "4. restart layanan NexShop"
ssh -o BatchMode=yes "$HOST" "sudo systemctl restart nexshop 2>/dev/null || sudo systemctl restart nexshop-backend 2>/dev/null || (cd '$DIR' && pm2 restart all 2>/dev/null) || echo '  (perlu restart manual)'"

say "5. tunggu layanan siap"
sleep 6

say "6. uji health jembatan"
ssh -o BatchMode=yes "$HOST" "curl -s -m 10 http://127.0.0.1:3000/api/lumawall/health"

say "7. uji dari luar"
curl -s -m 15 https://nexshop.cloud/api/lumawall/health || echo "  (gagal dari luar)"

printf '\n  SELESAI\n\n'
