#!/usr/bin/env python3
"""Cek koneksi iPaymu memakai kredensial NexShop.

Tidak pernah mencetak kunci. Hanya melaporkan status koneksi, mode, dan
apakah VA-nya valid - cukup untuk tahu apakah jalur pembayaran siap dipakai.

iPaymu menandatangani setiap permintaan:
    signature = HMAC_SHA256(method ":" va ":" body_json ":" api_key) -> hex
lalu dikirim di header `signature`, bersama `va` dan `timestamp` (YmdHis).
"""
import hashlib
import hmac
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\ariel\Documents\NexShop 1.2\nexshop-backend\.env")


def read_env(path):
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        out[k.strip()] = v
    return out


def main():
    if not ENV.exists():
        print("  env NexShop tidak ditemukan")
        return 1
    env = read_env(ENV)

    va = env.get("IPAYMU_VA", "")
    key = env.get("IPAYMU_API_KEY", "")
    mode = env.get("IPAYMU_MODE", "")

    if not va or not key:
        print("  IPAYMU_VA / IPAYMU_API_KEY kosong di .env")
        return 1

    print("  va terisi      : ya (panjang %d)" % len(va))
    print("  key terisi     : ya (panjang %d)" % len(key))
    print("  IPAYMU_MODE    : %s" % (mode or "(kosong)"))
    print("  mode terbaca   : %s" % ("SANDBOX" if str(mode).lower() in ("0", "sandbox", "false") else "PRODUCTION"))

    base = "https://my.ipaymu.com/api/v2"
    print("  endpoint       : %s" % base)

    # ── cek saldo: endpoint paling ringan, membuktikan signature benar ──
    body = "{}"
    method = "POST"
    path = "/api/v2/balance"
    ts = time.strftime("%Y%m%d%H%M%S")
    to_sign = "%s:%s:%s:%s" % (method, va, body, key)
    sig = hmac.new(key.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        base + "/balance",
        data=body.encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "va": va,
            "signature": sig,
            "timestamp": ts,
            "Accept": "application/json",
        },
    )

    print()
    print("  ══ uji /balance ══")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", "replace")
            print("     HTTP %s" % resp.status)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        print("     HTTP %s" % e.code)
    except Exception as e:
        print("     GAGAL koneksi: %s" % e)
        return 1

    # Hanya laporkan struktur, jangan bocorkan saldo/akun.
    try:
        data = json.loads(raw)
    except Exception:
        print("     respons bukan JSON: %s" % re.sub(r"\s+", " ", raw)[:160])
        return 1

    status = data.get("Status")
    message = data.get("Message")
    print("     Status  : %s" % status)
    print("     Message : %s" % message)

    body_data = data.get("Data") or {}
    if isinstance(body_data, dict):
        keys = sorted(body_data.keys())
        print("     field   : %s" % (", ".join(keys) if keys else "(kosong)"))

    ok = str(status) == "200"
    print()
    print("  HASIL: %s" % ("koneksi iPaymu OK - kredensial valid" if ok
                          else "kredensial ditolak / mode salah"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
