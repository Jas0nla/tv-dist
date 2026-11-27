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
    # curl fallback (2026-11-25): GitHub Pages truncates urllib reads
    # (IncompleteRead) on the big iptv-org files while curl gets them
    # whole; without this the US/CA/AU/TH/news sources silently vanish
    # from the build (total_out dropped 973 -> 526 before this fix).
    import subprocess
    for attempt in range(2):
        try:
            r = subprocess.run(['curl', '-fsSL', '--max-time', '90', '-A', UA['User-Agent'], url],
                               capture_output=True, timeout=100)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode('utf-8', 'ignore').splitlines()
            last = RuntimeError('curl rc=%d' % r.returncode)
        except Exception as e:
            last = e
        time.sleep(2)
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
PROV=re.compile(r'北京|天津|上海|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|广西|海南|四川|贵州|云南|陕西|甘肃|青海|内蒙古|新疆|西藏|宁夏|广州|深圳|苏州|杭州|南京|武汉|成都|西安|长沙|郑州|济南|沈阳|哈尔滨|长春|昆明|贵阳|南宁|海口|兰州|西宁|银川|呼和浩特|乌鲁木齐|拉萨|合肥|福州|南昌|石家庄|太原|宁波|大连|青岛|厦门|邯郸|邢台|衡水')
FOURK=re.compile(r'(?i)4K|UHD|2160|超高清')
def classify(n, hint):
    t=n+' '+hint
    if FOURK.search(n): return '4K超高清'
    if TW.search(n): return '台湾'
    if HK.search(n): return '香港'
    if re.search(r'CCTV|央视|央視|CGTN|央视频|央視頻|中央电视台|中央電視台', t): return '央视'
    if SGMY.search(n): return '新马'
    if re.search(r'卫视|衛視', t): return '卫视'
    if re.search(r'电影|電影|影院|影视频道|影視|Movie|美亚|美亞', t): return '电影'
    if re.search(r'体育|體育|足球|篮球|籃球|赛事|賽事|Sports|ESPN|五星体育', t): return '体育'
    if re.search(r'少儿|少兒|卡通|动漫|動漫|动画|動畫|宝宝|寶貝|Kids|金鹰卡通|优漫', t): return '少儿动漫'
    if PROV.search(n): return '地方台'
    if re.search(r'纪录|紀錄|科教|探索|Discovery|地理|纪实|紀實|求索|世界地理', t): return '纪录科教'
    if re.search(r'新闻|新聞|资讯|資訊|财经|財經|News', t):
        if re.search(r'(?i)CNN|BBC|NHK|DW|France ?24|Al ?Jazeera|Bloomberg|CNBC|Fox News|Sky News|Euronews|ABC News|CBC|NBC News|Newsmax|RT News|WION|NDTV|Times Now|Arirang|CNA|寰宇', n) or not re.search(r'[\u4e00-\u9fff]', n): return '世界新闻'
        return '大陆新闻'
    if re.search(r'综艺|綜藝|娱乐|娛樂|音乐|音樂|戏曲|戲曲|时尚|時尚|生活|旅游|旅遊|美食|健康|养生|養生|女性|都市频道|都市頻道', t): return '综艺生活'
    if re.search(r'地方|本地|市台|新闻综合|新聞綜合|公共频道|公共頻道|经济科教|經濟科教|影视频道|都市|民生', t) or re.search(r'(综合|公共|电视台|電視台|综合频道|綜合頻道)$', n): return '地方台'
    if not re.search(r'[\u4e00-\u9fff]', n): return '国际'
    return '综合'
ORDER=['4K超高清','香港','台湾','央视','卫视','新马','电影','体育','少儿动漫','大陆新闻','世界新闻','纪录科教','综艺生活','地方台','国际','澳新','日本','泰国','加拿大','美国新闻','美国体育','美国影视','美国少儿','美国综合','美加','点播轮播','综合']
USCA_KEEP = re.compile(r'(?i)Pluto|Roku Channel|Xumo|Tubi|Samsung TV|LG Channels|Plex|Stirr|Freevee|Redbox|CNN|Fox News|Fox Sports|FS1|FS2|MSNBC|CNBC|Bloomberg|ABC News|CBS News|NBC News|Newsmax|Weather Channel|ESPN|NFL Network|NBA TV|MLB Network|NHL Network|Golf Channel|Tennis Channel|AMC|FX |FXX|Paramount|Comedy Central|MTV|VH1|BET|Nickelodeon|Nick Jr|Cartoon Network|Disney|Discovery|History|A&E|Lifetime|Hallmark|Turner Classic|Bravo|Oxygen|Syfy|TNT|TBS|USA Network|National Geographic|Nat Geo|Animal Planet|HGTV|Food Network|TLC|Travel Channel|BBC America|Sundance|Showtime|Starz|PBS|The CW|MeTV|Court TV|CTV|CBC|Global News|Global TV|Citytv|CP24|TSN|Sportsnet|TVA|Noovo|ICI |OMNI|Fairchild|Talentvision|CHCH|BNN|Much')
FAMOUS_NEWS = re.compile(r'(?i)Al ?Jazeera|Aljazeera|半岛|BBC World|BBC News|CNN|Deutsche Welle|DW News|DW English|DW Deutsch|DW Latino|DW Arabic|France 24|NHK World|TRT World|Euronews|Sky News|RT News|Russia Today|WION|NDTV|CNA|Arirang|KBS World|Bloomberg|CNBC|Fox News|MSNBC|ABC News|CBS News|NBC News|GB News|India Today|Times Now')
DROP_NAME = re.compile(r'(?i)arabia|arabic|mubasher|阿拉伯')
def dropped(n):
    if DROP_NAME.search(n): return True
    if re.match(r'(?i)Al Jazeera(?! English)', n): return True
    return False
# --- Junk filter (2026-11-24, user-approved): test cards / promo entries are
# not TV channels. Name patterns catch test/promo-named entries; URL patterns
# catch proxies verified to serve test-card playlists instead of the named
# channel (goodiptv.club/douyu/* was verified 2026-11-24 to serve the
# feiyang666999 testvideo playlist for every room). Liveness checks cannot
# catch these: the streams play fine, the content is wrong.
JUNK_NAME = re.compile(r'(?i)测试源|測試源|测试台|測試台|测试频道|測試頻道|测试图|測試圖|彩条|彩條|肥羊|扫码|掃碼|交流群|test\s*(channel|pattern|signal)|\btest\s*tv\b')
JUNK_URL = re.compile(r'(?i)goodiptv\.club/douyu/|feiyang666999|/testvideo/|4gtv\.cnlive\.club')
# --- VOD / loop split (2026-11-24, user): single-drama loops and recorded
# galas (kwimgs recordings, huya/yy loop rooms via ottiptv/metshop) are not
# live TV. They get their own group instead of polluting the fallback group.
# jdshipin is NOT in this list: its /TVOD/ path also carries live channels
# (HOY, ViuTV), so it stays with the classifier.
VOD_NAME = re.compile(r'春晚')
VOD_URL = re.compile(r'(?i)kwimgs\.com|ottiptv\.cc|metshop\.top')
FILTERS = {
 'https://iptv-org.github.io/iptv/countries/us.m3u': USCA_KEEP,
 'https://iptv-org.github.io/iptv/countries/ca.m3u': USCA_KEEP,
 'https://iptv-org.github.io/iptv/categories/news.m3u': FAMOUS_NEWS,
}
seen=set(); per_name={}; groups={g:[] for g in ORDER}
SRC_PROV={}
total_in=0; junk_filtered=0
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
        if JUNK_NAME.search(n) or JUNK_URL.search(url):
            junk_filtered+=1; continue
        if u in FILTERS and not FILTERS[u].search(n): continue
        if u not in FORCED and (VOD_NAME.search(n) or VOD_URL.search(url)):
            g='点播轮播'
        else:
            g=FORCED.get(u) or classify(n, hint_of(inf))
        key=(g,norm(n))
        if per_name.get(key,0)>=3: continue
        per_name[key]=per_name.get(key,0)+1
        inf2=re.sub(r'group-title="[^"]*"', f'group-title="{g}"', inf) if 'group-title="' in inf else (inf.replace('#EXTINF:-1 ', f'#EXTINF:-1 group-title="{g}" ',1) if inf.startswith('#EXTINF:-1 ') else inf)
        groups[g].append((inf2,url))
        SRC_PROV.setdefault(url, '源表：'+u)
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
# --- Taiwan hybrid injection ---
# 2026-11-23 retest from the Pi: all 9 upstreams play DIRECTLY from the US
# home IP (playlist + segments verified; the earlier geo-block attribution
# was wrong). Each channel therefore gets the direct line FIRST and the Pi
# relay line (Pi -> West World Taiwan exit) SECOND as fallback, in case an
# upstream ever starts geo-locking or the direct path dies. These entries
# replace any source-list entries for the same channels and lead the group.
import base64 as _b64
RELAY_BASE = 'http://192.168.216.88:8899/tw/UnyixzLPyFFocqnxQgzL9-65PrGaHSDR'
RELAY_CHANNELS = [
    # TVBS新闻台 removed 2026-11-26: 61.221.215.25/hls/9 verified a frozen 2025-03 recording loop (MEDIA-SEQUENCE stuck at 38); TVBS now comes from EXTRA_YT below.
    ('纬来精采', 'http://61.221.215.25:8800/hls/48/index.m3u8'),
    ('东森超视', 'http://38.64.72.148:80/hls/modn/list/2013/chunklist1.m3u8'),
    ('TVBS亚洲', 'http://38.64.72.148/hls/modn/list/4005/chunklist0.m3u8'),
    ('TVBS亚洲', 'http://38.64.72.148:80/hls/modn/list/4005/playlist.m3u8'),
    # 纬来体育 2026-11-26: both epg.pw lines verified nosignal placeholders; replaced with frame-verified 1080p direct line (F1 live, Videoland Sports HD logo).
    ('纬来体育', 'http://50.7.233.114:8278/videolandsport/playlist.m3u8'),
    ('台视新闻', 'http://38.64.72.148/hls/modn/list/4013/chunklist1.m3u8'),
    ('三立戏剧', 'http://61.221.215.25:8800/hls/41/index.m3u8'),
]
RELAY_NAMES = {norm(n) for n, _ in RELAY_CHANNELS} | {norm('TVBS-Asia (1080p)')}
def _relay_url(origin):
    return RELAY_BASE + '/' + _b64.urlsafe_b64encode(origin.encode()).decode().rstrip('=')
if '台湾' in groups:
    groups['台湾'] = [(inf, url) for inf, url in groups['台湾'] if norm(name_of(inf)) not in RELAY_NAMES]
    hybrid_entries = []
    for n, u in RELAY_CHANNELS:
        hybrid_entries.append(('#EXTINF:-1 group-title="台湾",%s' % n, u))
        hybrid_entries.append(('#EXTINF:-1 group-title="台湾",%s' % n, _relay_url(u)))
        SRC_PROV.setdefault(u, '台湾上游直连（硬编码）')
        SRC_PROV.setdefault(_relay_url(u), 'Pi中继（西部世界台湾出口）')
    groups['台湾'] = hybrid_entries + groups['台湾']
# --- Extra verified Taiwan lines (2026-11-23 source hunt) ---
# Tested from the Pi on the home network AND via the Taiwan exit: all play
# DIRECTLY from home (no relay needed). Injected after the relay block so
# report-based pruning can never drop them; check_live.py PRUNE protects
# these hosts as well. The cnlive key (?q=...) is a static relay key from
# the source lists; if it rotates, re-hunt and update here.
EXTRA_TW = [
    # 2026-11-26 audit: all five ChiSheng9 TVxx lines removed - nested lists contain YouTube watch-page URLs, not streams (dead). 三立/中视/华视/民视 are covered by EXTRA_YT relay slugs (setn/ctv/cts/ftv); 东森财经新闻 has no verified replacement yet. ChiSheng9 URLs are blacklisted below.
    # All 11 4gtv.cnlive.club lines were REMOVED 2026-11-24: verified the
    # same evening that every one of them now serves a two-segment static
    # app-download ad loop (t2.live2.dpdns.org/static/sailei.*.ts) instead of
    # the named channel. 民视新闻/三立新闻/华视新闻/中视新闻 still have their
    # YouTube lines below; the rest fall back to source-list lines.
    ('民视综合', 'http://211.72.174.95:8115/0.ts'),
    ('公视', 'http://211.72.174.95:8116/0.ts'),
]
# YouTube official 24h live streams, CHANNEL-based since 2026-11-25:
# the Pi relay resolves each channel's current /live at request time
# (yt-dlp) and proxies the stream itself, so rotating live IDs and the
# TV's direct-connect IPv6 fallback problem no longer break these lines.
# Values are relay slugs (see CHANNELS in relay.py on the Pi). All ten
# Taiwan news channels are covered; 东森/中天/公视 are YouTube-only here
# (their old fixed video IDs were verified dead 2026-11-24).
_YT_BASE = 'http://192.168.216.88:8899/yt/' + RELAY_BASE.split('/tw/')[1]
EXTRA_YT = [
    ('东森新闻', 'ebc'),
    ('中天新闻', 'cti'),
    ('公视新闻', 'pts'),
    ('镜新闻', 'mnews'),
    ('民视新闻', 'ftv'),
    ('三立新闻', 'setn'),
    ('华视新闻', 'cts'),
    ('中视新闻', 'ctv'),
    ('TVBS新闻台', 'tvbs'),
    ('台视新闻', 'ttv'),
]
def _yt_url(slug):
    return _YT_BASE + '/live/' + slug
if '台湾' in groups:
    _have = {u for _, u in groups['台湾']}
    _extra = [('#EXTINF:-1 group-title="台湾",%s' % n, u) for n, u in EXTRA_TW if u not in _have]
    _extra += [('#EXTINF:-1 group-title="台湾",%s' % n, _yt_url(v)) for n, v in EXTRA_YT if _yt_url(v) not in _have]
    for _n, _u in EXTRA_TW: SRC_PROV.setdefault(_u, 'EXTRA_TW（硬编码验通线）')
    for _n, _v in EXTRA_YT: SRC_PROV.setdefault(_yt_url(_v), 'YouTube官方直播（Pi中继频道制 /yt/live/ 解析+代理）')
    _cut = len(RELAY_CHANNELS) * 2
    groups['台湾'] = groups['台湾'][:_cut] + _extra + groups['台湾'][_cut:]

# --- Extra verified HK lines (2026-11-24 source hunt, home-verified) ---
# Same replace-treatment as the relay block: drop same-name source lines in
# the HK group, then prepend these, so per-channel counts stay clean.
EXTRA_HK = [
    ('翡翠台', 'http://r.jdshipin.com/GeWKr'),
    ('翡翠台', 'http://php.jdshipin.com:8880/TVOD/iptv.php?id=fct4'),
    ('翡翠台', 'http://120.198.95.220:9901/tsfile/live/1004_1.m3u8?key=txiptv'),
    ('无线新闻台', 'https://cdn.haititivi.com/website/haitinews/index.m3u8'),
    ('凤凰中文', 'https://playtv-live.ifeng.com/live/06OLEGEGM4G.m3u8'),
    ('凤凰中文', 'http://playtv-live.ifeng.com:80/live/06OLEGEGM4G.m3u8'),
    ('凤凰资讯', 'http://221.7.175.154:8445/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('凤凰资讯', 'https://playtv-live.ifeng.com/live/06OLEEWQKN4.m3u8'),
    ('凤凰卫视', 'http://221.7.175.154:8445/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0'),
    ('凤凰卫视', 'http://221.7.175.154:8445/tsfile/live/1020_1.m3u8'),
]
if '香港' in groups:
    _hk_names = {norm(n) for n, _ in EXTRA_HK}
    groups['香港'] = [(inf, url) for inf, url in groups['香港'] if norm(name_of(inf)) not in _hk_names]
    _have_hk = {u for _, u in groups['香港']}
    _extra_hk = [('#EXTINF:-1 group-title="香港",%s' % n, u) for n, u in EXTRA_HK if u not in _have_hk]
    groups['香港'] = _extra_hk + groups['香港']
    for _n, _u in EXTRA_HK: SRC_PROV.setdefault(_u, 'EXTRA_HK（硬编码验通线）')
# --- YueChan 4K lines (2026-11-24): ffprobe-verified before inclusion;
# names that measured below 4K were renamed honestly above at patch time.
EXTRA_4K = [

]
for _n, _u in EXTRA_4K:
    _g = classify(_n, '')
    if any(_u == uu for _, uu in groups[_g]): continue
    groups[_g].insert(0, ('#EXTINF:-1 group-title="%s",%s' % (_g, _n), _u))

# --- US/CA split (2026-11-25, user): the merged 美加 group (~300 lines from
# the iptv-org US+CA country lists) is too big to browse, so it is split by
# deterministic name rules into 加拿大 + five US groups. Canada is checked
# first: Canadian brands (CBC/CTV/TVA/TSN/...) and the iptv-org ' CA'
# Canadian-feed suffix go to 加拿大 even when the content is sports/kids.
# 'CTV (United States)' is a self-contradictory source label: it is NOT
# forced into 加拿大 and falls through to 美国综合. US rules run
# news -> sports -> kids -> entertainment; Pluto FAST channels follow their
# content brand, except the documentary-style Pluto channels (History /
# Military / Science / Sanctuary / Misterios Medicos / Lives) which land in
# 美国综合 together with PBS, local stations and the Discovery/HGTV/Food /
# History families. Anything unclaimed lands in 美国综合. Other groups are
# untouched; the per-channel cap was already applied on the merged group,
# so it still holds inside every subgroup.
CA_BRAND = re.compile(r'(?i)CBC|Radio-Canada|Ici RDI|\bRDI\b|\bTVA\b|CP24|\bBNN\b|\bTSN|Sportsnet|Fairchild|Talentvision|\bOMNI\b')
USCA_PLUTO_DOCU = re.compile(r'(?i)Pluto TV (History|Military|Science|Sanctuary|Misterios Medicos|Lives)\b')
def _usca_split(name):
    cleaned = re.sub(r'\[[^\]]*\]', '', name)
    cleaned = re.sub(r'\(\d{3,4}p\)', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # --- Canada ---
    if re.search(r'\bCTV\b', cleaned) and '(United States)' in cleaned:
        pass  # contradictory label: do not hard-assign to Canada
    elif re.search(r'\sCA$', cleaned) or CA_BRAND.search(cleaned) or re.search(r'(?i)\bCTV\b', cleaned):
        return '加拿大'
    # --- US ---
    if re.search(r'(?i)ABC News|CBS News|NBC News|CNN|Fox News|MSNBC|CNBC|Bloomberg|Newsmax|Weather Channel|Fox Weather', cleaned): return '美国新闻'
    if re.search(r'(?i)ESPN|Fox Sports|Golf Channel|NBA TV|NFL Network|NHL Network|Tennis Channel|Snooker', cleaned): return '美国体育'
    if re.search(r'(?i)Cartoon Network|Disney|Nickelodeon|Nick Jr|PBS Kids|Reino Infantil|Retro Kid|MeTV Toons|Kids & Family|Family Zone', cleaned): return '美国少儿'
    if USCA_PLUTO_DOCU.search(cleaned): return '美国综合'
    if re.search(r'(?i)A&E|\bAMC\b|\bBET\b|Bravo|Comedy Central|Hallmark|Lifetime|Logo|\bMTV\b|\bVH1\b|Paramount|SYFY|Showtime|Starz|\bTBS\b|TNT(?! Sports)|USA Network|RCTV|Pluto|Spike|\bFX\b|FXX|FXM', cleaned): return '美国影视'
    return '美国综合'
if groups.get('美加'):
    _split = {g: [] for g in ('加拿大', '美国新闻', '美国体育', '美国影视', '美国少儿', '美国综合')}
    for inf, url in groups['美加']:
        g = _usca_split(name_of(inf))
        _split[g].append((re.sub(r'group-title="[^"]*"', f'group-title="{g}"', inf), url))
    for g, entries in _split.items():
        groups[g] = entries
    groups['美加'] = []

# --- Resolution labels (2026-11-24, user): every channel name carries a
# resolution suffix like " (1080P)". Source of truth is the probe map
# resolutions.json (ffprobe-measured heights; see probe_resolutions.py);
# fallback is a quality marker already present in the source name/tvg-id.
# Lines with neither stay unlabelled rather than guessed. Note some lines
# marketed as 4K measure at 1080P; the label always shows the measured value.
RES_MAP={}
try: RES_MAP={k: int(v) for k, v in json.load(open(os.path.join(BASE, 'resolutions.json'))).items()}
except Exception: RES_MAP={}
def _res_of(url):
    h=RES_MAP.get(url)
    if h: return h
    m=re.search(r'192\.168\.216\.88:8899/tw/[^/]+/([A-Za-z0-9_-]+)$', url)
    if m:
        try:
            origin=_b64.urlsafe_b64decode(m.group(1) + '=' * (-len(m.group(1)) % 4)).decode()
            return RES_MAP.get(origin)
        except Exception:
            return None
    return None
def _label_for(name, inf, url):
    h=_res_of(url)
    if h:
        if h>=2000: return '4K'
        if h>=1000: return '1080P'
        if h>=700: return '720P'
        return 'SD'
    t=name+' '+inf
    if re.search(r'(?i)4k|uhd|2160|超高清', t): return '4K'
    if re.search(r'(?i)1080|fhd', t): return '1080P'
    if re.search(r'(?i)720', t): return '720P'
    if re.search(r'(?i)@sd|\bsd\b|480|标清|標清', t): return 'SD'
    if re.search(r'(?i)@hd|\bhd\b|高清', t): return 'HD'
    return None
_QTAIL=re.compile(r'[\s\-_·]*(?:\(\s*(?:4k|uhd|fhd|hd|sd|2160p?|1080p?|720p?|480p?)\s*\)|4k|uhd|fhd|hd|sd|2160p|1080p|720p|480p|高清|超清|标清|藍光|蓝光)\s*$', re.I)
def _src_tag(url):
    # Source tags (2026-11-25, user): YouTube-sourced lines carry
    # " - YouTube"; lines served via the Pi relay carry " - Pi". A relayed
    # YouTube line carries only " - YouTube" (source beats transport).
    if '/yt/' in url or 'youtube.com' in url or 'youtu.be' in url: return ' - YouTube'
    if '192.168.216.88' in url: return ' - Pi'
    return ''
def with_res(inf, url):
    if ',' not in inf: return inf
    head, name = inf.rsplit(',', 1)
    name = name.strip()
    if not name: return inf
    label = _label_for(name, inf, url)
    base = name
    while True:
        b2 = _QTAIL.sub('', base).strip()
        if b2 == base or not b2: break
        base = b2
    if not base: base = name
    return head + ',' + base + _src_tag(url) + (f' ({label})' if label else '')

# --- Merge rebuild (2026-11-25, user-approved): fix the audit's 22 clear
# mis-groups, then keep exactly ONE line per channel across the whole
# table. Winner priority: home-verified (home-verified.json) > measured
# resolution (resolutions.json + probe ledger) > build order. Losers are
# not deleted: they are written to backup-pool.json with provenance,
# measured status and the reason they lost, so a dead main line can be
# swapped from the pool. Red line: a channel whose lines are all
# unmeasured still keeps one line -- unmeasured is not dead.
import urllib.parse as _up
def _canon(u):
    try:
        p = _up.urlsplit(u)
        net = p.hostname or ''
        if p.port and not ((p.scheme == 'http' and p.port == 80) or (p.scheme == 'https' and p.port == 443)):
            net += ':%d' % p.port
        return _up.urlunsplit((p.scheme, net, p.path, p.query, ''))
    except Exception:
        return u
HOME_OK = set()
try:
    for _e in json.load(open(os.path.join(BASE, 'home-verified.json'))):
        HOME_OK.add(_e['url']); HOME_OK.add(_canon(_e['url']))
except Exception:
    pass
PROBE_H = {}
try:
    for _l in open(os.path.join(BASE, 'resolution-probe-20261124.jsonl'), encoding='utf-8'):
        _l = _l.strip()
        if not _l: continue
        _r = json.loads(_l)
        if _r.get('ok') and _r.get('height'):
            PROBE_H[_r['url']] = int(_r['height'])
            if _r.get('store_key'): PROBE_H[_r['store_key']] = int(_r['height'])
except Exception:
    pass
_TW_RE = re.compile(r'192\.168\.216\.88:8899/tw/[^/]+/([A-Za-z0-9_-]+)$')
def _origin_of(url):
    m = _TW_RE.search(url)
    if not m: return None
    try: return _b64.urlsafe_b64decode(m.group(1) + '=' * (-len(m.group(1)) % 4)).decode()
    except Exception: return None
def _height_of(url):
    h = _res_of(url)
    if h: return h
    if url in PROBE_H: return PROBE_H[url]
    o = _origin_of(url)
    return PROBE_H.get(o) if o else None
def _home_ok(url):
    if url in HOME_OK or _canon(url) in HOME_OK: return True
    o = _origin_of(url)
    return bool(o) and (o in HOME_OK or _canon(o) in HOME_OK)
FIX_MOVES = []
def _move(name_norms, from_g, to_g):
    if from_g not in groups or to_g not in groups: return
    keep, moved = [], []
    for inf, url in groups[from_g]:
        if norm(name_of(inf).replace('（', '(').replace('）', ')')) in name_norms:
            moved.append((re.sub(r'group-title="[^"]*"', 'group-title="%s"' % to_g, inf), url))
        else:
            keep.append((inf, url))
    if moved:
        groups[from_g] = keep
        groups[to_g].extend(moved)
        FIX_MOVES.append({'names': sorted(name_norms), 'from': from_g, 'to': to_g, 'moved': len(moved)})
if '4K超高清' in groups and '卫视' in groups:
    _keep, _moved = [], []
    for _inf, _url in groups['4K超高清']:
        _nm = name_of(_inf)
        if norm(_nm) == norm('东方卫视') and _label_for(_nm, _inf, _url) != '4K':
            _moved.append((re.sub(r'group-title="[^"]*"', 'group-title="卫视"', _inf), _url))
        else:
            _keep.append((_inf, _url))
    if _moved:
        groups['4K超高清'] = _keep; groups['卫视'].extend(_moved)
        FIX_MOVES.append({'names': ['东方卫视(非4K线)'], 'from': '4K超高清', 'to': '卫视', 'moved': len(_moved)})
_move({norm(x) for x in ('CHC家庭影院', 'CHC动作电影', 'CHC影迷电影')}, '央视', '电影')
_move({norm('CETV-1'), norm('CETV-3')}, '央视', '综合')
_move({norm('五星体育')}, '卫视', '体育')
_move({norm('ViuTV')}, '国际', '香港')
_move({norm('Channel U')}, '国际', '新马')
_move({norm(x) for x in ('RT Español', 'RT Français', 'RT DE', 'RT Balkan')}, '综合', '世界新闻')
_move({norm(x) for x in ('西游记', '水浒传', '笑傲江湖', '闯关东')}, '综合', '点播轮播')
# Radio Uno Tacna is a radio stream, not a TV channel; the audit offered
# "drop or 综合" -- moved to 综合 so no channel disappears from the table.
_move({norm('Radio Uno Tacna')}, '世界新闻', '综合')
BAD_LINES = {'http://211.72.174.95:8115/0.ts': '电视实测无声（HEVC 流），有替代线时降级'}
def _chkey(n):
    # Channel identity for the one-line rule: the repo norm() plus
    # full-width parens folded to half-width, so source suffixes like
    # （斗鱼）are stripped as decoration just like (1080p) is.
    return norm(n.replace('（', '(').replace('）', ')'))
_seq = 0; _cands = {}
for _g in ORDER:
    for _inf, _url in groups[_g]:
        _cands.setdefault(_chkey(name_of(_inf)), []).append((_seq, _g, _inf, _url))
        _seq += 1
_pre_channels = len(_cands)
_pre_counts = {g: len(groups[g]) for g in ORDER if groups[g]}
_pool = []; _winners = {}; _bad_kept = []
for _k, _lst in _cands.items():
    def _wkey(c):
        return (0 if _home_ok(c[3]) else 1, -(_height_of(c[3]) or 0), c[0])
    _elig = [c for c in _lst if c[3] not in BAD_LINES] or _lst
    _win = min(_elig, key=_wkey)
    _winners[_k] = _win
    if _win[3] in BAD_LINES: _bad_kept.append(_win[3])
    _wh = _height_of(_win[3])
    if _home_ok(_win[3]): _why = '家里验通优先'
    elif _wh: _why = '实测清晰度最高（%d）' % _wh
    else: _why = 'build 顺序靠前（同频道均未测/同高）'
    for _c in _lst:
        if _c is _win: continue
        _h = _height_of(_c[3])
        _reason = BAD_LINES.get(_c[3]) or ('同频道只留一条，胜出依据：' + _why)
        _pool.append({'channel': name_of(_c[2]), 'url': _c[3], 'group': _c[1],
                      'source': SRC_PROV.get(_c[3], '源表抓取'), 'height': _h,
                      'resolution': _label_for(name_of(_c[2]), _c[2], _c[3]),
                      'status': '家里验通' if _home_ok(_c[3]) else ('实测' if _h else '未测'),
                      'reason': _reason, 'winner_url': _win[3]})
_seq = 0
for _g in ORDER:
    _new = []
    for _inf, _url in groups[_g]:
        if _winners[_chkey(name_of(_inf))][0] == _seq: _new.append((_inf, _url))
        _seq += 1
    groups[_g] = _new
_pool.sort(key=lambda r: (r['channel'], r['url']))
json.dump(_pool, open(os.path.join(BASE, 'backup-pool.json'), 'w'), ensure_ascii=False, indent=1)
json.dump({'pre_unique_channels': _pre_channels, 'pre_counts': _pre_counts,
           'pool_count': len(_pool), 'fixes': FIX_MOVES, 'bad_line_kept': _bad_kept,
           'pre_channel_names': sorted(_cands.keys())},
          open(os.path.join(BASE, 'merge-report.json'), 'w'), ensure_ascii=False, indent=1)
print('MERGE pre_channels=%d pool=%d bad_kept=%s fixes=%s' % (_pre_channels, len(_pool), _bad_kept, json.dumps(FIX_MOVES, ensure_ascii=False)), file=sys.stderr)

# --- Duplicate 4K shelf (2026-11-25, user): grouping is not exclusive.
# A channel whose winning line MEASURED 2160 keeps its content group and
# is listed a second time in 4K超高清; the dedicated 4K channels already
# in 4K超高清 likewise appear in their content group. Only a measured
# 2160 earns the extra 4K listing -- a "4K" name alone never does.
def _set_group(inf, g):
    if 'group-title="' in inf:
        return re.sub(r'group-title="[^"]*"', 'group-title="%s"' % g, inf)
    return inf.replace('#EXTINF:-1 ', '#EXTINF:-1 group-title="%s" ' % g, 1)
_shelf = []
for _g in ORDER:
    if _g == '4K超高清':
        continue
    for _inf, _url in groups[_g]:
        if (_res_of(_url) or 0) >= 2000:
            _shelf.append((_set_group(_inf, '4K超高清'), _url))
if _shelf:
    _have4k = {u for _, u in groups['4K超高清']}
    groups['4K超高清'].extend(e for e in _shelf if e[1] not in _have4k)
_4K_HOME = {'苏州': '地方台', '河北': '地方台', 'cctv': '央视'}
_home_added = 0
for _inf, _url in list(groups['4K超高清']):
    _home = _4K_HOME.get(_chkey(name_of(_inf)))
    if _home and _home in groups and all(u != _url for _, u in groups[_home]):
        groups[_home].append((_set_group(_inf, _home), _url))
        _home_added += 1
print('DUP4K shelf_added=%d home_added=%d' % (len(_shelf), _home_added), file=sys.stderr)

out=['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml"']
counts={}
for g in ORDER:
    if not groups[g]: continue
    counts[g]=len(groups[g])
    for inf,url in groups[g]: out.append(with_res(inf,url)); out.append(url)
# --- New/removed channel diff vs the previously published list ---
# Makes weekly auto-adds auditable: which channels flowed in from sources,
# which disappeared. Written to new-channels.json and summarised in the
# build report.
prev_urls=set()
prev_path=os.path.join(BASE, 'huaren-live.m3u')
if os.path.exists(prev_path):
    try:
        prev_urls={l.strip() for l in open(prev_path, encoding='utf-8') if l.strip() and not l.startswith('#')}
    except Exception:
        prev_urls=set()
new_urls={url for g in ORDER for _, url in groups[g]}
added_urls=new_urls-prev_urls; removed_urls=prev_urls-new_urls
added_list=[{'name': name_of(inf), 'group': g, 'url': url} for g in ORDER for inf, url in groups[g] if url in added_urls]
import datetime as _dt
diff_rep={'built_at': _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
          'added_count': len(added_urls), 'removed_count': len(removed_urls),
          'added': added_list[:300]}
json.dump(diff_rep, open(os.path.join(BASE, 'new-channels.json'),'w'), ensure_ascii=False, indent=1)
open(os.path.join(BASE, 'huaren-live.m3u'),'w',encoding='utf-8').write('\n'.join(out)+'\n')
rep={'total_in':total_in,'counts':counts,'total_out':sum(counts.values()),
     'junk_filtered':junk_filtered,'added_count':len(added_urls),'removed_count':len(removed_urls)}
json.dump(rep, open(os.path.join(BASE, 'build-report.json'),'w'), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False))
