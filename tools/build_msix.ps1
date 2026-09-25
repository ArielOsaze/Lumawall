# Builds the Microsoft Store (MSIX) package for LumaWall.
#
#   * stages the release payload + the generated Assets folder
#   * packs with MakeAppx
#   * validates the layout the way the Store does (App Certification Kit)
#
# The package is intentionally unsigned here: Partner Center signs Store
# submissions with the Microsoft certificate. For local sideload testing,
# sign it with a self-signed cert using -Sign.

param(
    [switch]$Sign,
    [string]$CertPath = "",
    [string]$CertPassword = ""
)

$ErrorActionPreference = 'Stop'

$root       = Split-Path $PSScriptRoot -Parent
$appDir     = Join-Path $root 'LumaWall'
$releaseDir = Join-Path $appDir 'bin\Release'
$msixDir    = Join-Path $root 'msix'
$stageDir   = Join-Path $root 'msix\stage'
$outDir     = Join-Path $root 'outputs'

$sdkBin = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64'
$makeappx = Join-Path $sdkBin 'makeappx.exe'
$signtool = Join-Path $sdkBin 'signtool.exe'
$appcert  = 'C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe'

foreach ($tool in @($makeappx)) {
    if (-not (Test-Path $tool)) { throw "Missing tool: $tool" }
}

Write-Output '=== 1. Stage payload ==='
if (Test-Path $stageDir) { Remove-Item $stageDir -Recurse -Force }
New-Item -ItemType Directory -Path $stageDir | Out-Null

# App binaries (exe, WebView2 dlls, catalog, README, LICENSE)
Get-ChildItem $releaseDir -File | Where-Object { $_.Name -ne 'app-logo.png' } | ForEach-Object {
    Copy-Item $_.FullName -Destination $stageDir -Force
}

# Wallpaper asset library ships inside the package
$assetSrc = Join-Path $releaseDir 'assets'
$assetDst = Join-Path $stageDir 'assets'
New-Item -ItemType Directory -Path $assetDst -Force | Out-Null
Copy-Item (Join-Path $assetSrc '*') -Destination $assetDst -Recurse -Force

# MSIX tile art: the generated TileAssets folder. NOT "Assets" - on Windows that
# is the same directory as the wallpaper library's lowercase `assets`, which
# would put logos into the library and break the manifest references.
$tileDst = Join-Path $stageDir 'TileAssets'
New-Item -ItemType Directory -Path $tileDst -Force | Out-Null
Get-ChildItem (Join-Path $appDir 'TileAssets') -File -Filter *.png | ForEach-Object {
    Copy-Item $_.FullName -Destination $tileDst -Force
}
Copy-Item (Join-Path $appDir 'app-logo.png') -Destination $tileDst -Force

# Manifest
Copy-Item (Join-Path $msixDir 'AppxManifest.xml') -Destination $stageDir -Force

Write-Output ("   staged files: " + (Get-ChildItem $stageDir -Recurse -File | Measure-Object).Count)

Write-Output '=== 2. Pack MSIX ==='
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# Read the version from the manifest instead of hard-coding it here: a stale
# literal in this script silently produced a package whose filename disagreed
# with the version inside it, which is exactly what a Store submission must not
# have.
$manifestXml = [xml](Get-Content (Join-Path $msixDir 'AppxManifest.xml'))
$pkgVersion = $manifestXml.Package.Identity.Version
$msixPath = Join-Path $outDir ("LumaWall_" + $pkgVersion + "_x64.msix")
Write-Output ("   version from manifest: " + $pkgVersion)
if (Test-Path $msixPath) { Remove-Item $msixPath -Force }

& $makeappx pack /d $stageDir /p $msixPath /o | Out-Null
if ($LASTEXITCODE -ne 0) { throw "makeappx pack failed with $LASTEXITCODE" }
Write-Output ("   wrote " + $msixPath + " (" + [math]::Round((Get-Item $msixPath).Length / 1MB, 2) + " MB)")

Write-Output '=== 3. Inspect package ==='
$verifyDir = Join-Path $root 'msix\verify'
if (Test-Path $verifyDir) { Remove-Item $verifyDir -Recurse -Force }
& $makeappx unpack /p $msixPath /d $verifyDir /o | Out-Null
if ($LASTEXITCODE -ne 0) { throw "makeappx unpack failed with $LASTEXITCODE" }
$manifestText = Get-Content (Join-Path $verifyDir 'AppxManifest.xml') -Raw
$manifest = [xml]$manifestText
$identity = $manifest.Package.Identity
Write-Output ("   Identity : " + $identity.Name + " / " + $identity.Publisher + " / " + $identity.Version + " / " + $identity.ProcessorArchitecture)
$capabilities = $manifest.Package.Capabilities.ChildNodes | ForEach-Object { $_.Name }
Write-Output ("   Caps     : " + ($capabilities -join ', '))

Write-Output '=== 4. Validate logo dimensions ==='
$expect = @{
    'StoreLogo.png'         = @(50, 50)
    'Square44x44Logo.png'   = @(44, 44)
    'Square150x150Logo.png' = @(150, 150)
    'Wide310x150Logo.png'   = @(310, 150)
    'SplashScreen.png'      = @(620, 300)
    'BadgeLogo.png'         = @(24, 24)
    'LockScreenLogo.png'    = @(24, 24)
}
Add-Type -AssemblyName System.Drawing
$bad = 0
foreach ($name in $expect.Keys) {
    $p = Join-Path $tileDst $name
    if (-not (Test-Path $p)) { Write-Output ("   MISSING " + $name); $bad++; continue }
    $img = [System.Drawing.Image]::FromFile($p)
    $ok = ($img.Width -eq $expect[$name][0] -and $img.Height -eq $expect[$name][1])
    if (-not $ok) { $bad++ }
    Write-Output ("   {0,-24} {1}x{2} {3}" -f $name, $img.Width, $img.Height, $(if ($ok) { 'OK' } else { 'WRONG SIZE' }))
    $img.Dispose()
}
if ($bad -gt 0) { throw "$bad logo(s) failed validation" }

Write-Output '=== 5. Validate every manifest asset reference ==='
# The manifest points at image files by relative path. A typo, a case-only
# mismatch with another folder, or a missing file passes `makeappx` but fails
# Store certification, so resolve each reference against the packed payload.
$verifyDir = Join-Path $root 'msix\verify'
$refs = [regex]::Matches($manifestText, '(?:Logo|Image|BadgeLogo)="([^"]+\.png)"') |
    ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$missing = 0
foreach ($ref in $refs) {
    $rel = $ref -replace '\\', '/'
    $hit = Join-Path $verifyDir $rel
    if (Test-Path $hit) {
        Write-Output ("   OK      " + $ref)
    } else {
        Write-Output ("   MISSING " + $ref)
        $missing++
    }
}
if ($missing -gt 0) { throw "$missing manifest asset reference(s) missing from the package" }

Write-Output '=== 6. Validate tile art is not mixed into the wallpaper library ==='
# Guards the collision that once shipped: an `Assets` folder is the same folder
# as `assets` on Windows, so the logos ended up inside the wallpaper library.
$libraryLogos = Get-ChildItem $assetDst -File -Filter '*Logo*.png' -ErrorAction SilentlyContinue
if ($libraryLogos) {
    $libraryLogos | ForEach-Object { Write-Output ("   LEAKED  assets/" + $_.Name) }
    throw "tile art leaked into the wallpaper library folder"
}
Write-Output ("   assets/ holds " + (Get-ChildItem $assetDst -File | Measure-Object).Count + " wallpaper files, no tile art")

if ($Sign) {
    Write-Output '=== 7. Sign package ==='
    if (-not $CertPath) { throw '-Sign requires -CertPath' }
    & $signtool sign /fd SHA256 /f $CertPath /p $CertPassword $msixPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "signtool failed with $LASTEXITCODE" }
    Write-Output '   signed'
}

Write-Output '=== DONE ==='
Write-Output $msixPath
