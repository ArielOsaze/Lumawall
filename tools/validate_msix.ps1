# Standalone validation of the MSIX package, covering the same checks the
# App Certification Kit performs for logo/layout/manifest rules (appcert.exe
# itself requires elevation, which is not available in this session).

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$root   = Split-Path $PSScriptRoot -Parent
# Resolve the package by glob: the version is owned by AppxManifest.xml and the
# build script names the file after it, so a hard-coded name here goes stale on
# the very next version bump and makes this whole validation silently skip.
$msixFile = Get-ChildItem (Join-Path $root 'outputs') -Filter 'LumaWall_*_x64.msix' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $msixFile) { Write-Output '  [FAIL] no msix package found in outputs'; exit 1 }
$msix = $msixFile.FullName
Write-Output ("  package under test: " + $msixFile.Name)
$verify = Join-Path $root 'msix\verify'
$assets = Join-Path $root 'LumaWall\TileAssets'

$fail = 0
function Check($name, $ok, $detail) {
    $script:fail += if ($ok) { 0 } else { 1 }
    Write-Output ("  [{0}] {1}{2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $name, $(if ($detail) { "  -> $detail" } else { '' }))
}

Write-Output '=== A. Package container ==='
Check 'msix exists' (Test-Path $msix)
$size = (Get-Item $msix).Length
Check 'size sane (<200MB)' ($size -lt 200MB) ("{0:N2} MB" -f ($size / 1MB))

Write-Output '=== B. Manifest rules ==='
$mf = [xml](Get-Content (Join-Path $verify 'AppxManifest.xml') -Raw)
$id = $mf.Package.Identity
Check 'Identity/@Name present' (-not [string]::IsNullOrWhiteSpace($id.Name)) $id.Name
Check 'Identity/@Publisher CN= format' ($id.Publisher -match '^CN=') $id.Publisher
Check 'Identity/@Version 4-part' ($id.Version -match '^\d+\.\d+\.\d+\.\d+$') $id.Version
Check 'Identity/@ProcessorArchitecture valid' ($id.ProcessorArchitecture -in @('x64','x86','arm64','neutral')) $id.ProcessorArchitecture
Check 'PublisherDisplayName present' (-not [string]::IsNullOrWhiteSpace($mf.Package.Properties.PublisherDisplayName)) $mf.Package.Properties.PublisherDisplayName
Check 'DisplayName present' (-not [string]::IsNullOrWhiteSpace($mf.Package.Properties.DisplayName)) $mf.Package.Properties.DisplayName
Check 'Description present' (-not [string]::IsNullOrWhiteSpace($mf.Package.Properties.Description))
Check 'TargetDeviceFamily Windows.Desktop' ($mf.Package.Dependencies.TargetDeviceFamily.Name -eq 'Windows.Desktop')
Check 'runFullTrust declared' (($mf.Package.Capabilities.ChildNodes | ForEach-Object { $_.Name }) -contains 'runFullTrust')
$langs = $mf.Package.Resources.Resource | ForEach-Object { $_.Language }
Check 'at least 1 language resource' ($langs.Count -ge 1) ($langs -join ', ')

Write-Output '=== C. Declared tile images exist in package ==='
$ve = $mf.Package.Applications.Application.'uap:VisualElements'
$declared = @(
    $mf.Package.Properties.Logo,
    $ve.Square150x150Logo,
    $ve.Square44x44Logo,
    $ve.'uap:DefaultTile'.Wide310x150Logo,
    $ve.'uap:SplashScreen'.Image,
    $ve.'uap:LockScreen'.BadgeLogo
) | Where-Object { $_ }
foreach ($rel in $declared) {
    $p = Join-Path $verify ($rel -replace '\\', '\')
    Check ("declared: " + $rel) (Test-Path $p)
}

Write-Output '=== D. Mandatory dimensions (Store rule) ==='
$expect = @{
    'StoreLogo.png'         = @(50, 50)
    'Square44x44Logo.png'   = @(44, 44)
    'Square150x150Logo.png' = @(150, 150)
    'Wide310x150Logo.png'   = @(310, 150)
    'SplashScreen.png'      = @(620, 300)
    'BadgeLogo.png'         = @(24, 24)
    'LockScreenLogo.png'    = @(24, 24)
}
foreach ($name in ($expect.Keys | Sort-Object)) {
    $p = Join-Path (Join-Path $verify 'TileAssets') $name
    if (-not (Test-Path $p)) { Check $name $false 'missing'; continue }
    $img = [System.Drawing.Image]::FromFile($p)
    $ok = ($img.Width -eq $expect[$name][0] -and $img.Height -eq $expect[$name][1])
    Check $name $ok ("{0}x{1}" -f $img.Width, $img.Height)
    $img.Dispose()
}

Write-Output '=== E. Scale variants present ==='
foreach ($base in @('StoreLogo','Square44x44Logo','Square150x150Logo','Wide310x150Logo','SplashScreen','BadgeLogo','LockScreenLogo')) {
    $found = @()
    foreach ($s in @('', '.scale-125', '.scale-150', '.scale-200', '.scale-400')) {
        if (Test-Path (Join-Path $assets ($base + $s + '.png'))) { $found += $(if ($s) { $s } else { '100' }) }
    }
    Check ($base + ' scales') ($found.Count -eq 5) ($found -join ',')
}

Write-Output '=== F. altform / targetsize (taskbar + Start) ==='
foreach ($f in @('Square44x44Logo.altform-unplated.png','Square44x44Logo.altform-lightunplated.png')) {
    Check $f (Test-Path (Join-Path $assets $f))
}
$ts = Get-ChildItem $assets -Filter 'Square44x44Logo.targetsize-*.png' -ErrorAction SilentlyContinue
Check 'targetsize set' ($ts.Count -ge 5) ("$($ts.Count) files")

Write-Output '=== G. Payload integrity ==='
foreach ($f in @('LumaWall.exe','Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll','catalog.json','README.txt','LICENSE.txt')) {
    Check $f (Test-Path (Join-Path $verify $f))
}
$assetDir = Join-Path $verify 'assets'
$assetCount = if (Test-Path $assetDir) { (Get-ChildItem $assetDir -File | Measure-Object).Count } else { 0 }
Check 'wallpaper assets bundled' ($assetCount -ge 90) ("$assetCount files")

Write-Output '=== H. Badge is monochrome (Store rule) ==='
$badgePath = Join-Path $verify 'TileAssets\BadgeLogo.png'
if (Test-Path $badgePath) {
    $bmp = New-Object System.Drawing.Bitmap($badgePath)
    $colored = 0
    for ($y = 0; $y -lt $bmp.Height; $y++) {
        for ($x = 0; $x -lt $bmp.Width; $x++) {
            $c = $bmp.GetPixel($x, $y)
            if ($c.A -gt 8 -and -not ($c.R -eq $c.G -and $c.G -eq $c.B)) { $colored++ }
        }
    }
    $bmp.Dispose()
    Check 'badge monochrome' ($colored -eq 0) ("$colored colored pixels")
}

Write-Output ''
if ($fail -eq 0) {
    Write-Output '=== ALL CHECKS PASSED ==='
    exit 0
} else {
    Write-Output ("=== $fail CHECK(S) FAILED ===")
    exit 1
}
