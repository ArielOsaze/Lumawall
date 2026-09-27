"""Wire the desktop timer and the config reference into MainWindow.

Three things have to happen for the new features to be live:

  1. the manager needs the config, so a wallpaper can be handed its display's settings;
  2. the timer has to be created, started from the config, and refreshed when a setting
     changes;
  3. the manager has to be told when the config changes, or a slider would only take
     effect on the next wallpaper change.

Each is added where the existing code already does the equivalent thing, so the new work
follows the same lifetime as what is there.
"""

from pathlib import Path

WINDOW = Path('LumaWall/MainWindow.cs')
with WINDOW.open(encoding='utf-8', newline='') as handle:
    text = handle.read()
original = text

# ── 1. the manager gets the live config, and a timer is created ──────────────
anchor = '        private readonly WallpaperManager manager = new WallpaperManager();\r\n'
assert anchor in text, 'manager field not found'
text = text.replace(anchor, anchor + (
    '        // The desktop timer. Created here and started from the config, so its lifetime\r\n'
    '        // matches the window\'s: no timer exists while the app is closed, and closing the\r\n'
    '        // app cannot leave a stray widget on the desktop.\r\n'
    '        private DesktopTimer desktopTimer;\r\n'
), 1)

# ── 2. hand the config to the manager and start the timer ────────────────────
#
# Placed immediately after the window's own Loaded handler is wired, which is where the
# rest of the startup work already happens.
loaded_anchor = '            timer.Start();\r\n'
assert loaded_anchor in text, 'timer.Start() anchor not found'
text = text.replace(loaded_anchor, (
    '            timer.Start();\r\n'
    '\r\n'
    '            // The manager needs the live config so every wallpaper can be handed its\r\n'
    '            // display\'s look and span group. Set here rather than in the constructor\r\n'
    '            // because the config is loaded before the window is built, and a wallpaper\r\n'
    '            // created during startup has to see it.\r\n'
    '            manager.Config = config;\r\n'
    '\r\n'
    '            // The desktop timer, if the user has it on.\r\n'
    '            desktopTimer = new DesktopTimer(delegate { return config.Timer; });\r\n'
    '            desktopTimer.Start();\r\n'
), 1)

# ── 3. stop the timer on exit ────────────────────────────────────────────────
exit_anchor = 'private void ExitApp() { exiting = true; healthTimer.Stop(); RemoveForegroundHook(); manager.CloseAll(); tray.Visible = false; tray.Dispose(); Application.Current.Shutdown(); }'
assert exit_anchor in text, 'ExitApp not found'
text = text.replace(exit_anchor, (
    'private void ExitApp()\r\n'
    '        {\r\n'
    '            exiting = true;\r\n'
    '            healthTimer.Stop();\r\n'
    '            RemoveForegroundHook();\r\n'
    '            // The timer owns a top-level window, so it has to be disposed explicitly:\r\n'
    '            // shutting down the application does not close a window that was never\r\n'
    '            // activated, and it would stay on the desktop after the app exited.\r\n'
    '            if (desktopTimer != null) { try { desktopTimer.Dispose(); } catch { } desktopTimer = null; }\r\n'
    '            manager.CloseAll();\r\n'
    '            tray.Visible = false;\r\n'
    '            tray.Dispose();\r\n'
    '            Application.Current.Shutdown();\r\n'
    '        }'
), 1)

with WINDOW.open('w', encoding='utf-8', newline='') as handle:
    handle.write(text)

print('  manager.Config wired:   %s' % ('manager.Config = config;' in text))
print('  desktopTimer created:   %s' % ('desktopTimer = new DesktopTimer' in text))
print('  desktopTimer disposed:  %s' % ('desktopTimer.Dispose()' in text))
print('  bytes: %d -> %d' % (len(original), len(text)))
