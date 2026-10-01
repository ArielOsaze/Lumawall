#!/usr/bin/env python3
"""Telusuri halaman tag dewasa DesktopHut dan kumpulkan kartu wallpaper-nya.

Kenapa alat ini ada: kategori "Mature 18+" hanya berisi 249 dari 22.879 entri,
dan permintaannya adalah kategori itu harus banyak dan isinya bagus. Situs
sumbernya tidak punya halaman kategori dewasa, tetapi ia PUNYA halaman tag -
dan tag-tag itu adalah cara situs itu sendiri mengelompokkan wallpapernya.
Memakai tag berarti kategorinya berasal dari situsnya, bukan dari tebakan atas
kata-kata di judul.

KENAPA ALAT INI DITULIS ULANG - dan ini pelajaran yang mahal:

Versi pertama menebak URL wallpaper dari bentuknya: halaman wallpaper dianggap
selalu berakhiran kode 4 huruf, seperti /raiden-shogun-gjwl. Ternyata situs itu
punya DUA bentuk URL:

  lama  /beach-babe                     slug pendek, tanpa kode
  baru  /Anime-Girl-On-The-Beach-...-For-PC

Penyaring kode-4 membuang bentuk lama SELURUHNYA. Terhadap halaman 1 dan 40
tag beach-bikini: dari 44 tautan, hanya 5 yang lolos - 89% hilang. Itu sebabnya
penelusuran berhenti di 182 URL padahal satu tag saja punya 40 halaman.

Jadi sekarang tidak menebak dari bentuk URL. Setiap halaman tag ditulis sebagai
kartu, dan kartunya menandai dirinya sendiri:

  <a href="/slug" class="wallpaper-card ...">
      <img src="...thumbnail..." >
      <span class="badge-res">Full HD</span>
      <h3 class="card-title">Judul Yang Sudah Bersih</h3>
  </a>

Itu satu-satunya penanda yang benar untuk "ini wallpaper", dan sekaligus
memberi judul, thumbnail, dan resolusinya - tiga hal yang di versi lama harus
ditebak dari halaman masing-masing, dan judulnya pun terpotong.

Yang ditelusuri hanya tag dewasa. Halaman tag lain sudah pernah ditelusuri dan
hasilnya ada di katalog.

Setiap halaman ditelusuri sampai habis, bukan hanya halaman pertama: satu tag
bisa punya puluhan halaman, dan berhenti di halaman pertama akan menghasilkan
kategori yang isinya sedikit - persis masalah yang sedang diperbaiki.

Kemajuan ditulis setelah setiap tag, supaya jalannya bisa dilanjutkan.

Pemakaian:
  python tools/kejar-mature.py
  python tools/kejar-mature.py --halaman-maks 60
"""
import argparse
import concurrent.futures as cf
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Tag dewasa di DesktopHut. Ini yang situsnya sendiri pakai untuk mengelompokkan
# wallpaper bergaya dewasa, jadi kategorinya berasal dari situsnya.
TAG = [
    "adult", "bikini", "lingerie", "swimsuit", "sexy", "hot", "seductive",
    "sensual", "pinup", "gravure", "boudoir", "nude", "beach-bikini",
    "leotard", "bodysuit", "catsuit", "stockings", "thigh-highs", "garter",
    "corset", "nightgown", "negligee", "topless", "bra", "panties", "undress",
    "big-breasts", "curvy", "voluptuous", "sultry", "provocative", "cleavage",
    "busty", "milf", "shemale", "hentai", "ecchi", "lewd", "nsfw",
    "bathing", "shower", "bedroom", "massage", "yoga", "gym", "cheerleader",
    "schoolgirl", "nurse", "maid", "bunny", "cat-girl", "fox-girl",
]

# Kartu wallpaper. Struktur ini yang menandai sebuah tautan sebagai wallpaper -
# bukan bentuk URL-nya.
#
# Judulnya diambil dari atribut title, bukan dari card-title. Alasannya:
# card-title membawa keterangan tag situsnya di belakang judul -
# "Beach Babe Live Wallpaper for PC - Beach bikini Wallpaper" - dan membuang
# akhiran itu tidak bisa dilakukan dengan aman, karena judul asli juga memakai
# tanda hubung: "Sabrina Carpenter - Summer Live Wallpaper" akan terpotong jadi
# "Sabrina Carpenter".
#
# Atribut title bersih: "Download Beach Babe Live Wallpaper". Cukup buang kata
# "Download " di depannya.
KARTU = re.compile(
    r'<a\s+href="(/[^"]+)"\s+class="wallpaper-card[^"]*"\s+title="([^"]*)"'
    r'[^>]*>(.*?)</a>',
    re.S)
JUDUL_KARTU = re.compile(r'<h3 class="card-title">(.*?)</h3>', re.S)
THUMB_KARTU = re.compile(r'<img\s+src="([^"]+)"')
RES_KARTU = re.compile(r'<span class="badge-res">(.*?)</span>', re.S)

# Stock footage BUKAN artwork, dan kategorinya mensyaratkan artwork.
#
# Halaman /tag/adult di situs ini berisi dua hal yang sangat berbeda: rekaman
# kamera wanita di kantor dan kolam renang - yang "adult" dalam arti demografis,
# bukan dalam arti kategori ini - dan artwork bergaya anime. Membiarkan keduanya
# masuk berarti kategori Mature berisi video kantor, dan itu persis "kategorinya
# nyasar" yang harus dihindari.
#
# Penandanya ada di judulnya sendiri: situs itu menamai rekamannya dengan
# "Stock Video ...", "Stock Footage ...", dan kadang "Free Stock Video ...".
# Judul dari kartu sudah bersih, jadi penanda ini bisa dibaca langsung - di
# versi lama judulnya harus diambil dari og:title yang terpotong, dan penanda
# ini sering ikut terpotong sehingga rekamannya lolos.
STOCK = re.compile(r"\b(stock\s*(video|footage)|video\s*stock|footage)\b", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def bersih(teks):
    """Teks dari HTML: entitas dibuka, spasi dirapikan."""
    teks = re.sub(r"<[^>]+>", "", teks)
    for a, b in (("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'),
                 ("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">")):
        teks = teks.replace(a, b)
    return re.sub(r"\s+", " ", teks).strip()


def kartu_di(html):
    """Semua kartu wallpaper di satu halaman tag."""
    hasil = {}
    for href, judul_atribut, isi in KARTU.findall(html):
        if href.startswith(("/tag/", "/page/", "/collections", "/explore")):
            continue

        # Judul dari atribut title: "Download Beach Babe Live Wallpaper".
        judul = bersih(judul_atribut)
        judul = re.sub(r"^Download\s+", "", judul, flags=re.I).strip()

        # Kalau atributnya kosong, pakai card-title sebagai cadangan - tetapi
        # hanya bagian sebelum keterangan tag situsnya, dan itu memang bisa
        # memotong judul asli yang bertanda hubung. Karena itu atribut title
        # yang diutamakan.
        if not judul:
            m = JUDUL_KARTU.search(isi)
            if not m:
                continue
            judul = re.split(r"\s+-\s+", bersih(m.group(1)))[0].strip()

        if not judul or STOCK.search(judul):
            continue

        slug = href.rstrip("/").split("/")[-1]
        t = THUMB_KARTU.search(isi)
        r = RES_KARTU.search(isi)
        hasil[slug] = {
            "slug": slug,
            "url": "https://desktophut.com" + href,
            "title": judul,
            "thumbnailUrl": t.group(1) if t else "",
            "resolution": bersih(r.group(1)) if r else "",
        }
    return hasil


def telusuri_tag(tag, halaman_maks):
    """Semua kartu wallpaper di satu tag, sampai halamannya habis."""
    kumpulan = {}
    for halaman in range(1, halaman_maks + 1):
        url = "https://desktophut.com/tag/%s" % tag
        if halaman > 1:
            url += "?page=%d" % halaman

        # Situs ini membalas 410 kalau diminta terlalu cepat - bukan 429, jadi
        # tidak terlihat seperti pembatasan laju, padahal itu. Jeda di antara
        # permintaan membuat penelusuran panjang berjalan sampai selesai.
        if halaman > 1:
            time.sleep(1.5)

        try:
            html = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            # 410 juga berarti "terlalu cepat" di situs ini. Ditunggu sebentar
            # lalu dicoba lagi, bukan langsung ditinggalkan - kalau tidak, satu
            # halaman yang tertunda akan memotong seluruh tag.
            time.sleep(5)
            continue
        except Exception:
            time.sleep(3)
            continue

        baru = kartu_di(html)
        if not baru:
            break

        sebelum = len(kumpulan)
        kumpulan.update(baru)
        # Kalau satu halaman tidak menambah apa pun, halamannya sudah berulang
        # atau habis - berhenti daripada menelusuri halaman kosong tanpa akhir.
        if len(kumpulan) == sebelum and halaman > 1:
            break

    return tag, kumpulan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--halaman-maks", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    kemajuan = OUT / "mature-urls.json"
    sudah = read_json(kemajuan, {"urls": [], "kartu": {}, "tags": {}})
    semua = {}
    for k in (sudah.get("kartu") or {}).values():
        if k.get("slug"):
            semua[k["slug"]] = k
    for u in sudah.get("urls") or []:
        slug = u.rstrip("/").split("/")[-1]
        semua.setdefault(slug, {"slug": slug, "url": u, "title": "",
                                "thumbnailUrl": "", "resolution": ""})
    per_tag = dict(sudah.get("tags") or {})

    print()
    print("  == menelusuri %d tag dewasa ==" % len(TAG))
    print("     sudah terkumpul: %d kartu" % len(semua))
    print()

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for tag, kartu in ex.map(lambda t: telusuri_tag(t, args.halaman_maks), TAG):
            baru = [s for s in kartu if s not in semua]
            per_tag[tag] = len(kartu)
            semua.update(kartu)
            print("     %-16s %4d kartu  (+%d baru)" % (tag, len(kartu), len(baru)))

            # Ditulis setiap tag, supaya jalannya bisa dilanjutkan kalau
            # dihentikan di tengah - dan supaya hasil yang sudah didapat tidak
            # hilang karena satu tag yang gagal.
            write_json(kemajuan, {
                "urls": sorted(k["url"] for k in semua.values()),
                "kartu": semua,
                "tags": per_tag,
            })

    # Tandai sebagai dewasa, supaya pengumpul memasukkannya ke kategori mature
    # atas dasar penilaian situsnya sendiri, bukan tebakan atas judulnya.
    write_json(OUT / "adult-urls.json", {
        "urls": sorted(k["url"] for k in semua.values())
    })

    print()
    print("  == selesai ==")
    print("     kartu dewasa terkumpul : %d" % len(semua))
    print("     disimpan                : %s" % kemajuan)
    print("     daftar dewasa           : %s" % (OUT / "adult-urls.json"))
    print()
    print("  Langkah berikutnya: jalankan pengumpulnya untuk mengukur dan")
    print("  memasukkan kartu-kartu ini ke katalog.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
