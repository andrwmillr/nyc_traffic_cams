import folium
import json
import re
from branca.element import Element

with open('trafficgifs_places_dict.json') as f:
    coords = json.load(f)

with open('clip_metadata.json') as f:
    clip_meta = json.load(f)

with open('nyctmc_cameras.json') as f:
    live_cameras = json.load(f)

nyc_places = {'Manhattan', 'New York', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'}

borough_colors_dark = {
    'Manhattan': '#00ffff',
    'New York': '#00ffff',
    'Brooklyn': '#4d88ff',
    'Queens': '#44dd77',
    'Bronx': '#ff8844',
    'Staten Island': '#bb66ff',
}
borough_colors_light = {
    'Manhattan': '#0088aa',
    'New York': '#0088aa',
    'Brooklyn': '#2255cc',
    'Queens': '#228844',
    'Bronx': '#cc5500',
    'Staten Island': '#7733bb',
}
borough_colors = borough_colors_dark

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

# --- Build LIVE_CAMERAS for JS injection ---
live_cam_data = []
for cam in live_cameras:
    if cam.get('isOnline') == 'true':
        area = cam.get('area', '')
        live_cam_data.append({
            'id': cam['id'],
            'name': cam['name'],
            'lat': cam['latitude'],
            'lng': cam['longitude'],
            'color': borough_colors_dark.get(area, '#ffffff'),
            'colorLight': borough_colors_light.get(area, '#666666'),
        })
live_cam_json = json.dumps(live_cam_data, separators=(',', ':'))

# --- Create map ---

m = folium.Map(location=[40.0, -74.5], zoom_start=4, tiles='CartoDB DarkMatter')

for coord, entries in coords.items():
    if any(e['place'] in nyc_places for e in entries):
        loc = json.loads(coord)
        place = entries[0]['place']
        color = borough_colors_dark.get(place, '#ffffff')
        color_light = borough_colors_light.get(place, '#666666')

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
        cm.options['colorDark'] = color
        cm.options['colorLight'] = color_light
        cm.add_to(m)

map_var = m.get_name()

# --- Inject data ---
Element(f'<script>var CLIP_DATA={clip_data_json};var LIVE_CAMERAS={live_cam_json};</script>').add_to(m.get_root().html)

# --- Title overlay ---
title_html = '''
<div id="map-title">NYC TRAFFIC &mdash; LIVE</div>
<style>
:root {
    --panel-bg: rgba(0, 0, 0, 0.88);
    --panel-border: rgba(255, 255, 255, 0.15);
    --panel-shadow: 0 0 30px rgba(0, 255, 255, 0.15), 0 4px 16px rgba(0, 0, 0, 0.6);
    --text-primary: #ffffff;
    --text-secondary: rgba(255, 255, 255, 0.5);
    --text-dim: rgba(255, 255, 255, 0.3);
    --text-muted: rgba(255, 255, 255, 0.2);
    --accent: #00ffff;
    --accent-glow: rgba(0, 255, 255, 0.4);
    --accent-bg: rgba(0, 255, 255, 0.1);
    --accent-bg-hover: rgba(0, 255, 255, 0.25);
    --accent-bg-active: rgba(0, 255, 255, 0.4);
    --title-shadow: 0 0 12px rgba(0, 255, 255, 0.6), 0 2px 6px rgba(0, 0, 0, 0.8);
    --btn-border: rgba(255, 255, 255, 0.2);
    --btn-bg: rgba(255, 255, 255, 0.05);
    --track-bg: rgba(255, 255, 255, 0.1);
    --dot-bg: rgba(255, 255, 255, 0.3);
    --thumb-border: #ffffff;
    --locked-stroke: #ffffff;
}
:root.theme-light {
    --panel-bg: rgba(255, 255, 255, 0.92);
    --panel-border: rgba(0, 0, 0, 0.12);
    --panel-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    --text-primary: #1a1a2e;
    --text-secondary: rgba(0, 0, 0, 0.5);
    --text-dim: rgba(0, 0, 0, 0.3);
    --text-muted: rgba(0, 0, 0, 0.2);
    --accent: #0077aa;
    --accent-glow: rgba(0, 119, 170, 0.3);
    --accent-bg: rgba(0, 119, 170, 0.08);
    --accent-bg-hover: rgba(0, 119, 170, 0.15);
    --accent-bg-active: rgba(0, 119, 170, 0.25);
    --title-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
    --btn-border: rgba(0, 0, 0, 0.15);
    --btn-bg: rgba(0, 0, 0, 0.03);
    --track-bg: rgba(0, 0, 0, 0.1);
    --dot-bg: rgba(0, 0, 0, 0.2);
    --thumb-border: #ffffff;
    --locked-stroke: #0077aa;
}
#map-title {
    position: fixed;
    top: 80px;
    left: 12px;
    font-family: 'Courier New', monospace;
    font-size: 22px;
    font-weight: bold;
    color: var(--text-primary);
    letter-spacing: 3px;
    text-shadow: var(--title-shadow);
    z-index: 1000;
    pointer-events: none;
    opacity: 0;
    transition: opacity 1s ease-in, color 0.5s, text-shadow 0.5s;
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
    <img id="live-image" width="100%" style="display:none; border-radius:4px;">
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
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 14px;
    z-index: 1000;
    display: none;
    box-shadow: var(--panel-shadow);
    transition: background 0.5s, border-color 0.5s, box-shadow 0.5s;
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
    color: var(--text-primary);
    letter-spacing: 1px;
    margin-bottom: 8px;
    text-shadow: 0 0 6px var(--accent-glow);
    transition: color 0.5s, text-shadow 0.5s;
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
    border: 1.5px solid var(--btn-border);
    background: var(--btn-bg);
    color: var(--text-muted);
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
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-bg);
    cursor: pointer;
}
#compass .dir.available:hover {
    background: var(--accent-bg-hover);
}
#compass .dir.active-dir {
    background: var(--accent-bg-active);
    border-color: var(--text-primary);
    color: var(--text-primary);
    box-shadow: 0 0 8px var(--accent-glow);
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
    background: var(--dot-bg);
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
    border: 1px solid var(--btn-border);
    color: var(--text-primary);
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
    border-color: var(--accent);
    color: var(--accent);
}
#clip-counter {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: var(--text-secondary);
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
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    padding: 12px 16px;
    z-index: 1000;
    opacity: 0;
    transition: opacity 1s ease-in, background 0.5s, border-color 0.5s;
}
#time-slider-panel.visible {
    opacity: 1;
}
#time-slider-label {
    font-family: 'Courier New', monospace;
    font-size: 10px;
    font-weight: bold;
    color: var(--text-secondary);
    letter-spacing: 2px;
    margin-bottom: 4px;
}
#time-range-display {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    font-weight: bold;
    color: var(--accent);
    margin-bottom: 8px;
    text-shadow: 0 0 6px var(--accent-glow);
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
    background: var(--accent);
    border: 2px solid var(--thumb-border);
    cursor: pointer;
    pointer-events: all;
    position: relative;
    z-index: 2;
    box-shadow: 0 0 6px var(--accent-glow);
    margin-top: -4px;
}
#time-slider-container input[type="range"]::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 2px;
    background: var(--track-bg);
}
#time-track-fill {
    position: absolute;
    height: 4px;
    background: var(--accent-bg-active);
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
    color: var(--text-dim);
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
    stroke: var(--locked-stroke);
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

    var liveImg = document.getElementById('live-image');
    var clipNav = document.getElementById('clip-nav');

    var state = {{
        activeMarker: null,
        lockedMarker: null,
        clipKey: null,
        playlist: [],
        clipIndex: 0,
        timeRange: [0, 23],
        orientation: null,
        ready: false,
        mode: 'live',
        liveInterval: null,
        liveCameraId: null,
        liveMarkers: [],
        archiveMarkers: []
    }};

    // Smoother trackpad zoom
    map.options.wheelPxPerZoomLevel = 300;

    // --- Day/night theme based on local time ---
    var lightTiles = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png', {{
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd', maxZoom: 20
    }});
    var hour = new Date().getHours();
    var isDay = hour >= 6 && hour < 19;
    if (isDay) {{
        // Remove default dark tiles, add light
        map.eachLayer(function(layer) {{
            if (layer instanceof L.TileLayer) map.removeLayer(layer);
        }});
        lightTiles.addTo(map);
        document.documentElement.classList.add('theme-light');
    }}

    function recolorMarkers(theme) {{
        var key = theme === 'light' ? 'colorLight' : 'colorDark';
        state.archiveMarkers.forEach(function(m) {{
            var c = m.options[key];
            if (c) m.setStyle({{ color: c, fillColor: c }});
        }});
        state.liveMarkers.forEach(function(m) {{
            var c = m.options[key];
            if (c) m.setStyle({{ color: c, fillColor: c }});
        }});
    }}

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
        setMode('live');
        if (isDay) recolorMarkers('light');
        setTimeout(function() {{ state.ready = true; }}, 500);
    }});

    // --- Collect archive markers ---
    map.eachLayer(function(layer) {{
        if (layer instanceof L.CircleMarker && layer.options.clipKey) {{
            state.archiveMarkers.push(layer);
            layer.on('mouseover', function(e) {{
                if (!state.ready || state.lockedMarker || state.mode !== '2020') return;
                showVideo(layer);
            }});
            layer.on('click', function(e) {{
                if (!state.ready || state.mode !== '2020') return;
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

    // --- Create live camera markers (hidden initially) ---
    LIVE_CAMERAS.forEach(function(cam) {{
        var lm = L.circleMarker([cam.lat, cam.lng], {{
            radius: 5,
            fill: true,
            fillOpacity: 0.8,
            color: isDay ? cam.colorLight : cam.color,
            fillColor: isDay ? cam.colorLight : cam.color,
            weight: 2
        }});
        lm.options.cameraId = cam.id;
        lm.options.title = cam.name;
        lm.options.colorDark = cam.color;
        lm.options.colorLight = cam.colorLight;
        state.liveMarkers.push(lm);

        lm.on('mouseover', function() {{
            if (!state.ready || state.lockedMarker || state.mode !== 'live') return;
            showLive(lm);
        }});
        lm.on('click', function() {{
            if (!state.ready || state.mode !== 'live') return;
            if (state.lockedMarker === lm) {{
                state.lockedMarker._path.classList.remove('marker-locked');
                state.lockedMarker = null;
            }} else {{
                if (state.lockedMarker && state.lockedMarker._path) {{
                    state.lockedMarker._path.classList.remove('marker-locked');
                }}
                state.lockedMarker = lm;
                showLive(lm);
                lm._path.classList.add('marker-locked');
            }}
        }});
    }});

    // --- Live feed functions ---
    function showLive(layer) {{
        if (state.activeMarker && state.activeMarker._path) {{
            state.activeMarker._path.classList.remove('marker-active');
        }}
        state.activeMarker = layer;
        if (layer._path) {{
            layer._path.classList.add('marker-active');
        }}

        titleEl.textContent = layer.options.title;
        compassEl.style.display = 'none';
        clipNav.style.display = 'none';
        video.style.display = 'none';
        liveImg.style.display = 'block';
        panel.classList.add('active');

        state.liveCameraId = layer.options.cameraId;
        refreshLiveImage();

        if (state.liveInterval) clearInterval(state.liveInterval);
        state.liveInterval = setInterval(refreshLiveImage, 2000);
    }}

    function refreshLiveImage() {{
        if (!state.liveCameraId) return;
        liveImg.src = 'https://webcams.nyctmc.org/api/cameras/' + state.liveCameraId + '/image?t=' + Date.now();
    }}

    // --- Mode toggle ---
    function setMode(mode) {{
        state.mode = mode;

        // Clear active state
        if (state.activeMarker && state.activeMarker._path) {{
            state.activeMarker._path.classList.remove('marker-active');
        }}
        if (state.lockedMarker && state.lockedMarker._path) {{
            state.lockedMarker._path.classList.remove('marker-locked');
        }}
        state.activeMarker = null;
        state.lockedMarker = null;
        state.clipKey = null;
        panel.classList.remove('active');
        if (state.liveInterval) {{
            clearInterval(state.liveInterval);
            state.liveInterval = null;
        }}

        if (mode === '2020') {{
            mapTitle.textContent = 'NYC TRAFFIC \\u2014 2020';
            // Show archive markers, hide live
            state.archiveMarkers.forEach(function(m) {{ m.addTo(map); }});
            state.liveMarkers.forEach(function(m) {{ m.remove(); }});
            // Show 2020 controls
            timeSliderPanel.style.display = '';
            video.style.display = '';
            liveImg.style.display = 'none';
            clipNav.style.display = '';
        }} else {{
            mapTitle.textContent = 'NYC TRAFFIC \\u2014 LIVE';
            // Show live markers, hide archive
            state.archiveMarkers.forEach(function(m) {{ m.remove(); }});
            state.liveMarkers.forEach(function(m) {{ m.addTo(map); }});
            // Hide 2020 controls
            timeSliderPanel.style.display = 'none';
        }}
    }}
}});
</script>
'''
Element(interaction_js).add_to(m.get_root().html)

m.save('index.html')
