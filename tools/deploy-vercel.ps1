# RETIRED — the git integration owns this project now.
#
# Vercel is connected to GitHub, so every `git push` deploys the site. That path and
# a CLI deploy have contradictory root-directory requirements, and git won:
#
#   owning path      rootDirectory   deploy runs from
#   ---------------  --------------  ----------------
#   git auto-deploy  "site"          the repo root
#   CLI deploy       ""              the site subfolder
#
# rootDirectory is "site" (see tools/set-vercel-root.py). Running this script now
# would fail with `The specified Root Directory "site" does not exist`, because the
# CLI resolves the value against the current directory and looks for site/site.
#
#   deploy:  git push
#   check:   powershell -File tools/verify-live-site.ps1
#
# Kept because the checks below are still the right shape if the project is ever
# switched back to CLI ownership (git link removed, rootDirectory cleared).

# Deploys the LumaWall site to Vercel, refusing to run if the logged-in account
# is not the one that owns the LumaWall project.
#
# Why this guard exists: this machine already has a Vercel session for a
# DIFFERENT project (akuntuntas / akuntuntas.xinet.id). A plain `vercel deploy`
# would silently publish LumaWall into that account, which is exactly the
# mistake the user warned about.
#
# The script therefore:
#   1. asks Vercel who is logged in
#   2. refuses if that account is the known-unrelated one
#   3. refuses if a project named lumawall is not reachable in that account
#   4. deploys the `site` folder to production only after both checks pass

param(
    [string]$ProjectName = "lumawall",
    [switch]$AllowCreate
)

$ErrorActionPreference = 'Stop'

# The Vercel CLI writes its banner to stderr. With ErrorActionPreference=Stop,
# PowerShell turns that into a terminating error even though the command
# succeeded, so native calls are run with the preference relaxed and their exit
# code checked explicitly.
function Invoke-Vercel {
    param([string[]]$Arguments)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & vercel @Arguments 2>&1 | Out-String
        return $out
    } finally {
        $ErrorActionPreference = $prev
    }
}

$site = Join-Path (Split-Path -Parent $PSScriptRoot) 'site'
if (-not (Test-Path $site)) { $site = Join-Path $PSScriptRoot 'site' }
if (-not (Test-Path (Join-Path $site 'index.html'))) {
    Write-Host "site folder not found at $site" -ForegroundColor Red
    exit 1
}

# The 404 this project actually hit, and how it happens:
#
# There is a `.vercel` link file at the repo root as well as in site/. Both point at
# the same project, so `vercel deploy` run from the ROOT links to the same project
# and publishes the root - which has no index.html. The deployment comes back Ready,
# it becomes the production deployment, and the production alias moves to it, so
# lumawall.xinet.id serves "The page could not be found" while every step reported
# success.
#
# The guard is to refuse unless the folder being published actually contains a site.
$rootVercel = Join-Path (Split-Path -Parent $PSScriptRoot) '.vercel'
if (Test-Path $rootVercel) {
    $rootIndex = Join-Path (Split-Path -Parent $PSScriptRoot) 'index.html'
    if (-not (Test-Path $rootIndex)) {
        Write-Host ""
        Write-Host "WARNING: a .vercel link exists at the repo root, which has no index.html." -ForegroundColor Yellow
        Write-Host "         Deploying from there produces an empty deployment that still" -ForegroundColor Yellow
        Write-Host "         becomes production - that is what caused the 404." -ForegroundColor Yellow
        Write-Host "         This script deploys '$site' only. Do not run 'vercel deploy'" -ForegroundColor Yellow
        Write-Host "         from the repo root." -ForegroundColor Yellow
        Write-Host ""
    }
}

function Step($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   $t" -ForegroundColor Green }
function Bad($t)  { Write-Host "   $t" -ForegroundColor Red }

# ── 1. who is logged in ──────────────────────────────────────────────────────
Step "Logged-in Vercel account"
$who = Invoke-Vercel @('whoami')
$who = ($who -split "`n" | Where-Object { $_.Trim() -and $_ -notmatch 'Vercel CLI' } | Select-Object -Last 1).Trim()
Write-Host "   $who"

if ($who -match 'akuntuntas') {
    Bad "This is the AkunTuntas account (project akuntuntas.xinet.id)."
    Bad "LumaWall must NOT be deployed here."
    Write-Host ""
    Write-Host "   Log in with the LumaWall account first:  vercel login" -ForegroundColor Yellow
    exit 2
}
Ok "account is not the unrelated AkunTuntas one"

# ── 2. is the project reachable ──────────────────────────────────────────────
Step "Project '$ProjectName'"
$projects = Invoke-Vercel @('projects', 'ls')
$found = $projects -split "`n" | Where-Object { $_ -match ("^\s*" + [regex]::Escape($ProjectName) + "\s") }

if (-not $found) {
    Bad "no project named '$ProjectName' in this account"
    Write-Host ""
    Write-Host "   Projects visible:" -ForegroundColor Yellow
    ($projects -split "`n" | Where-Object { $_.Trim() } | Select-Object -Skip 2) | ForEach-Object { Write-Host "     $_" }
    if (-not $AllowCreate) {
        Write-Host ""
        Write-Host "   Re-run with -AllowCreate to create it, or fix the account." -ForegroundColor Yellow
        exit 3
    }
} else {
    Ok ("found: " + $found.Trim())
}

# ── 3. sanity-check the payload ──────────────────────────────────────────────
Step "Payload"
$files = Get-ChildItem $site -Recurse -File
$totalMb = [math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host ("   " + $files.Count + " files, " + $totalMb + " MB")

foreach ($need in @('index.html', 'assets\video\lumawall-promo.mp4', 'assets\css\style.css', 'assets\js\main.js')) {
    if (Test-Path (Join-Path $site $need)) { Ok $need } else { Bad "MISSING $need"; exit 4 }
}

# The video must be a real, complete file - not a fragment being written right
# now. A render once published a 48-byte mp4 that returned 200 with
# Content-Type: video/mp4, so existence and content type were both fine while the
# video was empty. The check is a size floor plus the mp4 box structure.
$videoPath = Join-Path $site 'assets\video\lumawall-promo.mp4'
$video = Get-Item $videoPath
$videoMb = [math]::Round($video.Length / 1MB, 2)
Write-Host ("   promo video: " + $videoMb + " MB")

if ($video.Length -lt 1MB) {
    Bad "the promo video is only $($video.Length) bytes - it is incomplete."
    Bad "A render may still be writing it. Wait for the render to finish, then re-run."
    exit 7
}

$head = [System.IO.File]::ReadAllBytes($videoPath)[0..11]
$brand = [System.Text.Encoding]::ASCII.GetString($head[4..11])
if ($brand -notmatch 'ftyp') {
    Bad "the promo video does not start with an mp4 header (found '$brand')."
    exit 8
}
Ok "promo video looks complete ($brand)"

# Any leftover .part file means a render is in flight or was interrupted. The
# renderer writes "<name>.part.mp4", so the pattern has to include the extension -
# a filter of '*.part' matched nothing and the guard silently passed.
$parts = Get-ChildItem $site -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*.part*' }
if ($parts) {
    Bad "found $($parts.Count) incomplete file(s) - a render is still running:"
    $parts | ForEach-Object { Bad ("  " + $_.FullName.Replace($site, '') + "  " + [math]::Round($_.Length/1MB,1) + " MB") }
    Bad "Wait for the render to finish, then re-run."
    exit 9
}

# ── 4. deploy ────────────────────────────────────────────────────────────────
Step "Deploying to production"
Write-Host "   project : $ProjectName"
Write-Host "   folder  : $site"
Write-Host ""

Push-Location $site
try {
    $output = Invoke-Vercel @('deploy', '--prod', '--yes', '--name', $ProjectName)
    Write-Host $output
} finally {
    Pop-Location
}

$url = ([regex]::Match($output, 'https://[a-zA-Z0-9\.\-]+\.vercel\.app')).Value
Step "Result"
if ($url) {
    Ok ("deployed: " + $url)
} else {
    Bad "could not read the deployment URL from the output above"
    exit 5
}

# ── 5. make sure the PUBLIC domain serves the new deployment ─────────────────
#
# Why this step exists: `vercel deploy --prod` reported success, the deployment
# URL answered 200, and the site was still a 404 on its real domain. The
# production alias had not been moved, so visitors saw "The page could not be
# found" while every check the script made passed.
#
# A deploy is only finished when the domain a visitor types actually serves it.
Step "Verifying the public domain"

$domains = @('lumawall.xinet.id')
foreach ($d in $domains) {
    $code = 0
    for ($try = 1; $try -le 6; $try++) {
        try {
            $prev = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $resp = Invoke-WebRequest "https://$d" -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0 -ErrorAction SilentlyContinue
            $ErrorActionPreference = $prev
            if ($resp) { $code = [int]$resp.StatusCode }
        } catch {
            if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        }
        if ($code -eq 200) { break }
        Start-Sleep -Seconds 4
    }

    if ($code -eq 200) {
        # A 200 is not enough on its own: the empty deployment this project served
        # also answered, and only the body revealed it was "The page could not be
        # found". Check that the response actually contains the site.
        $body = ''
        try {
            $prev = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $body = (Invoke-WebRequest "https://$d" -UseBasicParsing -TimeoutSec 30).Content
            $ErrorActionPreference = $prev
        } catch { }

        if ($body -match 'LumaWall' -and $body -match 'lumawall-promo\.mp4') {
            Ok "$d -> 200, and the page is the LumaWall site"
        } else {
            Bad "$d -> 200 but the body is not the site (empty deployment?)"
            Write-Host ""
            Write-Host "   First 200 characters of what was served:" -ForegroundColor Yellow
            Write-Host ("   " + $body.Substring(0, [Math]::Min(200, $body.Length))) -ForegroundColor Yellow
            Write-Host ""
            Write-Host "   Repointing the domain at the deployment just made:" -ForegroundColor Yellow
            $aliasOut = Invoke-Vercel @('alias', 'set', $url, $d)
            Write-Host $aliasOut
            Start-Sleep -Seconds 6
            $code2 = 0
            try {
                $prev = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'
                $resp2 = Invoke-WebRequest "https://$d" -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0 -ErrorAction SilentlyContinue
                $ErrorActionPreference = $prev
                if ($resp2) { $code2 = [int]$resp2.StatusCode }
            } catch {
                if ($_.Exception.Response) { $code2 = [int]$_.Exception.Response.StatusCode }
            }
            if ($code2 -eq 200) { Ok "$d -> 200 after re-aliasing" }
            else { Bad "$d still returns $code2 - check the domain in the Vercel dashboard"; exit 6 }
        }
    } else {
        Bad "$d -> $code"
        Write-Host ""
        Write-Host "   The deployment is live but the domain is not serving it." -ForegroundColor Yellow
        Write-Host "   Pointing the domain at this deployment:" -ForegroundColor Yellow
        $aliasOut = Invoke-Vercel @('alias', 'set', $url, $d)
        Write-Host $aliasOut

        Start-Sleep -Seconds 6
        $code2 = 0
        try {
            $prev = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $resp2 = Invoke-WebRequest "https://$d" -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0 -ErrorAction SilentlyContinue
            $ErrorActionPreference = $prev
            if ($resp2) { $code2 = [int]$resp2.StatusCode }
        } catch {
            if ($_.Exception.Response) { $code2 = [int]$_.Exception.Response.StatusCode }
        }
        if ($code2 -eq 200) { Ok "$d -> 200 after re-aliasing" }
        else { Bad "$d still returns $code2 - check the domain in the Vercel dashboard"; exit 6 }
    }
}

Write-Host ""
Ok "done - the site is live"
