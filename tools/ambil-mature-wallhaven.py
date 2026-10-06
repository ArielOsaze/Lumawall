#!/usr/bin/env python3
"""Ambil 1000+ entri anime mature dari wallhaven, lewat pencarian tag.

KENAPA ALAT INI ADA:

Permintaannya: "cari yg mature banyakin ini cuma 69 masa aku mat at least 1000
buat mature pastiin anime mature ya".

Sumber yang sudah dipakai - moewalls dan desktophut - hanya punya sekitar 80
dan 150 judul dewasa. Tidak ada sumber gratis mana pun yang punya 1000 VIDEO
anime dewasa. wallhaven punya puluhan ribu gambar anime bergaya ecchi pada HD
ke atas, dan itu cukup.

APA ARTINYA, DAN DITULIS DI LISENSI TIAP ENTRI:

  Entri ini GAMBAR STATIS, bukan video. Kategori "anime" di wallhaven berarti
  ilustrasinya bergaya anime, bukan adegan dari serial anime. Jadi ini ilustrasi
  anime, bukan potongan anime.

KENAPA PER TAG, BUKAN MENYAPU SELURUH KATEGORI:

Menyapu seluruh kategori memang memberi 62.684 kandidat, tetapi wallhaven tidak
mengembalikan tag pada hasil pencarian - jadi setiap gambar butuh satu
permintaan tambahan untuk mendapat namanya. Untuk 1100 entri itu berarti 1100
permintaan, atau sekitar 27 menit pada jeda 1,5 detik yang diwajibkan.

Mencari per tag memberi nama itu gratis: tag yang dicari sudah menjadi namanya.
Seratus tag x lima halaman = 500 permintaan, sekitar 12 menit, dan hasilnya
sama banyaknya.

PENYARING:

  - categories=010     hanya kategori anime
  - purity=010         hanya "sketchy" (ecchi), yaitu bit tengah dari tiga
                       bit wallhaven. Dibuktikan dari aritmetika situsnya:
                       SFW saja 163.785, sketchy saja 99.849, keduanya
                       263.634 - tepat jumlahnya, jadi 100 = SFW dan
                       010 = sketchy. "nsfw" (001) tidak dipakai: isinya
                       eksplisit, dan aplikasi ini dijual di Microsoft Store
                       yang melarangnya
  - atleast=1920x1080  HD ke atas; katalog mensyaratkan itu
  - lanskap saja       potret tidak muat di layar lebar; disaring di sini
                       karena filter rasio pada pencarian memotong hasil
                       terlalu banyak ("swimsuit" tinggal 3 dari 156)

Jeda 1,5 detik antar permintaan: wallhaven membatasi 45 permintaan per menit,
dan tanpa jeda pengambilan berhenti di tengah dengan HTTP 429.

KENAPA sorting=date_added, BUKAN toplist:

"toplist" dibatasi ke jendela waktu tertentu, dan tanpa parameter topRange
jendela itu jatuh ke nilai bawaan yang hanya menyisakan 67 gambar. Dibuktikan
dengan membandingkan mode pengurutan pada query yang sama:

    toplist tanpa topRange   total=67      last_page=3
    toplist + topRange=1y    total=1119    last_page=47
    toplist + topRange=1M    total=67      last_page=3
    date_added               total=17963   last_page=749

Itu sebabnya pengambilan selalu berhenti di sekitar 67 entri, berapa pun
banyaknya halaman yang diminta - bukan karena batas laju, dan bukan karena
tag-nya salah. date_added memberi seluruh 17.963 hasil dan urutannya tetap.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SIMPAN = W / "build" / "wallhaven-mature.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TARGET = 1150
JEDA = 1.5
HALAMAN_MAKS = 60

# Tag yang dicari, dan yang menjadi nama entri. Semuanya tag ecchi anime yang
# benar-benar ada di wallhaven, dengan jumlah hasil yang sudah diperiksa:
# cleavage 2095, stockings 3369, maid 1701, bunny girl 768, beach 480,
# swimsuit 156, bikini 118, underwear 72, ecchi 64.
# Tag yang benar-benar dipakai di wallhaven, diurutkan dari yang paling
# produktif. Yang terbukti kosong sudah dibuang - "poolside", "onsen",
# "bikini armor", "sarong", "tan lines", "nymph", "siren" dan sejenisnya
# hanya menghabiskan waktu.
TAG = [
    # pakaian renang dan pantai - inti kategori ini
    "swimsuit", "bikini", "beach", "swimwear", "summer", "pool",
    "one-piece swimsuit", "school swimsuit", "sundress", "sunbathing",
    # pakaian dalam dan pakaian ketat
    "lingerie", "underwear", "bra", "panties", "stockings", "thighhighs",
    "leotard", "bodysuit", "corset", "garter belt", "nightgown",
    "negligee", "camisole", "slip dress", "see-through", "wet clothes",
    # potongan dan gaya
    "cleavage", "midriff", "bare shoulders", "backless", "off shoulder",
    "plunging neckline", "halter neck", "choker", "barefoot",
    # tokoh dan kostum
    "maid", "nurse", "bunny girl", "bunny suit", "cat girl", "fox girl",
    "cheerleader", "waitress", "secretary", "teacher", "office lady",
    "shrine maiden", "witch", "demon girl", "succubus", "vampire",
    "elf", "angel", "goddess", "queen", "princess", "knight",
    "samurai", "ninja", "kunoichi", "idol", "dancer", "mermaid",
    "fairy", "valkyrie", "sorceress", "assassin", "kimono", "yukata",
    "ecchi", "dress",
]

_terakhir = [0.0]


def get_json(url, timeout=60, percobaan=5):
    for i in range(percobaan):
        selang = time.time() - _terakhir[0]
        if selang < JEDA:
            time.sleep(JEDA - selang)
        try:
            r = urllib.request.Request(url, headers=UA)
            isi = urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")
            _terakhir[0] = time.time()
            return json.loads(isi)
        except Exception as e:
            _terakhir[0] = time.time()
            if "429" in str(e):
                time.sleep(20 + 15 * i)
                continue
            if i == percobaan - 1:
                raise
            time.sleep(3 * (i + 1))
    return None


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MENGAMBIL 1000+ ANIME MATURE DARI WALLHAVEN")
print("  ══════════════════════════════════════════════════════════════════")
print()

katalog = json.load(open(CATALOG, encoding="utf-8"))
items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
sudah = set()
for e in items:
    for k in ("videoUrl", "thumbnailUrl", "sourceUrl"):
        v = (e.get(k) or "").strip().lower()
        if v:
            sudah.add(v)
print("  katalog: %d entri, %d url sudah ada" % (len(items), len(sudah)))
print()

# Pencarian per tag dengan sorting=date_added.
#
# Setiap tag memberi total penuh (swimsuit 12.538, bikini 12.975, cleavage
# 18.359, stockings 10.295), dan tag yang dicari langsung menjadi nama entri -
# jadi tidak perlu satu permintaan tambahan per gambar untuk namanya.
terkumpul = {}
for tag in TAG:
    if len(terkumpul) >= TARGET:
        break
    dapat_tag = 0
    for halaman in range(1, HALAMAN_MAKS + 1):
        url = ("https://wallhaven.cc/api/v1/search"
               "?q=%s&categories=010&purity=010&atleast=1920x1080"
               "&sorting=date_added&per_page=24&page=%d"
               % (urllib.parse.quote(tag), halaman))
        try:
            d = get_json(url)
        except Exception as e:
            print("     %-18s hal %d gagal: %s" % (tag, halaman, str(e)[:36]))
            break
        if d is None:
            break
        data = d.get("data", [])
        if not data:
            break

        for e in data:
            path = (e.get("path") or "").strip()
            thumb = (e.get("thumbs") or {}).get("large") or ""
            if not path or not thumb:
                continue
            if path.lower() in sudah or path.lower() in terkumpul:
                continue
            w = int(e.get("dimension_x") or 0)
            h = int(e.get("dimension_y") or 0)
            # Lanskap sungguhan dan tajam. Potret tidak muat di layar lebar,
            # dan di bawah 1920 tidak tajam di monitor 1080p.
            if w < 1920 or h < 1080 or w <= h:
                continue
            terkumpul[path.lower()] = {
                "id": e.get("id"),
                "path": path,
                "thumb": thumb,
                "res": "%dx%d" % (w, h),
                "tag": tag,
                "page": e.get("url"),
                "favorit": e.get("favorites") or 0,
            }
            dapat_tag += 1

        if len(terkumpul) >= TARGET:
            break

    print("     %-18s +%-3d  (total %d)" % (tag, dapat_tag, len(terkumpul)))

print()
print("  terkumpul: %d entri unik" % len(terkumpul))

SIMPAN.parent.mkdir(parents=True, exist_ok=True)
with open(SIMPAN, "w", encoding="utf-8") as f:
    json.dump(list(terkumpul.values()), f, ensure_ascii=False, indent=1)
print("  disimpan: %s" % SIMPAN)

entri = []
for k in terkumpul.values():
    nama = k["tag"].strip().title()
    entri.append({
        "title": "%s - %s" % (nama, (k["id"] or "?").upper()),
        "videoUrl": k["path"],
        "thumbnailUrl": k["thumb"],
        "license": "Wallhaven - ilustrasi anime (gambar statis)",
        "sourceUrl": k["page"],
        "category": "Mature 18+",
        "kind": "static",
        "author": "Wallhaven community",
        "animation": "",
        "resolution": k["res"],
    })

print()
print("  %d entri siap ditambahkan" % len(entri))
print()
for e in entri[:5]:
    print("     %-38s %s" % (e["title"][:38], e["resolution"]))
print()
