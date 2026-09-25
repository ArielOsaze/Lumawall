# Deploy notes

## Vercel: check the account first

This machine has two Vercel logins:

| account | team | owns |
|---|---|---|
| `akuntuntas-5733` | AkunTuntas | `akuntuntas.xinet.id` |
| `arielbudinex-4629` | LumaWall | `lumawall.xinet.id` |

`vercel deploy` publishes into whichever account is currently logged in. Always
run `vercel whoami` first. `tools/deploy-vercel.ps1` refuses to run against the
AkunTuntas account, because deploying LumaWall there would be a silent mistake.

## `deploy --prod` success does not mean the domain works

`vercel deploy --prod` reported success and the deployment URL returned 200, but
`lumawall.xinet.id` returned **404** — the production alias had not been moved to
the new deployment. Every check the script made passed while visitors saw
"The page could not be found".

Always fetch the real domain after deploying, and move the alias if it is stale:

```
vercel alias set <deployment-url> lumawall.xinet.id
```

`tools/deploy-vercel.ps1` now does this automatically as its final step.

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
