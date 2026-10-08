// UjiBacaTeks.cs - buktikan alat pembaca teks exe bekerja sebelum dipercaya.
//
// KENAPA BERKAS INI ADA:
//
// PeriksaCepat melaporkan "ffmpeg bisa diunduh sendiri: 0" pada build yang
// terpasang. Sebelum melaporkan itu sebagai bug, alatnya harus dibuktikan bisa
// menemukan teks yang PASTI ada - kalau tidak, "0" bisa berarti "tidak ada",
// atau bisa berarti "alatnya salah membaca".
//
// Itu pelajaran yang sudah berulang di proyek ini: pemeriksa yang tidak bisa
// gagal, dan pemeriksa yang tidak dibuktikan bisa membaca, sama-sama tidak
// berguna.
//
// Yang diuji: mencari teks yang dijamin ada di setiap build (nama aplikasi,
// nama kategori, nama kelas), lalu membandingkan jumlahnya antara exe yang
// dibangun dan exe yang terpasang.

using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

class UjiBacaTeks
{
    static string BacaTeks(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        return Encoding.Unicode.GetString(bytes) + "\n" + Encoding.ASCII.GetString(bytes);
    }

    static void Periksa(string label, string path)
    {
        Console.WriteLine();
        Console.WriteLine("  ══ " + label + " ══");
        if (!File.Exists(path))
        {
            Console.WriteLine("     ! tidak ada: " + path);
            return;
        }

        var fi = new FileInfo(path);
        Console.WriteLine("     " + path);
        Console.WriteLine("     ukuran: " + (fi.Length / 1024) + " KB, diubah " + fi.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"));
        Console.WriteLine();

        string teks = BacaTeks(path);

        // Teks yang DIJAMIN ada - kalau ini 0, alatnya yang salah.
        string[,] pasti = {
            { "LumaWall",              "nama aplikasi" },
            { "Mature 18",             "nama kategori" },
            { "catalog.json",          "nama berkas katalog" },
            { "renderer ready",        "pesan log" },
        };

        // Teks fitur baru - yang sedang dipertanyakan.
        string[,] fitur = {
            { "gyan.dev",              "alamat unduh ffmpeg" },
            { "pemroses video",        "pesan kemajuan unduhan" },
            { "kenburns",              "kenburns" },
            { "Ffmpeg",                "kelas Ffmpeg" },
            { "Compression.ZipFile",   "pembaca zip .NET" },
        };

        Console.WriteLine("     teks yang DIJAMIN ada:");
        int gagal = 0;
        for (int i = 0; i < pasti.GetLength(0); i++)
        {
            int n = Regex.Matches(teks, Regex.Escape(pasti[i, 0])).Count;
            Console.WriteLine("        " + (n > 0 ? "ADA " : "!!  ") + pasti[i, 1].PadRight(24) + n);
            if (n == 0) gagal++;
        }

        Console.WriteLine();
        Console.WriteLine("     teks fitur baru:");
        for (int i = 0; i < fitur.GetLength(0); i++)
        {
            int n = Regex.Matches(teks, Regex.Escape(fitur[i, 0])).Count;
            Console.WriteLine("        " + (n > 0 ? "ADA " : "TIDAK ADA ") + fitur[i, 1].PadRight(24) + n);
        }

        Console.WriteLine();
        if (gagal > 0)
        {
            Console.WriteLine("     ! " + gagal + " teks yang dijamin ada TIDAK ditemukan.");
            Console.WriteLine("       Berarti alat ini yang salah membaca, bukan exe-nya.");
        }
        else
        {
            Console.WriteLine("     Alat ini terbukti bisa membaca teks exe.");
            Console.WriteLine("       Jadi 'TIDAK ADA' di atas berarti memang tidak ada di build itu.");
        }
    }

    static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine("   MEMBUKTIKAN ALAT PEMBACA TEKS EXE BEKERJA");
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");

        Periksa("exe yang DIBANGUN (repo)",
                args.Length > 0 ? args[0]
                : @"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\LumaWall\bin\Release\LumaWall.exe");

        Periksa("exe yang TERPASANG",
                args.Length > 1 ? args[1]
                : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                               "Programs", "LumaWall", "LumaWall.exe"));

        Console.WriteLine();
        return 0;
    }
}
