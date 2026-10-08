// PeriksaCepat.cs - periksa versi dan fitur pada build yang TERPASANG.
//
// KENAPA BERKAS INI ADA:
//
// Pertanyaan "di PC-ku sudah versi terbaru?" tidak bisa dijawab dengan
// FileVersion saja. Nomor versi bisa benar sementara isinya belum ikut
// terpasang - dan itu pernah terjadi di proyek ini: katalog di folder
// terpasang sempat tertinggal dari katalog di repo.
//
// Jadi yang diperiksa bukan hanya nomornya, tetapi juga:
//
//   1. Versi yang dilaporkan aplikasi itu sendiri (AppVersion, bukan berkas)
//   2. Katalog yang benar-benar dipakai: jumlah entri, Mature, thumbnail baru
//   3. Fitur ffmpeg: apakah kode unduh otomatisnya ada di build itu
//
// Dijalankan dengan: PeriksaCepat.exe <folder terpasang>
//
// Dibaca dengan mencari teks di dalam exe, karena itu cara yang paling langsung
// untuk mengetahui apakah sebuah fitur benar-benar ikut dibangun - jauh lebih
// pasti daripada membaca nomor versi.

using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

class PeriksaCepat
{
    static int Gagal = 0;

    static void Baris(string label, string nilai)
    {
        Console.WriteLine("     " + label.PadRight(22) + ": " + nilai);
    }

    static void Cek(bool benar, string pesan)
    {
        Console.WriteLine("     " + (benar ? "OK  " : "!!  ") + pesan);
        if (!benar) Gagal++;
    }

    static string BacaTeks(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        // Teks .NET disimpan sebagai UTF-16 dan ASCII, jadi keduanya dibaca.
        return Encoding.Unicode.GetString(bytes) + "\n" + Encoding.ASCII.GetString(bytes);
    }

    static int Main(string[] args)
    {
        string folder = args.Length > 0
            ? args[0]
            : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                           "Programs", "LumaWall");

        Console.WriteLine();
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine("   MEMERIKSA BUILD YANG TERPASANG DI PC INI");
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine();
        Baris("folder", folder);
        Console.WriteLine();

        string exe = Path.Combine(folder, "LumaWall.exe");
        string catalog = Path.Combine(folder, "catalog.json");

        if (!File.Exists(exe))
        {
            Console.WriteLine("  ! LumaWall.exe tidak ada di folder itu");
            return 1;
        }

        // ── 1. versi ──────────────────────────────────────────────────────
        Console.WriteLine("  ── 1. versi ──");
        var info = System.Diagnostics.FileVersionInfo.GetVersionInfo(exe);
        Baris("FileVersion", "[" + (info.FileVersion ?? "") + "]");
        Baris("ProductVersion", "[" + (info.ProductVersion ?? "") + "]");
        Baris("ukuran exe", (new FileInfo(exe).Length / 1024) + " KB");
        Baris("diubah", File.GetLastWriteTime(exe).ToString("yyyy-MM-dd HH:mm:ss"));
        Console.WriteLine();

        // ── 2. fitur di dalam exe ─────────────────────────────────────────
        Console.WriteLine("  ── 2. fitur di dalam exe ──");
        string teks = BacaTeks(exe);

        int alamatFfmpeg = Regex.Matches(teks, "gyan\\.dev").Count;
        int pesanFfmpeg = Regex.Matches(teks, "pemroses video").Count;
        int zipFile = Regex.Matches(teks, "Compression\\.ZipFile").Count;
        int kenburns = Regex.Matches(teks, "kenburns").Count;

        Cek(alamatFfmpeg > 0, "ffmpeg bisa diunduh sendiri (alamat unduh ada: " + alamatFfmpeg + ")");
        Cek(pesanFfmpeg > 0, "pesan kemajuan unduhan ada: " + pesanFfmpeg);
        Cek(zipFile > 0, "pembaca zip bawaan .NET dipakai: " + zipFile);
        Cek(kenburns > 0, "kenburns ada: " + kenburns);
        Console.WriteLine();

        // ── 3. katalog yang benar-benar dipakai ───────────────────────────
        Console.WriteLine("  ── 3. katalog yang dipakai aplikasi ──");
        if (!File.Exists(catalog))
        {
            Console.WriteLine("  ! catalog.json tidak ada");
            Gagal++;
        }
        else
        {
            string isi = File.ReadAllText(catalog, Encoding.UTF8);
            int entri = Regex.Matches(isi, "\"videoUrl\"").Count;
            int mature = Regex.Matches(isi, "\"Mature 18\\+\"").Count;
            int thumbBaru = Regex.Matches(isi, "lumawall\\.xinet\\.id/assets/thumbs").Count;
            int placeholder = Regex.Matches(isi, "nsfw_min\\.png").Count;

            Baris("entri", entri.ToString());
            Baris("Mature 18+", mature.ToString());
            Baris("thumbnail baru", thumbBaru.ToString());
            Baris("placeholder NSFW", placeholder.ToString());
            Console.WriteLine();
            Cek(entri > 26000, "katalog lengkap (" + entri + " entri)");
            Cek(mature >= 1000, "Mature cukup banyak (" + mature + ", target 1000)");
            Cek(thumbBaru >= 55, "thumbnail baru ikut terpasang (" + thumbBaru + ")");
            Cek(placeholder == 0, "tidak ada placeholder 'NSFW' (" + placeholder + ")");
        }
        Console.WriteLine();

        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        if (Gagal == 0)
        {
            Console.WriteLine("   BUILD YANG TERPASANG SUDAH LENGKAP");
        }
        else
        {
            Console.WriteLine("   ADA " + Gagal + " HAL YANG BELUM IKUT TERPASANG");
        }
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine();
        return Gagal == 0 ? 0 : 1;
    }
}
