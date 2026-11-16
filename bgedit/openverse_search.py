# Search Openverse (CC images, Flickr source), download wide images, write meta + contact sheet.
import sys, json, os, time, urllib.request, urllib.parse, cv2, numpy as np
UA = {'User-Agent': 'poem-bg-editor/0.1'}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
q, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(out, exist_ok=True)
api = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'source': 'flickr', 'aspect_ratio': 'wide', 'size': 'large', 'page_size': 20, 'license_type': 'all-cc'})
res = json.loads(get(api))['results']
meta, tiles = [], []
for r in res:
    if not r['url'].startswith('https://live.staticflickr.com'): continue
    k = len(meta); fn = f"{out}/{k:02d}.jpg"
    url = r['url'].replace('_o.', '_b.') if '_o.' in r['url'] else r['url']
    for u in ([r['url'].rsplit('.', 1)[0].rsplit('_', 1)[0] + '_h.jpg'] if r['url'].count('_') >= 2 else []) + [r['url']]:
        try:
            data = get(u); open(fn, 'wb').write(data)
            im0 = cv2.imread(fn)
            if im0 is not None and im0.shape[1] >= 1000: break
        except Exception: im0 = None
    if im0 is None or im0.shape[1] < 1000: continue
    meta.append({'k': k, 'title': r['title'], 'creator': r.get('creator'), 'license': f"CC {r['license'].upper()} {r.get('license_version','')}", 'page': r.get('foreign_landing_url'), 'file': fn, 'size': im0.shape[:2]})
    im = cv2.resize(im0, (384, 216)); cv2.putText(im, str(k), (8, 34), 0, 1.1, (0, 255, 255), 3)
    tiles.append(im)
    if len(meta) >= n: break
json.dump(meta, open(f"{out}/meta.json", 'w'), ensure_ascii=False, indent=1)
if not tiles: sys.exit('no results')
while len(tiles) % 4: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f"{out}/sheet.jpg", np.vstack([np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)]))
for m in meta: print(m['k'], m['license'], m['size'], m['title'])
