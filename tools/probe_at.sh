#!/usr/bin/env bash
# Membaca halaman AkunTuntas yang sudah live untuk mempelajari pola checkout-nya.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)/build/atprobe"
cd "$DIR" || exit 1

echo "  ══ script eksternal ══"
grep -oE '<script[^>]*src="[^"]*"' at.html | head -20

echo
echo "  ══ jumlah <script> ══"
grep -c "<script" at.html

echo
echo "  ══ kata kunci aksi ══"
grep -oE '(Beli|Bayar|Order|Checkout|Unduh|Download|Harga|Rp)[^<]{0,45}' at.html | head -25

echo
echo "  ══ endpoint/url di dalam halaman ══"
grep -oE '(/api/[A-Za-z0-9_/.-]*)|(https://[A-Za-z0-9._/-]+)' at.html | sort -u | head -30

echo
echo "  ══ fetch / XHR ══"
grep -oE '(fetch|XMLHttpRequest|axios)[^;]{0,90}' at.html | head -15
