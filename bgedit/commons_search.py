# Search Wikimedia Commons, download landscape thumbnails + license metadata, make a contact sheet.
import sys, json, os, urllib.request, urllib.parse, cv2, numpy as np
UA = {'User-Agent': 'poem-bg-editor/0.1 (educational video project)'}
import time
def get(url):
    for i in range(5):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (i + 1))
    raise RuntimeError('rate limited')
q, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12
os.makedirs(out, exist_ok=True)
api = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
    'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrsearch': q + ' filetype:bitmap',
    'gsrlimit': 40, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata'})
pages = json.loads(get(api)).get('query', {}).get('pages', {})
meta, tiles = [], []
for p in sorted(pages.values(), key=lambda p: p.get('index', 0)):
    ii = p['imageinfo'][0]
    if ii['width'] < 1600 or ii['size'] > 25e6 or ii['width'] / ii['height'] < 1.3: continue
    em = ii.get('extmetadata', {})
    lic = em.get('LicenseShortName', {}).get('value', '?')
    k = len(meta); fn = f"{out}/{k:02d}.jpg"
    try: open(fn, 'wb').write(get(ii['url'])); time.sleep(1)
    except Exception as e: continue
    meta.append({'k': k, 'title': p['title'], 'license': lic, 'artist': em.get('Artist', {}).get('value', ''), 'url': ii['descriptionurl'], 'file': fn})
    im0 = cv2.imread(fn)
    if im0 is None: continue
    im = cv2.resize(im0, (384, 216)); cv2.putText(im, str(k), (8, 34), 0, 1.1, (0, 255, 255), 3)
    tiles.append(im)
    if len(meta) >= n: break
json.dump(meta, open(f"{out}/meta.json", 'w'), ensure_ascii=False, indent=1)
if not tiles: sys.exit('no results')
while len(tiles) % 4: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f"{out}/sheet.jpg", np.vstack([np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)]))
for m in meta: print(m['k'], m['license'], m['title'])
