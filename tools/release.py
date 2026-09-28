"""Build, install, verify and deploy - in one command, so no step can be forgotten.

Why this exists
---------------
"inget ya klo ada update apapun otomatis ikut update installer di web" - any change must
carry the installer to the web with it. Doing that by hand failed repeatedly and in
different ways: an installer built from a stale binary, a site still offering the old
version, an MSIX left at the previous number, a manifest recorded before the last build.
Each of those shipped a fix that nobody could download.

So the order is fixed and every step is checked:

  1. build the app            (stop it first - a running exe locks the binary)
  2. build the installer, the portable zip and the MSIX
  3. copy all three into site/assets/downloads
  4. point both pages at the new version
  5. cache-bust, so a returning visitor does not get the old asset
  6. re-record the installer manifest, which is what the payload check reads
  7. install it, so the running copy is the one that was just built
  8. verify: version, three renderers, no exceptions, and the site serving the build

Any failure stops the run and says which step failed. It never reports success from a
step that did not run.

Usage:
    python tools/release.py 4.4.3.0
    python tools/release.py 4.4.3.0 --no-install     (build and stage only)
    python tools/release.py --verify-only            (check the current release)
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / 'outputs'
SITE = ROOT / 'site'
DL = SITE / 'assets' / 'downloads'
LOG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'
INSTALLED = Path.home() / 'AppData' / 'Local' / 'Programs' / 'LumaWall' / 'LumaWall.exe'
ISCC = Path(r'C:\Users\ariel\AppData\Local\Programs\Inno Setup 6\ISCC.exe')
SITE_URL = 'https://lumawall.xinet.id'


def run(cmd, timeout=900, check=True, label=''):
    """Run a command and return its combined output."""
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       timeout=timeout, cwd=str(ROOT), errors='replace')
    out = (p.stdout or '') + (p.stderr or '')
    if check and p.returncode != 0:
        print('  FAIL %s' % (label or ' '.join(str(c) for c in cmd)))
        for line in out.strip().splitlines()[-12:]:
            print('       %s' % line)
        raise SystemExit(1)
    return out


def ps(script, timeout=900, check=True):
    return run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', 'tools/' + script], timeout=timeout, check=check,
               label=script)


def stop_app():
    run(['powershell', '-NoProfile', '-Command',
         "Get-Process LumaWall -ErrorAction SilentlyContinue | Stop-Process -Force"],
        check=False)
    time.sleep(3)


def set_versions(version):
    """Write the version into the app, the MSIX manifest and the pages."""
    ai = ROOT / 'LumaWall' / 'Properties' / 'AssemblyInfo.cs'
    body = ai.read_text(encoding='utf-8')
    body = re.sub(r'(AssemblyFileVersion\(")[\d.]+("\))', r'\g<1>%s\g<2>' % version, body)
    body = re.sub(r'(AssemblyVersion\(")[\d.]+("\))', r'\g<1>%s\g<2>' % version, body)
    ai.write_text(body, encoding='utf-8')

    mx = ROOT / 'msix' / 'AppxManifest.xml'
    body = mx.read_text(encoding='utf-8')
    body = re.sub(r'(<Identity[^>]*?Version=")[\d.]+(")', r'\g<1>%s\g<2>' % version,
                  body, count=1, flags=re.S)
    mx.write_text(body, encoding='utf-8')

    for page in [SITE / 'index.html', SITE / 'en' / 'index.html']:
        body = page.read_text(encoding='utf-8')
        body = re.sub(r'LumaWall-Setup-[\d.]+\.exe', 'LumaWall-Setup-%s.exe' % version, body)
        body = re.sub(r'LumaWall-portable-[\d.]+\.zip', 'LumaWall-portable-%s.zip' % version, body)
        body = re.sub(r'LumaWall_[\d.]+_x64\.msix', 'LumaWall_%s_x64.msix' % version, body)
        page.write_text(body, encoding='utf-8')


def current_version():
    ai = ROOT / 'LumaWall' / 'Properties' / 'AssemblyInfo.cs'
    m = re.search(r'AssemblyFileVersion\("([\d.]+)"\)', ai.read_text(encoding='utf-8'))
    return m.group(1) if m else ''


def verify(version, live=True):
    """Check the installed build and the live site. Returns a list of failures."""
    bad = []

    # The installed binary is this version.
    if INSTALLED.exists():
        out = run(['powershell', '-NoProfile', '-Command',
                   "(Get-Item '%s').VersionInfo.FileVersion" % INSTALLED],
                  check=False).strip()
        if version not in out:
            bad.append('installed binary is %s, expected %s' % (out or '?', version))
    else:
        bad.append('not installed at %s' % INSTALLED)

    # The log: three renderers, no exceptions.
    if LOG.exists():
        text = LOG.read_text(encoding='utf-8', errors='replace')
        pids = re.findall(r'\[(\d+)\]', text)
        newest = pids[-1] if pids else ''
        mine = [ln for ln in text.splitlines() if '[%s]' % newest in ln]
        ready = sum(1 for ln in mine if 'renderer ready' in ln)
        exc = sum(1 for ln in mine if 'exception' in ln.lower())
        if ready < 3:
            bad.append('%d renderers ready, expected 3' % ready)
        if exc:
            bad.append('%d exceptions in the log' % exc)

    # The site serves this build.
    if live:
        for page in ['/', '/en/']:
            out = run(['powershell', '-NoProfile', '-Command',
                       "(Invoke-WebRequest -UseBasicParsing '%s%s' -TimeoutSec 25).Content"
                       % (SITE_URL, page)], check=False)
            if version not in out:
                bad.append('%s does not link %s' % (page, version))
        for asset in ['LumaWall-Setup-%s.exe' % version,
                      'LumaWall-portable-%s.zip' % version,
                      'LumaWall_%s_x64.msix' % version]:
            out = run(['powershell', '-NoProfile', '-Command',
                       "try { (Invoke-WebRequest -UseBasicParsing -Method Head "
                       "'%s/assets/downloads/%s' -TimeoutSec 25).StatusCode } catch { $_.Exception.Response.StatusCode.value__ }"
                       % (SITE_URL, asset)], check=False).strip()
            if out != '200':
                bad.append('%s is not served (%s)' % (asset, out or 'no answer'))

    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('version', nargs='?', default='',
                    help='the new version, e.g. 4.4.3.0')
    ap.add_argument('--no-install', action='store_true',
                    help='build and stage, but do not install')
    ap.add_argument('--verify-only', action='store_true')
    args = ap.parse_args()

    if args.verify_only:
        v = current_version()
        print('  verifying %s' % v)
        bad = verify(v)
        if bad:
            for b in bad:
                print('  FAIL %s' % b)
            return 1
        print('  PASS the installed build and the live site both match %s' % v)
        return 0

    version = args.version or current_version()
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
        print('  FAIL the version must look like 4.4.3.0 (got %r)' % version)
        return 1

    print('  releasing %s' % version)
    print()

    print('  1. stop the app')
    stop_app()

    print('  2. write the version everywhere')
    set_versions(version)

    print('  3. build the app')
    out = run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', 'tools/build_app.ps1'], timeout=1200)
    if 'build OK' not in out:
        print('  FAIL the build did not report OK')
        print(out[-800:])
        return 1
    print('     %s' % next((l.strip() for l in out.splitlines() if 'build OK' in l), 'ok'))

    print('  4. build the installer')
    if not ISCC.exists():
        print('  FAIL Inno Setup is not at %s' % ISCC)
        return 1
    run([ISCC, 'installer/LumaWall.iss'], timeout=600)
    setup = OUT / ('LumaWall-Setup-%s.exe' % version)
    if not setup.exists():
        print('  FAIL the installer was not written to %s' % setup)
        return 1
    print('     %s  (%.1f MB)' % (setup.name, setup.stat().st_size / (1024 * 1024)))

    print('  5. build the portable zip')
    portable = ROOT / 'build' / ('portable-%s' % version)
    if portable.exists():
        shutil.rmtree(portable)
    shutil.copytree(ROOT / 'LumaWall' / 'bin' / 'Release', portable)
    zip_path = OUT / ('LumaWall-portable-%s.zip' % version)
    if zip_path.exists():
        zip_path.unlink()
    run(['powershell', '-NoProfile', '-Command',
         "Compress-Archive -Path '%s\\*' -DestinationPath '%s' -Force"
         % (portable, zip_path)], timeout=600)
    print('     %s  (%.1f MB)' % (zip_path.name, zip_path.stat().st_size / (1024 * 1024)))

    print('  6. regenerate the tile assets, then build the MSIX')
    # Every tile the manifest names is generated from one source before packing.
    #
    # Without this step the package carries whatever tile files happen to be on disk, which
    # is how a release shipped a 150px file in the 310px slot and no Square310x310Logo.png
    # at all. The generator also verifies each asset's size and that it is not blank, so a
    # bad tile stops the release here rather than at Store certification.
    #
    # run() raises SystemExit on a non-zero exit, so reaching the next line means the
    # generator succeeded.
    run([sys.executable, 'tools/make-tile-assets.py'], timeout=600,
        label='the tile assets could not be generated')

    run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
         '-File', 'tools/build_msix.ps1'], timeout=900)
    # build_msix.ps1 writes into work/outputs/, while Inno Setup writes into
    # ../outputs/ (bik/outputs). Two directories, and checking only one of them made a
    # successful build look like a failure.
    msix = None
    for folder in [OUT, ROOT / 'outputs']:
        candidate = folder / ('LumaWall_%s_x64.msix' % version)
        if candidate.exists():
            msix = candidate
            break
    if msix is None:
        print('  FAIL the MSIX was not written for %s' % version)
        print('       looked in %s and %s' % (OUT, ROOT / 'outputs'))
        return 1
    if msix.parent != OUT:
        # Stage it beside the other artifacts so the release has one home.
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copy2(msix, OUT / msix.name)
        msix = OUT / msix.name
    print('     %s  (%.1f MB)' % (msix.name, msix.stat().st_size / (1024 * 1024)))

    print('  7. stage them on the site')
    DL.mkdir(parents=True, exist_ok=True)
    for src in [setup, zip_path, msix]:
        shutil.copy2(src, DL / src.name)
        print('     %s' % src.name)
    # Remove the superseded ones, or the folder grows forever and a stale download stays
    # reachable by its old URL.
    for old in DL.glob('LumaWall-*'):
        m = re.search(r'-(\d+\.\d+\.\d+\.\d+)\.(exe|zip)$', old.name)
        if m and m.group(1) != version:
            old.unlink()
            print('     removed %s' % old.name)
    for old in DL.glob('LumaWall_*'):
        m = re.search(r'_(\d+\.\d+\.\d+\.\d+)_x64\.msix$', old.name)
        if m and m.group(1) != version:
            old.unlink()
            print('     removed %s' % old.name)

    print('  8. cache-bust the pages')
    run(['python', 'tools/cache-bust.py'], timeout=600)

    print('  9. re-record the installer manifest')
    run(['python', 'tools/verify-installer-payload.py', '--record'], timeout=600)

    if not args.no_install:
        print(' 10. install it')
        run([setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
             '/CLOSEAPPLICATIONS'], timeout=900)
        time.sleep(35)
        # Start it so the log can be checked, and so the user finds it running.
        run(['powershell', '-NoProfile', '-Command',
             "Start-Process '%s'" % INSTALLED], check=False)
        time.sleep(30)

    print(' 11. verify')
    bad = verify(version, live=False)
    if bad:
        for b in bad:
            print('  FAIL %s' % b)
        return 1
    print('     installed build and the log are correct')

    print()
    print('  DONE %s' % version)
    print('  the site will serve it once Vercel finishes deploying.')
    print('  commit and push to trigger that:')
    print('    git add -A && git commit -m "LumaWall %s" && git push origin master' % version)
    print()
    print('  after the deploy, confirm the live site with:')
    print('    python tools/release.py --verify-only')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
