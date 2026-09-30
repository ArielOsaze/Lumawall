using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Text;
using System.IO;

namespace LumaWall
{
    /// <summary>
    /// Mendaftarkan font yang ikut dibundel aplikasi, supaya bisa dipakai tanpa
    /// dipasang di sistem pengguna.
    ///
    /// Kenapa ini perlu: GDI+ hanya bisa memakai font yang ada di daftar
    /// koleksinya. Menaruh berkas .ttf di sebelah aplikasi tidak cukup -
    /// `new FontFamily("Inter Light")` akan gagal dan diam-diam jatuh ke font
    /// sistem, yang persis masalah "fontnya masih basic" yang dilaporkan.
    ///
    /// Cara yang benar adalah `PrivateFontCollection`, dan itu tidak langsung
    /// terlihat. Yang pertama dicoba adalah `AddFontMemResourceEx` dari gdi32:
    /// panggilannya BERHASIL (mengembalikan handle, melaporkan 1 face), tetapi
    /// `new FontFamily("Inter")` tetap gagal sesudahnya. Sebabnya, fungsi itu
    /// mendaftar ke GDI, sedangkan `System.Drawing` memakai GDI+ yang punya
    /// daftar sendiri - jadi berhasilnya panggilan itu tidak berarti apa-apa di
    /// sini, dan kegagalannya muncul jauh kemudian sebagai font yang salah.
    ///
    /// `PrivateFontCollection` bekerja pada GDI+ langsung, hanya berlaku untuk
    /// proses ini, dan tidak menulis apa pun ke sistem pengguna.
    /// </summary>
    internal static class FontLoader
    {
        // Harus hidup selama aplikasi: FontFamily yang dibuat dari koleksi ini
        // menyimpan rujukan ke memorinya. Kalau koleksinya dibuang, font yang
        // sudah dibuat bisa kehilangan datanya saat pengumpul sampah bekerja.
        private static readonly PrivateFontCollection koleksi = new PrivateFontCollection();
        private static bool sudah;
        private static readonly List<string> keluarga = new List<string>();

        /// <summary>Benar kalau ada setidaknya satu font yang berhasil dimuat.</summary>
        public static bool Terdaftar { get; private set; }

        /// <summary>Nama keluarga font yang benar-benar tersedia setelah pemuatan.</summary>
        public static string[] Keluarga { get { return keluarga.ToArray(); } }

        /// <summary>Alasan kegagalan terakhir, untuk log. Kosong kalau berhasil.</summary>
        public static string Kesalahan = "";

        /// <summary>
        /// Muat semua .ttf di folder `fonts` di sebelah aplikasi.
        ///
        /// Aman dipanggil lebih dari sekali. Tidak pernah melempar - font adalah
        /// penyempurnaan tampilan, dan aplikasi harus tetap berjalan tanpanya.
        /// </summary>
        public static void Daftarkan()
        {
            if (sudah) return;
            sudah = true;

            try
            {
                string folder = Path.Combine(
                    Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location),
                    "fonts");

                if (!Directory.Exists(folder))
                {
                    Kesalahan = "folder fonts tidak ada";
                    AppLog.Write("Font: " + Kesalahan + " - memakai font sistem");
                    return;
                }

                string[] berkas = Directory.GetFiles(folder, "*.ttf");
                if (berkas.Length == 0)
                {
                    Kesalahan = "tidak ada berkas .ttf";
                    AppLog.Write("Font: " + Kesalahan + " - memakai font sistem");
                    return;
                }

                foreach (string f in berkas)
                {
                    try
                    {
                        // AddFontFile membaca berkasnya dan menyalin apa yang
                        // diperlukan ke memori sendiri, jadi berkasnya boleh
                        // ditutup setelah ini - penting karena aplikasi bisa
                        // berjalan dari folder yang tidak bisa ditulis.
                        koleksi.AddFontFile(f);
                    }
                    catch (Exception ex)
                    {
                        AppLog.Write("Font " + Path.GetFileName(f) + " gagal: " + ex.Message);
                    }
                }

                foreach (FontFamily k in koleksi.Families)
                {
                    keluarga.Add(k.Name);
                }

                Terdaftar = keluarga.Count > 0;
                if (!Terdaftar) Kesalahan = "tidak ada keluarga font yang termuat";

                AppLog.Write("Font: " + keluarga.Count + " keluarga dimuat ("
                    + string.Join(", ", keluarga.ToArray()) + ")");
            }
            catch (Exception ex)
            {
                Kesalahan = ex.Message;
                AppLog.Write("Pemuatan font gagal: " + ex.Message);
            }
        }

        /// <summary>
        /// FontFamily dari koleksi ini, atau null kalau namanya tidak ada.
        ///
        /// `new FontFamily(nama)` TIDAK melihat koleksi ini - ia hanya mencari
        /// font yang terpasang di sistem. Itu jebakan yang membuat font sudah
        /// termuat tetapi tetap tidak terpakai: koleksinya berisi 'Inter' dan
        /// 'Inter Light', sementara `new FontFamily("Inter Light")` melempar,
        /// dan pemanggil yang menangkapnya diam-diam jatuh ke font sistem.
        /// Persis begitulah "fontnya masih basic" terjadi meski pemuatan font
        /// melaporkan sukses.
        ///
        /// Bentuk yang benar adalah `new FontFamily(nama, koleksi)`, dan hanya
        /// itu yang dipakai di sini.
        /// </summary>
        public static FontFamily AmbilDariKoleksi(string nama)
        {
            if (string.IsNullOrEmpty(nama)) return null;
            try
            {
                var f = new FontFamily(nama, koleksi);
                return f.Name == nama ? f : null;
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Keluarga font yang dipakai aplikasi, dengan cadangan ke font sistem.
        ///
        /// Diperiksa dari kenyataannya, bukan dari asumsi bahwa pemuatan pasti
        /// berhasil: kalau Inter tidak ada, yang dikembalikan adalah font sistem
        /// yang pasti tersedia, sehingga pemanggil tidak perlu memikirkan
        /// kemungkinan itu.
        /// </summary>
        public static FontFamily Ambil(string nama, string cadangan)
        {
            FontFamily f = AmbilDariKoleksi(nama);
            if (f != null) return f;
            try { return new FontFamily(cadangan); }
            catch { return FontFamily.GenericSansSerif; }
        }

        /// <summary>
        /// Keluarga font terbaik yang tersedia dari daftar nama, terbaik dulu.
        ///
        /// Mengembalikan nama yang benar-benar bisa dipakai, bukan nama yang
        /// diminta - sehingga pemanggil tidak pernah membuat Font dari nama yang
        /// tidak ada dan mendapat font sistem tanpa sadar.
        /// </summary>
        public static string PertamaYangAda(string[] nama, string cadangan)
        {
            foreach (string n in nama)
            {
                try
                {
                    var f = new FontFamily(n);
                    if (f.Name == n) return n;
                }
                catch { }
            }
            return cadangan;
        }

        /// <summary>Lepas koleksi font. Dipanggil saat aplikasi keluar.</summary>
        public static void Lepaskan()
        {
            try { koleksi.Dispose(); } catch { }
            keluarga.Clear();
            Terdaftar = false;
        }
    }
}
