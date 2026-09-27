"""Wire the new per-display options into the wallpaper manager.

The manager creates and reuses wallpaper windows in several places, and every one of them
has to hand the window its display's settings. Missing any single one leaves that
wallpaper wearing the previous display's grade, which reads as "the colour setting went to
the wrong monitor" - so the calls are added at each site explicitly rather than relying on
one entry point.
"""

from pathlib import Path

PROGRAM = Path('LumaWall/Program.cs')
# newline='' keeps the CRLF line endings exactly as they are on disk. Without it Python
# translates them to LF, and every anchor written with \r\n then fails to match - which is
# a confusing failure, because the same text appears to be right there in the file.
with PROGRAM.open(encoding='utf-8', newline='') as handle:
    text = handle.read()
original = text

# ── 1. the manager holds the live config and can push options ────────────────
anchor = (
    "        private bool globalPaused;\r\n"
    "        private readonly HashSet<string> pausedDevices = new HashSet<string>(StringComparer.OrdinalIgnoreCase);\r\n"
)
assert anchor in text, 'manager fields anchor not found'

addition = anchor + (
    "\r\n"
    "        /// <summary>\r\n"
    "        /// The live settings, so a window can be handed its display's look and span group.\r\n"
    "        ///\r\n"
    "        /// A reference rather than a copy: the user can change these while wallpapers are\r\n"
    "        /// running, and a snapshot taken at startup would go stale. Null until the window\r\n"
    "        /// sets it, and every reader tolerates null - a wallpaper created before that point\r\n"
    "        /// uses the neutral defaults, which is the behaviour of the build before these\r\n"
    "        /// features existed.\r\n"
    "        /// </summary>\r\n"
    "        public AppConfig Config;\r\n"
    "\r\n"
    "        /// <summary>\r\n"
    "        /// Hands a window the settings that apply to its display.\r\n"
    "        ///\r\n"
    "        /// Called at every point a wallpaper is created, changed or re-asserted. Skipping\r\n"
    "        /// any of them leaves that wallpaper wearing the previous display's grade, which\r\n"
    "        /// looks like a colour setting that went to the wrong monitor.\r\n"
    "        /// </summary>\r\n"
    "        private void PushOptions(WallpaperWindow window, string deviceName)\r\n"
    "        {\r\n"
    "            if (window == null) return;\r\n"
    "            AppConfig config = Config;\r\n"
    "            if (config == null) return;\r\n"
    "            try { window.SetOptions(config.OptionsFor(deviceName), config.SpanGroupFor(deviceName)); }\r\n"
    "            catch { }\r\n"
    "        }\r\n"
    "\r\n"
    "        /// <summary>\r\n"
    "        /// Re-applies the current look and span to every live wallpaper.\r\n"
    "        ///\r\n"
    "        /// This is what the settings page calls after a slider moves. Without it the user\r\n"
    "        /// would have to change wallpaper to see the effect, and the natural conclusion\r\n"
    "        /// would be that the control does nothing.\r\n"
    "        /// </summary>\r\n"
    "        public void RefreshOptions()\r\n"
    "        {\r\n"
    "            var all = new List<WallpaperWindow>();\r\n"
    "            foreach (var pair in windows) all.Add(pair.Value);\r\n"
    "            foreach (var pair in pending) all.Add(pair.Value);\r\n"
    "            foreach (WallpaperWindow window in all)\r\n"
    "            {\r\n"
    "                try { PushOptions(window, window.DeviceName); } catch { }\r\n"
    "            }\r\n"
    "        }\r\n"
)
text = text.replace(anchor, addition, 1)

# ── 2. every site that creates, reuses or changes a wallpaper ────────────────
#
# Matched on the surrounding lines rather than on the call alone, because these calls
# appear more than once and each one has to be treated individually.
sites = [
    # already active; reasserted
    ("                existing.ReassertDesktop();\r\n"
     "                SyncPause(existing, screen.DeviceName);\r\n",
     "                existing.ReassertDesktop();\r\n"
     "                SyncPause(existing, screen.DeviceName);\r\n"
     "                PushOptions(existing, screen.DeviceName);\r\n"),
    # changed inside the permanent host
    ("                existing.ChangeMedia(path, mute, fps);\r\n"
     "                SyncPause(existing, screen.DeviceName);\r\n",
     "                existing.ChangeMedia(path, mute, fps);\r\n"
     "                SyncPause(existing, screen.DeviceName);\r\n"
     "                PushOptions(existing, screen.DeviceName);\r\n"),
    # a swap that is already preparing
    ("                preparing.SetMute(mute);\r\n"
     "                preparing.SetTargetFps(fps);\r\n"
     "                SyncPause(preparing, screen.DeviceName);\r\n",
     "                preparing.SetMute(mute);\r\n"
     "                preparing.SetTargetFps(fps);\r\n"
     "                SyncPause(preparing, screen.DeviceName);\r\n"
     "                PushOptions(preparing, screen.DeviceName);\r\n"),
]

for old, new in sites:
    assert old in text, 'site not found: %r' % old[:60]
    text = text.replace(old, new, 1)

# The freshly created window: options are pushed before Show(), so the page's first paint
# already carries the grade instead of flashing the ungraded frame first.
old_new_window = (
    "            var window = new WallpaperWindow(screen, path, mute, fps);\r\n"
    "            pending[screen.DeviceName] = window;\r\n"
)
assert old_new_window in text, 'new-window site not found'
text = text.replace(old_new_window, (
    "            var window = new WallpaperWindow(screen, path, mute, fps);\r\n"
    "            // Pushed before Show() so the page's very first painted frame already carries\r\n"
    "            // the user's grade. Doing it after would flash the ungraded picture first.\r\n"
    "            PushOptions(window, screen.DeviceName);\r\n"
    "            pending[screen.DeviceName] = window;\r\n"
), 1)

# ── 3. WallpaperWindow exposes its device name for the refresh pass ──────────
old_matches = "        public bool MatchesScreen(Forms.Screen target)"
assert old_matches in text, 'MatchesScreen anchor not found'
text = text.replace(old_matches, (
    "        /// <summary>The display this wallpaper is attached to.</summary>\r\n"
    "        public string DeviceName { get { return screen.DeviceName; } }\r\n"
    "\r\n"
    "        public bool MatchesScreen(Forms.Screen target)"
), 1)

with PROGRAM.open('w', encoding='utf-8', newline='') as handle:
    handle.write(text)
print('  manager wired: %d -> %d bytes' % (len(original), len(text)))
print('  PushOptions call sites: %d' % text.count('PushOptions('))
print('  RefreshOptions present: %s' % ('public void RefreshOptions()' in text))
print('  DeviceName exposed:     %s' % ('public string DeviceName' in text))
