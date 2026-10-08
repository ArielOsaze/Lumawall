// BuktiFitur.cs - buktikan fitur benar-benar ada di dalam exe, dengan cara
// yang benar.
//
// KENAPA BERKAS INI ADA:
//
// PeriksaCepat melaporkan "gyan.dev: 0" pada exe yang terpasang, padahal
// Ffmpeg.cs ada di repo, ada di csproj, dan lebih tua dari exe-nya. Artinya
// salah satu dari dua hal: fiturnya tidak ikut dibangun, atau cara pembacaan
// teks di alat itu yang salah.
//
// Menebak tidak cukup. Alat ini membaca exe dengan cara yang lebih teliti:
//
//   1. Membaca sebagai UTF-16 (cara .NET menyimpan string literal)
//   2. Membaca sebagai UTF-8
//   3. Membaca sebagai ASCII
//
// String literal di .NET disimpan sebagai UTF-16 di bagian #US dari metadata,
// bukan sebagai ASCII. Pencarian yang hanya membaca ASCII akan melaporkan
// "tidak ada" untuk teks yang sebenarnya ada - dan itu akan menuduh build yang
// sehat sebagai build yang rusak.
//
// Alat ini juga mencari teks yang DIJAMIN ada, supaya bisa dibuktikan bahwa
// cara pembacaannya memang bekerja.

using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

class BuktiFitur
{
    static int Main(string[] args)
    {
        string path = args.Length > 0 ? args[0] : @"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\LumaWall\bin\Release\LumaWall.exe";

        Console.WriteLine();
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine("   MEMBUKTIKAN FITUR ADA DI DALAM EXE");
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine();
        Console.WriteLine("  exe: " + path);

        if (!File.Exists(path))
        {
            Console.WriteLine("  ! tidak ada");
            return 1;
        }

        byte[] bytes = File.ReadAllBytes(path);
        var fi = new FileInfo(path);
        Console.WriteLine("  ukuran: " + (fi.Length / 1024) + " KB, diubah " + fi.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"));
        Console.WriteLine();

        // Tiga cara membaca, dan jumlah temuan per cara.
        string utf16 = Encoding.Unicode.GetString(bytes);
        string utf8 = Encoding.UTF8.GetString(bytes);
        string ascii = Encoding.ASCII.GetString(bytes);

        Console.WriteLine("  ── jumlah temuan per cara pembacaan ──");
        Console.WriteLine("     " + "teks".PadRight(30) + "UTF-16  UTF-8  ASCII");
        Console.WriteLine("     " + new string('-', 56));

        // Teks yang DIJAMIN ada di setiap build, supaya cara bacanya terbukti.
        string[] pasti = { "LumaWall", "catalog.json", "MainWindow", "WebView2" };
        Console.WriteLine("     (teks yang dijamin ada - pembuktian cara baca)");
        foreach (string t in pasti)
        {
            int a = Regex.Matches(utf16, Regex.Escape(t)).Count;
            int b = Regex.Matches(utf8, Regex.Escape(t)).Count;
            int c = Regex.Matches(ascii, Regex.Escape(t)).Count;
            Console.WriteLine("     " + t.PadRight(30) + a.ToString().PadRight(8) + b.ToString().PadRight(7) + c);
        }

        Console.WriteLine();
        Console.WriteLine("     (fitur baru yang sedang dipertanyakan)");
        string[] fitur = {
            "gyan.dev",
            "ffmpeg-release-essentials",
            "pemroses video",
            "Ffmpeg",
            "kenburns",
            "ffmpeg.exe",
            "Menyiapkan",
        };
        foreach (string t in fitur)
        {
            int a = Regex.Matches(utf16, Regex.Escape(t)).Count;
            int b = Regex.Matches(utf8, Regex.Escape(t)).Count;
            int c = Regex.Matches(ascii, Regex.Escape(t)).Count;
            Console.WriteLine("     " + t.PadRight(30) + a.ToString().PadRight(8) + b.ToString().PadRight(7) + c);
        }

        Console.WriteLine();
        Console.WriteLine("  ── kesimpulan ──");

        int alamat = Math.Max(Regex.Matches(utf16, "gyan\\.dev").Count, Regex.Matches(ascii, "gyan\\.dev").Count);
        int ffmpegKelas = Math.Max(Regex.Matches(utf16, "Ffmpeg").Count, Regex.Matches(ascii, "Ffmpeg").Count);
        int alamatFfmpeg = Regex.Matches(utf16, "ffmpeg-release-essentials").Count;

        Console.WriteLine("     kelas Ffmpeg ada        : " + (ffmpegKelas > 0 ? "YA (" + ffmpegKelas + ")" : "TIDAK"));
        Console.WriteLine("     alamat unduh ffmpeg ada : " + (alamatFfmpeg > 0 ? "YA (" + alamatFfmpeg + ")" : "TIDAK"));

        if (ffmpegKelas > 0 && alamatFfmpeg > 0)
        {
            Console.WriteLine();
            Console.WriteLine("     Fitur unduh ffmpeg ADA di build ini.");
            Console.WriteLine("     Laporan '0' sebelumnya berasal dari alat yang hanya membaca ASCII,");
            Console.WriteLine("     sedangkan string literal .NET disimpan sebagai UTF-16.");
            return 0;
        }

        Console.WriteLine();
        Console.WriteLine("     Fitur unduh ffmpeg TIDAK ADA di build ini.");
        return 1;
    }
}
