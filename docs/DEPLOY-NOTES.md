# Deploy notes

## Deploying the site

```
powershell -File tools/deploy-vercel.ps1
```

That script is the only supported path. It refuses the wrong Vercel account,
deploys `site/` to production, then fetches the public domain and moves the alias
itself if the domain is not serving the new deployment.

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
