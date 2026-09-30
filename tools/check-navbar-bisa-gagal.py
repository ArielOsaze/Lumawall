#!/usr/bin/env python3
"""Buktikan check-navbar.py bisa GAGAL, bukan hanya bisa lulus.

Ini penting karena pemeriksaan navbar sempat lulus sambil tidak memeriksa apa
pun: satu kesalahan di dalamnya membuat setiap hasil kembali kosong, dan
"kosong" diperlakukan sebagai "tidak ada masalah". Pemeriksaan yang selalu lulus
lebih berbahaya daripada tidak ada pemeriksaan sama sekali.

Versi pertama skrip ini salah dan tidak membuktikan apa-apa: ia merusak halaman
di dalam browser-nya sendiri, sementara pemeriksaan yang diuji membuka browser
BARU dengan halaman yang dimuat ulang dari berkas - jadi kerusakannya tidak
pernah terlihat oleh yang menguji. Yang benar adalah merusak berkasnya.

Karena itu berkas situsnya yang diubah sementara, lalu dikembalikan. Berkas
aslinya disalin lebih dulu, dan pemulihannya ada di blok `finally` supaya
kerusakan tidak pernah tertinggal - termasuk kalau skrip ini dihentikan.

Pemakaian:
  python tools/check-navbar-bisa-gagal.py
"""
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALAMAN = ROOT / 'site' / 'index.html'
PERIKSA = ROOT / 'tools' / 'check-navbar.py'


def _hapus_panel(t):
    """Kosongkan isi setiap panel menu, tanpa menyentuh pembungkusnya.

    Ini kerusakan yang berbeda dari "menunya hilang": menunya masih ada dan
    masih terbuka, tetapi tidak ada tujuan di dalamnya. Pemeriksaan yang hanya
    menghitung menu akan meloloskannya.
    """
    import re
    return re.sub(r'(<div class="nav-drop-panel">).*?(</div>)', r'\1\2', t, flags=re.S)


def jalankan_periksa():
    r = subprocess.run([sys.executable, str(PERIKSA)],
                       capture_output=True, text=True, timeout=600)
    keluaran = (r.stdout or '') + (r.stderr or '')
    return r.returncode, keluaran


def main():
    print()
    print('  ══ buktikan pemeriksaan navbar bisa gagal ══')
    print()

    if not HALAMAN.exists():
        print('  ! %s tidak ada' % HALAMAN)
        return 1

    asli = HALAMAN.read_text(encoding='utf-8')

    # Kerusakan yang diuji, masing-masing adalah hal yang pemeriksaannya
    # mengklaim bisa dilihat.
    # Kerusakannya harus tepat mengenai struktur yang ada di halaman, kalau
    # tidak, penggantiannya tidak terjadi dan yang diuji bukan apa-apa. Versi
    # pertama skrip ini mengganti kelas yang salah, sehingga dua dari tiga
    # kasusnya tidak merusak apa pun dan hasilnya menyesatkan.
    kasus = [
        ('kedua menu bertingkat dihapus',
         lambda t: t.replace('class="nav-drop"', 'class="nav-drop-off"')),

        ('tautan di dalam menu dihapus',
         lambda t: _hapus_panel(t)),

        ('tombol menu mobile dihilangkan',
         lambda t: t.replace('class="nav-burger"', 'class="nav-burger-off"')),

        ('menu mobile dihapus',
         lambda t: t.replace('class="nav-mobile"', 'class="nav-mobile-off"')),
    ]

    tertangkap = 0
    try:
        for nama, rusak in kasus:
            hasil_rusak = rusak(asli)
            if hasil_rusak == asli:
                # Kerusakan yang tidak mengubah apa pun akan dilaporkan sebagai
                # "tidak tertangkap" padahal pemeriksaannya belum diuji.
                print('  ! %-30s tidak mengubah berkas - kasus ini dilewati' % nama)
                continue
            HALAMAN.write_text(hasil_rusak, encoding='utf-8')
            time.sleep(0.3)

            kode, keluaran = jalankan_periksa()
            gagal = kode != 0
            ada_laporan = ('✗' in keluaran) or ('masalah' in keluaran)

            tanda = '✓' if gagal else '✗'
            print('  %s %-30s keluar=%d lapor-masalah=%s' % (tanda, nama, kode, ada_laporan))
            if gagal:
                tertangkap += 1
    finally:
        HALAMAN.write_text(asli, encoding='utf-8')
        time.sleep(0.3)
        kode, _ = jalankan_periksa()
        if kode != 0:
            print()
            print('  ! berkas sudah dipulihkan tetapi pemeriksaan masih gagal')
            print('    jalankan sendiri untuk melihat sebabnya:')
            print('      python tools/check-navbar.py')
            return 1
        print()
        print('  berkas dipulihkan; pemeriksaan kembali lulus')

    print()
    if tertangkap == len(kasus):
        print('  ✓ pemeriksaan menangkap %d dari %d kerusakan' % (tertangkap, len(kasus)))
        print('    Berarti pemeriksaan itu benar-benar mengukur, bukan selalu lulus.')
        return 0

    print('  ✗ hanya menangkap %d dari %d kerusakan' % (tertangkap, len(kasus)))
    print('    Pemeriksaan itu tidak mengukur apa yang diklaimnya.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
