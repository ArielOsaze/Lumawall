# Verifies that lumawall.xinet.id is serving the site, and that the project's
# deploy path is still the one that works.
#
# ── why this is a verifier and not a deployer ────────────────────────────────
#
# This project is connected to GitHub, so Vercel deploys on every push. That path
# and a CLI deploy have CONTRADICTORY root-directory requirements, so only one can
# own the project:
#
#   owning path      rootDirectory   the deploy runs from
#   ---------------  --------------  ---------------------
#   git auto-deploy  "site"          the repo root
#   CLI deploy       ""              the site subfolder
#
# Git owns this project. rootDirectory is "site", which is what makes a push build
# the site folder instead of the repo root.
#
# The 404 this replaces: rootDirectory was empty, so every push published the repo
# ROOT - which has no index.html - as an empty deployment. The empty deployment
# became production, the production alias followed it, and the domain returned 404
# within seconds of each push. It happened twice in one evening.
#
# Running a CLI deploy from site/ while rootDirectory is "site" fails with
# `The specified Root Directory "site" does not exist`, because the CLI resolves
# the value relative to the current directory and looks for site/site. So this
# script does not deploy. It checks that the ownership model is intact and that the
# domain is really serving the site, which is the part that silently broke.
#
#   deploy:  git push          (Vercel builds it)
#   check:   powershell -File tools/verify-live-site.ps1

param(
    [string]$Project = "lumawall",
    [string]$Team = "luma-wall1",
    [string]$Domain = "lumawall.xinet.id",
    [string]$ExpectRoot = "site"
)

$ErrorActionPreference = 'Stop'

function Step($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   $t" -ForegroundColor Green }
function Bad($t)  { Write-Host "   $t" -ForegroundColor Red }

$problems = @()

# ── 1. the ownership model ───────────────────────────────────────────────────
Step "Deploy path (project $Team/$Project)"

$authPath = Join-Path $env:APPDATA 'com.vercel.cli\Data\auth.json'
if (-not (Test-Path $authPath)) {
    Bad "no Vercel token at $authPath"
    exit 1
}
$token = (Get-Content $authPath -Raw | ConvertFrom-Json).token

$api = "https://api.vercel.com/v9/projects/$Project`?teamId=$Team"
$proj = Invoke-RestMethod -Uri $api -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 60

$rootDir = $proj.rootDirectory
$linked = [bool]$proj.link

Write-Host "   rootDirectory : $(if ($rootDir) { $rootDir } else { '(repo root)' })"
Write-Host "   git link      : $(if ($linked) { 'connected to ' + $proj.link.repo } else { 'none' })"

if ($linked) {
    # Git owns it: the root directory must point at the folder holding the site.
    if ($rootDir -ne $ExpectRoot) {
        $problems += "git is connected but rootDirectory is '$rootDir', not '$ExpectRoot'"
        Bad "a push would build the wrong folder - that is what caused the 404"
        Write-Host ""
        Write-Host "   Fix with:  python tools/set-vercel-root.py" -ForegroundColor Yellow
    } else {
        Ok "a push builds '$ExpectRoot', so it cannot publish an empty deployment"
    }
} else {
    # No git link: a CLI deploy from the site folder is the path, and it needs an
    # empty rootDirectory.
    if ($rootDir) {
        $problems += "no git link, but rootDirectory is '$rootDir' - a CLI deploy would look for $rootDir/$rootDir"
        Bad "a CLI deploy from the site folder would fail"
    } else {
        Ok "CLI deploy path is open (no git link, rootDirectory empty)"
    }
}

# ── 2. the domain serves the site ────────────────────────────────────────────
Step "The domain"

$code = 0
$body = ''
for ($try = 1; $try -le 6; $try++) {
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $resp = Invoke-WebRequest "https://$Domain/" -UseBasicParsing -TimeoutSec 40
        $ErrorActionPreference = $prev
        if ($resp) { $code = [int]$resp.StatusCode; $body = $resp.Content }
    } catch {
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    }
    if ($code -eq 200 -and $body -match 'LumaWall') { break }
    Start-Sleep -Seconds 4
}

if ($code -ne 200) {
    $problems += "$Domain returned $code"
    Bad "$Domain -> $code"
} elseif ($body -notmatch 'LumaWall' -or $body -notmatch 'lumawall-promo\.mp4') {
    # The empty deployment answered 200 too. A status code is not proof.
    $problems += "$Domain returned 200 but the body is not the site"
    Bad "$Domain -> 200, but the body is not the LumaWall site (empty deployment?)"
    Write-Host ""
    Write-Host ("   served: " + $body.Substring(0, [Math]::Min(160, $body.Length))) -ForegroundColor Yellow
} else {
    Ok "$Domain -> 200, and the body is the LumaWall site ($($body.Length) chars)"
}

# ── 3. the heavy assets ──────────────────────────────────────────────────────
Step "Assets"

foreach ($asset in @('assets/video/lumawall-promo.mp4', 'assets/shots/poster-promo.png', 'assets/css/style.css')) {
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $r = Invoke-WebRequest "https://$Domain/$asset" -UseBasicParsing -TimeoutSec 120 -Method Head
        $ErrorActionPreference = $prev
        $len = [int]$r.Headers['Content-Length']
        if ($len -gt 0) {
            Ok ("{0,-38} {1,10:N0} bytes" -f $asset, $len)
        } else {
            $problems += "$asset has no Content-Length"
            Bad "$asset reported no size"
        }
    } catch {
        $problems += "$asset could not be fetched"
        Bad "$asset - $($_.Exception.Message)"
    }
}

# ── verdict ──────────────────────────────────────────────────────────────────
Write-Host ""
if ($problems.Count) {
    Write-Host "   $($problems.Count) problem(s):" -ForegroundColor Red
    foreach ($p in $problems) { Write-Host "     $p" -ForegroundColor Red }
    exit 1
}
Ok "the deploy path is intact and the site is live"
