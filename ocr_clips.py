import cv2
import pytesseract
import os
import json
import re

pytesseract.pytesseract.tesseract_cmd = '/usr/local/opt/tesseract/bin/tesseract'

clips_dir = 'individual_clips'
results = {}

intersections = sorted(os.listdir(clips_dir))
total = 0
for intersection in intersections:
    intersection_path = os.path.join(clips_dir, intersection)
    if not os.path.isdir(intersection_path):
        continue

    clips = sorted(f for f in os.listdir(intersection_path) if f.endswith('.mp4'))
    results[intersection] = []

    for clip_name in clips:
        total += 1
        clip_path = os.path.join(intersection_path, clip_name)

        cap = cv2.VideoCapture(clip_path)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f'[{total}] FAILED to read {intersection}/{clip_name}')
            results[intersection].append({'clip': clip_name, 'text': None})
            continue

        # Crop top 20% of frame where the overlay text lives
        h, w = frame.shape[:2]
        crop = frame[0:int(h * 0.20), :]

        # Convert to grayscale and threshold for better OCR
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        text = pytesseract.image_to_string(thresh, config='--psm 6').strip()

        # Parse orientation and timestamp
        orientation = None
        timestamp = None

        # Fuzzy match "Facing" — OCR often garbles it
        facing_match = re.search(r'[Ff][ao][cr][ei]n?g?\s+(North|South|East|West|NE|NW|SE|SW)', text, re.IGNORECASE)
        if not facing_match:
            # Try just finding the direction word on its own near start
            facing_match = re.search(r'\b(North|South|East|West)\b', text, re.IGNORECASE)
        if facing_match:
            orientation = facing_match.group(1).title()

        # Match both date formats
        ts_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)', text, re.IGNORECASE)
        if not ts_match:
            ts_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)', text, re.IGNORECASE)
        # Fallback: just grab a date
        if not ts_match:
            ts_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
        if not ts_match:
            ts_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)

        if ts_match:
            timestamp = ts_match.group(1)

        results[intersection].append({
            'clip': clip_name,
            'raw_text': text,
            'orientation': orientation,
            'timestamp': timestamp,
        })

        status = f'orientation={orientation}, timestamp={timestamp}'
        print(f'[{total}] {intersection}/{clip_name}: {status}')

with open('clip_metadata.json', 'w') as f:
    json.dump(results, f, indent=2)

# Summary stats
orientations_found = sum(1 for i in results.values() for c in i if c.get('orientation'))
timestamps_found = sum(1 for i in results.values() for c in i if c.get('timestamp'))
print(f'\nDone! {total} clips processed')
print(f'Orientations found: {orientations_found}/{total}')
print(f'Timestamps found: {timestamps_found}/{total}')
