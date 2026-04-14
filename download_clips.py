import json
import os
import re
import requests

with open('trafficgifs_places_dict.json') as f:
    data = json.load(f)

nyc_places = {'Manhattan', 'New York', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'}
out_dir = 'individual_clips'

total = 0
failed = 0

for coord, entries in data.items():
    if not any(e['place'] in nyc_places for e in entries):
        continue

    intersection = re.sub('[+-/]', ' ', entries[0]['text'].split(' https')[0])
    intersection_dir = os.path.join(out_dir, intersection)
    os.makedirs(intersection_dir, exist_ok=True)

    for i, entry in enumerate(entries):
        total += 1
        filename = f'clip_{i:03d}.mp4'
        filepath = os.path.join(intersection_dir, filename)

        if os.path.exists(filepath):
            print(f'[{total}] skip {intersection}/{filename}')
            continue

        try:
            r = requests.get(entry['media_url'], timeout=15)
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(r.content)
            print(f'[{total}] {intersection}/{filename} ({len(r.content)//1024}KB)')
        except Exception as e:
            failed += 1
            print(f'[{total}] FAILED {intersection}/{filename}: {e}')

print(f'\nDone! {total} clips, {failed} failed')
