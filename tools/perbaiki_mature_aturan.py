"""Aturan penentuan gaya dewasa, dipakai bersama oleh beberapa alat.

Kenapa dipisah: aturan ini dipakai dua tempat - saat memperbaiki entri lama yang
salah kategori, dan saat memasukkan entri baru dari API. Kalau keduanya punya
salinannya sendiri, keduanya akan berbeda cepat atau lambat, dan kategori
mature akan berisi aturan yang berbeda untuk entri lama dan entri baru.

Yang penting di sini adalah PENGECUALIANNYA, bukan daftar katanya. Tanpa itu,
"Meteor Shower" (hujan meteor) dan "Rice Shower" (nama tokoh) ikut pindah ke
kategori dewasa, dan kategori itu justru menjadi tempat sampah.
"""
import re

ATURAN = [
    # Pakaian renang dan pakaian dalam: hampir selalu bergaya dewasa.
    (r"\b(bikini|swimsuit|swimwear|beachwear|lingerie|boudoir|negligee|"
     r"nightgown|garter|corset|leotard|bodysuit|catsuit|panties)\b", None),

    # Kata sifat yang menyebut daya tarik.
    (r"\b(seductive|sensual|sultry|provocative|sexy|flirty|alluring)\b", None),

    # Keadaan yang biasanya dipakai untuk menampilkan tubuh.
    #
    # "Shower" TIDAK ada di daftar ini, dan itu keputusan yang disengaja:
    # "Meteor Shower" adalah hujan meteor, dan "Rice Shower" adalah nama tokoh
    # Uma Musume. Memasukkan kata itu akan memindahkan wallpaper luar angkasa
    # dan balapan kuda ke kategori dewasa - persis "kategorinya nyasar" yang
    # harus dihindari, hanya saja ke arah sebaliknya.
    (r"\b(hot[-\s]?spring|onsen|bathing|poolside|sunbathing|"
     r"beach[-\s]?bikini|swimsuit[-\s]?selfie|bikini[-\s]?selfie)\b", None),

    # Pakaian yang menandakan tema tertentu - dengan pengecualian.
    #
    # "schoolgirl" dan "student" TIDAK ada di daftar ini. Itu keputusan yang
    # disengaja: keduanya menandakan karakter yang masih sekolah, dan kategori
    # dewasa tidak boleh memuatnya. Aturan ini juga berlaku untuk seluruh
    # nama seri yang tokohnya anak-anak - lihat SERI_ANAK di bawah.
    (r"\b(maid|nurse|cheerleader|gravure|pin[-\s]?up)\b",
     r"\b(maid\s+cafe|cheerleader\s+uniform\s+only)\b"),

    (r"\bbunny\s+(girl|suit|outfit|costume|dress|leotard)\b", None),

    # "Gym" dan "Yoga" menandakan pakaian olahraga yang ketat - KECUALI kalau
    # yang dimaksud adalah tokoh atau tempat.
    (r"\b(gym|yoga)\b",
     r"\b(gym\s+leader|pokemon\s+gym|gym\s+badge|gym\s+interior|"
     r"yoga\s+class\s+only|gym\s+time\s+only)\b"),

    # "Idol" HANYA dihitung kalau disertai penanda penampilan. Sebagai kata
    # tunggal ia terlalu umum: "Idol Master" adalah nama game, dan "Idol"
    # sendirian bisa berarti apa saja.
    (r"\b(idol\s+(live|stage|performance|debut|costume|outfit|style)|"
     r"starlight\s+idol|idol\s+ver)\b", None),

    # Kata yang sudah pasti.
    (r"\b(ecchi|lewd|nsfw|hentai|waifu|sexy\s+girl|hot\s+girl)\b", None),
]

# Seri yang tokohnya anak-anak, atau yang seluruh gayanya tidak pantas masuk
# kategori dewasa.
#
# Ini bukan daftar kata yang buruk - ini daftar SERI. Wallpaper dari seri ini
# bisa punya judul apa saja ("Klee at the Beach", "Nahida in the Rain") dan
# tetap tidak pantas: yang menentukan bukan kata "beach"-nya, melainkan siapa
# yang ada di gambar. Blue Archive juga masuk daftar ini karena tokohnya
# berseragam sekolah, dan itu sudah ditetapkan sebagai batas.
SERI_ANAK = re.compile(
    r"\b(blue\s+archive|pokemon|pokémon|genshin\s+klee|klee|nahida|qiqi|"
    r"yaoyao|diona|kanna|anya|nezuko|ibuki|"
    r"little\s+girl|child|kids?|toddler|baby|infant|"
    r"loli|lolita|juvenile|underage|teen|"
    r"schoolgirl|school\s+girl|elementary|middle\s+school|"
    r"kindergarten|nursery)\b",
    re.I,
)

POLA = [(re.compile(kata, re.I),
         re.compile(kecuali, re.I) if kecuali else None)
        for kata, kecuali in ATURAN]


def bergaya_dewasa(judul):
    """Apakah judul ini bergaya dewasa, menurut aturan di atas.

    Seri anak diperiksa LEBIH DULU, dan itu yang menentukan: sebuah judul yang
    mengandung "bikini" tetapi juga "Blue Archive" bukan wallpaper dewasa,
    karena yang ada di gambarnya adalah tokoh berseragam sekolah.
    """
    if not judul:
        return False
    if SERI_ANAK.search(judul):
        return False
    for pola, kecuali in POLA:
        if pola.search(judul):
            if kecuali and kecuali.search(judul):
                continue
            return True
    return False
