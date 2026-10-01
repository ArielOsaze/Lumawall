using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;

namespace LumaWall
{
    /// <summary>
    /// Merender setiap gaya jam ke berkas PNG, supaya tampilannya bisa DILIHAT.
    ///
    /// Kenapa alat ini ada: seluruh pekerjaan jam sebelumnya dikerjakan dari kode
    /// tanpa pernah melihat hasilnya. Itu sebabnya beberapa perbaikan berturut-turut
    /// ("font sudah diganti", "ukuran sudah dibesarkan", "bayangan sudah
    /// dikurangi") tidak menyelesaikan keluhan yang sama - setiap kali, yang
    /// diperiksa adalah kode, bukan gambar.
    ///
    /// Gambar di sini dibuat dengan GDI+ dan fungsi font yang SAMA dengan yang
    /// dipakai jendela jam (`FontLoader` + `FacesFor`), lalu digambar dengan
    /// urutan yang sama: bayangan dulu, huruf di atasnya. Jadi berkas yang
    /// dihasilkan memperlihatkan hal yang sama dengan jam di desktop.
    ///
    /// Pemakaian:
    ///   LumaWall.exe --render-jam &lt;folder-keluar&gt;
    /// </summary>
    internal static class RenderJam
    {
        public static int Jalankan(string folder)
        {
            try { Directory.CreateDirectory(folder); }
            catch (Exception ex)
            {
                Console.WriteLine("  ! folder tidak bisa dibuat: " + ex.Message);
                return 1;
            }

            // Font harus didaftarkan lebih dulu: tanpa ini setiap nama Inter
            // gagal dan semua gambar memakai Segoe - dan hasilnya justru
            // memperlihatkan masalah yang sedang diperiksa, bukan yang sudah
            // diperbaiki.
            FontLoader.Daftarkan();
            Console.WriteLine("  font dimuat: " + string.Join(", ", FontLoader.Keluarga));

            string[] gaya = { "ioslarge", "ioslight", "iosstack", "iosdate", "minimal", "glass", "bold", "card" };
            int lebar = 900, tinggi = 260;

            foreach (string style in gaya)
            {
                var bmp = new Bitmap(lebar, tinggi, PixelFormat.Format32bppArgb);
                using (var g = Graphics.FromImage(bmp))
                {
                    g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
                    g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.AntiAlias;

                    // Dua bidang: gelap di kiri, terang di kanan. Huruf putih harus
                    // terbaca di keduanya, dan bentuknya harus tetap sama.
                    using (var kuas = new System.Drawing.Drawing2D.LinearGradientBrush(
                        new Rectangle(0, 0, lebar, tinggi),
                        Color.FromArgb(255, 22, 26, 36),
                        Color.FromArgb(255, 170, 178, 192),
                        System.Drawing.Drawing2D.LinearGradientMode.Horizontal))
                    {
                        g.FillRectangle(kuas, 0, 0, lebar, tinggi);
                    }

                    bool tipis = style == "ioslarge" || style == "ioslight"
                        || style == "iosstack" || style == "iosdate"
                        || style == "minimal" || style == "glass";

                    // Ukuran per gaya, sama seperti yang dipakai jendela jam.
                    float ukuran = style == "ioslarge" ? 118f
                        : style == "ioslight" ? 96f
                        : style == "iosstack" ? 84f
                        : style == "iosdate" ? 78f
                        : style == "bold" ? 92f
                        : style == "card" ? 84f
                        : 88f;

                    string teks = "20:31";
                    var font = DesktopTimer.TimeFontUntukUji(ukuran, style);

                    var format = new StringFormat
                    {
                        Alignment = StringAlignment.Center,
                        LineAlignment = StringAlignment.Center,
                    };

                    var kotak = new RectangleF(0, 10, lebar, 150);

                    // Urutan yang sama dengan jendela jam: bayangan dulu, huruf di atasnya.
                    if (tipis)
                    {
                        // Bayangan rapat: satu salinan gelap, digeser ke bawah.
                        float turun = Math.Max(1f, 1.4f);
                        using (var lembut = new SolidBrush(Color.FromArgb(64, 0, 0, 0)))
                        {
                            g.DrawString(teks, font, lembut,
                                new RectangleF(kotak.X, kotak.Y + turun, kotak.Width, kotak.Height), format);
                        }
                    }
                    else
                    {
                        // Halo delapan arah, untuk huruf tebal.
                        float radius = 1.6f;
                        using (var bayang = new SolidBrush(Color.FromArgb(120, 0, 0, 0)))
                        {
                            for (int i = 0; i < 8; i++)
                            {
                                double sudut = Math.PI * 2 * i / 8;
                                var geser = new RectangleF(
                                    kotak.X + (float)(Math.Cos(sudut) * radius),
                                    kotak.Y + (float)(Math.Sin(sudut) * radius),
                                    kotak.Width, kotak.Height);
                                g.DrawString(teks, font, bayang, geser, format);
                            }
                        }
                    }

                    using (var brush = new SolidBrush(Color.White))
                    {
                        g.DrawString(teks, font, brush, kotak, format);
                    }

                    // Tanggal di bawahnya, seperti di desktop.
                    var fontKecil = DesktopTimer.TimeFontUntukUji(ukuran * 0.22f, style);
                    using (var brush = new SolidBrush(Color.FromArgb(184, 255, 255, 255)))
                    {
                        g.DrawString("Thursday, 1 October", fontKecil, brush,
                            new RectangleF(0, 170, lebar, 60), format);
                    }

                    font.Dispose();
                    fontKecil.Dispose();
                }

                string berkas = Path.Combine(folder, "jam-" + style + ".png");
                bmp.Save(berkas, ImageFormat.Png);
                bmp.Dispose();
                Console.WriteLine("  " + Path.GetFileName(berkas));
            }

            // Satu gambar gabungan supaya bisa dibandingkan sekaligus.
            var semua = new Bitmap(lebar, tinggi * gaya.Length, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(semua))
            {
                g.Clear(Color.FromArgb(255, 16, 18, 24));
                for (int i = 0; i < gaya.Length; i++)
                {
                    using (var satu = new Bitmap(Path.Combine(folder, "jam-" + gaya[i] + ".png")))
                    {
                        g.DrawImage(satu, 0, i * tinggi);
                    }
                }
            }
            string gabung = Path.Combine(folder, "jam-semua.png");
            semua.Save(gabung, ImageFormat.Png);
            semua.Dispose();
            Console.WriteLine("  " + Path.GetFileName(gabung));

            return 0;
        }
    }
}
