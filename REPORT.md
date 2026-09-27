# Wallpaper Engine & Lively Wallpaper — Memory / Performance Management
### Scraped from public documentation, developer statements and community threads
Compiled from primary sources. Every claim is tagged:

- **[DOC]** = stated in official developer documentation
- **[DEV]** = stated by a named developer/maintainer in a public thread or commit
- **[SRC]** = read directly from the shipped/upstream source code (verifiable behaviour, not a marketing claim)
- **[USER]** = user-reported, unverified
- **[SPEC]** = community speculation / inference — treat as unconfirmed

---

## 1. The documented "Performance" settings and what each does internally

### 1.1 Wallpaper Engine — Performance tab

Wallpaper Engine's Performance tab exposes playback actions per trigger. The three states are
**Keep running**, **Pause**, and **Stop (free memory)**.

| Setting (Performance tab) | Documented behaviour |
|---|---|
| **Other application fullscreen** | Default = *Pause*. Can be set to **Stop (free memory)**. [DOC] |
| **Other application maximized** | Separate trigger from fullscreen (maximized still shows the taskbar). [DEV] |
| **Display asleep** | Can be set to **Stop (free memory)** → "Wallpaper Engine stops all playback when you turn your display off". [DOC] |
| **Application Rules** | Per-`.exe` rules: condition *Is running* / *Is playing audio* → playback action *Keep running* / *Pause* / *Stop (free memory)*. [DOC] |
| **FPS / MSAA / post-processing / quality** | Affect Scene + Web wallpapers only. **"This won't influence the performance of videos, they have fixed frame rates and quality."** [DOC] |

**What "Stop (free memory)" means internally — the developers' own wording:**

> "This means Wallpaper Engine will completely remove all wallpapers from memory when the application or game is launched" — [help.wallpaperengine.io/en/functionality/applicationrules.html](https://help.wallpaperengine.io/en/functionality/applicationrules.html)

> "You can configure Wallpaper Engine to free up any memory when in-game by changing the **Other application fullscreen** option to **Stop (free memory)**… Wallpaper Engine will now completely remove all wallpapers from memory when the .exe you configured is launched." — [help.wallpaperengine.io/en/performance/game.html](https://help.wallpaperengine.io/en/performance/game.html)

> "If you configure wallpapers to automatically 'Stop' (as opposed to just pausing them), they will be completely unloaded and not have any effect on any game or application." — Biohazard [DEV], [Common questions before buying](https://steamcommunity.com/app/431960/discussions/2/1354868867716443792)

**The single most important dev statement on Pause vs Stop and VRAM:**

> **"Pausing" will still occupy VRAM, "Stopping" will not use any VRAM.** … If you pause a wallpaper, the same amount of VRAM will still be used. If you "stop" a wallpaper, no VRAM will be used. If you want wallpapers to stop using video-ram while in-game, set the "Other application fullscreen" option to "Stop (free memory)".
> — Tim [DEV], [Does pausing still use some VRAM?](https://steamcommunity.com/app/431960/discussions/2/4846526298379420618)

> "Yes it still keeps using RAM. Change the fullscreen option to 'Stop' and it will free all the RAM while playing games."
> — Biohazard [DEV], [Ram](https://steamcommunity.com/app/431960/discussions/2/1643167006281752857)

### 1.2 Lively Wallpaper — Settings → Performance

Documented on the official wiki: **[github.com/rocksdanister/lively/wiki/Performance](https://github.com/rocksdanister/lively/wiki/Performance)**

| Setting | Documented behaviour |
|---|---|
| **Wallpaper Playback → Pause Algorithm** | Grid (default) / All Process / Foreground Process / Direct3D |
| **Application Focused** | Pause / ignore |
| **Application Fullscreen** | Pause / ignore (default = *pause*) |
| **Battery / Power-save mode** | Pause on battery, pause in power-save mode |
| **Remote Desktop** | Pause when an RDP session is active |
| **Display pause rule** | Per-display or all-screens pause |

**Pause algorithms, in the maintainer's own words [DOC]:**

- **Grid (default)** — "The screen is divided into a grid (tiles), and intersection calculation is used to check if windows are visually covering the display (by default 95% coverage, settings field `ProcessMonitorGridTileCoverageThreshold`)." Reliable across window arrangements and displays.
- **All Process** — "Pauses wallpapers when any running application is covering the screen, does not work in some situations like multiple window side by side."
- **Foreground Process** — "Pauses wallpapers when the active application is covering the screen."
- **Direct3D** — "Checks if a full-screen (exclusive mode) Direct3D application is running; **none of the additional performance settings have any effect in this mode, not recommended**."

**Source-code confirmation [SRC]** — `Lively.Common/Helpers/WindowUtil.cs`, `IsDisplayCoveredByWindowGrid()`:
```
int cols = ceil(width / tileSize); rows = ceil(height / tileSize);
foreach window: if IsWindowCoveringTarget(rect, screenBounds, 0.95) return true;
                mark overlapping tiles covered; if ((totalTiles-coveredCount)/totalTiles <= threshold) return true;
```
Defaults from `Lively.Models/SettingsModel.cs`:
```
ProcessMonitorAlgorithm      = grid
ProcessMonitorGridTileSize   = 50          // tiles
ProcessMonitorGridTileCoverageThreshold = 0.05   // 5% uncovered ⇒ pause
AppFocusPause                = ignore
AppFullscreenPause           = pause
BatteryPause                 = ignore
VideoPlayerHwAccel           = true
ProcessTimerInterval         = 500 ms
```
So the *"95% coverage"* in the wiki is the single-window fast-path (`IsWindowCoveringTarget(...,0.95)`); the **grid** path pauses when **95% of tiles are covered** (i.e. ≤5% of the screen remains visible). The two numbers describe the same "≥95% covered" rule from opposite directions — this is a genuine doc/code ambiguity worth knowing.

> "**Regardless of wallpaper type, lively will completely pause the playback of the wallpaper when fullscreen apps or games run.**" [DOC]

> "Wallpaper pauses (~0% usage) when running fullscreen games or application" — [rocksdanister.com/lively](https://www.rocksdanister.com/lively/) [DOC]

**⚠️ Important caveat that the docs omit but the maintainer states in issues [DEV]:**
Lively's "pause" keeps the player process alive — it does **not** free VRAM:

> "High use of GPU VRAM when wallpapers are paused… even when I pause them, it is using like 10% of my 12gb VRAM" — [issue #2995](https://github.com/rocksdanister/lively/issues/2995) [USER]
> Maintainer: "That was originally planned but other things came up and ended up being forgotten. To be honest this one is going to be very difficult to implement since wallpapers are separate program so each time new processes will need to be spawned and closed repeatedly which is taxing and error prone… **The recommendation for the time being is to use smaller files.**" — rocksdanister [DEV]

Source confirms pause = mpv `set_property pause true`, process stays alive [SRC]:
```csharp
public void Pause()  { SendMessage("{\"command\":[\"set_property\",\"pause\",true]}\n"); }
public void Play()   { SendMessage("{\"command\":[\"set_property\",\"pause\",false]}\n"); }
public async Task Close() { ... SendMessage("{\"command\":[\"quit\"]}\n"); }
```

---

## 2. Do they pause/suspend wallpapers when a fullscreen app is running?

**Yes — both, by default, and this is documented.**

**Wallpaper Engine [DOC]:** "By default, Wallpaper Engine pauses itself while you are in-game." ([performance/game.html](https://help.wallpaperengine.io/en/performance/game.html))

Developer clarification of what counts as "fullscreen" vs "maximized" [DEV]:
> "A maximized window will still show the task bar, i.e. it doesn't actually cover the entire screen like fullscreen windows do."
> "There is no difference between games or applications, if anything is fullscreen, the respective option should be triggered."
> — Biohazard, [Wallpaper Engine doesn't stop when applications are maximized](https://steamcommunity.com/app/431960/discussions/1/1697175413675068655)

**Lively [DOC]:** "lively will completely pause the playback of the wallpaper when fullscreen apps or games run." Additionally: pause on battery, pause on remote desktop, pause per running application, and "Play wallpaper only on desktop."

**Both have known gaps where pause fails to trigger** (relevant if your goal is reliably low RAM):
- Wallpaper Engine: multiple side-by-side / partially-overlapping windows. Community tool `wallpaper-engine-controller` exists specifically because "Wallpaper Engine has basic occlusion detection (pausing for maximized windows on a monitor), but it doesn't handle advanced scenarios like multiple side-by-side windows obscuring the desktop." ([github.com/dnetguru/wallpaper-engine-controller](https://github.com/dnetguru/wallpaper-engine-controller)) [SPEC/USER]
- Lively: the old foreground-window algorithm had exactly this failure mode, which the maintainer replaced in 2025:
  > "New 'Grid' algorithm divides the screen into 50x50 tiles and check for intersection with all the top level windows, this solves all edge cases: 1. Overlapping window. 2. Snapped window or any side by side layout. 3. Large size window but not covering desktop based on position. 4. Reliable desktop detection (no window = desktop.)" — rocksdanister [DEV], [issue #474](https://github.com/rocksdanister/lively/issues/474), fixed in commit `034e9a6`

---

## 3. Do they keep decoded frames in RAM, or stream them?

This is the core question, and the two apps answer it very differently.

### 3.1 Wallpaper Engine — **streams from disk by default; optional full-file RAM load**

Wallpaper Engine has a **"Video loading"** option in **Settings → General** with two modes. It is **not covered on the official help site** (verified: neither `help.wallpaperengine.io` nor `docs.wallpaperengine.io` contains the strings "Video loading" or "in-memory"), so the authoritative statements are developer posts:

> "You can change the behavior of how the video is loaded with the **'Video loading'** option in the 'General' tab in the settings. **'In-memory' will load the full video into RAM once** and **'from disk' will stream the video from your hard drive.**"
> — Tim [DEV], [Long videos as background](https://steamcommunity.com/app/431960/discussions/2/2965021152098201960)

> "Generally this is no issue as **videos are streamed from disk**, but an SSD would definitely be preferable for a huge video like this."
> — Biohazard [DEV], same thread

> "**The from disk option is safer, the in-memory is pretty much experimental.**"
> — Biohazard [DEV], [RAM usage](https://steamcommunity.com/app/431960/discussions/2/144512942751658993)

> "No, it doesn't load any that aren't in use. **It should only load the active video type wallpapers into RAM with that option**…"
> — Biohazard [DEV], same thread (answering a user who saw 26.2 GB used)

**Bottom line for your comparison baseline: for low RAM, "from disk" is the correct mode.** In-memory mode loads the *entire video file* into system RAM, which is why one user with 16 GB hit 12 GB used and had to switch back:

> "My memory usage was running at 12GB out of 16. I was using the new 64-bit option. Took me a while to find the cause. I switched it back to load from disk and everything is normal again." [USER]
> "using the RAM option won't show up in the task manager. It showed 70% usage but doesn't show up on the processes list." [USER]

Patch note confirming in-memory mode has been fragile historically [DOC]:
> "Fixed an issue that lead to crashes when using in-memory video loading." — [Steam patch, 15 Feb 2017](https://store.steampowered.com/news/posts/?feed=steam_community_announcements&appids=431960&enddate=1488555074)

### 3.2 Lively — **streams via mpv (demuxer readahead), never loads the whole file**

Lively delegates video to **mpv** (default), with libVlc / VLC / Windows Media Foundation as alternates. From source [SRC], `VideoMpvPlayer.cs` builds the command line:

```
--volume=0 --loop-file --keep-open --media-controls=no --geometry=-9999:0
--force-window=yes --no-window-dragging --cursor-autohide=no --window-minimized=yes
--stop-screensaver=no --input-default-bindings=no --no-border --input-cursor=no --no-osc
--input-ipc-server=<pipe>
--hwdec=auto-safe          (or --hwdec=no when hardware acceleration is off)
--target-colorspace-hint-mode=...
--config-dir=<dir>         (or --no-config)
```
Notably **there is no `--cache=yes`, no `--demuxer-max-bytes`, and no `--demuxer-cache-wait`** — i.e. Lively does *not* ask mpv to buffer the whole file; it uses mpv's default streaming demuxer readahead. Lively does expose a user `mpv.conf` at `…\plugins\mpv\portable_config\` (or `%LocalAppData%\Lively Wallpaper\Mpv\portable_config\`) so you can add e.g. `--aid=no` to drop the audio track and cut memory/decoder work. [DOC] [Video-Guide](https://github.com/rocksdanister/lively/wiki/Video-Guide)

For reference, mpv's own manual defines the buffering knobs Lively leaves at default: `--demuxer-max-bytes` "controls how much the demuxer is allowed to buffer ahead", `--demuxer-max-back-bytes` controls past-data retention, and `--cache-on-disk` exists to write cache to disk instead of RAM. ([mpv.io/manual/stable](https://mpv.io/manual/stable/)) [DOC, upstream]

**Both apps decode on the GPU by default** [DOC][DEV]:
- WE: "It is also using the video decoder of your GPU by default to reduce CPU usage to a minimum." ([videos/performance.html](https://help.wallpaperengine.io/en/videos/performance.html)); toggle is "Video hardware acceleration" in General (Tim: "I do not recommend this because it will put load on your CPU").
- Lively: `VideoPlayerHwAccel = true` by default [SRC]; "For best performance GPU decode (dedicated video hardware) is used to render the wallpaper, if you experience any stability issues then turn this feature off." [DOC]

**The decode path materially changes RAM.** When the GPU can't decode a format, the player silently falls back to software decoding and memory + CPU both jump. Both devs say this explicitly:
> "It may be that the Windows component that Wallpaper Engine relies on cannot handle your video format (encoder or bitrate would probably the issue) properly and it falls back on to the CPU" — Tim [DEV], [High CPU usage for Video Wallpaper](https://steamcommunity.com/app/431960/discussions/2/598530430735518764)
> "1080/720p x264 video format is recommended, webm memory usage can be due to many reasons such as **lack of decoding support in the gpu** and the higher resolution (4k) of the clip." — rocksdanister [DEV], [issue #1000](https://github.com/rocksdanister/lively/issues/1000)

---

## 4. Multiple monitors

| Aspect | Wallpaper Engine | Lively |
|---|---|---|
| Default pause granularity | **Per monitor** — "If you have multiple monitors, it will pause per monitor by default, meaning that if you start a game on one screen, only that one screen will be paused while Wallpaper Engine will continue to run on the other screens" — Biohazard [DEV] [FAQ](https://steamcommunity.com/app/431960/discussions/2/1354868867716443792) | Configurable: `DisplayPause` = **per-display** or **all-screens** [SRC] `SettingsModel.DisplayPauseSettings` |
| Span / stretched layout | Span layout forces "pause all monitors" — "Changed multi-monitor stretch layout to always use 'pause all monitors'." (2017 patch) [DOC] | — |
| Per-app wallpaper sets | Application Rules can Load wallpaper / Load playlist (spans all screens) or **Load Profile** for independent per-screen sets — [wallpaperperapp.html](https://help.wallpaperengine.io/en/functionality/wallpaperperapp.html) | Per-screen wallpaper assignment in the control panel |
| GPU requirement | **All monitors must be on the same GPU.** "Using both independent graphics solutions at the same time will break hardware acceleration of the desktop window manager… Windows will be forced to copy the wallpaper image from one GPU to the other - a very slow operation." Also: "Many users assume that switching Wallpaper Engine to a secondary GPU will increase the overall system performance. However, this is merely a common misconception and the overall system performance will actually degrade… Wallpaper Engine must use the same GPU as Windows Explorer." — [performance/dwm.html](https://help.wallpaperengine.io/en/performance/dwm.html) [DOC] | Not documented as a constraint |

**Known multi-monitor pause bugs** (both apps, useful for calibrating expectations):
- Lively #3264 [USER]: "When the same wallpaper is duplicated across multiple monitors, Lively pauses the wallpaper on all monitors when a fullscreen/maximized window is detected on just one monitor." (labelled *duplicate*)
- Lively #3110 [USER]: with per-screen pause, "the unfocused monitor's wallpaper starts playing even though there is a fullscreen window in that monitor."
- Lively #3282 [USER]: desktop input loss on an unrelated monitor while another monitor's wallpaper is paused (Windows 26H2, v2.2.1.4 beta).
- Lively #2982 [USER]: "Wallpaper pauses on all screens even when 'Per screen' pause rule is selected."
- WE: the community `wallpaper-engine-controller` exists because WE's occlusion detection "doesn't handle advanced scenarios like multiple side-by-side windows."

---

## 5. Developer explanations of memory handling (primary sources)

**Wallpaper Engine — "Tim" and "Biohazard" (developers), via Steam:**

1. **Pause ≠ free VRAM; Stop = free VRAM** — [discussions/2/4846526298379420618](https://steamcommunity.com/app/431960/discussions/2/4846526298379420618)
2. **In-memory vs from-disk loading semantics** — [discussions/2/2965021152098201960](https://steamcommunity.com/app/431960/discussions/2/2965021152098201960)
3. **In-memory mode is "pretty much experimental"; only active videos are loaded** — [discussions/2/144512942751658993](https://steamcommunity.com/app/431960/discussions/2/144512942751658993)
4. **Paused wallpapers still consume RAM** — [discussions/2/1643167006281752857](https://steamcommunity.com/app/431960/discussions/2/1643167006281752857)
5. **Multi-monitor pauses per monitor by default** — [discussions/2/1354868867716443792](https://steamcommunity.com/app/431960/discussions/2/1354868867716443792)
6. **GPU decode is the default; disable only as a troubleshooting step** — [discussions/2/3469487093572254279](https://steamcommunity.com/app/431960/discussions/2/3469487093572254279)
7. **Fullscreen vs maximized semantics** — [discussions/1/1697175413675068655](https://steamcommunity.com/app/431960/discussions/1/1697175413675068655)
8. **Most wallpapers < ~500 MB VRAM; the editor's VRAM counter ignored hidden layers (fixed)** — [discussions/2/3449213285573970990](https://steamcommunity.com/app/431960/discussions/2/3449213285573970990)
9. **Large-resolution GIFs are "unpacked for GPU-only rendering" → far more VRAM than the equivalent video** — [discussions/1/3194737075880795372](https://steamcommunity.com/app/431960/discussions/1/3194737075880795372)

**Wallpaper Engine — designer documentation (the only *formal* memory docs):**
- [Texture Optimization](https://docs.wallpaperengine.io/en/scene/performance/texture.html) [DOC]: DXT5 ("Good Performance") / DXT1 ("High Performance") "will occupy **only a quarter of memory** compared to an uncompressed image"; power-of-two padding cost is called out (a 1920×1080 DXT5 image is padded to 2048×2048); cropping layers "can significantly reduce the VRAM usage" on 4K+ wallpapers.
- [Project Resolution](https://docs.wallpaperengine.io/en/scene/performance/resolution.html) [DOC]: "you will achieve the best performance if the wallpaper matches the resolution of your screen"; non-native aspect ratios mean "an increased graphics card usage… and larger file sizes."
- [FPS Limiter](https://docs.wallpaperengine.io/en/web/performance/fps.html) [DOC]: web wallpapers are told to read the user's FPS limit via `wallpaperPropertyListener.applyGeneralProperties`.

**Lively Wallpaper — "rocksdanister" (maintainer):**
1. **Performance wiki** (resource model, pause algorithms, Task Manager clock-rate caveat) — [wiki/Performance](https://github.com/rocksdanister/lively/wiki/Performance)
2. **"Lively application and wallpapers are two separate things… it all depends on the wallpaper you choose to run."** [DOC]
3. **Pause does not release VRAM; close/reload is "very difficult to implement"** — [issue #2995](https://github.com/rocksdanister/lively/issues/2995)
4. **Grid algorithm design + commit `034e9a6`** — [issue #474](https://github.com/rocksdanister/lively/issues/474)
5. **WebView2 memory leak is not Lively's — "must be a bug on their end"** — [issue #3143](https://github.com/rocksdanister/lively/issues/3143)
6. **Recommended video format: 1080p/720p x264; GPU decode verified by "Video Decode" in Task Manager's GPU Engine column** — [issue #129](https://github.com/rocksdanister/lively/issues/129), [issue #682](https://github.com/rocksdanister/lively/issues/682)
7. **`ProcessMonitorGridTileCoverageThreshold` / `ProcessMonitorGridTileSize` are configurable in `Settings.json`** — [issue #3122](https://github.com/rocksdanister/lively/issues/3122)

**Lively release notes describing memory work [DOC]:**
- "UI will be completely shutdown when not being used (feature can be turned off in settings) to save memory." (v2.0 core/UI split) — [releases](https://github.com/rocksdanister/lively/releases)
- "Reduced idle memory consumption." (new Direct3D pause algorithm release)
- "New Core is powered by .NET Core 6 and has improved performance and reduced resource usage."
- "Replaced the default foreground window based pause detection with a grid based screen coverage algorithm…" + "Each display can now pause independently in per-display mode."
- "Improved handling of media elements - when a wallpaper is paused, any playing video or audio elements on the page are also paused automatically." (web wallpapers)

---

## 6. User-reported RAM figures (your comparison baseline)

### 6.1 Wallpaper Engine

| Reported figure | Context | Source | Type |
|---|---|---|---|
| **23 MB** | Developer's own wallpaper, cited as a normal reference figure | [Tim, Feb 2026](https://steamcommunity.com/app/431960/discussions/2/789954579030910571) | [DEV] |
| **41 MB** (whole app) | Developer, **on a 4K screen**: "It depends on the wallpaper, mainly the type and its resolution. Right now the app is using 41 Megabytes of system memory on my system on a 4K screen." | [Tim, Jul 2023](https://steamcommunity.com/app/431960/discussions/2/3805029995442981776) | [DEV] |
| **< 500 MB VRAM** | Developer's stated ceiling for normal wallpapers: "The vast majority of wallpapers uses less than around 500 MB of VRAM, anything above that is usually a good indicator that something odd has been done in the editor" | [Tim, Aug 2022](https://steamcommunity.com/app/431960/discussions/2/3449213285573970990) | [DEV] |
| **~40 MB** | 2017 user: scene & video wallpapers; web/apps ">100 MB" | [2017](https://steamcommunity.com/app/431960/discussions/2/135508292192566758) | [USER] |
| **33 MB** | 4 animated pixel-art wallpapers across 4 monitors | [2017](https://steamcommunity.com/app/431960/discussions/2/135514507321726823) | [USER] |
| **~400 MB** | Single machine, unspecified wallpaper | [2017](https://steamcommunity.com/app/431960/discussions/2/135514507321726823) | [USER] |
| **140 MB** | Looping a small GIF (Scene type) | [r/wallpaperengine](https://www.reddit.com/r/wallpaperengine/comments/6kfzrv/using_too_much_ram_for_looping_small_gif/) | [USER] |
| **172–175 MB** (wallpaper64.exe) | **Dual-monitor, looping videos** | [same thread, dchaosblade](https://www.reddit.com/r/wallpaperengine/comments/6kfzrv/using_too_much_ram_for_looping_small_gif/) | [USER] |
| **< 100 MB, "mostly under 50 MB"** | "most scenic wallpaper" on an i3 + 4 GB RAM | [r/wallpaperengine](https://www.reddit.com/r/wallpaperengine/comments/sg3dkr/im_planning_on_buying_this_tomorrow_but_my/) | [USER] |
| **">100 MB"** | 4K video wallpapers specifically: "4k video wallpapers only take above 100mb ram" | [same thread](https://www.reddit.com/r/wallpaperengine/comments/sg3dkr/im_planning_on_buying_this_tomorrow_but_my/) | [USER] |
| **790 MB → 12–13 GB, then crash** | Playlist of ~15 → ~50 wallpapers (1K–4K), growing over hours. Developer: "That should not happen" | [Feb 2026 thread](https://steamcommunity.com/app/431960/discussions/2/789954579030910571) | [USER] + [DEV] |
| **4.1 GB RAM** while "paused animation" | User report; dev: "4.1 GB of RAM usage is quite a lot… change 'Other application fullscreen' to 'Stop (free memory)'" | [same thread](https://steamcommunity.com/app/431960/discussions/2/789954579030910571) | [USER] + [DEV] |
| **5 GB system RAM + 3.7 GB VRAM** | One pathological workshop wallpaper; dev called it "probably one of the worst performing wallpapers I have ever seen" | [Aug 2022](https://steamcommunity.com/app/431960/discussions/2/3449213285573970990) | [USER] + [DEV] |
| **26.2 GB** | User with 32 GB RAM using **in-memory** video loading | [Jan 2017](https://steamcommunity.com/app/431960/discussions/2/144512942751658993) | [USER] |
| **12 GB / 16 GB** | Same in-memory mode issue; fixed by switching to "from disk" | [same thread](https://steamcommunity.com/app/431960/discussions/2/144512942751658993) | [USER] |

**Practical baseline from these numbers:** a normal **1080p video wallpaper** sits in the **tens of MB** (≈30–100 MB) range for the wallpaper process; a **4K video wallpaper** is commonly reported **just above 100 MB** of system RAM, with VRAM in the low hundreds of MB. Anything in the GB range is either in-memory loading, a broken/pathological wallpaper, a playlist leak, or a paused-but-not-stopped wallpaper on a big multi-monitor setup.

### 6.2 Lively Wallpaper

| Reported figure | Context | Source | Type |
|---|---|---|---|
| **~150 MB (idle)** | "task manager shows that the lively uses around 150mb of RAM (idle) when running but when an app is maximized it does not decrease. Should it not go down since the wallpaper gets paused?" | [r/LivelyWallpaper](https://www.reddit.com/r/LivelyWallpaper/comments/3_x4m06u/) | [USER] |
| **~300 MB** | "taking up 300MB of space just sitting there" | [same thread](https://www.reddit.com/r/LivelyWallpaper/comments/3_x4m06u/) | [USER] |
| **~20 MB + 1% CPU** | User comparison: "Switched to wallpaper engine for this but I can say that it was significantly lower on resource usage with Lively. If I recall, it was about 1% CPU and approx 20 MB RAM." | [r/LivelyWallpaper](https://www.reddit.com/r/LivelyWallpaper/comments/3_p9eknz/) | [USER] |
| **~1.5 GB private bytes after 24 h** | Web (website) wallpaper memory growth | [issue #3143](https://github.com/rocksdanister/lively/issues/3143) | [USER] |
| **~1 GB not freed** | After a website wallpaper was closed | [issue #3143](https://github.com/rocksdanister/lively/issues/3143) | [USER] |
| **4K WebM ≈ 10× a 1080p MP4** | The only explicit 1080p-vs-4K figure I could find for Lively. Dev reply: 1080/720p x264 recommended; webm may lack GPU decode support + higher resolution | [issue #1000](https://github.com/rocksdanister/lively/issues/1000) | [USER] + [DEV] |
| **~40 MB** | Third-party PR claiming RAM reduced to ~40 MB with Vulkan/ANGLE changes — **closed without merge**, so not shipped | [PR #3255](https://github.com/rocksdanister/lively/pull/3255) | [USER/contrib] |
| **10% of 12 GB VRAM (≈1.2 GB) while *paused*** | 3 screens, video wallpapers, paused — VRAM is *not* released by pausing | [issue #2995](https://github.com/rocksdanister/lively/issues/2995) | [USER] |

Note the honest framing in Lively's own docs: **"Lively application and wallpapers are two separate things… So to answer the question - it all depends on the wallpaper you choose to run."** [DOC] Lively's documented minimum is **4 GB RAM** for the OS + app overall ([Getting Started](https://github.com/rocksdanister/lively/wiki/Getting-Started)).

---

## 7. Documented vs. speculation — the explicit split

### ✅ Documented by the developers (high confidence)
- Fullscreen/maximized auto-pause is the default in both apps. [DOC]
- **Stop (free memory)** unloads wallpapers entirely; **Pause** does not release VRAM. [DEV]
- WE's **"Video loading: from disk"** streams; **"in-memory"** loads the whole file into RAM and is "pretty much experimental". [DEV]
- Lively's Grid algorithm = 50×50 tiles, pauses at ≥95% coverage; thresholds configurable in `Settings.json`. [DOC]+[SRC]
- Both use GPU hardware video decoding by default; unsupported codecs/resolutions silently fall back to CPU software decode. [DOC]+[DEV]
- WE pauses **per monitor** by default; span layout forces pause-all. [DEV]
- WE: all monitors should be on one GPU or DWM performance collapses. [DOC]
- WE's *only* formal memory docs are the designer-side texture/resolution pages (DXT5/DXT1 = ¼ memory, power-of-two padding, crop layers). [DOC]
- Both recommend **1080p/720p x264** as the low-cost video format. [DOC]+[DEV]

### ❓ Not documented anywhere official (I had to get these from dev forum replies or source)
- The **existence and semantics of WE's "Video loading" setting** — no help-site page; only Steam dev replies.
- WE's **default** for "Video loading" is not stated in any first-party doc. Community guides recommend "from disk"; the devs call in-memory "experimental", so from-disk is the safe assumption but is **not an official stated default**.
- The exact Lively coverage-threshold semantics (95% single-window vs 95%-tiles) — only reconcilable by reading `WindowUtil.cs`.
- Lively's **absence** of explicit mpv cache flags (i.e. reliance on mpv defaults) — only visible in source.
- Lively's numeric RAM figures: the maintainer does **not** publish any MB/GB figures. All Lively numbers are user reports.

### ⚠️ Community speculation / inference (do not cite as fact)
- "**Pause keeps the whole decoded stream in VRAM, Stop frees it**" is often stated as a general rule — the accurate dev statement is only the Pause-vs-Stop distinction above; the *amount* of VRAM retained is not quantified by the devs.
- The **300 MB Lively idle** and **~20 MB Lively** figures are single-user anecdotes on different versions/hardware and directly contradict each other — treat as noise.
- The **~40 MB via Vulkan** figure comes from a **closed, unmerged** community PR that also disclosed AI assistance; it is not a shipping feature.
- Claims that GIFs "require more memory" are correct in direction but the *mechanism* ("unpacked for GPU-only rendering") comes from a single dev reply; no formal doc quantifies it.
- The claim that WE's in-memory mode loads *all downloaded wallpapers* is **false** — the developer explicitly corrected it: "It should only load the active video type wallpapers into RAM with that option."
- Reddit's r/wallpaperengine FAQ line "Video wallpapers don't use a lot of resources…" is **community-maintained**, not developer-authored. [SPEC]
- Any "WE uses X MB for a 4K wallpaper" figure from a third-party blog (e.g. wallpaperengine.space, cloudspress, itechguides) is unsourced aggregation — I excluded those numbers from the tables above.

---

## 8. Practical takeaways for keeping RAM low with high-res video wallpapers

Derived strictly from the documented behaviour above:

1. **Use "Stop (free memory)", not "Pause", on the fullscreen/maximized triggers** — this is the only setting both dev teams say actually releases RAM/VRAM.
2. **Keep WE's video loading on "from disk"**; in-memory multiplies RAM by the file size and is labelled experimental.
3. **Re-encode 4K sources to 1080p x264** (both dev teams recommend this); 4K/HEVC/WebM/AV1 raise the odds of a silent software-decode fallback, which is where the multi-GB numbers come from.
4. **Verify hardware decode is actually happening** — WE: the video is decoded by the GPU by default; Lively: check for "Video Decode" in Task Manager's GPU Engine column.
5. **Prefer video over high-resolution GIF/Scene for the same content** — a large GIF is unpacked for GPU rendering and costs far more VRAM than the equivalent video.
6. **Fix multi-monitor topology first** — all monitors on one GPU; two GPUs make DWM copy frames between cards.
7. **Beware playlists** — the one reproducible leak in the WE corpus is RAM growing while cycling a large playlist; and Lively pauses per-display/all-screens inconsistently in several open issues.
8. **On Lively, pausing does not free VRAM** — if you need VRAM back for gaming, you must close the wallpaper (or the app), since the maintainer says a close/reload-on-game feature is unimplemented.

---

## 9. Full source list

**Official documentation**
- WE help — Performance issues / low FPS with games: https://help.wallpaperengine.io/en/performance/game.html
- WE help — Fix issues with specific apps or games (Application Rules, "Stop (free memory)"): https://help.wallpaperengine.io/en/functionality/applicationrules.html
- WE help — Video freezes / stuttering / bad performance (GPU decoder default): https://help.wallpaperengine.io/en/videos/performance.html
- WE help — High GPU usage misconception: https://help.wallpaperengine.io/en/performance/gpu.html
- WE help — Desktops with Integrated and Dedicated GPU (dwm.exe): https://help.wallpaperengine.io/en/performance/dwm.html
- WE help — Hibernation / Screensavers ("Display asleep → Stop (free memory)"): https://help.wallpaperengine.io/en/general/brokensleep.html
- WE help — Using LAV and DirectShow (4K/HEVC): https://help.wallpaperengine.io/en/videos/lav.html
- WE help — Command Line Controls (`pause` / `stop` / `play`): https://help.wallpaperengine.io/en/functionality/cli.html
- WE help — Select wallpapers per application / multi-monitor profiles: https://help.wallpaperengine.io/en/functionality/wallpaperperapp.html
- WE help — Centering wallpaper with monitors of different resolutions: https://help.wallpaperengine.io/en/general/multiscreencenter.html
- WE docs — Texture Optimization (VRAM, DXT5/DXT1 = ¼ memory): https://docs.wallpaperengine.io/en/scene/performance/texture.html
- WE docs — Project Resolution: https://docs.wallpaperengine.io/en/scene/performance/resolution.html
- WE docs — Web FPS Limiter: https://docs.wallpaperengine.io/en/web/performance/fps.html
- WE designer docs index: https://docs.wallpaperengine.io/en/
- Lively wiki — Performance (pause algorithms, resource model): https://github.com/rocksdanister/lively/wiki/Performance
- Lively wiki — Video Guide (mpv.conf, GPU decode): https://github.com/rocksdanister/lively/wiki/Video-Guide
- Lively wiki — Getting Started (4 GB RAM minimum): https://github.com/rocksdanister/lively/wiki/Getting-Started
- Lively wiki — Common Problems (RTSS, sleep/audio): https://github.com/rocksdanister/lively/wiki/Common-Problems
- Lively wiki — Command Line Controls (`--play`): https://github.com/rocksdanister/lively/wiki/Command-Line-Controls
- Lively wiki — Web Player (Cef "less RAM usage", cache behaviour): https://github.com/rocksdanister/lively/wiki/Web-Player
- Lively homepage ("pauses ~0% usage when fullscreen"): https://www.rocksdanister.com/lively/
- mpv manual (demuxer/cache options, hwdec): https://mpv.io/manual/stable/

**Developer statements (Steam / GitHub)**
- Tim — Pause occupies VRAM, Stop does not: https://steamcommunity.com/app/431960/discussions/2/4846526298379420618
- Tim — "Video loading": in-memory vs from disk: https://steamcommunity.com/app/431960/discussions/2/2965021152098201960
- Biohazard — in-memory is "experimental"; only active videos loaded: https://steamcommunity.com/app/431960/discussions/2/144512942751658993
- Biohazard — paused wallpapers still use RAM: https://steamcommunity.com/app/431960/discussions/2/1643167006281752857
- Biohazard — 41 MB on a 4K screen; Stop → ~0 RAM in games: https://steamcommunity.com/app/431960/discussions/2/3805029995442981776
- Biohazard — per-monitor pause by default; Stop unloads entirely: https://steamcommunity.com/app/431960/discussions/2/1354868867716443792
- Biohazard — fullscreen vs maximized semantics: https://steamcommunity.com/app/431960/discussions/1/1697175413675068655
- Tim — most wallpapers < 500 MB VRAM; pathological wallpaper 5 GB/3.7 GB: https://steamcommunity.com/app/431960/discussions/2/3449213285573970990
- Tim — "my current wallpaper is using 23 Megabytes": https://steamcommunity.com/app/431960/discussions/2/789954579030910571
- Biohazard — GIF unpacked for GPU rendering costs more VRAM: https://steamcommunity.com/app/431960/discussions/1/3194737075880795372
- Tim — GPU decode by default, LAV alternative: https://steamcommunity.com/app/431960/discussions/2/3469487093572254279
- Tim — LAV fix for a 4K120 decode fallback: https://steamcommunity.com/app/431960/discussions/2/598530430735518764
- Biohazard — hwdec support determines CPU cost: https://steamcommunity.com/app/431960/discussions/2/1696045708644625403
- Steam patch — in-memory loading crash fix + span = pause all: https://store.steampowered.com/news/posts/?feed=steam_community_announcements&appids=431960&enddate=1488555074
- rocksdanister — Grid algorithm design + commit: https://github.com/rocksdanister/lively/issues/474
- rocksdanister — pause doesn't free VRAM; close/reload "very difficult": https://github.com/rocksdanister/lively/issues/2995
- rocksdanister — WebView2 leak "must be a bug on their end": https://github.com/rocksdanister/lively/issues/3143
- rocksdanister — recommended 1080p/720p x264 + "Video Decode" check: https://github.com/rocksdanister/lively/issues/129
- rocksdanister — transcode-on-import proposal (1080p optimal): https://github.com/rocksdanister/lively/issues/682 and https://github.com/rocksdanister/lively/issues/1769
- rocksdanister — grid threshold configurable in Settings.json: https://github.com/rocksdanister/lively/issues/3122
- rocksdanister — 1080/720p x264 recommended; webm memory due to missing GPU decode + 4K: https://github.com/rocksdanister/lively/issues/1000
- Lively releases (UI shutdown to save memory, reduced idle memory, core rewrite): https://github.com/rocksdanister/lively/releases
- Community PR claiming ~40 MB with Vulkan (closed, unmerged): https://github.com/rocksdanister/lively/pull/3255

**Multi-monitor / pause bugs (community-reported)**
- https://github.com/rocksdanister/lively/issues/3264 · https://github.com/rocksdanister/lively/issues/3110 · https://github.com/rocksdanister/lively/issues/3282 · https://github.com/rocksdanister/lively/issues/2982 · https://github.com/rocksdanister/lively/issues/2938 · https://github.com/rocksdanister/lively/issues/3003
- https://github.com/dnetguru/wallpaper-engine-controller (WE occlusion limitation)

**User RAM figures**
- https://www.reddit.com/r/wallpaperengine/comments/6kfzrv/using_too_much_ram_for_looping_small_gif/
- https://www.reddit.com/r/wallpaperengine/comments/sg3dkr/im_planning_on_buying_this_tomorrow_but_my/
- https://www.reddit.com/r/wallpaperengine/comments/7osbni/how_to_make_wallpaper_engine_load_video_from_ram/
- https://www.reddit.com/r/wallpaperengine/comments/16tr4e6/does_wallpaper_engine_use_a_lot_of_resources/
- https://www.reddit.com/r/wallpaperengine/comments/fayfui/wallpaper_engine_tech_support_questions_thread_faq/
- https://www.reddit.com/r/LivelyWallpaper/comments/3_x4m06u/ · https://www.reddit.com/r/LivelyWallpaper/comments/1rot1fu/insane_ram_usage/ · https://www.reddit.com/r/LivelyWallpaper/comments/leqhks/i_need_it_to_use_less_ram/ · https://www.reddit.com/r/LivelyWallpaper/comments/j1q3k6/phyllotaxis_uses_alot_of_system_resources/
- https://steamcommunity.com/app/431960/discussions/2/135508292192566758 · https://steamcommunity.com/app/431960/discussions/2/135514507321726823 · https://steamcommunity.com/app/431960/discussions/2/2568690592375563184 · https://steamcommunity.com/app/431960/discussions/2/1696045708644625403

**Source code read for behavioural confirmation (Lively, `core-separation` branch)**
- `src/Lively/Lively.Models/SettingsModel.cs` — defaults (grid, 50 tiles, 0.05 threshold, hwaccel on, 500 ms timer)
- `src/Lively/Lively.Common/Helpers/WindowUtil.cs` — `IsDisplayCoveredByWindowGrid()`
- `src/Lively/Lively/Core/Suspend/Playback.cs` — evaluation loops, `PauseWallpapers()` / `PlayWallpapers()`
- `src/Lively/Lively/Core/Wallpapers/VideoMpvPlayer.cs` — mpv command line, Pause/Play/Close
- `src/Lively/Lively.UI.Shared/ViewModels/Settings/SettingsPerformanceViewModel.cs` — exposed performance settings
