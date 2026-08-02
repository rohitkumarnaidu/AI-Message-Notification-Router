"""Audit Phase 7 media cache contents."""
import json, os, sys

sys.path.insert(0, 'code')

cache_path = '.cache/media_cache.json'
if os.path.exists(cache_path):
    with open(cache_path) as f:
        cache = json.load(f)
    print('Media cache entries:', len(cache))
    for k in list(cache.keys())[:5]:
        v = cache[k]
        print(f'  Key: {k[:60]}')
        print(f'    failure:', v.get('failure'))
        print(f'    failure_reason:', v.get('failure_reason', '')[:80])
        print(f'    extracted_text len:', len(v.get('extracted_text', '')))
        print(f'    summary:', v.get('summary', '')[:80])
        print()
else:
    print('No media cache file found')
