#!/usr/bin/env python3
"""Uji apakah Supabase Storage bisa dipakai sebagai penyimpanan gerbang unduhan.

Latar: proyek Supabase NexShop tidak menerima perintah DDL lewat REST API, jadi
tabel baru tidak bisa dibuat dari sini. Yang bisa dilakukan adalah menulis objek
di bucket. Kalau objek bisa dibuat, dibaca, dan dihapus dengan andal - termasuk
satu perilaku penting: membuat objek yang sudah ada HARUS gagal - maka Storage
cukup untuk menyimpan pesanan dan token, di bucket terpisah yang tidak menyentuh
data NexShop sama sekali.

Perilaku "membuat gagal kalau sudah ada" itu kuncinya. Itu satu-satunya operasi
atomik yang tersedia, dan cukup untuk membangun kunci (mutex) supaya dua
permintaan yang datang bersamaan tidak bisa dua-duanya lolos.

Skrip ini tidak pernah mencetak kunci.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\ariel\Documents\NexShop 1.2\nexshop-backend\.env")
BUCKET = "lumawall"


def read_env(path):
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def call(url, key, method, body=None, headers=None):
    h = {"apikey": key, "Authorization": "Bearer " + key}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def main():
    env = read_env(ENV)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("  kredensial tidak lengkap")
        return 1

    print("  proyek: %s" % url.replace("https://", "").split(".")[0])
    print()

    results = []

    def check(nama, ok, detail=""):
        results.append((nama, ok, detail))
        print("  %s %s%s" % ("\u2713" if ok else "\u2717", nama, ("  -> " + detail) if detail else ""))

    path = "_selftest/probe.json"
    obj_url = "%s/storage/v1/object/%s/%s" % (url, BUCKET, path)
    auth_url = "%s/storage/v1/object/authenticated/%s/%s" % (url, BUCKET, path)
    payload = json.dumps({"uji": True, "waktu": "sekarang"}).encode()

    # ── 1. buat objek baru ────────────────────────────────────────────────────
    code, raw = call(obj_url, key, "POST", payload,
                     {"Content-Type": "application/json", "x-upsert": "false"})
    check("membuat objek baru", code in (200, 201), "HTTP %s" % code)

    # ── 2. buat lagi HARUS gagal (ini yang jadi dasar kunci/mutex) ───────────
    code2, raw2 = call(obj_url, key, "POST", payload,
                       {"Content-Type": "application/json", "x-upsert": "false"})
    check("membuat objek yang sudah ada harus GAGAL", code2 not in (200, 201),
          "HTTP %s" % code2)

    # ── 3. baca kembali lewat jalur privat ────────────────────────────────────
    code3, raw3 = call(auth_url, key, "GET")
    ok3 = code3 == 200 and b'"uji"' in raw3
    check("membaca objek privat", ok3, "HTTP %s, %d byte" % (code3, len(raw3)))

    # ── 4. tanpa kunci harus ditolak ──────────────────────────────────────────
    req = urllib.request.Request(auth_url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code4 = resp.status
    except urllib.error.HTTPError as e:
        code4 = e.code
    except Exception:
        code4 = 0
    check("tanpa kunci harus ditolak", code4 != 200, "HTTP %s" % code4)

    # ── 5. daftar objek ───────────────────────────────────────────────────────
    list_url = "%s/storage/v1/object/list/%s" % (url, BUCKET)
    code5, raw5 = call(list_url, key, "POST",
                       json.dumps({"prefix": "_selftest", "limit": 10}).encode(),
                       {"Content-Type": "application/json"})
    found = False
    if code5 == 200:
        try:
            found = any(i.get("name") == "probe.json" for i in json.loads(raw5))
        except Exception:
            pass
    check("mendaftar isi bucket", code5 == 200 and found, "HTTP %s" % code5)

    # ── 6. timpa dengan upsert ────────────────────────────────────────────────
    code6, raw6 = call(obj_url, key, "POST", json.dumps({"uji": "kedua"}).encode(),
                       {"Content-Type": "application/json", "x-upsert": "true"})
    check("menimpa objek (upsert)", code6 in (200, 201), "HTTP %s" % code6)

    # ── 7. hapus ──────────────────────────────────────────────────────────────
    code7, raw7 = call(obj_url, key, "DELETE")
    check("menghapus objek", code7 in (200, 204), "HTTP %s" % code7)

    # ── 8. setelah dihapus, bisa dibuat lagi ──────────────────────────────────
    code8, raw8 = call(obj_url, key, "POST", payload,
                       {"Content-Type": "application/json", "x-upsert": "false"})
    check("setelah dihapus, bisa dibuat lagi", code8 in (200, 201), "HTTP %s" % code8)

    # bersihkan
    call(obj_url, key, "DELETE")

    gagal = [r for r in results if not r[1]]
    print()
    if gagal:
        print("  %d dari %d uji gagal - Storage belum bisa dipakai sebagai penyimpanan." % (len(gagal), len(results)))
        return 1
    print("  semua %d uji lulus - Storage bisa dipakai, termasuk kunci atomik." % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
