#!/usr/bin/env python3
"""Periksa kemampuan proyek Supabase NexShop lewat REST API.

Yang dicari: apakah ada fungsi RPC yang bisa menjalankan SQL. Kalau ada, tabel
untuk gerbang unduhan bisa dibuat langsung tanpa perlu akses dashboard.

Tidak pernah mencetak kunci - hanya nama fungsi dan status HTTP.
"""
import json
import sys
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
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get(url, key):
    req = urllib.request.Request(
        url, headers={"apikey": key, "Authorization": "Bearer " + key}, method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def main():
    env = read_env(ENV)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("  kredensial tidak lengkap")
        return 1

    print("  proyek: %s" % url.replace("https://", "").split(".")[0])
    print()

    status, raw = get(url + "/rest/v1/", key)
    if status != 200:
        print("  ! tidak bisa membaca OpenAPI: HTTP %s" % status)
        return 1

    try:
        spec = json.loads(raw)
    except Exception:
        print("  ! respons bukan JSON")
        return 1

    paths = spec.get("paths", {})
    rpcs = sorted(p for p in paths if p.startswith("/rpc/"))
    print("  fungsi RPC yang tersedia: %d" % len(rpcs))
    for r in rpcs:
        methods = ",".join(sorted(paths[r].keys()))
        print("     %-40s %s" % (r.replace("/rpc/", ""), methods))

    # Fungsi yang bisa menjalankan SQL arbitrer sangat berbahaya kalau terbuka;
    # kalau ada, itu temuan penting - bukan sekadar kemudahan.
    berbahaya = [r for r in rpcs if any(
        kata in r.lower() for kata in ("exec", "sql", "query", "run", "ddl"))]
    print()
    if berbahaya:
        print("  RPC yang mungkin bisa menjalankan SQL:")
        for b in berbahaya:
            print("     %s" % b.replace("/rpc/", ""))
    else:
        print("  tidak ada RPC yang bisa menjalankan SQL.")

    # Tabel yang sudah ada, untuk memastikan nama tidak bentrok.
    defs = spec.get("definitions", {})
    print()
    print("  jumlah tabel: %d" % len(defs))
    for nama in ("orders", "products", "download_tokens", "lw_orders", "lw_tokens"):
        print("     %-20s %s" % (nama, "ada" if nama in defs else "-"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
