"""polish-copy.py — tightens the site's copy.

The problems this fixes are structural, not word-level:

  · three feature headings in a row all used the same "X, bukan Y" shape, which
    reads as a template rather than as three separate points
  · two section headings asked a question the page then answered ("Bedanya di
    mana"), a device that adds a sentence without adding information
  · the tagline described a category ("wallpaper hidup") instead of making a
    promise, so it said nothing a competitor could not also say
  · several leads repeated the heading above them in longer words

Run:  python tools/polish-copy.py
"""

import io

PATH = 'site/index.html'

REPLACEMENTS = [
    # ── the three repeated "X, bukan Y" headings ──────────────────────────────
    ('Decode di GPU, bukan CPU',
     'Video didecode chip grafis'),
    ('Berhenti per layar, bukan semua',
     'Berhenti hanya di layar yang tertutup'),
    ('Reaksi dari event, bukan polling',
     'Reaksi dalam ratusan milidetik'),

    # ── headings that ask a question instead of making a point ───────────────
    ('Bedanya di mana',
     'Bersebelahan dengan bawaan Windows'),
    ('Antarmuka yang dibuat untuk dipakai',
     'Semua yang kamu butuhkan, satu jendela'),
    ('Dibangun untuk dipakai setiap hari',
     'Dibangun untuk dipakai bertahun-tahun'),
    ('Yang sering ditanya',
     'Pertanyaan yang paling sering masuk'),

    # ── the tagline ──────────────────────────────────────────────────────────
    # "Desktop kamu layak terlihat hidup" describes a category. This makes a
    # promise the product can keep, and names the thing that makes it different.
    ('Desktop kamu layak terlihat hidup',
     'Wallpaper yang bergerak, komputer yang tetap tenang'),

    # ── leads that restate their heading ─────────────────────────────────────
    ("""        Setiap keputusan teknis di LumaWall diambil untuk satu alasan: supaya
        wallpaper hidup bisa dibiarkan menyala tanpa kamu harus memikirkannya.""",
     """        Enam hal yang biasanya bikin wallpaper bergerak ditinggalkan: CPU yang
        panas, game yang tersendat, ikon desktop yang tidak bisa diklik."""),

    ("""        Tiga format, satu aplikasi yang sama. Pilih yang paling sesuai dengan cara
        kamu memakai komputer.""",
     """        Aplikasinya sama di ketiga format. Yang berbeda hanya cara memasangnya."""),

    ("""        Dibandingkan dengan wallpaper bawaan Windows, yang tidak dirancang untuk
        video.""",
     """        Bawaan Windows menangani gambar diam dengan baik. Untuk video, ada
        beberapa hal yang tidak bisa dilakukannya."""),

    ("""        Semua gambar di bawah diambil langsung dari aplikasi.""",
     """        Diambil langsung dari aplikasi, bukan dari rancangan."""),

    # ── the hero lead: it listed three features in one sentence ──────────────
    ("""        LumaWall memutar video sebagai wallpaper lewat hardware decode GPU, jadi CPU
        tetap di bawah 1%. Saat kamu membuka game fullscreen, wallpaper di layar itu
        berhenti sendiri dan langsung jalan lagi begitu game ditutup.""",
     """        Video diproses chip grafis, bukan prosesor, jadi CPU tetap di bawah 1%.
        Buka game fullscreen dan wallpaper di layar itu berhenti sendiri, lalu
        jalan lagi begitu game ditutup."""),
]

text = io.open(PATH, encoding='utf-8').read()
changed = 0

print('  rewrites:')
for old, new in REPLACEMENTS:
    if old in text:
        text = text.replace(old, new)
        changed += 1
        print('    %s' % new.split('\n')[0].strip()[:64])
    else:
        print('    (not found) %s' % old.split('\n')[0].strip()[:56])

if changed:
    io.open(PATH, 'w', encoding='utf-8').write(text)
    print()
    print('  %d replacement(s) written' % changed)
