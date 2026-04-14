import folium
import json
import re
from branca.element import Element

with open('trafficgifs_places_dict.json') as f:
    coords = json.load(f)

with open('clip_metadata.json') as f:
    clip_meta = json.load(f)

nyc_places = {'Manhattan', 'New York', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'}

borough_colors = {
    'Manhattan': '#00ffff',
    'New York': '#00ffff',
    'Brooklyn': '#4d88ff',
    'Queens': '#44dd77',
    'Bronx': '#ff8844',
    'Staten Island': '#bb66ff',
}

# --- Build CLIP_DATA for JS injection ---

orientation_normalize = {'Se': 'South', 'Ne': 'North'}

def extract_hour(ts):
    if not ts or ' ' not in ts:
        return None
    parts = ts.strip().split()
    try:
        time_str = parts[-2]
        ampm = parts[-1].upper()
        hour = int(time_str.split(':')[0])
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        return hour
    except (ValueError, IndexError):
        return None

clip_data = {}
for intersection, clips in clip_meta.items():
    clip_data[intersection] = []
    for c in clips:
        orient = c.get('orientation')
        if orient:
            orient = orientation_normalize.get(orient, orient)
            if orient not in ('North', 'South', 'East', 'West'):
                orient = None
        clip_data[intersection].append({
            'c': c['clip'],
            'o': orient,
            'h': extract_hour(c.get('timestamp')),
        })

clip_data_json = json.dumps(clip_data, separators=(',', ':'))

# --- Create map ---

m = folium.Map(location=[40.0, -74.5], zoom_start=4, tiles='CartoDB DarkMatter')

for coord, entries in coords.items():
    if any(e['place'] in nyc_places for e in entries):
        loc = json.loads(coord)
        place = entries[0]['place']
        color = borough_colors.get(place, '#ffffff')

        intersection = entries[0]['text'].split(' https')[0]
        clip_key = re.sub('[+-/]', ' ', intersection)

        cm = folium.CircleMarker(
            radius=5,
            location=loc,
            fill=True,
            fill_opacity=0.8,
            color=color,
            fill_color=color,
            weight=2,
        )
        cm.options['clipKey'] = clip_key
        cm.options['title'] = intersection
        cm.add_to(m)

map_var = m.get_name()

# --- Inject CLIP_DATA ---
Element(f'<script>var CLIP_DATA={clip_data_json};</script>').add_to(m.get_root().html)

# --- Title overlay ---
title_html = '''
<div id="map-title">NYC TRAFFIC &mdash; 2020</div>
<style>
#map-title {
    position: fixed;
    top: 80px;
    left: 12px;
    font-family: 'Courier New', monospace;
    font-size: 22px;
    font-weight: bold;
    color: #ffffff;
    letter-spacing: 3px;
    text-shadow: 0 0 12px rgba(0, 255, 255, 0.6), 0 2px 6px rgba(0, 0, 0, 0.8);
    z-index: 1000;
    pointer-events: none;
    opacity: 0;
    transition: opacity 1s ease-in;
}
#map-title.visible {
    opacity: 1;
}
</style>
'''
Element(title_html).add_to(m.get_root().html)

# --- Corner video panel ---
video_panel_html = '''
<div id="video-panel">
    <div id="video-title"></div>
    <div id="compass"></div>
    <video id="video-player" width="100%" controls muted loop></video>
    <div id="clip-nav">
        <button id="clip-prev">&lsaquo;</button>
        <span id="clip-counter"></span>
        <button id="clip-next">&rsaquo;</button>
    </div>
</div>
<style>
#video-panel {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 380px;
    background: rgba(0, 0, 0, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    padding: 14px;
    z-index: 1000;
    display: none;
    box-shadow: 0 0 30px rgba(0, 255, 255, 0.15), 0 4px 16px rgba(0, 0, 0, 0.6);
}
#video-panel.active {
    display: block;
    animation: panelSlideIn 0.3s ease-out;
}
@keyframes panelSlideIn {
    from { transform: translateX(420px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
#video-title {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    font-weight: bold;
    color: #ffffff;
    letter-spacing: 1px;
    margin-bottom: 8px;
    text-shadow: 0 0 6px rgba(0, 255, 255, 0.4);
}
#video-player {
    border-radius: 4px;
}

/* Compass */
#compass {
    display: none;
    width: 80px;
    height: 80px;
    position: relative;
    margin: 0 auto 4px auto;
}
#compass .dir {
    position: absolute;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 1.5px solid rgba(255,255,255,0.2);
    background: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.2);
    font-family: 'Courier New', monospace;
    font-size: 10px;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: default;
    transition: all 0.2s;
}
#compass .dir.available {
    border-color: #00ffff;
    color: #00ffff;
    background: rgba(0,255,255,0.1);
    cursor: pointer;
}
#compass .dir.available:hover {
    background: rgba(0,255,255,0.25);
}
#compass .dir.active-dir {
    background: rgba(0,255,255,0.4);
    border-color: #ffffff;
    color: #ffffff;
    box-shadow: 0 0 8px rgba(0,255,255,0.5);
}
#compass .dir-n { top: 0; left: 50%; transform: translateX(-50%); }
#compass .dir-s { bottom: 0; left: 50%; transform: translateX(-50%); }
#compass .dir-e { right: 0; top: 50%; transform: translateY(-50%); }
#compass .dir-w { left: 0; top: 50%; transform: translateY(-50%); }
#compass .center-dot {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 4px; height: 4px;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
}

/* Clip nav */
#clip-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 8px;
}
#clip-nav button {
    background: none;
    border: 1px solid rgba(255,255,255,0.2);
    color: #ffffff;
    font-size: 18px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}
#clip-nav button:hover {
    border-color: #00ffff;
    color: #00ffff;
}
#clip-counter {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: rgba(255,255,255,0.6);
}
</style>
'''
Element(video_panel_html).add_to(m.get_root().html)

# --- Time slider ---
time_slider_html = '''
<div id="time-slider-panel">
    <div id="time-slider-label">TIME OF DAY</div>
    <div id="time-range-display">12 AM &mdash; 11 PM</div>
    <div id="time-slider-container">
        <input type="range" id="time-min" min="0" max="23" value="0" step="1">
        <input type="range" id="time-max" min="0" max="23" value="23" step="1">
        <div id="time-track-fill"></div>
    </div>
    <div id="time-slider-ticks">
        <span>12A</span><span>6A</span><span>12P</span><span>6P</span><span>12A</span>
    </div>
</div>
<style>
#time-slider-panel {
    position: fixed;
    bottom: 20px;
    left: 20px;
    width: 260px;
    background: rgba(0, 0, 0, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    padding: 12px 16px;
    z-index: 1000;
    opacity: 0;
    transition: opacity 1s ease-in;
}
#time-slider-panel.visible {
    opacity: 1;
}
#time-slider-label {
    font-family: 'Courier New', monospace;
    font-size: 10px;
    font-weight: bold;
    color: rgba(255,255,255,0.5);
    letter-spacing: 2px;
    margin-bottom: 4px;
}
#time-range-display {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    font-weight: bold;
    color: #00ffff;
    margin-bottom: 8px;
    text-shadow: 0 0 6px rgba(0, 255, 255, 0.4);
}
#time-slider-container {
    position: relative;
    height: 24px;
}
#time-slider-container input[type="range"] {
    position: absolute;
    width: 100%;
    top: 0;
    height: 24px;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    pointer-events: none;
    margin: 0;
}
#time-slider-container input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #00ffff;
    border: 2px solid #ffffff;
    cursor: pointer;
    pointer-events: all;
    position: relative;
    z-index: 2;
    box-shadow: 0 0 6px rgba(0,255,255,0.5);
    margin-top: -4px;
}
#time-slider-container input[type="range"]::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.1);
}
#time-track-fill {
    position: absolute;
    height: 4px;
    background: rgba(0,255,255,0.4);
    border-radius: 2px;
    top: 10px;
    pointer-events: none;
    z-index: 1;
}
#time-slider-ticks {
    display: flex;
    justify-content: space-between;
    margin-top: 2px;
}
#time-slider-ticks span {
    font-family: 'Courier New', monospace;
    font-size: 9px;
    color: rgba(255,255,255,0.3);
}
</style>
'''
Element(time_slider_html).add_to(m.get_root().html)

# --- Pulsing marker animation ---
pulse_css = '''
<style>
@keyframes markerPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}
.leaflet-overlay-pane svg,
.leaflet-tile-pane {
    will-change: transform;
}
.leaflet-overlay-pane {
    opacity: 0;
    transition: opacity 1.5s ease-in;
}
.leaflet-overlay-pane.markers-visible {
    opacity: 1;
}
.markers-visible .leaflet-interactive {
    animation: markerPulse 3s ease-in-out infinite;
    transition: opacity 0.3s;
}
.leaflet-interactive.marker-active {
    opacity: 1 !important;
    stroke-width: 4;
    animation: none;
}
.leaflet-interactive.marker-locked {
    opacity: 1 !important;
    stroke-width: 4;
    stroke: #ffffff;
    animation: none;
}
.leaflet-interactive.marker-dimmed {
    opacity: 0.12 !important;
    animation: none;
    pointer-events: none;
}
</style>
'''
Element(pulse_css).add_to(m.get_root().html)

# --- Main interaction JS ---
interaction_js = f'''
<script>
document.addEventListener('DOMContentLoaded', function() {{
    var map = window['{map_var}'];
    if (!map) return;

    var panel = document.getElementById('video-panel');
    var video = document.getElementById('video-player');
    var titleEl = document.getElementById('video-title');
    var mapTitle = document.getElementById('map-title');
    var compassEl = document.getElementById('compass');
    var clipCounter = document.getElementById('clip-counter');
    var prevBtn = document.getElementById('clip-prev');
    var nextBtn = document.getElementById('clip-next');
    var timeSliderPanel = document.getElementById('time-slider-panel');
    var timeMin = document.getElementById('time-min');
    var timeMax = document.getElementById('time-max');
    var timeDisplay = document.getElementById('time-range-display');
    var trackFill = document.getElementById('time-track-fill');

    var state = {{
        activeMarker: null,
        lockedMarker: null,
        clipKey: null,
        playlist: [],
        clipIndex: 0,
        timeRange: [0, 23],
        orientation: null,
        ready: false
    }};

    // Smoother trackpad zoom
    map.options.wheelPxPerZoomLevel = 300;

    // --- Utility functions ---

    function formatHour(h) {{
        if (h === 0 || h === 24) return '12 AM';
        if (h === 12) return '12 PM';
        if (h < 12) return h + ' AM';
        return (h - 12) + ' PM';
    }}

    function buildPlaylist(clipKey) {{
        var all = CLIP_DATA[clipKey] || [];
        return all.filter(function(clip) {{
            var timeOk = clip.h === null ||
                (clip.h >= state.timeRange[0] && clip.h <= state.timeRange[1]);
            var orientOk = !state.orientation || clip.o === state.orientation;
            return timeOk && orientOk;
        }});
    }}

    function loadClip(index) {{
        if (state.playlist.length === 0) {{
            video.src = '';
            clipCounter.textContent = 'no clips';
            orientLabel.textContent = '';
            return;
        }}
        state.clipIndex = ((index % state.playlist.length) + state.playlist.length) % state.playlist.length;
        var clip = state.playlist[state.clipIndex];
        var path = 'individual_clips/' + encodeURIComponent(state.clipKey) + '/' + clip.c;
        video.src = path;
        video.play();
        clipCounter.textContent = (state.clipIndex + 1) + ' / ' + state.playlist.length;

        // Update orientation label
        updateCompassActive(clip.o);
    }}

    function getOrientations(clipKey) {{
        var all = CLIP_DATA[clipKey] || [];
        var orients = {{}};
        all.forEach(function(c) {{
            if (c.o) orients[c.o] = true;
        }});
        return Object.keys(orients);
    }}

    function updateCompass(clipKey) {{
        var orients = getOrientations(clipKey);
        if (orients.length <= 1) {{
            compassEl.style.display = 'none';
        }} else {{
            compassEl.style.display = 'block';
            ['North','South','East','West'].forEach(function(dir) {{
                var btn = compassEl.querySelector('.dir-' + dir[0].toLowerCase());
                if (btn) {{
                    btn.classList.toggle('available', orients.indexOf(dir) !== -1);
                    btn.classList.remove('active-dir');
                }}
            }});
        }}
    }}

    function updateCompassActive(orient) {{
        ['North','South','East','West'].forEach(function(dir) {{
            var btn = compassEl.querySelector('.dir-' + dir[0].toLowerCase());
            if (btn) {{
                btn.classList.toggle('active-dir',
                    state.orientation ? dir === state.orientation : dir === orient);
            }}
        }});
    }}

    function showVideo(layer) {{
        if (state.activeMarker && state.activeMarker._path) {{
            state.activeMarker._path.classList.remove('marker-active');
        }}
        state.activeMarker = layer;
        if (layer._path) {{
            layer._path.classList.add('marker-active');
        }}

        var newKey = layer.options.clipKey;
        if (newKey !== state.clipKey) {{
            state.orientation = null;
        }}
        state.clipKey = newKey;

        titleEl.textContent = layer.options.title;
        updateCompass(state.clipKey);
        state.playlist = buildPlaylist(state.clipKey);
        panel.classList.add('active');
        loadClip(0);
    }}

    function updateMarkerVisibility() {{
        map.eachLayer(function(layer) {{
            if (!(layer instanceof L.CircleMarker) || !layer.options.clipKey) return;
            var clips = CLIP_DATA[layer.options.clipKey] || [];
            var hasMatch = clips.some(function(c) {{
                return c.h === null ||
                    (c.h >= state.timeRange[0] && c.h <= state.timeRange[1]);
            }});
            if (layer._path) {{
                layer._path.classList.toggle('marker-dimmed', !hasMatch);
            }}
        }});
    }}

    function updateTrackFill() {{
        var min = Math.min(+timeMin.value, +timeMax.value);
        var max = Math.max(+timeMin.value, +timeMax.value);
        var left = (min / 23) * 100;
        var right = (max / 23) * 100;
        trackFill.style.left = left + '%';
        trackFill.style.width = (right - left) + '%';
    }}

    // --- Build compass HTML ---
    compassEl.innerHTML = '<div class="dir dir-n">N</div>' +
        '<div class="dir dir-s">S</div>' +
        '<div class="dir dir-e">E</div>' +
        '<div class="dir dir-w">W</div>' +
        '<div class="center-dot"></div>';

    // Compass click handlers
    ['North','South','East','West'].forEach(function(dir) {{
        var btn = compassEl.querySelector('.dir-' + dir[0].toLowerCase());
        if (btn) {{
            btn.addEventListener('click', function() {{
                if (!btn.classList.contains('available')) return;
                if (state.orientation === dir) {{
                    state.orientation = null;
                }} else {{
                    state.orientation = dir;
                }}
                state.playlist = buildPlaylist(state.clipKey);
                loadClip(0);
                updateCompassActive(state.orientation || (state.playlist.length ? state.playlist[0].o : null));
            }});
        }}
    }});

    // Clip nav
    prevBtn.addEventListener('click', function() {{
        loadClip(state.clipIndex - 1);
    }});
    nextBtn.addEventListener('click', function() {{
        loadClip(state.clipIndex + 1);
    }});

    // Time slider
    function onTimeSliderChange() {{
        var min = Math.min(+timeMin.value, +timeMax.value);
        var max = Math.max(+timeMin.value, +timeMax.value);
        state.timeRange = [min, max];
        timeDisplay.textContent = formatHour(min) + ' \\u2014 ' + formatHour(max);
        updateTrackFill();
        updateMarkerVisibility();
        // Rebuild playlist if a marker is active
        if (state.clipKey) {{
            state.playlist = buildPlaylist(state.clipKey);
            loadClip(0);
        }}
    }}
    timeMin.addEventListener('input', onTimeSliderChange);
    timeMax.addEventListener('input', onTimeSliderChange);
    updateTrackFill();

    // --- Cinematic fly-in ---
    setTimeout(function() {{
        map.flyTo([40.7480, -73.9900], 13, {{
            duration: 3.5,
            easeLinearity: 0.15
        }});
    }}, 800);

    var overlay = document.querySelector('.leaflet-overlay-pane');
    map.once('moveend', function() {{
        mapTitle.classList.add('visible');
        overlay.classList.add('markers-visible');
        timeSliderPanel.classList.add('visible');
        setTimeout(function() {{ state.ready = true; }}, 500);
    }});

    // --- Marker interactions ---
    map.eachLayer(function(layer) {{
        if (layer instanceof L.CircleMarker && layer.options.clipKey) {{
            layer.on('mouseover', function(e) {{
                if (!state.ready || state.lockedMarker) return;
                showVideo(layer);
            }});

            layer.on('click', function(e) {{
                if (!state.ready) return;
                if (state.lockedMarker === layer) {{
                    state.lockedMarker._path.classList.remove('marker-locked');
                    state.lockedMarker = null;
                }} else {{
                    if (state.lockedMarker && state.lockedMarker._path) {{
                        state.lockedMarker._path.classList.remove('marker-locked');
                    }}
                    state.lockedMarker = layer;
                    showVideo(layer);
                    layer._path.classList.add('marker-locked');
                }}
            }});
        }}
    }});
}});
</script>
'''
Element(interaction_js).add_to(m.get_root().html)

m.save('index.html')
