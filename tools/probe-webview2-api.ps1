# probe-webview2-api.ps1 - which memory APIs does the pinned WebView2 SDK actually have?
#
# Why this exists:
#
# The RAM plan depends on APIs that were added across several WebView2 releases
# (MemoryUsageTargetLevel in 1.0.1823.32, GetProcessExtendedInfosAsync later,
# TrySuspend in 1.0.1108.44). The project pins Microsoft.Web.WebView2 1.0.2903.40, but
# a plan that assumes a method exists and finds out at compile time wastes a build
# cycle, and one that silently skips a missing API loses the optimisation without
# saying so.
#
# So this loads the pinned assembly and prints which of the calls are present.
# Run it before writing code against them.
#
# NOTE: this file is deliberately ASCII-only. PowerShell 5.1 reads a .ps1 with no BOM
# as ANSI, so a UTF-8 em-dash in a comment turns into mojibake and breaks the parser.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/probe-webview2-api.ps1

$ErrorActionPreference = 'Stop'

$sdk = Join-Path $PSScriptRoot '..\packages\Microsoft.Web.WebView2.1.0.2903.40\lib\net462\Microsoft.Web.WebView2.Core.dll'
$sdk = [System.IO.Path]::GetFullPath($sdk)

if (-not (Test-Path $sdk)) {
    Write-Host "  SDK not found: $sdk"
    exit 1
}

Write-Host ''
Write-Host "  probing $sdk"
Write-Host ''

# Reflection-only: loading for real would pull in WPF/WinForms assemblies and the
# WebView2Loader native DLL, which is not what we are asking about.
$asm = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom($sdk)
Write-Host ("  assembly version {0}" -f $asm.GetName().Version)
Write-Host ''

# Each entry: the type to look at, and the member names we care about.
$checks = @(
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2'; Members = @(
        'MemoryUsageTargetLevel', 'TrySuspendAsync', 'Resume', 'IsSuspended',
        'CallDevToolsProtocolMethodAsync') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2Environment'; Members = @(
        'GetProcessInfos', 'GetProcessExtendedInfosAsync', 'CreateAsync') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2ProcessInfo'; Members = @(
        'ProcessId', 'Kind') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2ProcessExtendedInfo'; Members = @(
        'ProcessInfo', 'AssociatedFrameInfos') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2MemoryUsageTargetLevel'; Members = @(
        'Normal', 'Low') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2EnvironmentOptions'; Members = @(
        'AdditionalBrowserArguments') },
    @{ Type = 'Microsoft.Web.WebView2.Core.CoreWebView2Controller'; Members = @(
        'IsVisible', 'Close') }
)

$missing = 0
foreach ($check in $checks) {
    $type = $asm.GetType($check.Type)
    if ($null -eq $type) {
        Write-Host ("  {0,-52} TYPE MISSING" -f $check.Type)
        $missing++
        continue
    }

    $names = @()
    $names += $type.GetMembers([System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::Instance -bor [System.Reflection.BindingFlags]::Static) |
              ForEach-Object { $_.Name }

    foreach ($m in $check.Members) {
        if ($names -contains $m) {
            Write-Host ("  {0,-52} {1}" -f $type.Name, $m)
        } else {
            Write-Host ("  {0,-52} {1}   NOT PRESENT" -f $type.Name, $m)
            $missing++
        }
    }
}

Write-Host ''
if ($missing -gt 0) {
    Write-Host "  $missing member(s) missing - do not write code against them"
    exit 1
}
Write-Host '  every memory API the plan needs is present in the pinned SDK'
