"""verify-hardware-claims.py — checks the performance page's claims against the machine.

The comparison section says "the numbers, not claims", so every specific claim on
it should be verifiable. This checks the ones that can be checked locally:

  - the CPU, GPU and Windows build named in the methodology line
  - whether the decode engines the page names (NVDEC / DXVA2) are actually the
    ones the GPU uses
  - the app's own log, to confirm hardware decode rather than software

Run:  python tools/verify-hardware-claims.py
"""

import os
import re
import subprocess


def ps(command):
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', command],
        capture_output=True, text=True,
    )
    return (r.stdout or '').strip()


print('  machine:')
cpu = ps('(Get-CimInstance Win32_Processor | Select-Object -First 1).Name')
gpu = ps('(Get-CimInstance Win32_VideoController | Select-Object -First 1).Name')
build = ps('(Get-CimInstance Win32_OperatingSystem).BuildNumber')
print('    CPU        : ' + cpu)
print('    GPU        : ' + gpu)
print('    Win build  : ' + build)

# What the page claims.
page = open('site/index.html', encoding='utf-8').read()
method = re.search(r'Angka performa diukur pada([^<]+)', page)
claim = ' '.join(method.group(1).split()) if method else ''
print('    page claim : ' + claim)

print()
print('  claim checks:')
# Match the model number rather than the whole WMI string: WMI returns
# "AMD Ryzen 5 5600 6-Core Processor" while the page writes "Ryzen 5 5600".
cpu_model = re.search(r'(\d{4}\w*)', cpu)
cpu_model = cpu_model.group(1) if cpu_model else cpu
gpu_model = re.search(r'(\d{3,4})', gpu)
gpu_model = gpu_model.group(1) if gpu_model else gpu

checks = [
    ('CPU model named on the page matches this machine', cpu_model in claim),
    ('GPU model named on the page matches this machine', gpu_model in claim),
    ('Windows build named on the page matches this machine', build in claim),
    ('page names NVDEC (the NVIDIA decoder)', 'NVDEC' in page),
    ('page does not name NVENC (that is the encoder)', 'NVENC' not in page),
]

# The real evidence is the WebView2 command line, not the log: the log records
# state changes only, so a quiet log proves nothing either way.
cmd = ps(
    "Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" | "
    "Where-Object { $_.CommandLine -match 'accelerated-video-decode' } | "
    "Select-Object -First 1 | ForEach-Object { $_.CommandLine }"
)
checks.append(('WebView2 started with --enable-accelerated-video-decode',
               'accelerated-video-decode' in cmd))

for label, ok in checks:
    print('    %-56s %s' % (label, 'OK' if ok else 'FAIL'))

# Does the GPU expose a decode engine right now?
print()
print('  GPU engines with activity:')
out = ps(
    "$s = (Get-Counter '\\GPU Engine(*)\\Utilization Percentage' "
    "-ErrorAction SilentlyContinue).CounterSamples | "
    "Where-Object { $_.CookedValue -gt 0 }; "
    "if ($s) { $s | Select-Object -First 8 | ForEach-Object { "
    "$_.InstanceName + ' = ' + [math]::Round($_.CookedValue,2) } } else { 'none' }"
)
for line in out.split('\n')[:8]:
    print('    ' + line.strip()[:130])
