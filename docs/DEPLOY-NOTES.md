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

## The 404 outage, and why the Git integration was disconnected

`lumawall.xinet.id` went down with a 404 twice, in two different ways. Both
looked like success from the CLI, so both are worth knowing.

### Cause 1 — the production alias does not move by itself

`vercel deploy --prod` reported success and the deployment URL returned 200, but
the public domain was 404: the production alias stayed on an older deployment.
`deploy-vercel.ps1` now checks the real domain as its final step and re-aliases
if needed.

### Cause 2 — the Git integration built the wrong folder (the real one)

The Vercel project was connected to the GitHub repo, so every `git push` triggered
a build of the **repository root**. The site lives in `site/`, and the repo root
has no `index.html` — the build failed or produced an empty deployment, and Vercel
moved the production alias onto it.

Setting `rootDirectory: site` fixed the Git build but broke the CLI: the CLI runs
`cd site && vercel deploy`, so the upload already *is* the site folder, and
`rootDirectory: site` made it look for `site/site` inside that upload —

```
The specified Root Directory "site" does not exist.
```

**The two settings cannot both be correct.** The Git build needs
`rootDirectory=site`; the CLI needs it unset. The Git integration was therefore
disconnected, and the CLI is the only deploy path:

- `rootDirectory` is unset
- the project is not linked to the repository

If you ever re-connect the Git integration, set `rootDirectory` to `site` **and**
stop using the CLI deploy — and check the public domain afterwards either way.

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
