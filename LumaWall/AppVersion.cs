// AppVersion.cs - the one place the app's version number is written down.
//
// Why this exists: the version was hard-coded in two places in the shell ("4.0" in the
// title bar badge and "v4.0.0" in the rail footer) and in a third place in the installer
// script. By the time the app was at 4.1.2 the UI still said 4.0, and a user looking at
// the badge to check whether an update had installed would be told the wrong answer.
//
// These read from the assembly's own version, which the build sets from AssemblyInfo.cs.
// A number that is derived cannot drift from the binary it describes.

using System;
using System.Reflection;

namespace LumaWall
{
    internal static class AppVersion
    {
        /// <summary>The full version, as in "v4.1.2". For the rail footer.</summary>
        public static string Full
        {
            get { return "v" + Number; }
        }

        /// <summary>Major and minor only, as in "4.1". For the title-bar badge, which is
        /// 9pt and sits beside the wordmark where a third component would be noise.</summary>
        public static string Short
        {
            get
            {
                Version version = VersionOf();
                return version.Major + "." + version.Minor;
            }
        }

        /// <summary>All four components, as in "4.1.2.0".</summary>
        public static string Number
        {
            get
            {
                Version version = VersionOf();
                // Build and Revision are -1 when a version was written with fewer parts,
                // which prints as "4.1.-1.-1" if it is not checked.
                if (version.Build < 0) return version.Major + "." + version.Minor;
                if (version.Revision < 0) return version.Major + "." + version.Minor + "." + version.Build;
                return version.Major + "." + version.Minor + "." + version.Build + "." + version.Revision;
            }
        }

        private static Version VersionOf()
        {
            // The informational version carries a suffix like "-beta" when there is one;
            // the assembly version is the plain number the installer was built with.
            Assembly assembly = Assembly.GetExecutingAssembly();
            return assembly.GetName().Version ?? new Version(0, 0, 0, 0);
        }
    }
}
