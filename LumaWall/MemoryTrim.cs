using System;
using System.Runtime.InteropServices;

namespace LumaWall
{
    /// <summary>
    /// Working-set trimming for the WebView2 process group.
    ///
    /// Why this is the right lever for a wallpaper host, and where its limit is:
    ///
    /// A wallpaper is either animating where the user can see it, or it is stopped
    /// because something covers it, the session is locked, or the machine is on
    /// battery. The second state is the whole opportunity: the wallpaper is not on
    /// screen, so making its memory resident again costs a page fault that nobody
    /// sees. Trimming there is free.
    ///
    /// In the first state it is not free at all. Removing pages from a running
    /// decoder's working set means the frame pipeline faults them straight back in,
    /// which shows up as stutter. So nothing here is ever called while a wallpaper
    /// is playing - the callers are gated on the paused state.
    ///
    /// And the honest limit: SetProcessWorkingSetSize does not free commit. The
    /// pages are removed from the working set and, for a file-backed or
    /// pagefile-backed page, they can be dropped; but a private page that is still
    /// referenced comes back the moment it is touched. So this lowers the number
    /// Task Manager shows and the number that competes for physical RAM, and it does
    /// NOT lower commit charge. Both numbers are reported in the UI for that reason.
    /// </summary>
    internal static class MemoryTrim
    {
        // SetProcessWorkingSetSize needs PROCESS_SET_QUOTA and PROCESS_QUERY_INFORMATION.
        // EmptyWorkingSet needs PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA as well.
        private const int PROCESS_SET_QUOTA = 0x0100;
        private const int PROCESS_QUERY_INFORMATION = 0x0400;

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(int desiredAccess, bool inheritHandle, int processId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetProcessWorkingSetSize(IntPtr process, IntPtr minimumWorkingSetSize, IntPtr maximumWorkingSetSize);

        // EmptyWorkingSet lives in psapi.dll, NOT kernel32.dll. Declaring it in
        // kernel32 threw EntryPointNotFoundException at call time, and because that
        // exception was caught by the same try block that wrapped
        // SetProcessWorkingSetSize, it silently prevented the working-set call from
        // ever running - which is why the first build reported "0/5 process(es)"
        // trimmed. The measurement caught it; the log alone would not have.
        [DllImport("psapi.dll", SetLastError = true)]
        private static extern bool EmptyWorkingSet(IntPtr process);

        /// <summary>
        /// Removes as many pages as possible from one process's working set.
        ///
        /// The -1, -1 argument pair is the documented "trim it all" form: it is not a
        /// request for an infinite quota, it tells the memory manager to remove as
        /// many pages as it can right now.
        ///
        /// Returns false rather than throwing. A renderer inside Chromium's sandbox
        /// can refuse the handle, and that is a normal outcome to log rather than a
        /// reason to fail the wallpaper - so the caller counts successes and moves on.
        /// </summary>
        public static bool TrimProcess(int processId)
        {
            if (processId <= 0) return false;

            IntPtr handle = OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, false, processId);
            if (handle == IntPtr.Zero) return false;

            try
            {
                // EmptyWorkingSet is the documented shorthand for the same operation
                // and is used first because it also drops the process's standby pages.
                if (EmptyWorkingSet(handle)) return true;
                return SetProcessWorkingSetSize(handle, new IntPtr(-1), new IntPtr(-1));
            }
            catch
            {
                return false;
            }
            finally
            {
                CloseHandle(handle);
            }
        }

        /// <summary>Working set and commit of one process, in bytes. -1 when unreadable.</summary>
        public static bool TryGetMemory(int processId, out long workingSet, out long commit)
        {
            workingSet = -1;
            commit = -1;
            if (processId <= 0) return false;
            try
            {
                using (System.Diagnostics.Process process = System.Diagnostics.Process.GetProcessById(processId))
                {
                    workingSet = process.WorkingSet64;
                    commit = process.PrivateMemorySize64;
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }
    }
}
