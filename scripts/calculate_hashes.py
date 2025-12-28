import hashlib
import json
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if ':' in netloc:
        host, port = netloc.split(':')
        if (scheme == 'http' and port == '80') or (scheme == 'https' and port == '443'):
            netloc = host
    
    path = parsed.path
    path = re.sub(r'//+', '/', path) # remove double slashes
    # simplify dot segments (simple approach)
    parts = path.split('/')
    new_parts = []
    for part in parts:
        if part == '.': continue
        if part == '..': 
            if new_parts: new_parts.pop()
        else:
            new_parts.append(part)
    path = '/'.join(new_parts)
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    
    # Query normalization
    query = parsed.query
    if query:
        q_list = parse_qsl(query)
        filtered_q = []
        for k, v in q_list:
            if k.startswith('utm_') or k in ['gclid', 'fbclid']:
                continue
            filtered_q.append((k, v))
        # Sort by key then value
        filtered_q.sort(key=lambda x: (x[0], x[1]))
        query = urlencode(filtered_q)
    
    return urlunparse((scheme, netloc, path, '', query, ''))

def get_url_id(url):
    norm = normalize_url(url)
    return hashlib.sha1(norm.encode('utf-8')).hexdigest()

urls = [
    "https://ja.wikipedia.org/wiki/マンチェスター・シティFC",
    "https://www.fifa.com/ja/tournaments/mens/club-world-cup/usa-2025/articles/man-citys-fall-from-grace-and-rise-to-glory-ja",
    "https://sportiva.shueisha.co.jp/clm/football/wfootball/2018/09/06/100_split/",
    "http://www.newsweekjapan.jp/stories/world/2011/12/post-2365_1.php",
    "https://ja.wikipedia.org/wiki/メイン・ロード",
    "https://www.mancity.com/club/manchester-city-history",
    "https://en.wikipedia.org/wiki/History_of_Manchester_City_F.C.",
    "https://www.bbc.com/sport/football/45256691",
    "https://www.theguardian.com/football/2008/sep/01/manchestercity.premierleague",
    "https://www.mancity.com/features/maine-road-eras/",
    "https://www.stadiumguide.com/maineroad/"
]

output = {}
for u in urls:
    output[u] = get_url_id(u)

print(json.dumps(output, indent=2))
