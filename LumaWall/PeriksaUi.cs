using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace LumaWall
{
    /// <summary>
    /// Membangun setiap halaman di luar layar lalu melaporkan masalah tata
    /// letaknya sebagai teks.
    ///
    /// Kenapa ini ada: halaman-halaman ini tidak bisa diperiksa dengan tangkapan
    /// layar. Jendelanya memakai komposisi DirectComposition, sehingga PrintWindow
    /// menghasilkan bitmap kosong; dan CopyFromScreen menyalin apa pun yang ada di
    /// atasnya, yang di mesin kerja berarti aplikasi lain. Keduanya sudah dicoba
    /// dan keduanya menghasilkan gambar hitam atau gambar jendela yang salah.
    ///
    /// Yang bisa diperiksa dengan andal adalah POHON ELEMEN-nya, dan itu justru
    /// cukup: yang dicari adalah elemen yang keluar dari batas induknya, kontrol
    /// yang saling menimpa, dan teks yang lebih lebar daripada tempatnya. Semua
    /// itu pertanyaan tentang ukuran hasil hitungan WPF - dan ukuran itu bisa
    /// dibaca tanpa jendela pernah tampil.
    ///
    /// Halaman dibangun pada lebar jendela yang sesungguhnya, karena tata letak
    /// yang benar pada 1580px bisa rusak pada 920px - dan sebaliknya.
    ///
    /// Pemakaian:
    ///   LumaWall.exe --periksa-ui &lt;folder-keluaran&gt;
    /// </summary>
    internal static class PeriksaUi
    {
        public static int Jalankan(string folder)
        {
            try { Directory.CreateDirectory(folder); }
            catch (Exception ex)
            {
                Console.WriteLine("  ! folder tidak bisa dibuat: " + ex.Message);
                return 1;
            }

            FontLoader.Daftarkan();

            var masalah = new List<string>();
            var laporan = new StringBuilder();

            // Lebar yang diuji adalah lebar terkecil yang mungkin dipakai
            // jendela. Kalau tata letak benar di sini, ia benar di semua lebar
            // yang lebih besar - dan kalau salah, itu bug yang pasti terlihat
            // pengguna, bukan kemungkinan teoretis.
            double[] lebar = { 920, 1200, 1580 };

            string[] halaman = { "home", "library", "discover", "displays", "studio", "performance" };

            var jendela = new MainWindow();
            jendela.Width = 1580;
            jendela.Height = 940;

            // Halaman dibangun tanpa jendela pernah ditampilkan. Ukuran elemen
            // tetap dihitung: WPF mengukur pohonnya saat Measure dipanggil, dan
            // Measure dipanggil oleh UpdateLayout di bawah.
            jendela.Show();
            jendela.Hide();

            foreach (double w in lebar)
            {
                jendela.Width = w;

                foreach (string nama in halaman)
                {
                    try
                    {
                        // Halaman dibangun lewat jalur yang sama dengan tombol
                        // navigasi, jadi yang diperiksa adalah halaman yang
                        // benar-benar dilihat pengguna.
                        jendela.PeriksaHalaman(nama, laporan, masalah, w);
                    }
                    catch (Exception ex)
                    {
                        masalah.Add(string.Format("{0} @ {1}px: gagal dibangun - {2}",
                            nama, w, ex.Message));
                    }
                }
            }

            jendela.Close();

            string berkas = Path.Combine(folder, "ui-laporan.txt");
            File.WriteAllText(berkas, laporan.ToString(), Encoding.UTF8);

            Console.WriteLine();
            Console.WriteLine("  ══ hasil pemeriksaan tata letak ══");
            Console.WriteLine();
            foreach (string m in masalah)
            {
                Console.WriteLine("  " + m);
            }
            Console.WriteLine();
            if (masalah.Count == 0)
            {
                Console.WriteLine("  ✓ tidak ada masalah tata letak");
            }
            else
            {
                Console.WriteLine("  " + masalah.Count + " masalah");
            }
            Console.WriteLine("  laporan lengkap: " + berkas);
            Console.WriteLine();

            return masalah.Count == 0 ? 0 : 1;
        }
    }
}
