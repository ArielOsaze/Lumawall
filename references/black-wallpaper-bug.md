# The black-wallpaper bug: what it was, and the trap in testing for it

## The symptom

"Wallpaper cuma item, ga ke apply." The app reported every wallpaper ready, the log
was clean, and the desktop was black.

## What was actually wrong

Two separate things, and only one of them was a bug.

### 1. A real bug: the working-set trim killed the video decoders

The memory work trimmed the WebView2 process group's working set. It broke the
wallpapers twice, and both attempts are worth recording because both looked healthy
from inside the app.

**Attempt 1** - each paused wallpaper trimmed the pids `GetProcessInfos()` returned.
Every wallpaper in the app shares one `CoreWebView2Environment`, so that call returns
the **same list for all of them**, and the list includes the GPU process doing the
video decode. Pausing one monitor therefore trimmed the GPU process decoding the
other two.

Measured: GPU VideoDecode 6.4% → 0.0%, all three screens black. The log said
`Memory trimmed for paused wallpaper on \\.\DISPLAY3: 5/5 process(es)` and every
wallpaper still reported `renderer ready`.

**Attempt 2** - trim only when *every* wallpaper is stopped, so no decoder is live.
This is the version that should have worked.

Measured: it did work, and released **339 MB (447 MB → 108 MB, 76%** of the group's
working set). Then the covers came off, the wallpapers resumed - the log said
`resumed [\\.\DISPLAY2]` and the pause state was clean - and GPU VideoDecode stayed at
**0.0%**. The videos never came back. Restarting the app restored them immediately
(6.4% again).

So on this stack, trimming the working set of a process that owns a live video
decoder does not survive that decoder resuming, even though the documentation
describes the API as having no effect on rendering operations. The saving was real
and large; the price was a permanently black wallpaper, which is not a trade worth
making.

**Removed.** `tools/check-memory-plan.py` now pins both Win32 calls as forbidden, so
re-adding them fails a check rather than shipping a black desktop. The surviving
memory work - the browser arguments, the Chromium purge, `MemoryUsageTargetLevel`,
the V8 purge - is untouched by this and still in place.

### 2. Not a bug: the app was pausing the covered monitors correctly

The rest of the "black wallpaper" reports were the pause feature working. On this
machine all three monitors are covered by windows most of the time - Chrome, Settings,
Hermes, an NVIDIA overlay - and the app pauses a wallpaper whose screen is covered.
That is the behaviour that was asked for, and it is why a screenshot taken while
working shows a black desktop.

The measurement that distinguishes the two: **GPU VideoDecode**.

| what the GPU says | what it means |
|---|---|
| decode > 0% | wallpapers are rendering; a black screen is a window covering it |
| decode 0% while the app says a wallpaper is playing | the wallpaper is broken |

`tools/check-wallpaper-alive.ps1` reports both halves side by side - the app's own
pause decision from its log, and the GPU decode figure - and states which case the
machine is in.

## The trap in testing this

Two mistakes were made while testing, and both produced false evidence.

**Win+D is not a way to see the wallpaper.** It minimises windows, but the app's
fullscreen detector runs on the same event and can see the window during the
transition - so pressing Win+D produced a screenshot of a black desktop that was the
app *correctly* pausing, not the bug. Worse, on this machine the "Program Manager" and
overlay windows are themselves large enough to count as covering a monitor.

**A screenshot cannot tell the two cases apart.** It shows what is on screen, and
"black because a window covers it" and "black because the wallpaper is broken" look
identical. Only the GPU decode figure separates them.

## How to tell, next time

```
powershell -File tools/check-wallpaper-alive.ps1
```

That prints the app's last pause decision and the live GPU decode figure. If decode
is non-zero, the wallpapers work and something is covering the screen. If decode is
zero while the app believes a wallpaper is playing, it is a real bug - and the first
thing to check is whether anything in `MemoryTrim.cs` or the browser arguments has
started trimming again.

## What was also fixed on the way

`--process-per-site` was removed. It collapsed every display onto a single renderer -
the same coupling that made `--renderer-process-limit=1` unacceptable - so one renderer
crash would take down every monitor, and it is what let attempt 1's trim reach a
renderer that was still playing another monitor's video. Measured cost of removing it:
a renderer or two. Measured cost of keeping it: black wallpapers on every display.
