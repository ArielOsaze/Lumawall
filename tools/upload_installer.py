#!/usr/bin/env python3
"""Unggah installer LumaWall ke penyimpanan privat (Supabase Storage).

Kenapa ini perlu: berkas installer sebelumnya ikut masuk ke repositori situs,
sehingga siapa pun yang menebak alamatnya bisa mengunduhnya gratis - tanpa
membayar. Gerbang pembayaran jadi tidak ada artinya. Berkasnya harus berada di
tempat yang hanya bisa dibaca server, bukan di folder yang disajikan publik.

Bucket dibuat privat (public=false). Hanya service key yang bisa membaca, dan
service key itu hanya ada di environment Vercel - tidak pernah sampai ke
peramban.

Pemakaian:
  python tools/upload_installer.py --check
  python tools/upload_installer.py --upload
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"C:\Users\ariel\Documents\NexShop 1.2\nexshop-backend\.env")
BUCKET = "lumawall"

# Berkas yang diunggah: (path lokal, nama di bucket)
FILES = [
    ("site/assets/downloads/LumaWall-Setup-4.5.7.0.exe", "LumaWall-Setup-4.5.7.0.exe"),
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


def request(url, key, method="GET", body=None, headers=None):
    h = {"apikey": key, "Authorization": "Bearer " + key}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def ensure_bucket(url, key):
    """Buat bucket privat kalau belum ada."""
    status, raw = request(url + "/storage/v1/bucket/" + BUCKET, key)
    if status == 200:
        try:
            info = json.loads(raw)
            public = info.get("public")
            print("  bucket '%s' sudah ada (public=%s)" % (BUCKET, public))
            if public:
                print("  ! bucket publik - memperbaiki jadi privat")
                status, raw = request(
                    url + "/storage/v1/bucket/" + BUCKET, key, method="PUT",
                    body=json.dumps({"public": False}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                print("    hasil: HTTP %s" % status)
            return True
        except Exception:
            return True

    print("  bucket '%s' belum ada - membuat (privat)" % BUCKET)
    body = json.dumps({
        "id": BUCKET,
        "name": BUCKET,
        "public": False,
        "file_size_limit": 52428800,  # 50 MB, cukup untuk installer
        "allowed_mime_types": None,
    }).encode()
    status, raw = request(
        url + "/storage/v1/bucket", key, method="POST", body=body,
        headers={"Content-Type": "application/json"},
    )
    if status in (200, 201):
        print("  bucket dibuat.")
        return True
    print("  ! gagal membuat bucket: HTTP %s %s" % (status, raw[:200].decode("utf-8", "replace")))
    return False


def list_objects(url, key):
    body = json.dumps({"prefix": "", "limit": 100}).encode()
    status, raw = request(
        url + "/storage/v1/object/list/" + BUCKET, key, method="POST", body=body,
        headers={"Content-Type": "application/json"},
    )
    if status != 200:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def upload(url, key, local, remote):
    data = local.read_bytes()
    size_mb = len(data) / (1024 * 1024)
    print("  mengunggah %s (%.1f MB) -> %s/%s" % (local.name, size_mb, BUCKET, remote))

    status, raw = request(
        url + "/storage/v1/object/" + BUCKET + "/" + remote,
        key, method="POST", body=data,
        headers={
            "Content-Type": "application/octet-stream",
            "x-upsert": "true",
            "Cache-Control": "3600",
        },
    )
    if status in (200, 201):
        print("    berhasil (HTTP %s)" % status)
        return True
    print("    ! gagal: HTTP %s %s" % (status, raw[:300].decode("utf-8", "replace")))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="lihat isi bucket")
    ap.add_argument("--upload", action="store_true", help="unggah berkas")
    ap.add_argument("--local", help="berkas lokal (default dari daftar)")
    ap.add_argument("--remote", help="nama di bucket")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    env = read_env(ENV)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("  SUPABASE_URL / SUPABASE_SERVICE_KEY tidak ada di .env NexShop")
        return 1

    print("  proyek: %s" % url.replace("https://", "").split(".")[0])

    if args.check:
        print()
        print("  ══ isi bucket %s ══" % BUCKET)
        items = list_objects(url, key)
        if items is None:
            print("     bucket belum ada")
            return 1
        if not items:
            print("     (kosong)")
        for it in items:
            size = it.get("metadata", {}).get("size") if it.get("metadata") else None
            print("     - %-42s %s byte" % (it.get("name"), size if size else "?"))
        return 0

    if not args.upload:
        ap.print_help()
        return 1

    if not ensure_bucket(url, key):
        return 1

    print()
    jobs = FILES
    if args.local:
        remote = args.remote or Path(args.local).name
        jobs = [(args.local, remote)]

    ok = 0
    for local_path, remote in jobs:
        p = root / local_path
        if not p.exists():
            print("  ! tidak ada: %s" % local_path)
            continue
        if upload(url, key, p, remote):
            ok += 1

    print()
    print("  %d dari %d berkas terunggah." % (ok, len(jobs)))
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
