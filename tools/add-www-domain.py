"""add-www-domain.py — makes www.lumawall.xinet.id work.

Why: people type "www." out of habit, and right now that host does not resolve at
all - `nslookup www.lumawall.xinet.id` answers NXDOMAIN, and a browser shows its own
error page, which looks identical to the site being down. The bare domain works, so
the site is fine; only the www host is missing.

Two parts, and both are needed:

  1. the host has to be attached to the Vercel project
  2. DNS has to point at Vercel. The parent domain (xinet.id) is on third-party
     nameservers, so if the DNS provider is not already configured, Vercel reports
     the exact record to create.

Vercel then redirects www to the apex automatically once it is attached.

Run:  python tools/add-www-domain.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

PROJECT = 'lumawall'
TEAM = 'luma-wall1'
WWW = 'www.lumawall.xinet.id'

AUTH = os.path.expandvars(r'%APPDATA%\com.vercel.cli\Data\auth.json')


def token():
    if not os.path.exists(AUTH):
        return None
    try:
        return json.load(open(AUTH, encoding='utf-8')).get('token')
    except Exception:
        return None


def api(method, path, body=None, tok=None):
    url = 'https://api.vercel.com' + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + tok)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return {'__error': e.code, '__body': json.loads(e.read().decode())}
        except Exception:
            return {'__error': e.code}


def main():
    tok = token()
    if not tok:
        print('  no Vercel token at %s' % AUTH)
        return 1

    print('  attaching %s to %s...' % (WWW, PROJECT))
    res = api('POST', '/v10/projects/%s/domains?teamId=%s' % (PROJECT, TEAM),
              {'name': WWW}, tok=tok)

    if '__error' in res:
        err = res['__body'] if isinstance(res.get('__body'), dict) else {}
        code = err.get('error', {}).get('code')
        if code == 'domain_already_in_use' or code == 'domain_already_exists':
            print('    already attached')
        else:
            print('    failed: %s %s' % (res['__error'], err.get('error', {}).get('message', '')))
            return 1
    else:
        print('    attached')

    # What DNS does it want?
    print()
    print('  reading the required DNS record...')
    cfg = api('GET', '/v6/domains/%s/config?teamId=%s' % (WWW, TEAM), tok=tok)
    if '__error' in cfg:
        print('    could not read config: %s' % cfg['__error'])
    else:
        print('    misconfigured : %s' % cfg.get('misconfigured'))
        recs = cfg.get('recommendedIPv4') or cfg.get('recommendedCNAME') or []
        if recs:
            for r in recs:
                if isinstance(r, dict):
                    print('    %-6s %s' % (r.get('rank'), r.get('value')))
                else:
                    print('    %s' % r)

    print()
    print('  checking whether it resolves yet...')
    import socket
    try:
        socket.getaddrinfo(WWW, None)
        print('    resolves')
    except Exception:
        print('    does NOT resolve yet.')
        print()
        print('    The host is attached on Vercel. DNS still needs a record at the')
        print('    provider that runs xinet.id:')
        print('      type : CNAME')
        print('      name : www.lumawall')
        print('      value: cname.vercel-dns.com')
        print()
        print('    Until that record exists, www.lumawall.xinet.id shows the')
        print('    browser\'s own error page - which is what the user saw.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
