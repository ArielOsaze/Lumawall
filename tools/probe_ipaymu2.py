#!/usr/bin/env python3
"""Cari kombinasi endpoint + cara tanda tangan iPaymu yang benar.

iPaymu punya DUA lingkungan yang terpisah total - VA dan API key sandbox tidak
akan pernah diterima di endpoint produksi, dan sebaliknya. Skrip ini mencoba
semuanya dan melaporkan mana yang menjawab, tanpa pernah mencetak kuncinya.

Signature iPaymu v2 (dari dokumentasi resmi):
    signature = HMAC_SHA256(method ":" va ":" body ":" apiKey, apiKey)
body adalah string JSON mentah yang dikirim, bukan hash-nya.
"""
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\ariel\Documents\NexShop 1.2\nexshop-backend\.env")

ENDPOINTS = [
    ("sandbox", "https://sandbox.ipaymu.com/api/v2"),
    ("produksi", "https://my.ipaymu.com/api/v2"),
]


def read_env(path):
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def sign(method, va, body, key, variant):
    if variant == "raw":
        payload = "%s:%s:%s:%s" % (method, va, body, key)
    elif variant == "hashed":
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        payload = "%s:%s:%s:%s" % (method, va, body_hash, key)
    elif variant == "upper_method":
        payload = "%s:%s:%s:%s" % (method.upper(), va, body, key)
    else:
        payload = "%s:%s:%s:%s" % (method, va, body, key)
    return hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def call(base, path, va, key, body, variant):
    ts = time.strftime("%Y%m%d%H%M%S")
    sig = sign("POST", va, body, key, variant)
    req = urllib.request.Request(
        base + path,
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
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "EXC %s" % e


def main():
    env = read_env(ENV)
    va = env.get("IPAYMU_VA", "")
    key = env.get("IPAYMU_API_KEY", "")
    mode = env.get("IPAYMU_MODE", "")

    print("  VA terisi  : %s (panjang %d)" % ("ya" if va else "TIDAK", len(va)))
    print("  key terisi : %s (panjang %d)" % ("ya" if key else "TIDAK", len(key)))
    print("  mode .env  : %s" % (mode or "(kosong)"))
    print()

    body = "{}"
    found = []

    for env_name, base in ENDPOINTS:
        for variant in ("raw", "hashed"):
            code, raw = call(base, "/balance", va, key, body, variant)
            try:
                data = json.loads(raw)
                status = data.get("Status")
                message = str(data.get("Message", ""))[:70]
            except Exception:
                status = "-"
                message = raw[:70].replace("\n", " ")
            mark = "  <<<" if str(status) == "200" else ""
            print("  %-9s %-8s HTTP %-4s Status=%-5s %s%s"
                  % (env_name, variant, code, status, message, mark))
            if str(status) == "200":
                found.append((env_name, base, variant))
        print()

    if found:
        name, base, variant = found[0]
        print("  HASIL: kredensial berlaku di lingkungan %s (cara tanda tangan: %s)" % (name, variant))
        print("         endpoint: %s" % base)
        return 0

    print("  HASIL: tidak ada kombinasi yang diterima")
    print("         artinya kredensial sandbox di .env NexShop sudah tidak berlaku,")
    print("         atau akun iPaymu-nya belum diaktifkan.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
