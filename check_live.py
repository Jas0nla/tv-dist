#!/usr/bin/env python3
"""Two-stage liveness + playability check for huaren-live.m3u.
Stage 1 (knock): connect, fetch playlist, verify HLS format.
Stage 2 (play): for stage-1 passers, actually download the first segments and
measure sustained throughput vs the bitrate the stream needs -> verdict
smooth / ok / buffering. (Approach borrowed from Guovin/iptv-api: speed-test
and rank lines per channel.)
Run at home (Mac):  curl -sL https://raw.githubusercontent.com/Jas0nla/tv-dist/main/check_live.py | python3 -
PRUNE=1 (GitHub Actions): also writes huaren-live-pruned.m3u with only
hard-dead streams removed (HTTP 404/410, DNS-dead). Stdlib only."""
import sys, os, json, ssl, re, time, urllib.request, urllib.error, urllib.parse
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
    safe = "/:@!$&()*+,;=-._~%"
    path = urllib.parse.quote(p.path, safe=safe)
    query = urllib.parse.quote(p.query, safe=safe + "=?")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, query, ""))

def knock(entry):
    name, url = entry
    try:
        if re.search(r'\.(flv|ts|mp4)(\?|$)', url):
            req = urllib.request.Request(enc(url), headers=UA, method='GET')
            with urllib.request.urlopen(req, timeout=8, context=CTX) as r:
                r.read(1024)
                return (name, url, 'pass', 'direct-stream', None)
        st, body = get(enc(url))
        if '#EXT-X-STREAM-INF' in body:
            best = None; best_bw = -1; first = None
            lines = body.splitlines()
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-STREAM-INF'):
                    m = re.search(r'BANDWIDTH=(\d+)', line)
                    bw = int(m.group(1)) if m else 0
                    for j in range(i + 1, len(lines)):
                        s = lines[j].strip()
                        if s and not s.startswith('#'):
                            v = urllib.parse.urljoin(enc(url), s)
                            if first is None: first = (v, bw)
                            if bw > best_bw: best_bw = bw; best = (v, bw)
                            break
            pick = best or first
            if not pick: return (name, url, 'fail', 'no-variant', None)
            st2, body2 = get(pick[0])
            ok = ('#EXT-X-TARGETDURATION' in body2) or ('.ts' in body2) or ('.m4s' in body2)
            return (name, url, 'pass' if ok else 'fail', 'variant-' + str(st2), (pick[0], pick[1], body2) if ok else None)
        ok = ('#EXT-X-TARGETDURATION' in body) or ('.ts' in body) or ('.m4s' in body)
        return (name, url, 'pass' if ok else 'fail', 'not-m3u8', (url, 0, body) if ok else None)
    except urllib.error.HTTPError as e:
        return (name, url, 'fail', 'http%d' % e.code, None)
    except Exception as e:
        return (name, url, 'fail', (type(e).__name__ + ':' + str(e))[:70], None)

def play(res):
    name, url, status, detail, ctx = res
    if status != 'pass' or not ctx:
        return (name, url, status, detail, None, None)
    media_url, declared_bw, body = ctx
    try:
        segs = []; dur = 0.0
        lines = body.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:'):
                try: dur = float(line.split(':')[1].split(',')[0])
                except Exception: dur = 0.0
            else:
                s = line.strip()
                if s and not s.startswith('#'):
                    segs.append((urllib.parse.urljoin(media_url, s), dur))
                    dur = 0.0
            if len(segs) >= 4: break
        if not segs: return (name, url, 'pass', detail, None, 'no-segments')
        total_bytes = 0; t0 = time.time(); total_dur = 0.0; got = 0
        for surl, sdur in segs:
            req = urllib.request.Request(enc(surl), headers=UA)
            with urllib.request.urlopen(req, timeout=10, context=CTX) as r:
                while True:
                    chunk = r.read(262144)
                    if not chunk: break
                    total_bytes += len(chunk)
                    if time.time() - t0 > 10: break
            total_dur += sdur; got += 1
            if time.time() - t0 > 10: break
        elapsed = time.time() - t0
        if total_bytes == 0 or elapsed == 0:
            return (name, url, 'pass', detail, 0, 'no-data')
        kbps = int(total_bytes * 8 / elapsed / 1000)
        need = int(declared_bw / 1000) if declared_bw else (int(total_bytes * 8 / total_dur / 1000) if total_dur else 0)
        if need:
            ratio = kbps / need
            verdict = 'smooth' if ratio >= 1.5 else ('ok' if ratio >= 1.0 else 'buffering')
        else:
            verdict = 'smooth' if kbps >= 4000 else ('ok' if kbps >= 1500 else 'buffering')
        return (name, url, 'pass', detail, kbps, verdict)
    except Exception as e:
        return (name, url, 'pass', detail, None, 'play-error:' + type(e).__name__)

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
    uniq = {}
    for n, u, inf in entries: uniq.setdefault(u, n)
    tests = [(n, u) for u, n in uniq.items()]
    print('stage1 knock: testing %d streams...' % len(tests), flush=True)
    from concurrent.futures import as_completed
    stage1 = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        futs = [ex.submit(knock, t) for t in tests]
        for i, f in enumerate(as_completed(futs)):
            stage1.append(f.result())
            if (i + 1) % 200 == 0 or i + 1 == len(tests):
                print('  stage1 %d/%d' % (i + 1, len(tests)), flush=True)
    passed1 = [r for r in stage1 if r[2] == 'pass']
    print('stage1 done: %d passed, now stage2 play-test...' % len(passed1), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(play, r) for r in stage1]
        for i, f in enumerate(as_completed(futs)):
            results.append(f.result())
            if (i + 1) % 100 == 0 or i + 1 == len(stage1):
                print('  stage2 %d/%d' % (i + 1, len(stage1)), flush=True)
    passed = [r for r in results if r[2] == 'pass']
    failed = [r for r in results if r[2] != 'pass']
    from collections import Counter
    reasons = Counter(r[3].split(':')[0] for r in failed)
    verdicts = Counter(r[5] for r in passed if r[5])
    report = {'total': len(results), 'passed': len(passed), 'failed': len(failed),
              'fail_reasons': dict(reasons), 'verdicts': dict(verdicts),
              'streams': [{'name': r[0], 'url': r[1], 'status': r[2], 'reason': r[3],
                           'speed_kbps': r[4], 'verdict': r[5]} for r in results]}
    out_paths = []
    home_dl = os.path.expanduser('~/Downloads/live-check-results.json')
    try:
        json.dump(report, open(home_dl, 'w'), ensure_ascii=False, indent=1); out_paths.append(home_dl)
    except Exception:
        pass
    json.dump(report, open('live-check-results.json', 'w'), ensure_ascii=False, indent=1); out_paths.append('./live-check-results.json')
    if os.environ.get('PRUNE') == '1':
        hard = set(r[1] for r in failed if r[3] in ('http404', 'http410') or 'Name or service not known' in r[3] or 'nodename' in r[3] or 'Temporary failure in name resolution' in r[3])
        # rule (user, 2026-11-23): if two test results disagree, do NOT delete.
        # A stream the home-network test passed is never pruned by the runner test alone.
        for cand in (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'home-check-report.json'), 'home-check-report.json'):
            try:
                hrep = json.load(open(cand))
                home_pass = set(s['url'] for s in hrep['streams'] if s['status'] == 'pass')
                before = len(hard); hard -= home_pass
                print('PRUNE: kept %d disputed streams that passed at home' % (before - len(hard)))
                break
            except Exception:
                continue
        kept = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml"']
        removed = 0
        for n, u, inf in entries:
            if u in hard: removed += 1; continue
            kept.append(inf); kept.append(u)
        open('huaren-live-pruned.m3u', 'w', encoding='utf-8').write('\n'.join(kept) + '\n')
        json.dump(report, open('live-check-report.json', 'w'), ensure_ascii=False, indent=1)
        print('PRUNE: removed %d hard-dead streams' % removed)
    print('DONE total=%d alive=%d dead=%d' % (len(results), len(passed), len(failed)))
    print('fail reasons:', dict(reasons))
    print('play verdicts:', dict(verdicts))
    print('results written to:', ', '.join(out_paths))

if __name__ == '__main__':
    main()
