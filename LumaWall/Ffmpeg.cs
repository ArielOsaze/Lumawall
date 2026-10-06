// Ffmpeg.cs - satu tempat untuk mencari, dan kalau perlu MENGUNDUH, ffmpeg.
//
// KENAPA BERKAS INI ADA:
//
// Tiga fitur aplikasi memanggil ffmpeg:
//
//   * memperkecil video agar decode-nya ringan (perbaikan utama 4.5.20.0)
//   * membatasi FPS video
//   * mengubah gambar statis jadi video bergerak (kenburns)
//
// Ketiganya mencari ffmpeg.exe di dua tempat: folder aplikasi, lalu PATH.
// Folder aplikasi TIDAK PERNAH berisi ffmpeg - installer dan MSIX tidak
// menyertakannya - sehingga yang tersisa hanya PATH. Di mesin pengembang ffmpeg
// ada (dipasang lewat WinGet), jadi semuanya bekerja saat diuji. Di PC pembeli
// ffmpeg tidak ada, dan ketiga fitur itu GAGAL DIAM-DIAM: yang muncul hanya
// pesan "FFmpeg tidak ditemukan", dan perbaikan decode yang menjadi alasan
// rilis 4.5.20.0 tidak pernah berjalan untuk siapa pun yang membeli aplikasinya.
//
// Mengunduh saat pertama dibutuhkan dipilih daripada ikut dipaketkan karena:
//
//   * installer yang diunduh pembeli tetap 23 MB, bukan 100 MB lebih
//   * pembeli hanya mengunduhnya kalau fitur itu benar-benar dipakai
//   * ukurannya ~80 MB dan diunduh sekali, lalu disimpan
//
// Kalau unduhan gagal, fitur itu tidak aktif dan pesannya menyebutkan sebabnya -
// bukan diam-diam gagal seperti sebelumnya.

using System;
using System.ComponentModel;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;

namespace LumaWall
{
    internal static class Ffmpeg
    {
        /// <summary>
        /// Unduhan resmi ffmpeg untuk Windows 64-bit (build "essentials" gyan.dev).
        /// Isinya ffmpeg.exe, ffprobe.exe, dan ffplay.exe.
        /// </summary>
        private const string SumberUnduh =
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip";

        private static readonly object Kunci = new object();
        private static string jalur;
        private static bool sudahDicari;

        /// <summary>Dipanggil saat unduhan mulai dan selesai, untuk memberi tahu pengguna.</summary>
        public static Action<string> Lapor;

        /// <summary>Dipanggil dengan 0-100 selama unduhan, atau -1 kalau tidak diketahui.</summary>
        public static Action<int> Kemajuan;

        /// <summary>
        /// Jalur ffmpeg.exe, atau null kalau tidak ada dan tidak bisa diunduh.
        ///
        /// Hasilnya di-cache: pencarian hanya dilakukan sekali per sesi.
        /// </summary>
        public static string Cari()
        {
            lock (Kunci)
            {
                if (sudahDicari) return jalur;
                sudahDicari = true;

                // 1. Di samping aplikasi. Ini yang dipakai kalau pengguna - atau
                //    paket - menaruh ffmpeg di sana, dan tidak bergantung pada
                //    apa pun di mesinnya.
                foreach (string coba in new[]
                {
                    Path.Combine(FolderAplikasi(), "ffmpeg.exe"),
                    Path.Combine(FolderAplikasi(), "tools", "ffmpeg.exe"),
                })
                {
                    if (Berkas(coba)) { jalur = coba; return jalur; }
                }

                // 2. Sudah pernah diunduh sebelumnya: disimpan di folder data
                //    aplikasi supaya tidak ikut terhapus saat aplikasi diperbarui.
                foreach (string coba in new[]
                {
                    Path.Combine(FolderData(), "ffmpeg.exe"),
                    Path.Combine(FolderData(), "ffmpeg", "ffmpeg.exe"),
                })
                {
                    if (Berkas(coba)) { jalur = coba; return jalur; }
                }

                // 3. Di PATH. Ini yang bekerja di mesin pengembang.
                string dariPath = DariPath();
                if (dariPath != null) { jalur = dariPath; return jalur; }

                // 4. Unduh. Ini yang membuat fiturnya bekerja di PC pembeli.
                string hasil = Unduh();
                jalur = hasil;
                return jalur;
            }
        }

        /// <summary>Jalur ffprobe.exe, kalau ada di folder yang sama dengan ffmpeg.</summary>
        public static string CariProbe()
        {
            string ff = Cari();
            if (ff == null) return null;
            if (ff == "ffmpeg") return "ffprobe";   // di PATH, biarkan Windows mencarinya

            try
            {
                string coba = Path.Combine(Path.GetDirectoryName(ff), "ffprobe.exe");
                if (Berkas(coba)) return coba;
            }
            catch { }
            return null;
        }

        private static string FolderAplikasi()
        {
            try
            {
                return Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            }
            catch
            {
                return AppDomain.CurrentDomain.BaseDirectory;
            }
        }

        private static string FolderData()
        {
            try
            {
                string dasar = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "LumaWall");
                Directory.CreateDirectory(dasar);
                return dasar;
            }
            catch
            {
                return AppDomain.CurrentDomain.BaseDirectory;
            }
        }

        private static bool Berkas(string path)
        {
            try { return !string.IsNullOrEmpty(path) && File.Exists(path); }
            catch { return false; }
        }

        private static string DariPath()
        {
            try
            {
                foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
                {
                    try
                    {
                        string coba = Path.Combine(folder.Trim(), "ffmpeg.exe");
                        if (Berkas(coba)) return coba;
                    }
                    catch { }
                }
            }
            catch { }
            return null;
        }

        /// <summary>
        /// Mengunduh ffmpeg dan menyimpannya di folder data aplikasi.
        ///
        /// Arsipnya berisi folder bernomor versi (mis. ffmpeg-7.1-essentials_build),
        /// jadi ffmpeg.exe dicari di dalamnya, bukan diasumsikan di akar arsip.
        /// </summary>
        private static string Unduh()
        {
            string tujuan = Path.Combine(FolderData(), "ffmpeg.exe");

            try
            {
                string sementara = Path.Combine(Path.GetTempPath(),
                    "lumawall-ffmpeg-" + Guid.NewGuid().ToString("N") + ".zip");

                if (Lapor != null) Lapor("Menyiapkan ffmpeg untuk pertama kali…");

                using (var client = new WebClient())
                {
                    client.Headers.Add("User-Agent", "LumaWall/1.0");

                    client.DownloadProgressChanged += delegate(object s, DownloadProgressChangedEventArgs e)
                    {
                        if (Kemajuan != null) Kemajuan(e.ProgressPercentage);
                    };

                    // Diunduh secara sinkron: pemanggilnya sudah berjalan di
                    // thread latar, dan mengembalikan hasil yang belum selesai
                    // akan membuat pemanggil pertama memakai null.
                    client.DownloadFile(SumberUnduh, sementara);
                }

                if (!File.Exists(sementara)) return null;

                if (Lapor != null) Lapor("Memasang ffmpeg…");

                // Arsipnya dibaca tanpa pustaka luar: yang dicari hanya dua berkas
                // di dalam folder bernomor versi.
                string dikeluarkan = BacaZip(sementara, "ffmpeg.exe", tujuan);
                if (dikeluarkan == null)
                {
                    try { File.Delete(sementara); } catch { }
                    return null;
                }

                // ffprobe dipakai untuk membaca ukuran video. Kalau tidak ada,
                // ukurannya dibaca dengan cara lain, jadi kegagalannya tidak fatal.
                try
                {
                    string probe = Path.Combine(FolderData(), "ffprobe.exe");
                    BacaZip(sementara, "ffprobe.exe", probe);
                }
                catch { }

                try { File.Delete(sementara); } catch { }

                if (Lapor != null) Lapor("ffmpeg siap.");
                return Berkas(tujuan) ? tujuan : null;
            }
            catch (Exception e)
            {
                if (Lapor != null) Lapor("ffmpeg tidak bisa diunduh: " + e.Message);
                return null;
            }
        }

        /// <summary>
        /// Mengeluarkan satu berkas dari arsip zip berdasarkan namanya.
        ///
        /// Memakai System.IO.Compression.ZipFile, bukan pemindai buatan sendiri.
        ///
        /// Pemindai buatan sendiri sempat dipakai dan GAGAL pada arsip yang
        /// sebenarnya: arsip dari gyan.dev memakai data descriptor (bit 3 pada
        /// flag header), sehingga ukuran berkasnya tidak ada di header lokal
        /// melainkan di blok sesudah data. Pemindai yang menyalin sebesar ukuran
        /// dari daftar isi mengambil data berkas ditambah header entri
        /// berikutnya, dan hasilnya berkas rusak: ffmpeg.exe 35,7 MB
        /// (seharusnya 80 MB), tidak diawali tanda MZ, dan Windows menolaknya
        /// dengan "not compatible with the version of Windows you are running".
        ///
        /// Itu ketahuan hanya karena hasilnya benar-benar dijalankan. Kalau
        /// tidak, setiap pembeli akan menerima ffmpeg rusak dan tiga fitur
        /// (perkecil video, pembatas FPS, kenburns) tetap gagal seperti sebelum
        /// diperbaiki.
        /// </summary>
        private static string BacaZip(string zip, string namaDicari, string tujuan)
        {
            try
            {
                using (var arsip = System.IO.Compression.ZipFile.OpenRead(zip))
                {
                    foreach (var entri in arsip.Entries)
                    {
                        string nama = entri.FullName.Replace('\\', '/');
                        if (!nama.EndsWith("/" + namaDicari, StringComparison.OrdinalIgnoreCase) &&
                            !nama.Equals(namaDicari, StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        // Ditulis ke berkas sementara lebih dulu, lalu dipindah.
                        // Kalau unduhan atau ekstraksinya gagal di tengah, yang
                        // tertinggal bukan ffmpeg setengah jadi yang akan dipakai
                        // pada percobaan berikutnya.
                        string sementara = tujuan + ".sebagian";
                        using (var masuk = entri.Open())
                        using (var keluar = new FileStream(sementara, FileMode.Create, FileAccess.Write))
                        {
                            masuk.CopyTo(keluar, 65536);
                        }

                        if (File.Exists(tujuan)) File.Delete(tujuan);
                        File.Move(sementara, tujuan);
                        return tujuan;
                    }
                }
            }
            catch
            {
                return null;
            }
            return null;
        }

    }
}
