"""set-vercel-root.py — points the Vercel project at the site folder.

Why this is needed, and why it is the real fix:

The project is connected to the GitHub repo, so every `git push` triggers a
deployment. Vercel built from the repo ROOT, and the root has no index.html - the
site lives in site/. So each push published an empty deployment, that deployment
became production, the production alias followed it, and lumawall.xinet.id returned
404. It happened twice in one evening, each time minutes after a push:

    push 23:51:21  ->  deployment 23:51:29, entrypoint "."

Deleting the root .vercel link stopped a manual deploy from the root. It did not
stop the Git integration, because the integration reads the project's Root Directory
setting, not the link file. Setting that to `site` makes every future push build the
site folder instead.

This writes the setting through the Vercel API. It reads the token from the CLI's
own auth file, so no credential is stored in the repo.

Run:  python tools/set-vercel-root.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

PROJECT = 'lumawall'
TEAM = 'luma-wall1'
ROOT_DIRECTORY = 'site'

AUTH = os.path.expandvars(r'%APPDATA%\com.vercel.cli\Data\auth.json')


def token():
    if not os.path.exists(AUTH):
        return None
    try:
        data = json.load(open(AUTH, encoding='utf-8'))
    except Exception:
        return None
    return data.get('token')


def call(method, path, body=None, tok=None):
    url = 'https://api.vercel.com' + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + tok)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {'__error': e.code, '__body': e.read().decode()[:400]}


def main():
    tok = token()
    if not tok:
        print('  no Vercel token at %s' % AUTH)
        return 1

    print('  reading the project...')
    proj = call('GET', '/v9/projects/%s?teamId=%s' % (PROJECT, TEAM), tok=tok)
    if '__error' in proj:
        print('  could not read the project: %s' % proj)
        return 1

    pid = proj.get('id')
    current = proj.get('rootDirectory')
    print('    id              : %s' % pid)
    print('    rootDirectory   : %s' % (current or '(repo root)'))
    print('    framework       : %s' % proj.get('framework'))

    if current == ROOT_DIRECTORY:
        print()
        print('  already set to %r - nothing to change' % ROOT_DIRECTORY)
        return 0

    print()
    print('  setting rootDirectory to %r...' % ROOT_DIRECTORY)
    res = call('PATCH', '/v9/projects/%s?teamId=%s' % (PROJECT, TEAM),
               {'rootDirectory': ROOT_DIRECTORY}, tok=tok)
    if '__error' in res:
        print('  failed: %s' % res)
        return 1

    print('    rootDirectory is now: %s' % res.get('rootDirectory'))
    print()
    print('  Every future push will now build the site folder, so the deployment')
    print('  cannot be empty and the production alias cannot be moved to an empty one.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
