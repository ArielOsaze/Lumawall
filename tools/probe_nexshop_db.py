#!/usr/bin/env python3
"""Lihat apa yang ada di Supabase milik NexShop (tanpa mencetak kunci).

Tujuannya: tahu apakah proyek ini bisa dipakai untuk menyimpan token unduhan
LumaWall dan file installernya.
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


def get(url, key, extra_headers=None):
    headers = {"apikey": key, "Authorization": "Bearer " + key, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "EXC %s" % e


def main():
    env = read_env(ENV)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("  SUPABASE_URL / SUPABASE_SERVICE_KEY kosong")
        return 1

    print("  proyek : %s" % url.replace("https://", "").split(".")[0])
    print("  key    : terisi (panjang %d)" % len(key))
    print()

    print("  ══ tabel (lewat OpenAPI) ══")
    code, raw = get(url + "/rest/v1/", key)
    if code != 200:
        print("     HTTP %s" % code)
        print("     %s" % raw[:200])
        return 1
    try:
        defs = json.loads(raw).get("definitions", {})
    except Exception:
        print("     bukan JSON")
        return 1

    names = sorted(defs.keys())
    print("     %d tabel:" % len(names))
    for n in names:
        print("       - %s" % n)

    print()
    print("  ══ storage bucket ══")
    code, raw = get(url + "/storage/v1/bucket", key)
    if code == 200:
        try:
            buckets = json.loads(raw)
            if not buckets:
                print("     (belum ada bucket)")
            for b in buckets:
                print("       - %-20s public=%s" % (b.get("name"), b.get("public")))
        except Exception:
            print("     %s" % raw[:200])
    else:
        print("     HTTP %s: %s" % (code, raw[:150]))

    print()
    print("  ══ apakah LumaWall sudah ada ══")
    for table, col in (("products", "name"), ("products", "code")):
        code, raw = get(url + "/rest/v1/%s?select=*&limit=20" % table, key)
        if code == 200:
            try:
                rows = json.loads(raw)
                print("     %s: %d baris" % (table, len(rows)))
                for r in rows[:20]:
                    label = r.get("name") or r.get("nama") or r.get("code") or r.get("title") or "?"
                    print("       - %s" % str(label)[:60])
            except Exception:
                print("     %s" % raw[:150])
            break
        else:
            print("     HTTP %s: %s" % (code, raw[:120]))
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
