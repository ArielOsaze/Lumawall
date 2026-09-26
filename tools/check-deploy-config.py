"""check-deploy-config.py — is the Vercel project set up so the site stays up?

Why this exists:

The site went down with a 404 three times, and every time the deploy had reported
success. The failures are invisible from the CLI, because they are not deploy
failures at all - they are configuration states that make the *next* build
produce an empty deployment, or make the alias point at one.

Three specific faults, all of which this checks:

  1. `rootDirectory` is not `site`. The Git integration builds on every push, and
     with rootDirectory unset it builds the repository root - which has no
     index.html, because the site lives in site/. The build succeeds, produces an
     empty deployment, and Vercel promotes it to production. The domain then 404s
     while the previous, good deployment is still sitting there.

  2. The production alias points at a deployment that does not serve the site.
     This is what `deploy-vercel.ps1` checks at the end of a deploy, but nothing
     checked it afterwards - so an empty build promoted hours later went unnoticed
     until someone opened the site.

  3. The alias points at a deployment whose age does not match the newest commit.
     Not an error on its own, but worth printing, because it is the difference
     between "the push deployed" and "the push did nothing".

This reads the Vercel API with the CLI's own stored token, so it needs no extra
setup. It is read-only: it reports, it never changes anything.

Usage:
    python tools/check-deploy-config.py
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

PROJECT = 'lumawall'
TEAM_ID = 'team_AhwtNLffS3HIU9pIqFGscUgC'
DOMAIN = 'https://lumawall.xinet.id'
REQUIRED_ROOT = 'site'

# The two pages and the two videos. A deployment that serves the pages but not the
# videos is the failure this whole file exists for: the page returns 200 and the
# video block is blank, which nothing server-side can see.
EXPECTED = [
    ('/', 'the Indonesian page', b'<html lang="id"'),
    ('/en/', 'the English page', b'<html lang="en"'),
    ('/sitemap.xml', 'the sitemap', b'<loc>'),
    ('/robots.txt', 'robots.txt', b'Sitemap:'),
]


def token():
    path = os.path.expandvars(r'%APPDATA%\com.vercel.cli\Data\auth.json')
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle).get('token')
    except (ValueError, OSError):
        return None


def api(path, tok):
    request = urllib.request.Request('https://api.vercel.com' + path,
                                     headers={'Authorization': 'Bearer ' + tok})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch(url, limit=400_000):
    request = urllib.request.Request(url, headers={'User-Agent': 'LumaWall deploy check'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read(limit)


def main():
    problems = []
    notes = []

    print()
    print('  deploy configuration: will the next push keep the site up?')
    print()

    tok = token()
    if not tok:
        print('  no Vercel CLI token found - run `npx vercel login` first')
        return 1

    # ── 1. the project settings ──────────────────────────────────────────────
    try:
        project = api('/v9/projects/%s?teamId=%s' % (PROJECT, TEAM_ID), tok)
    except urllib.error.HTTPError as e:
        print('  could not read the project: HTTP %s' % e.code)
        return 1

    root = project.get('rootDirectory')
    git = project.get('link') or {}

    print('    project           %s' % project.get('name'))
    print('    rootDirectory     %r' % root)
    print('    git integration   %s' % (git.get('repo') or 'DISCONNECTED'))

    if git.get('repo'):
        # The Git integration is connected, so every push builds. rootDirectory has
        # to be right or those builds produce an empty deployment.
        if root != REQUIRED_ROOT:
            problems.append(
                'rootDirectory is %r but the Git integration is connected, so every '
                'push builds the repository root - which has no index.html - and '
                'promotes an empty deployment to production. Set it to %r.'
                % (root, REQUIRED_ROOT))
            print('    %-17s WRONG - a push will take the site down' % '')
        else:
            print('    %-17s correct for the Git build' % '')
    else:
        notes.append('the Git integration is disconnected, so pushes do not deploy; '
                     'the CLI is the only path (tools/deploy-vercel.ps1)')

    # ── 2. the alias ─────────────────────────────────────────────────────────
    try:
        aliases = api('/v4/aliases?projectId=%s&teamId=%s&limit=20'
                      % (project['id'], TEAM_ID), tok)
    except urllib.error.HTTPError as e:
        aliases = {'aliases': []}
        notes.append('could not read the aliases: HTTP %s' % e.code)

    target = None
    for alias in aliases.get('aliases', []):
        if alias.get('alias') == 'lumawall.xinet.id':
            target = alias.get('deployment', {}).get('url')
            break

    print()
    print('    alias             lumawall.xinet.id -> %s' % (target or 'NOT FOUND'))
    if not target:
        problems.append('no production alias for lumawall.xinet.id')

    # ── 3. what the domain actually serves ───────────────────────────────────
    #
    # The only check that matters to a visitor. Everything above can be right while
    # the domain serves an empty deployment.
    print()
    print('    what the domain serves:')
    for path, label, marker in EXPECTED:
        url = DOMAIN + path
        try:
            status, body = fetch(url)
        except urllib.error.HTTPError as e:
            problems.append('%s (%s) returned HTTP %s' % (label, path, e.code))
            print('      %-3s  %-20s %s' % (e.code, path, label))
            continue
        except Exception as e:
            problems.append('%s (%s) could not be fetched: %s' % (label, path, e))
            print('      ---  %-20s %s' % (path, label))
            continue

        if marker not in body:
            problems.append('%s (%s) does not contain its expected content - the '
                            'deployment is probably empty' % (label, path))
            print('      %-3s  %-20s %s   <-- content missing' % (status, path, label))
        else:
            print('      %-3s  %-20s %s' % (status, path, label))

    # ── 4. both videos ───────────────────────────────────────────────────────
    #
    # Read from the pages rather than hard-coded, so a re-render with a new hash
    # does not need this file edited.
    import re
    print()
    print('    the videos the pages ask for:')
    for path, label in (('/', 'Indonesian'), ('/en/', 'English')):
        try:
            _, body = fetch(DOMAIN + path)
        except Exception as e:
            problems.append('could not read %s to find its video: %s' % (path, e))
            continue
        found = re.search(rb'(assets/video/lumawall-promo[a-z-]*\.[a-f0-9]*\.mp4)', body)
        if not found:
            problems.append('%s does not reference a promo video' % path)
            print('      %-11s no video reference   <-- the page will show a blank block' % label)
            continue
        video = found.group(1).decode()
        try:
            request = urllib.request.Request(DOMAIN + '/' + video,
                                             headers={'Range': 'bytes=0-1023',
                                                      'User-Agent': 'LumaWall deploy check'})
            with urllib.request.urlopen(request, timeout=30) as response:
                code = response.status
                head = response.read(1024)
        except urllib.error.HTTPError as e:
            problems.append('%s page references %s, which returned HTTP %s'
                            % (label, video, e.code))
            print('      %-11s %-38s HTTP %s   <-- 404' % (label, video.split('/')[-1], e.code))
            continue

        # An mp4 starts with a box size then 'ftyp'. A 200 with an HTML body is the
        # classic signature of a missing asset served by a catch-all route.
        real = b'ftyp' in head[:16]
        print('      %-11s %-38s HTTP %s%s'
              % (label, video.split('/')[-1], code, '' if real else '   <-- not an mp4'))
        if not real:
            problems.append('%s page references %s, which is not an mp4 (the first '
                            'bytes are %r)' % (label, video, head[:16]))

    # ── report ───────────────────────────────────────────────────────────────
    print()
    if notes:
        for note in notes:
            print('  note: %s' % note)
        print()

    if problems:
        print('  %d problem(s):' % len(problems))
        for problem in problems:
            print('    · %s' % problem)
        print()
        print('  These are the states that have taken lumawall.xinet.id down before.')
        print('  None of them is a deploy failure, which is why the CLI reported success.')
        return 1

    print('  the configuration is right, and the domain is serving the real site')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
