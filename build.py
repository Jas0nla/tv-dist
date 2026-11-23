#!/usr/bin/env python3
"""v2.1: merge maintained sources, regroup cleanly (no orphan groups), dedupe, cap 3 lines/channel, apply blacklist. No stream testing here."""
import urllib.request, ssl, sys, json, re, os
BASE = os.path.dirname(os.path.abspath(__file__))
ctx = ssl.create_default_context()
UA = {'User-Agent':'Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36'}
def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=60, context=ctx).read().decode('utf-8','ignore').splitlines()
def parse(lines):
    out=[]; i=0
    while i < len(lines):
        if lines[i].startswith('#EXTINF'):
            inf=lines[i]; url=''; j=i+1
            while j < len(lines):
                s=lines[j].strip()
                if s and not s.startswith('#'): url=s; break
                if lines[j].startswith('#EXTINF'): break
                j+=1
            if url: out.append((inf,url))
            i=j
        else: i+=1
    return out
SOURCES=[
 'https://iptv-org.github.io/iptv/countries/hk.m3u',
 'https://iptv-org.github.io/iptv/countries/tw.m3u',
 'https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u',
 'https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u',
 'https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u',
 'https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u',
 'https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv4.m3u',
 'https://iptv-org.github.io/iptv/countries/sg.m3u',
 'https://iptv-org.github.io/iptv/countries/my.m3u',
 'https://iptv-org.github.io/iptv/countries/au.m3u',
 'https://iptv-org.github.io/iptv/countries/nz.m3u',
 'https://iptv-org.github.io/iptv/countries/jp.m3u',
 'https://iptv-org.github.io/iptv/countries/th.m3u',
]
FORCED = {
 'https://iptv-org.github.io/iptv/countries/au.m3u': '澳新',
 'https://iptv-org.github.io/iptv/countries/nz.m3u': '澳新',
 'https://iptv-org.github.io/iptv/countries/jp.m3u': '日本',
 'https://iptv-org.github.io/iptv/countries/th.m3u': '泰国',
}
try: blacklist=set(l.strip() for l in open(os.path.join(BASE, 'blacklist.txt')) if l.strip())
except FileNotFoundError: blacklist=set()
def name_of(inf): return inf.split(',')[-1].strip()
def hint_of(inf):
    m=re.search(r'group-title="([^"]*)"', inf); return m.group(1) if m else ''
def norm(n):
    n=re.sub(r'\[.*?\]|\(.*?\)','',n)
    n=re.sub(r'(?i)1080p|720p|480p|2160p|4k|uhd|fhd|hd|sd|高清|超清|标清|藍光|蓝光','',n)
    return re.sub(r'\s+','',n).lower()
TW=re.compile(r'三立|民视|民視|台视|台視|中视|中視|公视|公視|华视|華視|TVBS|壹电视|壹電視|镜新闻|鏡新聞|非凡|年代|八大|纬来|緯來|东森|東森|中天|大爱|大愛|客家|原民台|FTV|TTV News|台湾|台灣')
HK=re.compile(r'翡翠|TVB|凤凰|鳳凰|RTHK|ViuTV|HOY|香港|港台|Jade|Phoenix|有线|有線|开电视|開電視|明珠台|无线|無線|Now')
SGMY=re.compile(r'(?i)astro|RTM|(?<![A-Za-z0-9])TV[12](?![0-9])|Okey|8TV|八度|Channel ?8|Channel ?5|Mediacorp|Suria|Vasantham|马来西亚|馬來西亞|新加坡|Malaysia|Singapore|华丽|華麗|AEC|天映|Celestial|星卫|星衛')
FOURK=re.compile(r'(?i)4K|UHD|2160|超高清')
def classify(n, hint):
    t=n+' '+hint
    if FOURK.search(n): return '4K超高清'
    if TW.search(n): return '台湾'
    if HK.search(n): return '香港'
    if re.search(r'CCTV|央视|央視|CGTN|央视频|央視頻', t): return '央视'
    if SGMY.search(n): return '新马'
    if re.search(r'卫视|衛視', t): return '卫视'
    if re.search(r'电影|電影|影院|影视频道|影視|Movie', t): return '电影'
    if re.search(r'体育|體育|足球|篮球|籃球|赛事|賽事|Sports|ESPN|五星体育', t): return '体育'
    if re.search(r'少儿|少兒|卡通|动漫|動漫|动画|動畫|宝宝|寶貝|Kids|金鹰卡通|优漫', t): return '少儿动漫'
    if re.search(r'纪录|紀錄|科教|探索|Discovery|地理|纪实|紀實|求索|世界地理', t): return '纪录科教'
    if re.search(r'新闻|新聞|资讯|資訊|财经|財經|News', t): return '新闻'
    if re.search(r'综艺|綜藝|娱乐|娛樂|音乐|音樂|戏曲|戲曲|时尚|時尚|生活|旅游|旅遊|美食|健康|养生|養生|女性|都市频道|都市頻道', t): return '综艺生活'
    if re.search(r'地方|本地|市台|新闻综合|新聞綜合|公共频道|公共頻道|经济科教|經濟科教|影视频道|都市|民生', t): return '地方台'
    if not re.search(r'[\u4e00-\u9fff]', n): return '国际'
    return '综合'
ORDER=['4K超高清','香港','台湾','央视','卫视','新马','电影','体育','少儿动漫','新闻','纪录科教','综艺生活','地方台','国际','澳新','日本','泰国','综合']
seen=set(); per_name={}; groups={g:[] for g in ORDER}
total_in=0
for u in SOURCES:
    try: entries=parse(fetch(u))
    except Exception as e:
        print(f'WARN fetch failed {u}: {e}', file=sys.stderr); continue
    for inf,url in entries:
        total_in+=1
        if url in seen or url in blacklist: continue
        seen.add(url)
        n=name_of(inf); g=FORCED.get(u) or classify(n, hint_of(inf))
        key=(g,norm(n))
        if per_name.get(key,0)>=3: continue
        per_name[key]=per_name.get(key,0)+1
        inf2=re.sub(r'group-title="[^"]*"', f'group-title="{g}"', inf) if 'group-title="' in inf else (inf.replace('#EXTINF:-1 ', f'#EXTINF:-1 group-title="{g}" ',1) if inf.startswith('#EXTINF:-1 ') else inf)
        groups[g].append((inf2,url))
# fold tiny groups (<5) into 综合 so no group has just one or two channels
for g in ORDER:
    if g!='综合' and 0 < len(groups[g]) < 5:
        for inf,url in groups[g]:
            groups['综合'].append((re.sub(r'group-title="[^"]*"','group-title="综合"',inf), url))
        groups[g]=[]
# --- apply home-check report if present ---
import os
rep_path = os.path.join(BASE, 'home-check-report.json')
if os.path.exists(rep_path):
    rep = json.load(open(rep_path))
    info = {s['url']: s for s in rep['streams']}
    rinfo = {}
    try:
        rrep = json.load(open(os.path.join(BASE, 'check-report.json')))
        rinfo = {s['url']: s for s in rrep['streams']}
    except Exception:
        pass
    def _hard(s):
        return s is not None and s['status'] != 'pass' and (s['reason'] in ('http404', 'http410') or 'not known' in s['reason'] or 'nodename' in s['reason'] or 'Temporary failure' in s['reason'])
    def _fail(s):
        return s is not None and s['status'] != 'pass'
    def agreed_dead(url):
        # rule (user, 2026-11-23): disputed results are never deleted.
        h = info.get(url); r = rinfo.get(url)
        if _fail(h) and _fail(r): return True
        if h is None and _hard(r): return True
        if r is None and _hard(h): return True
        return False
    RANK = {'smooth': 0, 'ok': 1, 'buffering': 2}
    def rank_of(url, inf=''):
        if 'http-user-agent' in inf:
            s0 = info.get(url)
            if s0 is None or s0['status'] != 'pass': return 3
        s = info.get(url)
        if s is None: return 4
        if s['status'] != 'pass':
            r = rinfo.get(url)
            return 3 if (r is not None and r['status'] == 'pass') else 9
        v = s.get('verdict') or ''
        if v in RANK: return RANK[v]
        if v.startswith('play-error'): return 3
        return 2
    for g in list(groups):
        entries = groups[g]
        buckets = {}
        order = []
        for inf, url in entries:
            if 'http-user-agent' not in inf and agreed_dead(url): continue
            k = norm(name_of(inf))
            if k not in buckets: buckets[k] = []; order.append(k)
            buckets[k].append((rank_of(url, inf), inf, url))
        kept = []
        for k in order:
            b = sorted(buckets[k], key=lambda x: x[0])
            reported = [x for x in b if x[0] != 4]
            if reported and all(x[0] > 2 for x in reported) and not any(x[0] == 4 for x in b):
                pe = [x for x in b if x[0] == 3]
                if pe: kept.append((pe[0][1], pe[0][2]))
                continue
            kept.extend((inf, url) for _, inf, url in b[:3])
        groups[g] = kept
out=['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml"']
counts={}
for g in ORDER:
    if not groups[g]: continue
    counts[g]=len(groups[g])
    for inf,url in groups[g]: out.append(inf); out.append(url)
open(os.path.join(BASE, 'huaren-live.m3u'),'w',encoding='utf-8').write('\n'.join(out)+'\n')
rep={'total_in':total_in,'counts':counts,'total_out':sum(counts.values())}
json.dump(rep, open(os.path.join(BASE, 'build-report.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False))
