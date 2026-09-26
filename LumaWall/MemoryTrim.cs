using System;
using System.Runtime.InteropServices;

namespace LumaWall
{
    /// <summary>
    /// Reads the memory of the WebView2 process group.
    ///
    /// ── what used to be here, and why it is gone ─────────────────────────────
    ///
    /// This class also trimmed working sets: the Win32 calls that empty a process's
    /// working set over the whole browser group, on the reasoning that a wallpaper
    /// which is not on screen has pages nobody is waiting for, so taking them away is
    /// free. The reasoning was wrong, and it was measured wrong twice:
    ///
    ///   Attempt 1 - trim whenever one wallpaper paused. Every wallpaper in the app
    ///   shares one CoreWebView2Environment, so GetProcessInfos() returns the same
    ///   process list for all of them, and that list includes the GPU process doing
    ///   the video decode. Pausing one monitor therefore trimmed the GPU process
    ///   decoding the other two. Measured: GPU VideoDecode went 6.4% to 0.0% and all
    ///   three screens went black, while the log reported "5/5 process(es) trimmed"
    ///   and every wallpaper still reported itself ready.
    ///
    ///   Attempt 2 - trim only when every wallpaper is stopped, so no decoder is live.
    ///   Measured: it worked, and released 339 MB (447 MB to 108 MB, 76% of the
    ///   group's working set). Then the covers came off, the wallpapers resumed - the
    ///   log said "resumed" and the pause state was clean - and GPU VideoDecode stayed
    ///   at 0.0%. The videos never came back; only restarting the app restored them.
    ///
    /// So on this stack, trimming the working set of a process that owns a live video
    /// decoder does not survive that decoder resuming, even though the API
    /// documentation describes Trim as having no effect on rendering. A real 76%
    /// saving against a permanently black wallpaper is not a trade worth making, and
    /// attempt 2 shows the problem is not the pause logic - that logic was correct and
    /// the decoder still died.
    ///
    /// What is left is measurement, which is what should have come first. The app
    /// reports working set AND commit for the whole group, so a future attempt at a
    /// memory saving starts from numbers instead of an assumption.
    /// </summary>
    internal static class MemoryTrim
    {
        private const int PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(int desiredAccess, bool inheritHandle, int processId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        /// <summary>
        /// Working set and commit of one process, in bytes.
        ///
        /// Two numbers, not one, and the difference is the point. The working set is
        /// the physical RAM held right now - what Task Manager's Processes tab shows
        /// and what competes with the user's game. The commit is what has to fit in
        /// RAM plus pagefile - the Details tab's "Commit size". A panel that showed
        /// only one of them could be read as a saving that is not there, because
        /// moving pages out of a working set does not release commit.
        /// </summary>
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
                // Chromium sets a restrictive security descriptor on its processes and
                // a sandboxed renderer can refuse even a read. Normal, not an error:
                // the caller skips the process rather than blanking the panel.
                return false;
            }
        }
    }
}
