"""Validate the MSIX the way the Store does, without needing administrator rights.

Why this exists
---------------
`appcert.exe` (the App Certification Kit) is the real gate, but it requires elevation:
running it unelevated fails with "The requested operation requires elevation". That makes it
useless in a checker suite, and it means a packaging defect is discovered during submission
instead of during the build.

This checks the rules that actually reject submissions, by reading the package the way the
Store's ingestion does:

  * Identity is well formed - Name is a legal package name, Publisher is a valid
    distinguished name, Version is four numbers and matches the file name. A mismatch
    between the file name and the identity version is a rejection.
  * Every image the manifest references exists in the package, at the size the manifest's
    own name implies (Square310x310Logo must be 310x310). This is where a real defect was
    found: the manifest pointed the 71px slot at a 44px file, the 310px slot at a 150px file,
    and Square310x310Logo.png was missing entirely.
  * The required assets are present. StoreLogo is mandatory; without it the listing has no
    icon.
  * Capabilities are declared and known. `runFullTrust` is required for a desktop-bridge
    app, and is what a reparented WorkerW window needs.
  * The dependency on WebView2 is declared, so a machine without the Runtime is offered it.
  * Nothing that the Store rejects is inside: no installer executables, no debug symbols,
    no source files, no private keys.
  * The payload is not absurdly large.

Usage: python tools/check-store-package.py [path-to.msix]
"""
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs'

NS = {
    'f': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10',
    'uap': 'http://schemas.microsoft.com/appx/manifest/uap/windows10',
    'rescap': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities',
    'desktop': 'http://schemas.microsoft.com/appx/manifest/desktop/windows10',
}

# Sizes for the assets whose names do not carry them. Everything else is read from the name.
NAMED_SIZES = {
    'StoreLogo': (50, 50),
    'SplashScreen': (620, 300),
    'BadgeLogo': (24, 24),
    'LockScreenLogo': (24, 24),
}

# Files that must not be in a Store package. A .pdb or a .cs inside the payload is either
# dead weight or a source leak, and both draw certification notes.
FORBIDDEN = re.compile(
    r'\.(pdb|cs|csproj|sln|py|ps1|sh|bat|cmd|log|bak|tmp|pfx|snk|key|pem|cer|zip|7z|rar)$',
    re.IGNORECASE)

REQUIRED_ASSETS = ['StoreLogo', 'Square150x150Logo', 'Square44x44Logo']

# A package over this is not rejected, but it is a warning sign for a wallpaper app.
MAX_MB = 400


def find_package(argv):
    if len(argv) > 1:
        p = Path(argv[1])
        return p if p.exists() else None
    if not OUT.exists():
        return None
    # The newest by version, not by mtime: a rebuilt older version should not win.
    found = sorted(OUT.glob('LumaWall_*_x64.msix'))
    if not found:
        return None

    def version_key(p):
        m = re.search(r'_(\d+\.\d+\.\d+\.\d+)_', p.name)
        return tuple(int(x) for x in m.group(1).split('.')) if m else (0, 0, 0, 0)

    return max(found, key=version_key)


def main():
    package = find_package(sys.argv)
    if package is None:
        print('  FAIL no MSIX found in outputs/ - run tools/build_msix.ps1 first')
        return 1
    print('  package: %s  (%.2f MB)' % (package.name, package.stat().st_size / 1048576))
    print()

    failures = []
    notes = []

    try:
        zf = zipfile.ZipFile(package)
    except Exception as e:
        print('  FAIL the package cannot be opened: %s' % e)
        return 1

    names = zf.namelist()
    with zf.open('AppxManifest.xml') as fh:
        manifest_text = fh.read().decode('utf-8-sig')
    try:
        root = ElementTree.fromstring(manifest_text)
    except Exception as e:
        print('  FAIL AppxManifest.xml is not valid XML: %s' % e)
        return 1

    # ---- Identity ----------------------------------------------------------------
    identity = root.find('f:Identity', NS)
    if identity is None:
        failures.append('the manifest has no Identity element')
        print('  FAIL no Identity')
        return 1
    name = identity.get('Name', '')
    publisher = identity.get('Publisher', '')
    version = identity.get('Version', '')
    arch = identity.get('ProcessorArchitecture', '')

    print('  Identity')
    print('    Name        %s' % name)
    print('    Publisher   %s' % publisher)
    print('    Version     %s' % version)
    print('    Arch        %s' % arch)

    if not re.fullmatch(r'[A-Za-z0-9.\-]{3,50}', name):
        failures.append('Identity/@Name "%s" is not a legal package name' % name)
    if not re.fullmatch(r'CN=.+', publisher):
        failures.append('Identity/@Publisher "%s" must be a distinguished name' % publisher)
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        failures.append('Identity/@Version "%s" must be four numbers' % version)
    else:
        # The Store reads the version from the file name too, and a mismatch is a rejection.
        m = re.search(r'_(\d+\.\d+\.\d+\.\d+)_', package.name)
        if m and m.group(1) != version:
            failures.append('the file name says %s but the identity says %s'
                            % (m.group(1), version))
    if arch != 'x64':
        notes.append('architecture is %s' % arch)
    if publisher == 'CN=LumaWall':
        notes.append('Publisher is the placeholder "CN=LumaWall" - it must match the '
                     'publisher CN that Partner Center assigns to the account')
    print()

    # ---- Every referenced image exists, at the size its name implies ---------------
    #
    # Two forms in the manifest: attributes (Square150x150Logo="...") and elements
    # (<Logo>TileAssets\StoreLogo.png</Logo>). Matching only the attributes made this
    # checker claim the required StoreLogo was missing when it was right there - a false
    # failure that would have sent someone editing a correct manifest.
    refs = set(re.findall(r'(?:Logo|Image|BadgeLogo)="([^"]+\.png)"', manifest_text))
    refs |= set(re.findall(r'<(?:Logo|uap:Logo|uap:SplashScreen[^>]*)>([^<]+\.png)<',
                           manifest_text))
    refs = sorted(refs)
    print('  assets referenced by the manifest')
    for ref in refs:
        rel = ref.replace('\\', '/')
        if rel not in names:
            print('    %-42s MISSING' % ref)
            failures.append('%s is referenced but not in the package' % ref)
            continue

        base = Path(rel).stem
        m = re.match(r'(Square|Wide)(\d+)x(\d+)Logo$', base)
        if m:
            want = (int(m.group(2)), int(m.group(3)))
        elif base in NAMED_SIZES:
            want = NAMED_SIZES[base]
        else:
            print('    %-42s ok (unknown nominal size)' % ref)
            continue

        data = zf.read(rel)
        got = png_size(data)
        if got is None:
            print('    %-42s NOT A PNG' % ref)
            failures.append('%s is not a readable PNG' % ref)
        elif got != want:
            print('    %-42s %dx%d, the name says %dx%d' % (ref, got[0], got[1], want[0], want[1]))
            failures.append('%s is %dx%d but its name says %dx%d'
                            % (ref, got[0], got[1], want[0], want[1]))
        else:
            print('    %-42s %dx%d ok' % (ref, got[0], got[1]))
    print()

    for base in REQUIRED_ASSETS:
        if not any(base in r for r in refs):
            failures.append('the manifest does not reference %s, which the Store requires' % base)

    # ---- Capabilities ------------------------------------------------------------
    caps = [c.get('Name') for c in root.findall('.//f:Capability', NS)]
    caps += [c.get('Name') for c in root.findall('.//rescap:Capability', NS)]
    print('  capabilities: %s' % ', '.join(c for c in caps if c))
    if 'runFullTrust' not in caps:
        failures.append('runFullTrust is not declared - a reparented desktop window and a '
                        'child process both need it')
    if 'internetClient' not in caps:
        notes.append('internetClient is not declared; the catalogue fetch will be blocked')
    print()

    # ---- WebView2 dependency -----------------------------------------------------
    dep = root.find('.//f:Dependencies', NS)
    has_wv2 = manifest_text.find('Microsoft.WebView2') >= 0
    print('  WebView2 declared as a dependency: %s' % ('yes' if has_wv2 else 'no'))
    if not has_wv2:
        failures.append('WebView2 is not declared; a machine without the Runtime would '
                        'install the app and see nothing render')
    print()

    # ---- Nothing forbidden inside ------------------------------------------------
    bad = [n for n in names if FORBIDDEN.search(n)]
    print('  files the Store objects to: %d' % len(bad))
    for n in bad[:10]:
        print('    %s' % n)
    if bad:
        failures.append('%d file(s) that should not ship are in the package' % len(bad))
    print()

    size_mb = package.stat().st_size / 1048576
    if size_mb > MAX_MB:
        failures.append('the package is %.0f MB, over the %d MB this project allows' % (size_mb, MAX_MB))

    print('  payload: %d files, %.2f MB' % (len(names), size_mb))
    print()

    # ---- Report ------------------------------------------------------------------
    for n in notes:
        print('  NOTE  %s' % n)
    if failures:
        for f in failures:
            print('  FAIL  %s' % f)
        return 1
    print('  PASS the package is well formed: identity is legal, every asset is present at '
          'the right size, the capabilities and the WebView2 dependency are declared, and '
          'nothing forbidden is inside')
    print()
    print('  The App Certification Kit is the final gate and needs an elevated shell:')
    print('    appcert.exe -appx "%s" -reportoutputpath build\\appcert.xml' % package)
    return 0


def png_size(data):
    """Width and height from the PNG header, without decoding the image."""
    if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return (int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big'))


if __name__ == '__main__':
    raise SystemExit(main())
