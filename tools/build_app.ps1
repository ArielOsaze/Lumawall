# Builds LumaWall with the Windows SDK reference resolved.
#
# The app now references the WinRT facade (windows.winmd) for
# Windows.ApplicationModel.StartupTask, which is required for "start with
# Windows" to work in the MSIX build. That reference needs WindowsSdkDir and
# WindowsTargetPlatformVersion, and passing them through the shell keeps
# tripping over quoting, so they live here.

$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$proj = Join-Path $root 'LumaWall\LumaWall.csproj'

$msbuild = 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe'
if (-not (Test-Path $msbuild)) {
    $candidates = Get-ChildItem 'C:\Program Files*\Microsoft Visual Studio' -Recurse -Filter MSBuild.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like '*amd64*' } | Select-Object -First 1
    if ($candidates) { $msbuild = $candidates.FullName }
}
if (-not (Test-Path $msbuild)) { throw "MSBuild not found" }

# Pick the newest SDK that actually contains the WinRT facade.
$sdkRoot = 'C:\Program Files (x86)\Windows Kits\10'
$version = Get-ChildItem (Join-Path $sdkRoot 'UnionMetadata') -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName 'Facade\windows.winmd') } |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $version) { throw "No Windows SDK with a WinRT facade found under $sdkRoot" }

Write-Host ("  MSBuild : " + $msbuild)
Write-Host ("  SDK     : " + $version.Name)

& $msbuild $proj `
    /p:Configuration=Release `
    /p:FrameworkPathOverride="C:\Windows\Microsoft.NET\Framework64\v4.0.30319" `
    "/p:WindowsSdkDir=$sdkRoot\" `
    "/p:WindowsTargetPlatformVersion=$($version.Name)" `
    /v:minimal /nologo

if ($LASTEXITCODE -ne 0) { throw "build failed with $LASTEXITCODE" }
Write-Host "  build OK"
