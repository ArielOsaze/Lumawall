# RAM: what was implemented, what was measured, what was rejected

This is the record of the memory work, written after the measurements rather than
before, because three of the six things that were planned turned out to be wrong.

## The one number that shapes everything

Working set and commit are different numbers, and the difference is the whole story:

- **Working set** is what Task Manager's Processes tab shows. It is the resident
  physical RAM, and it is what competes with the game the user is trying to run.
- **Commit** is what Task Manager's Details tab shows as "Commit size". It is the
  reservation: RAM plus pagefile. It is what runs out.

`SetProcessWorkingSetSize` lowers the first and does **not** touch the second. So any
claim of the form "we saved N MB" has to say which one. This app now reports both.

## What was implemented

### 1. Browser arguments that remove state a wallpaper never needs

All quality-neutral: none changes resolution, frame rate, codec or colour handling.
They remove caches and history that exist because Chromium's defaults are built for
browsing, and a wallpaper page is loaded once and lives for weeks.

| Argument | What it removes |
|---|---|
| `--disable-back-forward-cache` | A frozen page snapshot (DOM + JS heap) per history step. A wallpaper never navigates back. |
| `--process-per-site` | One renderer per display becomes one renderer for the group. Safe here only because the content is our own local file. |
| `--js-flags=--scavenger_max_new_space_capacity_mb=8` | Caps the V8 young generation. Documented by WebView2 as a memory reducer. |
| `--disk-cache-size=33554432` | A hard ceiling on the disk cache. |
| `--skia-font-cache-limit-mb=8` | Ceiling on the font cache. |
| `--skia-resource-cache-limit-mb=16` | Ceiling on the resource cache. |

Measured effect: **the WebView2 group went from 8 processes to 6.**

### 2. A real purge, at the moment the wallpaper actually stops

`Memory.simulatePressureNotification` over the DevTools Protocol, called when the app
itself decides the wallpaper is stopped (fullscreen app covering it, session locked,
on battery). Chromium then drops discardable memory, trims caches and runs extra GCs.

This is the explicit form of what `--msWebView2SimulateMemoryPressureWhenInactive`
does automatically, and it replaces that flag for a concrete reason: **the flag keys
off WebView2's own notion of "inactive"** — an invisible controller or a suspended
WebView — and a wallpaper window is neither. It stays visible on the desktop behind
whatever covers it. The flag would never fire. The app already knows the real answer
because it is the thing that made the decision.

Also `Memory.forciblyPurgeJavaScriptMemory` on a one-minute throttle, for the same
reason one level down: a wallpaper page's JS heap is stale state, not working memory.

### 3. Working-set trimming of the whole group

`EmptyWorkingSet` / `SetProcessWorkingSetSize(-1,-1)` on every process in the group,
gated on the paused state and nothing else.

The gate is the entire safety argument. A playing wallpaper is having its frames
faulted in continuously, so trimming it would turn every one of those into a fresh
page fault and show as stutter. A stopped wallpaper is not being drawn at all, so the
pages it loses are pages nobody is waiting on.

Runs on a worker thread, with the PID list read on the UI thread first — CoreWebView2
objects belong to the thread that created them, and the trim itself is plain Win32 on
an integer, so only that part moves off-thread.

### 4. `MemoryUsageTargetLevel = Low` while paused

The documented API for this. Goes to `Low` on pause and back to `Normal` on resume,
before the first frame is drawn, so the restore is never visible.

Deliberately **not** combined with `TrySuspendAsync`: TrySuspend requires the
controller to be invisible and sets the target level itself, and a wallpaper window
stays visible, so it would be rejected with `ERROR_INVALID_STATE` anyway.

## What was measured

Baseline was the shipped build with none of this. Same machine, same three monitors,
same wallpapers.

| | working set | commit | browser processes |
|---|---|---|---|
| **before** playing | 498 MB | 1477 MB | 9 |
| **before** paused | 498 MB | 1477 MB | 9 |
| **after** playing | 260 MB | 1339 MB | 7 |
| **after** paused (after trim) | **208 MB** | 1339 MB | 7 |
| **after** resumed | 209 MB | 1339 MB | 7 |

- **Pausing now releases 53 MB of working set (20%)**, where before it released 0.
- Commit is unchanged by the trim, exactly as the documentation says. Reported anyway.
- Memory returns on resume, and the log confirms all three wallpapers re-render.

Reproduce with `tools/measure-memory.ps1`.

## The bug the measurement caught

The first build reported `Memory trimmed for paused wallpaper: 0/5 process(es)` — and
the working set still dropped 43 MB, because the browser-side purge was doing the
work. The trim was contributing nothing.

Cause: `EmptyWorkingSet` was declared in `kernel32.dll`. It lives in **`psapi.dll`**.
The wrong declaration threw `EntryPointNotFoundException` at call time, and because it
shared a `try` block with `SetProcessWorkingSetSize`, it silently prevented the
working-set call from ever running.

Two lessons, both of which this repo has now learned twice:

1. **A log line that reports a count is not evidence the count is non-zero.** `0/5`
   looked like a success message in a log full of them. The measurement script is what
   surfaced it.
2. **Never wrap two independent API calls in one `try`.** The first one failing hid
   the second one entirely.

`tools/probe-trim-access.ps1` exists to answer the next question that came up: whether
the sandbox refuses the handle. It does not — every process in the group opens and
trims, including the renderer and the GPU process. The hypothesis was wrong; the DLL
was the whole problem.

## What was rejected, and why

- **`--msWebView2SimulateMemoryPressureWhenInactive`** — never fires for this app (see
  above). Shipping it would be a comment claiming a saving that never happens.
- **`--renderer-process-limit=1`** — would make one renderer crash take down every
  monitor's wallpaper. A robustness regression for memory `--process-per-site`
  already saves.
- **Job objects with `JOB_OBJECT_LIMIT_PROCESS_MEMORY`** — enforcement, not reduction.
  Exceeding the limit makes `VirtualAlloc` fail, which crashes the renderer, and
  Chromium's sandbox already puts renderers in jobs so the assignment often fails
  anyway. A crash is not a memory optimisation.
- **`--enable-low-end-device-mode`** — the one flag in this space that can silently
  change raster and decode quality. The user's constraint was explicit: reduce RAM
  without reducing how good it looks.
- **EcoQoS / `IDLE_PRIORITY_CLASS`** — a CPU and power mechanism, not a RAM one.
  Microsoft states Efficiency mode does not reduce RAM. It would risk frame pacing on
  the visible path for no memory at all.
- **`MEMORY_PRIORITY_INFORMATION` = `VERY_LOW`** — saves 0 bytes at idle. It changes
  who loses first under pressure, which is worth having eventually, but it is not a
  saving and was not implemented as one.
- **Trimming a playing wallpaper** — the single most tempting mistake here. It lowers
  the Task Manager number and costs frames. Gated off permanently.

## Why the UI was changed too

The performance panel used to report only the host process's working set. For a
WebView2 host that is a fraction of the real number, because the browser, GPU and
renderer processes are separate and hold most of the memory. A panel reading "60 MB"
while Task Manager shows 500 MB across seven processes is worse than no panel: it
teaches the user not to believe it.

It now sums the whole group (de-duplicated by PID, because several wallpapers share
one environment) and shows the commit figure underneath. Two numbers, so a trim cannot
be mistaken for a release.
