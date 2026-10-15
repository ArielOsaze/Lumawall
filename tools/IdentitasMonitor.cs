// IdentitasMonitor.cs - cetak identitas setiap monitor yang terpasang SEKARANG,
// lalu bandingkan dengan yang tersimpan di config.
//
// KENAPA BERKAS INI ADA:
//
// Dilaporkan: "wallpaper sudah di-crop, tapi setelah restart balik lagi dan tidak
// tersimpan". Kecurigaan pertama: pengaturan crop disimpan dengan kunci identitas
// monitor, dan identitas itu TIDAK stabil - kalau berubah, pengaturan lama jadi
// yatim dan aplikasi membuat entri baru bernilai default, sehingga crop terlihat
// hilang.
//
// Config saat ini memuat EMPAT kunci monitor padahal hanya ada TIGA monitor:
//
//     LEN0A14#UID28928
//     VSC423F#UID28934
//     VSC423F#UID28932
//     VSC423F#UID28930
//
// Empat kunci untuk tiga monitor berarti salah satu dari dua hal:
//   (a) ada entri yatim dari monitor yang pernah terpasang, atau
//   (b) identitas monitor memang berubah, dan entri baru dibuat dengan default
//
// Keduanya harus dibedakan, karena obatnya berbeda. Alat ini membacakan
// identitas yang sesungguhnya sekarang, supaya bisa dibandingkan dengan config.
//
// Cara bacanya sama persis dengan MonitorIdentity.cs: EnumDisplayDevices dengan
// bendera GET_DEVICE_INTERFACE_NAME, lalu DeviceId diringkas menjadi
// "MODEL#UIDnnnnn".

using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

class IdentitasMonitor
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct NativeDisplayDevice
    {
        public int Size;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceString;
        public int StateFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceId;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool EnumDisplayDevices(string device, uint number, ref NativeDisplayDevice info, uint flags);

    private const uint GetDeviceInterfaceName = 0x00000001;

    static string Ringkas(string deviceInterface)
    {
        if (string.IsNullOrEmpty(deviceInterface)) return null;
        string[] parts = deviceInterface.Split('#');
        if (parts.Length < 3) return null;
        string model = parts[1];
        string instance = parts[2];
        int uid = instance.IndexOf("UID", StringComparison.OrdinalIgnoreCase);
        if (uid >= 0) instance = instance.Substring(uid);
        if (string.IsNullOrEmpty(model) || string.IsNullOrEmpty(instance)) return null;
        return model + "#" + instance;
    }

    static int Main()
    {
        Console.WriteLine();
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine("   IDENTITAS MONITOR SEKARANG vs YANG TERSIMPAN DI CONFIG");
        Console.WriteLine("  ══════════════════════════════════════════════════════════════════");
        Console.WriteLine();

        // ── Monitor yang terpasang sekarang ───────────────────────────────
        var sekarang = new List<string[]>();
        Console.WriteLine("  ── monitor yang terpasang SEKARANG ──");

        for (uint i = 0; i < 12; i++)
        {
            var info = new NativeDisplayDevice();
            info.Size = Marshal.SizeOf(typeof(NativeDisplayDevice));
            if (!EnumDisplayDevices(null, i, ref info, 0)) break;

            // Layar yang tidak aktif tetap dilaporkan; yang dipakai hanya yang aktif.
            bool aktif = (info.StateFlags & 0x1) != 0;
            string nomor = info.DeviceName;

            // Baca identitas monitor yang menempel pada adaptor ini.
            var monitor = new NativeDisplayDevice();
            monitor.Size = Marshal.SizeOf(typeof(NativeDisplayDevice));
            string identitas = null;
            string mentah = null;
            if (EnumDisplayDevices(nomor, 0, ref monitor, GetDeviceInterfaceName))
            {
                mentah = monitor.DeviceId;
                identitas = Ringkas(monitor.DeviceId);
            }

            if (!aktif) continue;

            Console.WriteLine("     " + nomor.PadRight(16) + (aktif ? "AKTIF" : "tidak aktif"));
            Console.WriteLine("        DeviceString : " + info.DeviceString);
            Console.WriteLine("        identitas    : " + (identitas ?? "(tidak terbaca)"));
            Console.WriteLine("        DeviceId     : " + (mentah ?? "-"));
            Console.WriteLine();
            sekarang.Add(new string[] { nomor, identitas });
        }

        // ── Kunci yang tersimpan di config ────────────────────────────────
        string cfgPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "LumaWall", "config.json");

        Console.WriteLine("  ── kunci monitor yang tersimpan di config ──");
        if (!File.Exists(cfgPath))
        {
            Console.WriteLine("     ! config.json tidak ada: " + cfgPath);
            return 1;
        }

        string isi = File.ReadAllText(cfgPath);
        var tersimpan = new List<string>();

        // DisplaysByMonitor: [{"Key":"...","Value":{...}}, ...]
        Match blok = Regex.Match(isi, "\"DisplaysByMonitor\"\\s*:\\s*\\[(.*?)\\]\\s*,\\s*\"", RegexOptions.Singleline);
        if (blok.Success)
        {
            foreach (Match m in Regex.Matches(blok.Groups[1].Value, "\"Key\"\\s*:\\s*\"([^\"]+)\""))
                tersimpan.Add(m.Groups[1].Value);
        }

        foreach (string k in tersimpan)
        {
            bool ada = false;
            foreach (string[] s in sekarang)
                if (s[1] != null && s[1].Equals(k, StringComparison.OrdinalIgnoreCase)) ada = true;
            Console.WriteLine("     " + (ada ? "DIPAKAI  " : "YATIM    ") + k);
        }
        Console.WriteLine();

        // ── Kesimpulan ────────────────────────────────────────────────────
        Console.WriteLine("  ── kesimpulan ──");
        int yatim = 0;
        foreach (string k in tersimpan)
        {
            bool ada = false;
            foreach (string[] s in sekarang)
                if (s[1] != null && s[1].Equals(k, StringComparison.OrdinalIgnoreCase)) ada = true;
            if (!ada) yatim++;
        }

        Console.WriteLine("     monitor terpasang   : " + sekarang.Count);
        Console.WriteLine("     kunci di config     : " + tersimpan.Count);
        Console.WriteLine("     kunci yatim         : " + yatim);
        Console.WriteLine();

        if (yatim > 0)
        {
            Console.WriteLine("     ADA kunci yatim. Artinya identitas monitor berubah, sehingga");
            Console.WriteLine("     pengaturan yang disimpan dengan kunci lama tidak terbaca lagi -");
            Console.WriteLine("     dan itulah sebabnya crop terlihat hilang setelah restart.");
            return 2;
        }

        Console.WriteLine("     Tidak ada kunci yatim: identitas monitor stabil.");
        Console.WriteLine("     Jadi crop yang hilang bukan disebabkan identitas yang berubah.");
        return 0;
    }
}
