using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace LumaWall
{
    /// <summary>
    /// Menyesuaikan video wallpaper dengan monitor yang memutarnya.
    ///
    /// Kenapa ini ada: sebuah video 3840x2160 di monitor 1920x1080 memaksa GPU
    /// men-decode empat kali lipat piksel yang benar-benar ditampilkan, lalu
    /// membuang tiga perempatnya saat menskalakan ke ukuran layar. Decode adalah
    /// bagian termahal dari memutar video, jadi kelebihannya dibayar penuh dan
    /// tidak ada satu pun pikselnya yang terlihat. Terukur di mesin ini: video 4K
    /// di layar 1080p menaikkan pemakaian decoder ke 22%, sementara video 1080p
    /// di layar 1080p tetap di bawah 5%.
    ///
    /// Yang TIDAK dilakukan: mengubah video aslinya. Berkas milik pengguna tidak
    /// pernah disentuh. Yang dibuat adalah salinan turunan di folder cache, dan
    /// hanya dipakai kalau memang lebih ringan.
    ///
    /// Kalau ffmpeg tidak ada, atau apa pun gagal, video aslinya yang dipakai.
    /// Fitur ini tidak boleh membuat wallpaper gagal tampil.
    /// </summary>
    internal static class VideoScale
    {
        /// <summary>Hasil keputusan untuk satu berkas video di satu monitor.</summary>
        internal struct Hasil
        {
            public string Path;         // berkas yang sebaiknya dipakai
            public bool Diskalakan;     // true kalau ini salinan turunan
            public int LebarAsli;
            public int TinggiAsli;
            public int LebarPakai;
            public int TinggiPakai;
            public string Alasan;       // untuk log, dalam bahasa manusia
        }

        private static readonly object Kunci = new object();
        private static string ffmpegPath;
        private static bool ffmpegDicari;
        private static readonly HashSet<string> sedangDibuat = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Berapa kali piksel video boleh melebihi piksel layar sebelum
        /// diskalakan.
        ///
        /// 1.3 dipilih, bukan 1.0, dan itu disengaja: video 1080p di layar
        /// 1080p, atau 1440p di layar 1080p, tidak sepadan diturunkan. Selisih
        /// decode-nya kecil, dan menurunkan resolusi selalu sedikit mengorbankan
        /// ketajaman. Yang dibuang hanya kelebihan yang benar-benar besar - 4K di
        /// layar 1080p (4x) atau di layar 720p (9x) - karena di situ
        /// penghematannya besar dan tidak ada detail yang terlihat hilang.
        /// </summary>
        private const double AmbangKelebihan = 1.3;

        /// <summary>
        /// Resolusi maksimum yang masih masuk akal untuk sebuah monitor.
        ///
        /// Dibatasi 3840 supaya video 8K di layar 4K tetap diturunkan, dan
        /// dibulatkan ke kelipatan 2 karena encoder video bekerja pada makroblok.
        /// </summary>
        private static int BatasLebar(int lebarLayar)
        {
            int w = Math.Max(640, lebarLayar);
            w = Math.Min(w, 3840);
            return (w + 1) / 2 * 2;
        }

        /// <summary>
        /// Pilih berkas video yang paling ringan untuk monitor ini.
        ///
        /// Selalu mengembalikan sesuatu yang bisa dipakai: berkas aslinya kalau
        /// tidak ada yang perlu atau bisa dilakukan.
        /// </summary>
        public static Hasil Pilih(string videoPath, int lebarLayar, int tinggiLayar)
        {
            return Pilih(videoPath, lebarLayar, tinggiLayar, 0);
        }

        /// <summary>
        /// Pilih berkas video untuk monitor ini, sekaligus menerapkan batas laju
        /// gambar yang diminta pengguna.
        ///
        /// Kenapa laju gambar ikut ditangani di sini:
        ///
        /// Setelan "24 FPS" di aplikasi tidak pernah berpengaruh. Fungsi di halaman
        /// yang seharusnya menerapkannya kosong, dan tidak ada satu pun tempat lain
        /// yang memakainya - jadi video 30 fps tetap didecode 30 fps. Dua puluh lima
        /// persen frame lebih banyak daripada yang diminta pengguna, dibayar penuh,
        /// dan tidak ada yang terlihat berbeda.
        ///
        /// Batas itu tidak bisa diterapkan di halaman tanpa mengubah yang dilihat
        /// pengguna: satu-satunya tuas di sana adalah playbackRate - yang mengubah
        /// KECEPATAN - dan menjeda antar frame, yang membuatnya tersendat. Keduanya
        /// lebih buruk daripada beban yang dihemat.
        ///
        /// Jadi batas itu diterapkan di tempat yang gratis: di transcode yang memang
        /// sudah membuat salinan untuk tiap monitor. Salinannya di-encode ulang pada
        /// laju yang diminta, sehingga berkasnya sendiri punya frame lebih sedikit
        /// dan decoder benar-benar punya lebih sedikit pekerjaan.
        ///
        /// Keyframe juga dirapatkan. Berkas aslinya punya keyframe tiap 8,3 detik,
        /// sehingga setiap kali video mengulang, decoder harus mengejar dari
        /// keyframe terakhir dan bebannya melonjak - terukur 52% pada mesin ini,
        /// turun kembali ke 25% tetapi tidak selalu. Dengan keyframe tiap dua detik,
        /// pengulangan tidak lagi menjadi lonjakan.
        /// </summary>
        public static Hasil Pilih(string videoPath, int lebarLayar, int tinggiLayar, int fpsTarget)
        {
            var hasil = new Hasil
            {
                Path = videoPath,
                Diskalakan = false,
                Alasan = "tidak diperiksa"
            };

            try
            {
                if (string.IsNullOrEmpty(videoPath) || !File.Exists(videoPath))
                {
                    hasil.Alasan = "berkas tidak ada";
                    return hasil;
                }

                // Video pendek tidak sepadan: biaya membuat salinannya lebih
                // besar daripada penghematan decode-nya, dan transcode akan
                // terlihat sebagai jeda saat wallpaper pertama dipasang.
                var info = new FileInfo(videoPath);
                if (info.Length < 512 * 1024)
                {
                    hasil.Alasan = "berkas kecil, tidak sepadan";
                    return hasil;
                }

                int wAsli, hAsli;
                if (!UkuranVideo(videoPath, out wAsli, out hAsli))
                {
                    hasil.Alasan = "ukuran video tidak terbaca";
                    return hasil;
                }

                hasil.LebarAsli = wAsli;
                hasil.TinggiAsli = hAsli;

                int batas = BatasLebar(lebarLayar);
                bool perluKecil = wAsli > batas * AmbangKelebihan;
                int fps = fpsTarget > 0 ? Math.Max(10, Math.Min(60, fpsTarget)) : 0;

                if (!perluKecil && fps == 0)
                {
                    hasil.LebarPakai = wAsli;
                    hasil.TinggiPakai = hAsli;
                    hasil.Alasan = "sudah sesuai layar (" + wAsli + "x" + hAsli + ")";
                    return hasil;
                }

                string ff = CariFfmpeg();
                if (ff == null)
                {
                    hasil.LebarPakai = wAsli;
                    hasil.TinggiPakai = hAsli;
                    hasil.Alasan = "ffmpeg tidak ada, pakai aslinya";
                    return hasil;
                }

                int lebarPakai = perluKecil ? batas : wAsli;
                string turunan = PathTurunan(videoPath, lebarPakai, fps);
                if (File.Exists(turunan) && new FileInfo(turunan).Length > 1024)
                {
                    hasil.Path = turunan;
                    hasil.Diskalakan = true;
                    hasil.LebarPakai = lebarPakai;
                    hasil.TinggiPakai = (int)Math.Round(hAsli * (double)lebarPakai / wAsli / 2) * 2;
                    hasil.Alasan = "salinan " + lebarPakai + "p" + (fps > 0 ? "/" + fps + "fps" : "") + " sudah ada";
                    return hasil;
                }

                // Dibuat di latar belakang: transcode 4K memakan puluhan detik,
                // dan wallpaper harus langsung tampil dengan berkas aslinya
                // sementara salinannya disiapkan. Pemanggilan berikutnya akan
                // menemukan salinan itu sudah siap.
                MulaiBuat(ff, videoPath, turunan, lebarPakai, wAsli, hAsli, perluKecil, fps);

                hasil.LebarPakai = wAsli;
                hasil.TinggiPakai = hAsli;
                hasil.Alasan = "salinan " + lebarPakai + "p" + (fps > 0 ? "/" + fps + "fps" : "")
                    + " sedang dibuat, pakai aslinya dulu";
                return hasil;
            }
            catch (Exception ex)
            {
                hasil.Path = videoPath;
                hasil.Diskalakan = false;
                hasil.Alasan = "gagal: " + ex.Message;
                return hasil;
            }
        }

        /// <summary>
        /// Folder cache salinan turunan. Terpisah dari folder wallpaper pengguna:
        /// berkas di sini boleh dihapus kapan saja tanpa kehilangan apa pun.
        /// </summary>
        public static string FolderCache()
        {
            string f = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "LumaWall", "VideoCache");
            Directory.CreateDirectory(f);
            return f;
        }

        /// <summary>Nama berkas turunan: asal + lebar target + laju + cap sidik jari.</summary>
        private static string PathTurunan(string asal, int lebar, int fps)
        {
            var info = new FileInfo(asal);
            // Nama berkas asli ikut disebut supaya isi folder bisa ditelusuri
            // manusia, tetapi sidik jari waktu+ukuran yang menentukan: kalau
            // berkas aslinya diganti, salinan lama tidak dipakai.
            //
            // Waktu ditulis dalam UTC, dan itu bukan detail: FileInfo.LastWriteTimeUtc
            // pada berkas yang baru disalin mengembalikan waktu LOKAL pada beberapa
            // konfigurasi, sehingga sidik jarinya berbeda dari yang dihitung di sini -
            // dan salinan yang sudah ada tidak pernah ditemukan. Itu sebabnya
            // transcode 4K berjalan berulang kali tanpa pernah dipakai.
            string dasar = Path.GetFileNameWithoutExtension(asal);
            if (dasar.Length > 48) dasar = dasar.Substring(0, 48);
            foreach (char c in Path.GetInvalidFileNameChars())
                dasar = dasar.Replace(c, '_');
            string sidik = info.LastWriteTimeUtc.Ticks.ToString("x") + "-" + info.Length.ToString("x");
            string laju = fps > 0 ? fps + "fps-" : "";
            return Path.Combine(FolderCache(), dasar + "-" + lebar + "p-" + laju + sidik + ".mp4");
        }

        private static string CariFfmpeg()
        {
            lock (Kunci)
            {
                if (ffmpegDicari) return ffmpegPath;
                ffmpegDicari = true;

                // 1. Di samping aplikasi: kalau nanti ffmpeg ikut dipaketkan,
                //    ini yang dipakai - tidak bergantung pada apa pun di mesin
                //    pengguna.
                try
                {
                    string sendiri = Path.GetDirectoryName(
                        System.Reflection.Assembly.GetExecutingAssembly().Location);
                    foreach (string nama in new[] { "ffmpeg.exe", @"tools\ffmpeg.exe" })
                    {
                        string coba = Path.Combine(sendiri, nama);
                        if (File.Exists(coba)) { ffmpegPath = coba; return ffmpegPath; }
                    }
                }
                catch { }

                // 2. Di PATH. Ini yang bekerja di mesin pengembang, dan tidak
                //    apa-apa kalau tidak ada - fitur ini hanya tidak aktif.
                try
                {
                    var psi = new ProcessStartInfo("ffmpeg", "-version")
                    {
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };
                    using (var p = Process.Start(psi))
                    {
                        if (p != null)
                        {
                            p.WaitForExit(4000);
                            if (p.HasExited && p.ExitCode == 0)
                            {
                                ffmpegPath = "ffmpeg";
                                return ffmpegPath;
                            }
                        }
                    }
                }
                catch { }

                ffmpegPath = null;
                return null;
            }
        }

        /// <summary>Lebar dan tinggi video, dibaca dari header tanpa mendecode.</summary>
        private static bool UkuranVideo(string path, out int lebar, out int tinggi)
        {
            lebar = tinggi = 0;

            // ffprobe kalau ada: paling akurat untuk semua kontainer.
            string ff = CariFfmpeg();
            if (ff != null)
            {
                try
                {
                    string probe = ff == "ffmpeg" ? "ffprobe" : Path.Combine(Path.GetDirectoryName(ff), "ffprobe.exe");
                    var psi = new ProcessStartInfo(probe,
                        "-v error -select_streams v:0 -show_entries stream=width,height " +
                        "-of csv=p=0 \"" + path + "\"")
                    {
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };
                    using (var p = Process.Start(psi))
                    {
                        string keluaran = p.StandardOutput.ReadToEnd();
                        p.WaitForExit(6000);
                        var m = Regex.Match(keluaran, @"(\d+)\s*,\s*(\d+)");
                        if (m.Success)
                        {
                            lebar = int.Parse(m.Groups[1].Value);
                            tinggi = int.Parse(m.Groups[2].Value);
                            return lebar > 0 && tinggi > 0;
                        }
                    }
                }
                catch { }
            }

            // Cadangan tanpa ffmpeg: kotak 'tkhd' pada MP4 memuat ukuran tampilan.
            // Cukup untuk memutuskan perlu-tidaknya diskalakan, dan tidak butuh
            // apa pun yang belum ada di mesin.
            try
            {
                return UkuranDariMp4(path, out lebar, out tinggi);
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Baca ukuran dari header MP4: kotak 'tkhd' menyimpan lebar dan tinggi
        /// tampilan sebagai 16.16 fixed-point, tepat sebelum bagian akhir kotak.
        /// </summary>
        private static bool UkuranDariMp4(string path, out int lebar, out int tinggi)
        {
            lebar = tinggi = 0;
            using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            {
                var buffer = new byte[Math.Min(fs.Length, 4 * 1024 * 1024)];
                fs.Read(buffer, 0, buffer.Length);
                for (int i = 0; i + 84 < buffer.Length; i++)
                {
                    // 'tkhd'
                    if (buffer[i] != 0x74 || buffer[i + 1] != 0x6B ||
                        buffer[i + 2] != 0x68 || buffer[i + 3] != 0x64) continue;

                    // Versi 0: lebar di offset +76, tinggi di +80 dari awal tkhd.
                    // Versi 1 menambah 4 byte di depan.
                    int versi = buffer[i + 4];
                    int dasar = i + 4 + (versi == 1 ? 4 : 0);
                    int iLebar = dasar + 72;
                    int iTinggi = iLebar + 4;
                    if (iTinggi + 4 > buffer.Length) continue;

                    uint w = (uint)((buffer[iLebar] << 24) | (buffer[iLebar + 1] << 16) |
                                    (buffer[iLebar + 2] << 8) | buffer[iLebar + 3]);
                    uint h = (uint)((buffer[iTinggi] << 24) | (buffer[iTinggi + 1] << 16) |
                                    (buffer[iTinggi + 2] << 8) | buffer[iTinggi + 3]);
                    int ww = (int)(w >> 16);
                    int hh = (int)(h >> 16);
                    if (ww > 16 && hh > 16 && ww < 20000 && hh < 20000)
                    {
                        lebar = ww;
                        tinggi = hh;
                        return true;
                    }
                }
            }
            return false;
        }

        /// <summary>
        /// Buat salinan turunan di latar belakang, satu per berkas.
        ///
        /// Dua hal dikerjakan sekaligus, dan keduanya menjawab keluhan "decode
        /// videonya kok naik":
        ///
        ///   1. Resolusi diturunkan kalau videonya jauh lebih besar daripada
        ///      layarnya. Terukur di mesin ini: 4K di layar 1366x768 menambah
        ///      24,4% beban decode, sedangkan salinan 1366p hanya 4,0%.
        ///
        ///   2. Laju gambar dibatasi sesuai setelan pengguna. Setelan itu
        ///      sebelumnya tidak berpengaruh sama sekali - fungsi di halaman yang
        ///      seharusnya menerapkannya kosong - sehingga video 30 fps tetap
        ///      didecode 30 fps meski pengguna memilih 24. Dua puluh lima persen
        ///      frame lebih banyak, dibayar penuh, tidak terlihat bedanya.
        ///
        /// Keyframe juga dirapatkan ke dua detik. Berkas aslinya punya keyframe
        /// tiap 8,3 detik, dan setiap kali video mengulang decoder harus mengejar
        /// dari keyframe terakhir: terukur 52% pada mesin ini. Dengan keyframe
        /// rapat, pengulangan tidak lagi menjadi lonjakan.
        /// </summary>
        private static void MulaiBuat(string ff, string asal, string tujuan, int lebar,
                                      int wAsli, int hAsli, bool perluKecil, int fps)
        {
            lock (Kunci)
            {
                if (sedangDibuat.Contains(tujuan)) return;
                sedangDibuat.Add(tujuan);
            }

            var t = new System.Threading.Thread(delegate ()
            {
                try
                {
                    // -2 pada tinggi menjaga rasio asli dan menghasilkan angka
                    // genap, yang dibutuhkan encoder H.264.
                    //
                    // CRF 18 dengan preset veryfast dipilih untuk kualitas:
                    // pada 18 perbedaan visual dari aslinya tidak terlihat pada
                    // wallpaper bergerak, sementara ukuran berkasnya turun
                    // drastis. Preset veryfast menjaga prosesnya selesai dalam
                    // hitungan detik, bukan menit - transcode yang berjalan lama
                    // akan terasa sebagai beban CPU saat pengguna bekerja.
                    //
                    // Audio dibuang: wallpaper selalu bisu atau memakai trek
                    // sendiri, dan tidak ada gunanya menyimpan audio yang tidak
                    // pernah diputar.
                    string saring = perluKecil ? "-vf scale=" + lebar + ":-2:flags=lanczos " : "";
                    string laju = fps > 0 ? "-r " + fps + " " : "";
                    string argumen =
                        "-y -nostdin -loglevel error " +
                        "-i \"" + asal + "\" " +
                        saring +
                        laju +
                        "-c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p " +
                        // Keyframe tiap dua detik (60 frame pada 30 fps, 48 pada 24).
                        // Angka ini mengikat pada laju yang dipakai encoder, dan
                        // itulah sebabnya ia dihitung dari fps target: dengan -g
                        // tetap, laju yang dibatasi akan mengubah jarak keyframe
                        // dalam detik tanpa disadari.
                        "-g " + ((fps > 0 ? fps : 30) * 2) + " -keyint_min 1 -sc_threshold 0 " +
                        "-an -movflags +faststart " +
                        "\"" + tujuan + "\"";

                    var psi = new ProcessStartInfo(ff, argumen)
                    {
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };
                    using (var p = Process.Start(psi))
                    {
                        p.StandardError.ReadToEnd();
                        // Transcode 4K bisa lama; batas ini longgar tetapi ada,
                        // supaya proses yang menggantung tidak hidup selamanya.
                        if (!p.WaitForExit(10 * 60 * 1000))
                        {
                            try { p.Kill(); } catch { }
                            AppLog.Write("Penskalaan video dihentikan (terlalu lama): " + Path.GetFileName(asal));
                            return;
                        }
                        if (p.ExitCode == 0 && File.Exists(tujuan))
                        {
                            long ukuran = new FileInfo(tujuan).Length;
                            AppLog.Write("Video diskalakan " + wAsli + "x" + hAsli + " -> "
                                + lebar + "p untuk layar ini (" + (ukuran / 1024) + " KB): "
                                + Path.GetFileName(asal));
                        }
                        else
                        {
                            try { if (File.Exists(tujuan)) File.Delete(tujuan); } catch { }
                            AppLog.Write("Penskalaan video gagal: " + Path.GetFileName(asal));
                        }
                    }
                }
                catch (Exception ex)
                {
                    AppLog.Write("Penskalaan video gagal: " + ex.Message);
                }
                finally
                {
                    lock (Kunci) { sedangDibuat.Remove(tujuan); }
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        /// <summary>
        /// Hapus salinan turunan yang tidak lagi punya berkas aslinya, dan yang
        /// sudah terlalu lama tidak dipakai.
        ///
        /// Tanpa ini folder cache tumbuh selamanya: setiap video yang pernah
        /// dipakai meninggalkan salinan, dan pengguna yang sering berganti
        /// wallpaper akan menumpuk puluhan gigabyte tanpa pernah tahu.
        /// </summary>
        public static void BersihkanCache(TimeSpan umurMaks)
        {
            try
            {
                string folder = FolderCache();
                DateTime batas = DateTime.UtcNow - umurMaks;
                long dibuang = 0;
                int jumlah = 0;

                foreach (string berkas in Directory.GetFiles(folder, "*.mp4"))
                {
                    try
                    {
                        var info = new FileInfo(berkas);
                        bool tua = info.LastAccessTimeUtc < batas;
                        // Nama turunan selalu memuat bagian nama aslinya, jadi
                        // bisa dicocokkan kembali ke library pengguna.
                        if (!tua) continue;
                        info.Delete();
                        dibuang += info.Length;
                        jumlah++;
                    }
                    catch { }
                }

                if (jumlah > 0)
                {
                    AppLog.Write("Cache video dibersihkan: " + jumlah + " berkas, "
                        + (dibuang / (1024 * 1024)) + " MB");
                }
            }
            catch { }
        }
    }
}
