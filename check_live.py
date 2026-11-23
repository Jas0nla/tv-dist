#!/usr/bin/env python3
"""Full liveness check for huaren-live.m3u.
Run at home (Mac):  curl -sL https://raw.githubusercontent.com/Jas0nla/tv-dist/main/check_live.py | python3 -
Run in GitHub Actions with PRUNE=1: tests the repo copy, writes live-check-report.json and huaren-live-pruned.m3u
(pruned = only hard failures removed: HTTP 404/410 and DNS-dead hosts; timeouts/5xx are kept).
Stdlib only."""
import sys, os, json, ssl, re, urllib.request, urllib.error, urllib.parse
from concurrent.futures import ThreadPoolExecutor
PLAYLIST_URL = 'https://raw.githubusercontent.com/Jas0nla/tv-dist/main/huaren-live.m3u'
UA = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36'}
CTX = ssl.create_default_context()

def get(url, timeout=8, limit=65536):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read(limit).decode('utf-8', 'ignore')

def get_full(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read().decode('utf-8', 'ignore')

def enc(url):
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(p.path, safe='/:@!$&'()*+,;=-._~%')
    query = urllib.parse.quote(p.query, safe='/:@!$&'()*+,;=-._~%=?')
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, query, ''))

def test(entry):
    name, url = entry
    try:
        if re.search(r'\.(flv|ts|mp4)(\?|$)', url):
            req = urllib.request.Request(enc(url), headers=UA, method='GET')
            with urllib.request.urlopen(req, timeout=8, context=CTX) as r:
                r.read(1024)
                return (name, url, 'pass', 'direct-stream')
        st, body = get(enc(url))
        if '#EXT-X-STREAM-INF' in body:
            for line in body.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    v = urllib.parse.urljoin(enc(url), line)
                    st2, body2 = get(v)
                    ok = ('#EXT-X-TARGETDURATION' in body2) or ('.ts' in body2) or ('.m4s' in body2)
                    return (name, url, 'pass' if ok else 'fail', 'variant-' + str(st2))
            return (name, url, 'fail', 'no-variant')
        ok = ('#EXT-X-TARGETDURATION' in body) or ('.ts' in body) or ('.m4s' in body)
        return (name, url, 'pass' if ok else 'fail', 'not-m3u8')
    except urllib.error.HTTPError as e:
        return (name, url, 'fail', 'http%d' % e.code)
    except Exception as e:
        return (name, url, 'fail', (type(e).__name__ + ':' + str(e))[:70])

def parse(text):
    lines = text.splitlines(); out = []; i = 0
    while i < len(lines):
        if lines[i].startswith('#EXTINF'):
            inf = lines[i]; url = ''; j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if s and not s.startswith('#'):
                    url = s; break
                if lines[j].startswith('#EXTINF'): break
                j += 1
            if url: out.append((inf.split(',')[-1].strip(), url, inf))
            i = j
        else:
            i += 1
    return out

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else PLAYLIST_URL
    if src.startswith('http'):
        _, text = get_full(src, timeout=60)
    else:
        text = open(src, encoding='utf-8').read()
    entries = parse(text)
    uniq = {}; 
    for n, u, inf in entries: uniq.setdefault(u, n)
    tests = [(n, u) for u, n in uniq.items()]
    print('testing %d streams...' % len(tests), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        for i, r in enumerate(ex.map(test, tests)):
            results.append(r)
            if (i + 1) % 250 == 0: print('  %d/%d' % (i + 1, len(tests)), flush=True)
    passed = [r for r in results if r[2] == 'pass']
    failed = [r for r in results if r[2] != 'pass']
    from collections import Counter
    reasons = Counter(r[3].split(':')[0] for r in failed)
    report = {'total': len(results), 'passed': len(passed), 'failed': len(failed),
              'fail_reasons': dict(reasons),
              'failures': [{'name': r[0], 'url': r[1], 'reason': r[3]} for r in failed]}
    out_paths = []
    home_dl = os.path.expanduser('~/Downloads/live-check-results.json')
    try:
        json.dump(report, open(home_dl, 'w'), ensure_ascii=False, indent=1); out_paths.append(home_dl)
    except Exception:
        pass
    json.dump(report, open('live-check-results.json', 'w'), ensure_ascii=False, indent=1); out_paths.append('./live-check-results.json')
    if os.environ.get('PRUNE') == '1':
        hard = set(r[1] for r in failed if r[3] in ('http404', 'http410') or 'Name or service not known' in r[3] or 'nodename' in r[3] or 'Temporary failure in name resolution' in r[3])
        kept = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml"']
        removed = 0
        for n, u, inf in entries:
            if u in hard: removed += 1; continue
            kept.append(inf); kept.append(u)
        open('huaren-live-pruned.m3u', 'w', encoding='utf-8').write('\n'.join(kept) + '\n')
        json.dump(report, open('live-check-report.json', 'w'), ensure_ascii=False, indent=1)
        print('PRUNE: removed %d hard-dead streams' % removed)
    print('DONE total=%d passed=%d failed=%d' % (len(results), len(passed), len(failed)))
    print('fail reasons:', dict(reasons))
    print('results written to:', ', '.join(out_paths))

if __name__ == '__main__':
    main()
