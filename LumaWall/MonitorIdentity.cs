using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace LumaWall
{
    /// <summary>
    /// The physical monitor behind a display number.
    ///
    /// Windows numbers displays in the order it finds them, and that order is not
    /// stable: unplugging and replugging an HDMI cable swaps the numbers between two
    /// monitors. Settings keyed by that number therefore follow the number rather than
    /// the screen, so a monitor inherits another monitor's framing - which is exactly
    /// how a wallpaper ends up mirrored and cropped on a display that was never
    /// configured that way.
    ///
    /// The monitor's own identity survives that. It comes from the display device's
    /// interface name, which carries the EDID vendor and product code plus the PnP
    /// instance Windows assigned to that physical monitor: "VSC423F#UID28932".
    ///
    /// The adapter instance in the middle of that name is deliberately dropped: it
    /// describes which connector the monitor is plugged into, which is the very thing
    /// that changes.
    /// </summary>
    internal static class MonitorIdentity
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

        private static readonly Dictionary<string, string> known =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Identity of the monitor behind a display number, or null when it cannot be read.
        ///
        /// Null is a normal answer, not a failure: a virtual display or a remote session
        /// has no EDID. Callers treat null as "cannot be reconciled" and leave that
        /// display alone, which is the safe behaviour - guessing would move settings onto
        /// a screen that never had them.
        /// </summary>
        public static string For(string deviceName)
        {
            if (string.IsNullOrEmpty(deviceName)) return null;
            lock (known)
            {
                string cached;
                if (known.TryGetValue(deviceName, out cached)) return cached;
            }

            string value = Read(deviceName);
            lock (known) known[deviceName] = value;
            return value;
        }

        /// <summary>
        /// Drops the cache so the next call reads the display again.
        ///
        /// Required after a monitor change: the same display number can now belong to a
        /// different monitor, and a cached answer would describe the old one.
        /// </summary>
        public static void Forget()
        {
            lock (known) known.Clear();
        }

        private static string Read(string deviceName)
        {
            try
            {
                var info = new NativeDisplayDevice();
                info.Size = Marshal.SizeOf(typeof(NativeDisplayDevice));
                if (!EnumDisplayDevices(deviceName, 0, ref info, GetDeviceInterfaceName)) return null;
                return Condense(info.DeviceId);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Reduces "\\?\DISPLAY#VSC423F#5&amp;20627078&amp;1&amp;UID28932#{guid}" to
        /// "VSC423F#UID28932".
        /// </summary>
        internal static string Condense(string deviceInterface)
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
    }
}
