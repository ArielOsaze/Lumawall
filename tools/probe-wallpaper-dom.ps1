# probe-wallpaper-dom.ps1 - reads the live DOM of the wallpaper pages.
#
# Why this exists:
#
# When a wallpaper is black, the log says "renderer ready" and "swap committed", and
# the config says the right file is assigned - so every piece of evidence inside the
# app says the wallpaper is fine. What is missing is what the PAGE thinks: whether a
# video element exists, whether it has a source, whether it is paused, and what its
# readyState is.
#
# That is only visible from inside the WebView, and the app exposes no way in. This
# attaches to the running WebView2 processes over the DevTools protocol and asks.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/probe-wallpaper-dom.ps1
#
# It needs the WebView2 to have been started with a remote debugging port. If it was
# not, this reports that and exits - it does not restart the app.

$ErrorActionPreference = 'Stop'

$port = 9222
$url = "http://127.0.0.1:$port/json/list"

Write-Host ''
Write-Host '  live wallpaper DOM probe'
Write-Host '  ' + ('-' * 56)

try {
    $targets = Invoke-RestMethod -Uri $url -TimeoutSec 5
} catch {
    Write-Host ''
    Write-Host "  no DevTools endpoint on port $port."
    Write-Host ''
    Write-Host '  LumaWall does not enable remote debugging, so the DOM cannot be'
    Write-Host '  inspected from outside. To get this view, the app needs to pass'
    Write-Host '  --remote-debugging-port=' + $port + ' in its browser arguments.'
    Write-Host ''
    exit 2
}

Write-Host ''
Write-Host ('  ' + $targets.Count + ' page(s)')
foreach ($t in $targets) {
    Write-Host ''
    Write-Host ('  ' + $t.title)
    Write-Host ('    url   ' + $t.url)
    Write-Host ('    ws    ' + $t.webSocketDebuggerUrl)
}
Write-Host ''
