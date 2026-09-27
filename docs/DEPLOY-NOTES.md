# Deploy notes

## Never trust a checker that has never failed

Two of this project's own checks were wrong in ways that made them useless, and
both passed for a long time before anyone noticed:

- **`tools/MeasureStudioLayout.cs` reported a 0px difference between the Studio
  columns** while the left column was visibly 746px shorter. It compared
  `ActualHeight` of the two Grid columns, and a Grid stretches both to the same
  height - the number could never be anything but zero. It sums the cards now.
  *A metric that cannot vary is not a measurement.*
- **`tools/test-studio-controls.ps1` counted exceptions across the whole log
  file**, so it reported a crash from a session that had already exited and
  blamed the current one. The app stamps every line with its pid; filter on it.

The rule that catches both: after writing a check, make the thing it checks
**fail on purpose** and confirm the check notices. Delete a translation key, push
a column out of balance, raise an exception in a click handler. A check that has
never gone red is a check that does not work.

## Two ways a WPF page can be broken while the build is clean

Both of these shipped in the same build and neither showed up in the log:

1. **A missing translation key renders as the key.** `Tr()` returns the key when
   it is not in the dictionary - 88 keys were missing, so the Studio page showed
   `studio.brightness` on a slider and `nav.studio` in the nav rail.
   `tools/check-translations.py` now fails on any key used but not defined, and on
   any entry that does not have exactly four languages.
2. **`button.Click += null` throws.** `SectionHeader(title, null, null)` from five
   call sites meant opening the Studio page raised `ArgumentNullException("handler")`
   every time. The window survived (the dispatcher catches it) and only the log
   recorded it. The helper guards now; a header with no action builds no button.

## WPF templating: `ControlTemplate` cannot target `Track`

`Track` is a `FrameworkElement`, not a `Control`, so `new ControlTemplate(typeof(Track))`
throws `ArgumentException` at construction. And `Track`'s parts - `Thumb`,
`DecreaseRepeatButton`, `IncreaseRepeatButton` - are plain CLR properties with no
`DependencyProperty` backing, so `FrameworkElementFactory.SetValue` cannot set
them either.

A custom `Slider` template therefore has to be **XAML**, parsed with
`XamlReader.Parse` and cached: property-element syntax is the only way to assign
`Track.Thumb` and friends. Everything else on the page is styled in code.

## Derive version numbers, never write them twice

The installer carried its own version string and the UI hard-coded two more. By
the time the binary was 4.1.2.0 the title-bar badge said `4.0`, the rail footer
said `v4.0.0`, and the installer said `4.1.3` - so Add/Remove Programs named a
version that was not installed.

- in code: read `Assembly.GetExecutingAssembly().GetName().Version` (`AppVersion.cs`)
- in Inno Setup: `#define MyAppVersion GetVersionNumbersString(AddBackslash(SourcePath) + "..\LumaWall\bin\Release\LumaWall.exe")`

## Rendering a WPF page to look at it

`tools/RenderStudioPage.cs` renders the real Studio page to a PNG. Things it
taught, each of which cost a run:

- **Match the app's bitness.** The app is x64; a 32-bit renderer throws
  `BadImageFormatException` loading it.
- **A Window must be shown before it has a visual tree.** `Show()` it off-screen
  at `Left = -32000`; without it the render is blank.
- **Pump the dispatcher** (`DispatcherPriority.ContextIdle`, a dozen times) before
  `RenderTargetBitmap.Render`, or the frame is captured mid-layout.
- **This machine's MSBuild has no .NET SDK resolver**, so an SDK-style csproj fails
  with "Could not resolve SDK Microsoft.NET.Sdk". Both helper projects are classic
  (non-SDK) projects for that reason.
- The app's window is capped at 950px tall, so the page scrolls in the real app -
  a render taller than that still comes out 1100px, which is the content height.

## A vision check is a hint, not a measurement

Asked whether "1x - 1x" in the preview summary was a repeated value, the vision
model explained it away as horizontal and vertical scale. It was the playback rate
and the zoom, printed without labels, and it read as a bug because it *was* one.
It also reported the Studio columns as balanced when one was 746px short.

Use vision to find *candidates*, then confirm each with arithmetic - a layout sum,
a key lookup, a log grep. The two together caught every fault in this list; either
one alone would have shipped several.

## Deploying the site


```
powershell -File tools/deploy-vercel.ps1
```

That script is the only supported path. It refuses the wrong Vercel account,
deploys `site/` to production, then fetches the public domain and moves the alias
itself if the domain is not serving the new deployment.

## Never run the real installer with a redirected /DIR

This cost the user their Start Menu entry, and the mechanism is worth understanding
because the damage is invisible until they go looking for the app.

To prove that the installer contained the fixed binary, it was run once with:

```
LumaWall-Setup-4.0.1.exe /VERYSILENT /DIR=<temporary folder>
```

The proof worked. The side effects were not considered:

- Inno Setup rewrote the Start Menu group, the uninstall registry entry and the
  `HKCU\...\Run` key to point at the **temporary folder**
- the temporary folder was then deleted, so every one of those became a dead
  reference
- Inno Setup also **remembers** the last install location and offers it as the
  default on the next run, so a later silent repair reinstalled to the temporary
  folder again and recreated it

The user's app looked like it had vanished. Its files were untouched the whole time
in `%LOCALAPPDATA%\Programs\LumaWall`.

**To inspect an installer, extract it - do not run it.** Copy the files out of an
existing install, or unpack the payload without executing the setup. Running it
writes to the registry and the Start Menu wherever you point it.

If it has already happened, `tools/reset-install-location.ps1` clears the remembered
location, the uninstall entry, the Run key, the Start Menu group and the temporary
folder - and keeps the real install and `%LOCALAPPDATA%\LumaWall` (settings,
wallpapers, logs). Then `tools/repair-install.ps1` reinstalls to the default location.
`tools/diagnose-install.ps1` reports which of those six places are broken, and is the
first thing to run when the app "disappears".

## Vercel: check the account first

This machine has two Vercel logins:

| account | team | owns |
|---|---|---|
| `akuntuntas-5733` | AkunTuntas | `akuntuntas.xinet.id` |
| `arielbudinex-4629` | LumaWall | `lumawall.xinet.id` |

`vercel deploy` publishes into whichever account is currently logged in. Always
run `vercel whoami` first. `tools/deploy-vercel.ps1` refuses to run against the
AkunTuntas account, because deploying LumaWall there would be a silent mistake.

## The 404 outage, and why rootDirectory must be `site`

`lumawall.xinet.id` went down with a 404 three times, in two different ways. All
three looked like success from the CLI, so all three are worth knowing.

### Cause 1 — the production alias does not move by itself

`vercel deploy --prod` reported success and the deployment URL returned 200, but
the public domain was 404: the production alias stayed on an older deployment.
`deploy-vercel.ps1` now checks the real domain as its final step and re-aliases
if needed.

### Cause 2 — the Git integration built the repository root

The Vercel project is connected to the GitHub repo, so every `git push` triggers
a build. With `rootDirectory` unset, that build starts at the **repository root**,
which has no `index.html` — the site lives in `site/`. The build produces an empty
deployment, Vercel promotes it to production, and the site 404s.

This happened again after the bilingual launch: a `git push` produced an empty
deployment and took the domain down, while the CLI deployment that had been
verified minutes earlier was still fine. The site was restored by re-pointing the
alias at that CLI deployment.

**`rootDirectory` must be `site`.** That is the setting the Git build needs, and
it is now set. Verified end to end: an empty commit pushed to `master` produced a
`READY` production deployment that serves both languages correctly.

### The consequence for the CLI

With `rootDirectory: site`, the CLI cannot deploy from inside `site/` any more —
it runs `cd site && vercel deploy`, so the upload already *is* the site folder,
and `rootDirectory: site` makes Vercel look for `site/site` inside it:

```
The specified Root Directory "site" does not exist.
```

**So the two paths are now split, and both are supported:**

| what you want | how |
|---|---|
| normal deploy after a change | `git push` — the Git build handles it |
| deploy without pushing | `powershell -File tools/deploy-vercel.ps1` |

`deploy-vercel.ps1` clears `rootDirectory` before deploying and restores it
afterwards, so the Git build keeps working. If it ever leaves `rootDirectory`
unset — a crash between the two steps — the next `git push` will produce an empty
deployment and take the site down. Check it with:

```
python tools/check-deploy-config.py
```

That script also verifies the alias points at a deployment that serves the real
site, which is the failure the CLI cannot see.

### Cause 3 - `npx vercel --prod` from the repository root

Running the CLI from the repository root does not work, and the error does not
say why:

```
Error: An unexpected error occurred!
Error: Upload aborted
```

It is uploading the entire repository - the app's `bin/`, the promo render's
`dist/`, the 42MB of installers under `site/assets/downloads/` - and the upload
is aborted part way. The CLI cannot know that `rootDirectory: site` means "start
here": it uploads what it is given, and the server then looks for `site/site`
inside it.

So there are exactly two working paths, and `vercel` from the root is neither:

| what you want | how |
|---|---|
| normal deploy after a change | `git push` - the Git build handles it |
| deploy without pushing | `powershell -File tools/deploy-vercel.ps1` |

Both verified end to end. Reach for `git push`: it is what the project is wired
for, and it produces a `READY` production deployment with the alias attached.

## Deployment protection

The project has `ssoProtection: all_except_custom_domains`, so every
`*.vercel.app` URL requires a Vercel login. The custom domain is public. Use
`vercel curl` to reach a protected deployment URL.

## The promo video

Rendered from React source in `promo/`, not from ffmpeg filters or PIL.

```
cd promo
node render.mjs --duration 52 --crf 18 --out ../site/assets/video/lumawall-promo.mp4
```

- Animations are pure functions of time (`promo/src/anim.js`). No motion library:
  a library drives from the wall clock, so the same frame number would produce a
  different image on every run.
- The renderer sets the frame explicitly via `window.__setFrame`, then captures
  with CDP. A re-run produces the same video.
- Assets come from `site/assets`, so the video cannot show a stale logo or a
  stale screenshot.

Verify after rendering:

```
python tools/check_frames.py site/assets/video/lumawall-promo.mp4 --expect 52
node tools/verify-live.mjs
```

A scene that throws renders as black frames while the renderer still reports
success — that happened once and cost 46 of 52 seconds. `SceneBoundary` and
`window.__sceneErrors` exist to make it loud instead.

## Building a catalogue from other people's sites

### A page's stated resolution describes its images, not its video

Every detail page on the source site said 1920x1080. The file it linked was 960x540. The
resolution text was about the page's own thumbnails, and reading it produced a catalogue of
SD files labelled as HD - the exact "pecah" the catalogue was supposed to avoid.

Measure the file. `ffprobe` on a Range-fetched head and tail is enough, because the MP4
header sits at one end or the other. Anything that cannot be measured is dropped, not
assumed: unknown is not good enough when the promise is "HD".

### A claimed resolution from a collection script is not evidence either

A collection of 7688 entries arrived with `w` and `h` fields. A sample of 30 files showed 1
claim out of 10 exact - a file claiming 3840x2160 was really 1280x720. Adopting those numbers
would have shipped a catalogue where a seventh of the entries look broken.

Re-measure every file before adopting it. The measurement is the only thing that goes in the
catalogue.

### The site's tag menu is not the page's tags

The page carries a site-wide tag menu listing hundreds of tags - football, ronaldo, japan,
torii - and a regex over the whole document picks those up instead of the page's own. That
filed the entire catalogue under Anime Girls. The page's own tags are in the `subtags` list.

The same mistake in the other direction: on a second source the tags field held
`' + encodeURIComponent(data.matchedTag.slug) + '`, a JavaScript template that was never
rendered. A tag that looks like source code is a parser bug, not a tag.

### A sitemap index can under-report the sitemap

`app-sitemap.xml` was read as 28 pages, from the index. Probing page 29 onwards found 1000
urls each, up to page 68: 67679 urls instead of 28005. The index listed fewer pages than
existed, so the collection was missing 60% of the site and there was no error to notice.

Probe past the last page the index mentions until several consecutive pages come back empty.

### 429 is "ask again later", not "gone"

The site rate-limits by IP. Two collection processes sharing one IP made 3400 files fail
measurement, and every one was recorded as unmeasurable. A retry with a growing pause (2, 6,
14 seconds) recovers them; treating 429 as a failure silently discards good entries.

Never run two collectors against the same host at once, and never let a checker count a 429
as a dead url - it reports the catalogue as broken when the files are fine.

### urllib refuses a path it cannot encode

Files whose titles are Japanese or Chinese produced `UnicodeEncodeError` on every request,
and a third of one collection was recorded as unmeasurable when the files were fine.
Percent-encode the path before the request. The same fault exists in every tool that fetches
a url, so the helper lives in one place and is imported.

### Write shared state atomically

The catalogue state was read while a collector was writing it, and the read failed with
"Expecting value: line 1 column 1" - the file existed but was empty at that instant.
`write_text` truncates first and fills afterwards, so there is a window where the file is
invalid. Write to a temporary file in the same directory and `os.replace` it: a reader sees
the old file or the new one, never a partial one.

### A category word list can have a word in two lists

"skyline" was in the Cars list as a Nissan model and in the City list as a city horizon. The
classifier tries Cars first, so 79 city wallpapers were filed under Cars. "dragon" sat in
Animals and Fantasy, "butterfly" in Animals and Nature, "racing" in Cars and Sports. A word
in two lists is not untidiness - it silently moves entries, and the total stays the same so
the counts look fine.

Write a checker that reports every overlap. Then decide the owner deliberately and say so in
a comment beside the word.

### A category rule order is a design decision, and it was wrong

Anime was checked before games, so 792 entries that the source tags as both "anime" and
"games" were filed under Anime Loop. A League of Legends or Genshin wallpaper is a game
wallpaper, and a browser filtering for Gaming should find it. Gaming went from 1470 to 4262
entries once the order was fixed.

### A checker must not read its own explanations as data

The overlap checker reported "skyline" as still present after it had been moved into a
comment - because the loader read the comment. `#   "skyline" - also a city horizon` put the
word straight back into the list. Strip comments before parsing, or the checker reports a
fault that is not there and hides the ones that are.

### Counts can be right while the contents are wrong

A category filter test passed - every category non-empty, every title distinct - while the
samples it printed showed "AI Girl" in City, One Piece wallpapers scattered across seven
categories, and 118 titles beginning with "2K". Print the sample titles, not just the
numbers. The number is what you hoped for; the titles are what a user sees.

### A title is not the wallpaper's name

The page title carries the site's own boilerplate: "... Live Wallpaper - Free Animated
Desktop Background | 67,000+ Free Live & Animated Wallpapers for PC". 11949 of 12090 titles
needed cleaning, and 335512 characters of boilerplate came out. Strip the suffix, the
resolution prefix ("2K Ganyu Genshin Impact"), and the uploader's file id
("GD035WAnQoVn603_Ai Generated Girl").

The file id matters twice: it is noise in the name, and its underscore is why an AI filter
using `\b` missed it - `_` is a word character, so the boundary never matched. Use
`(?<![a-z0-9])` instead.

### Generated art is labelled in the title when there is no tag

One source tags generated images with "ai"; the other has no such tag and says it only in the
title: "Midjourney Ai Fox Girl", "GD035WAnQoVn603_Ai Generated Girl". A filter that only
reads tags misses both. Check the title, the url and the description.

But check it precisely: "Ai Hoshino" is a character's name, not a statement that the image
was generated. A pattern that flags the word "ai" alone removes real artwork.
