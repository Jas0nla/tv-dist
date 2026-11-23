#!/usr/bin/env python3
"""v2.1: merge maintained sources, regroup cleanly (no orphan groups), dedupe, cap 3 lines/channel, apply blacklist. No stream testing here."""
import urllib.request, ssl, sys, json, re, os
BASE = os.path.dirname(os.path.abspath(__file__))
ctx = ssl.create_default_context()
UA = {'User-Agent':'Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36'}
def fetch(url):
    import time
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=60, context=ctx).read().decode('utf-8','ignore').splitlines()
        except Exception as e:
            last = e; time.sleep(2 * (attempt + 1))
    raise last
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
 'https://iptv-org.github.io/iptv/countries/us.m3u',
 'https://iptv-org.github.io/iptv/countries/ca.m3u',
 'https://iptv-org.github.io/iptv/categories/news.m3u',
]
FORCED = {
 'https://iptv-org.github.io/iptv/countries/au.m3u': '澳新',
 'https://iptv-org.github.io/iptv/countries/nz.m3u': '澳新',
 'https://iptv-org.github.io/iptv/countries/jp.m3u': '日本',
 'https://iptv-org.github.io/iptv/countries/th.m3u': '泰国',
 'https://iptv-org.github.io/iptv/countries/us.m3u': '美加',
 'https://iptv-org.github.io/iptv/countries/ca.m3u': '美加',
 'https://iptv-org.github.io/iptv/categories/news.m3u': '世界新闻',
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
    if re.search(r'新闻|新聞|资讯|資訊|财经|財經|News', t):
        if re.search(r'(?i)CNN|BBC|NHK|DW|France ?24|Al ?Jazeera|Bloomberg|CNBC|Fox News|Sky News|Euronews|ABC News|CBC|NBC News|Newsmax|RT News|WION|NDTV|Times Now|Arirang|CNA|寰宇', n) or not re.search(r'[\u4e00-\u9fff]', n): return '世界新闻'
        return '大陆新闻'
    if re.search(r'综艺|綜藝|娱乐|娛樂|音乐|音樂|戏曲|戲曲|时尚|時尚|生活|旅游|旅遊|美食|健康|养生|養生|女性|都市频道|都市頻道', t): return '综艺生活'
    if re.search(r'地方|本地|市台|新闻综合|新聞綜合|公共频道|公共頻道|经济科教|經濟科教|影视频道|都市|民生', t): return '地方台'
    if not re.search(r'[\u4e00-\u9fff]', n): return '国际'
    return '综合'
ORDER=['4K超高清','香港','台湾','央视','卫视','新马','电影','体育','少儿动漫','大陆新闻','世界新闻','纪录科教','综艺生活','地方台','国际','澳新','日本','泰国','美加','综合']
USCA_KEEP = re.compile(r'(?i)Pluto|Roku Channel|Xumo|Tubi|Samsung TV|LG Channels|Plex|Stirr|Freevee|Redbox|CNN|Fox News|Fox Sports|FS1|FS2|MSNBC|CNBC|Bloomberg|ABC News|CBS News|NBC News|Newsmax|Weather Channel|ESPN|NFL Network|NBA TV|MLB Network|NHL Network|Golf Channel|Tennis Channel|AMC|FX |FXX|Paramount|Comedy Central|MTV|VH1|BET|Nickelodeon|Nick Jr|Cartoon Network|Disney|Discovery|History|A&E|Lifetime|Hallmark|Turner Classic|Bravo|Oxygen|Syfy|TNT|TBS|USA Network|National Geographic|Nat Geo|Animal Planet|HGTV|Food Network|TLC|Travel Channel|BBC America|Sundance|Showtime|Starz|PBS|The CW|MeTV|Court TV|CTV|CBC|Global News|Global TV|Citytv|CP24|TSN|Sportsnet|TVA|Noovo|ICI |OMNI|Fairchild|Talentvision|CHCH|BNN|Much')
FAMOUS_NEWS = re.compile(r'(?i)Al ?Jazeera|Aljazeera|半岛|BBC World|BBC News|CNN|Deutsche Welle|DW News|DW English|DW Deutsch|DW Latino|DW Arabic|France 24|NHK World|TRT World|Euronews|Sky News|RT News|Russia Today|WION|NDTV|CNA|Arirang|KBS World|Bloomberg|CNBC|Fox News|MSNBC|ABC News|CBS News|NBC News|GB News|India Today|Times Now')
DROP_NAME = re.compile(r'(?i)arabia|arabic|mubasher|阿拉伯')
def dropped(n):
    if DROP_NAME.search(n): return True
    if re.match(r'(?i)Al Jazeera(?! English)', n): return True
    return False
FILTERS = {
 'https://iptv-org.github.io/iptv/countries/us.m3u': USCA_KEEP,
 'https://iptv-org.github.io/iptv/countries/ca.m3u': USCA_KEEP,
 'https://iptv-org.github.io/iptv/categories/news.m3u': FAMOUS_NEWS,
}
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
        n=name_of(inf)
        if dropped(n): continue
        if u in FILTERS and not FILTERS[u].search(n): continue
        g=FORCED.get(u) or classify(n, hint_of(inf))
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
            if s0 is None or s0['status'] != 'pass':
                r0 = rinfo.get(url)
                if r0 is not None and r0['status'] == 'pass':
                    v0 = r0.get('verdict') or ''
                    if v0 in RANK: return RANK[v0]
                    return 2
                if r0 is not None: return 8
                return 3
        s = info.get(url)
        if s is None:
            # no home data: fall back to the runner report for ORDER only
            # (deletion still requires agreed_dead; soft runner fails rank 3)
            r = rinfo.get(url)
            if r is None: return 4
            if r['status'] != 'pass': return 3
            v = r.get('verdict') or ''
            if v in RANK: return RANK[v]
            if v.startswith('play-error'): return 3
            return 2
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
        chans = []
        for idx, k in enumerate(order):
            b = sorted(buckets[k], key=lambda x: x[0])
            has_home = any(u in info for _, _, u in b)
            reported = [x for x in b if x[0] != 4]
            if has_home and reported and all(x[0] > 2 for x in reported) and not any(x[0] == 4 for x in b):
                pe = [x for x in b if x[0] == 3]
                ent = [(pe[0][1], pe[0][2])] if pe else []
            else:
                ent = [(inf, url) for _, inf, url in b[:3]]
            if ent:
                chans.append((min(x[0] for x in b), idx, ent))
        # channels ordered by their best line's rank (smooth first), stable on ties
        chans.sort(key=lambda c: (c[0], c[1]))
        groups[g] = [e for _, _, ent in chans for e in ent]
# --- Taiwan relay injection ---
# Channels geo-blocked from the US but verified playable through the home
# Raspberry Pi relay (Pi -> West World Taiwan exit). Relay lines replace the
# direct entries for the same channels and lead the Taiwan group.
import base64 as _b64
RELAY_BASE = 'http://192.168.216.88:8899/tw/j99zzuJ1NGaHW27i'
RELAY_CHANNELS = [
    ('TVBS新闻台', 'http://61.221.215.25:8800/hls/9/index.m3u8'),
    ('纬来精采', 'http://61.221.215.25:8800/hls/48/index.m3u8'),
    ('东森超视', 'http://38.64.72.148:80/hls/modn/list/2013/chunklist1.m3u8'),
    ('TVBS亚洲', 'http://38.64.72.148/hls/modn/list/4005/chunklist0.m3u8'),
    ('TVBS亚洲', 'http://38.64.72.148:80/hls/modn/list/4005/playlist.m3u8'),
    ('纬来体育', 'https://epg.pw/stream/8855a9936e37e608a0ec8a014cce1673dee9c5d68d560da376cc92e5edef2b25.m3u8'),
    ('纬来体育', 'https://epg.pw/stream/ab6df63b64d0cc44a1f4f029ed847a26fa54a7aebd455578fb05a63f02c22f4b.m3u8'),
    ('台视新闻', 'http://38.64.72.148/hls/modn/list/4013/chunklist1.m3u8'),
    ('三立戏剧', 'http://61.221.215.25:8800/hls/41/index.m3u8'),
]
RELAY_NAMES = {norm(n) for n, _ in RELAY_CHANNELS} | {norm('TVBS-Asia (1080p)')}
def _relay_url(origin):
    return RELAY_BASE + '/' + _b64.urlsafe_b64encode(origin.encode()).decode().rstrip('=')
if '台湾' in groups:
    groups['台湾'] = [(inf, url) for inf, url in groups['台湾'] if norm(name_of(inf)) not in RELAY_NAMES]
    relay_entries = [('#EXTINF:-1 group-title="台湾",%s' % n, _relay_url(u)) for n, u in RELAY_CHANNELS]
    groups['台湾'] = relay_entries + groups['台湾']
# --- Extra verified Taiwan lines (2026-11-23 source hunt) ---
# Tested from the Pi on the home network AND via the Taiwan exit: all play
# DIRECTLY from home (no relay needed). Injected after the relay block so
# report-based pruning can never drop them; check_live.py PRUNE protects
# these hosts as well. The cnlive key (?q=...) is a static relay key from
# the source lists; if it rotates, re-hunt and update here.
EXTRA_TW = [
    ('民视新闻', 'http://4gtv.cnlive.club/channel/nca14742/index.m3u8?q=1784702901150'),
    ('民视第一台', 'http://4gtv.cnlive.club/channel/nc56ba28/index.m3u8?q=1784702901150'),
    ('民视台湾台', 'http://4gtv.cnlive.club/channel/nce5d867/index.m3u8?q=1784702901150'),
    ('民视综合', 'http://211.72.174.95:8115/0.ts'),
    ('中天新闻', 'http://4gtv.cnlive.club/channel/3824d067/index.m3u8?q=1784702901150'),
    ('中视新闻', 'http://4gtv.cnlive.club/channel/7e6461d6/index.m3u8?q=1784702901150'),
    ('华视', 'http://4gtv.cnlive.club/channel/n721fc25a/index.m3u8?q=1784702901150'),
    ('华视新闻', 'http://4gtv.cnlive.club/channel/n692bc32c/index.m3u8?q=1784702901150'),
    ('东森新闻', 'http://4gtv.cnlive.club/channel/n5ca63a3a/index.m3u8?q=1784702901150'),
    ('三立新闻', 'http://4gtv.cnlive.club/channel/4fa717ad/index.m3u8?q=1784702901150'),
    ('三立综合', 'http://4gtv.cnlive.club/channel/45c7d3e3/index.m3u8?q=1784702901150'),
    ('公视', 'http://211.72.174.95:8116/0.ts'),
    ('TVBS欢乐', 'http://4gtv.cnlive.club/channel/498f035d/index.m3u8?q=1784702901150'),
]
# YouTube official 24h live streams, resolved on demand by the Pi relay
# (/yt/ route, yt-dlp). Backup lines for news channels + 镜新闻 (YT-only).
_YT_BASE = 'http://192.168.216.88:8899/yt/' + RELAY_BASE.split('/tw/')[1]
EXTRA_YT = [
    ('镜新闻', '5n0y6b0Q25o'),
    ('民视新闻', 'ylYJSBUgaMA'),
    ('三立新闻', 'yeYC0mbSIOo'),
    ('华视新闻', 'wM0g8EoUZ_E'),
    ('中视新闻', 'TCnaIE_SAtM'),
]
if '台湾' in groups:
    _have = {u for _, u in groups['台湾']}
    _extra = [('#EXTINF:-1 group-title="台湾",%s' % n, u) for n, u in EXTRA_TW if u not in _have]
    _extra += [('#EXTINF:-1 group-title="台湾",%s' % n, _YT_BASE + '/' + v) for n, v in EXTRA_YT if (_YT_BASE + '/' + v) not in _have]
    _cut = len(RELAY_CHANNELS)
    groups['台湾'] = groups['台湾'][:_cut] + _extra + groups['台湾'][_cut:]
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
