#!/usr/bin/env bash
# Isi kredensial jembatan LumaWall di .env server NexShop, lalu restart layanan.
#
# Kredensial ditulis langsung ke .env server, bukan dikirim lewat argumen
# perintah: argumen terlihat di daftar proses, dan .env server hanya bisa dibaca
# root (mode 600).
#
# Skrip ini idempoten: kalau kuncinya sudah ada, nilainya diganti, bukan
# ditambahkan lagi sehingga tidak ada duplikat yang membuat bingung.
set -euo pipefail

HOST="${NEXSHOP_HOST:-nexshop}"
DIR="/var/www/NEXSHOP_ALL/nexshop-backend"
ENVFILE="$DIR/.env"

VA="1179007792634063"
API_KEY="1A477100-1F52-43A6-AB87-7B67D502578F"
BRIDGE_SECRET="6f3a9c1e8b4d7250af93c6e1d84b027f5a3c9e7d2b6184f0a5c8e3d19b7462af"

say() { printf '\n  === %s ===\n' "$1"; }

say "1. periksa .env server"
ssh -o BatchMode=yes "$HOST" "ls -la '$ENVFILE'"

say "2. tambahkan atau perbarui kunci jembatan"
# Nilai dikirim lewat stdin, bukan argumen, supaya tidak muncul di daftar
# proses mesin ini maupun server.
ssh -o BatchMode=yes "$HOST" "sudo python3 - '$ENVFILE'" <<PY
import sys
from pathlib import Path

p = Path(sys.argv[1])
t = p.read_text(encoding="utf-8")

kunci = {
    "LUMAWALL_IPAYMU_VA": "$VA",
    "LUMAWALL_IPAYMU_API_KEY": "$API_KEY",
    "LUMAWALL_BRIDGE_SECRET": "$BRIDGE_SECRET",
}

baris = t.split("\n")
ada = set()
hasil = []
for b in baris:
    if "=" in b and not b.strip().startswith("#"):
        nama = b.split("=", 1)[0].strip()
        if nama in kunci:
            hasil.append("%s=%s" % (nama, kunci[nama]))
            ada.add(nama)
            continue
    hasil.append(b)

for nama, nilai in kunci.items():
    if nama not in ada:
        hasil.append("%s=%s" % (nama, nilai))

# Pastikan berkas diakhiri satu baris baru saja, tidak menumpuk baris kosong.
teks = "\n".join(hasil).rstrip("\n") + "\n"
p.write_text(teks, encoding="utf-8")

print("  kunci di .env sekarang:")
for nama in kunci:
    print("    %s = (terisi)" % nama)
PY

say "3. pastikan izin berkas tetap ketat"
ssh -o BatchMode=yes "$HOST" "sudo chmod 600 '$ENVFILE' && sudo chown root:root '$ENVFILE' && ls -la '$ENVFILE'"

say "4. cek sintaks server.js"
ssh -o BatchMode=yes "$HOST" "cd '$DIR' && node --check server.js && echo '  sintaks OK'"

say "5. restart layanan"
ssh -o BatchMode=yes "$HOST" "sudo systemctl restart nexshop 2>/dev/null && echo '  nexshop direstart' || (sudo systemctl restart nexshop-backend 2>/dev/null && echo '  nexshop-backend direstart') || echo '  GAGAL restart - periksa nama layanan'"

say "6. tunggu layanan siap"
sleep 8

say "7. uji health jembatan dari dalam server"
ssh -o BatchMode=yes "$HOST" "curl -s -m 10 http://127.0.0.1:3000/api/lumawall/health"

printf '\n'
say "8. uji dari luar"
curl -s -m 15 https://nexshop.cloud/api/lumawall/health || echo "  (gagal dari luar)"

printf '\n\n'
