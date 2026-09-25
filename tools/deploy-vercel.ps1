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
    Write-Host ""
    Write-Host "   Verify:  Invoke-WebRequest $url -UseBasicParsing | Select StatusCode" -ForegroundColor Yellow
} else {
    Bad "could not read the deployment URL from the output above"
    exit 5
}
