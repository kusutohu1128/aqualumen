#!/usr/bin/python3
"""Verify the staging archive against the immutable rc3 archive. Read-only; writes package.json here."""
import hashlib, json, sys
from pathlib import Path
from zipfile import ZipFile
here = Path(__file__).resolve().parent
repo = here.parents[2]
st = repo / 'build/weather-light-staging'
rc3 = repo / 'build/Aqualumen-1.7.0-rain-rc3.zip'
new = st / 'Aqualumen-weather-air.zip'
sha = lambda b: hashlib.sha256(b).hexdigest()
def entries(p):
    with ZipFile(p) as z: return {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}
a, b = entries(rc3), entries(new)
changed = sorted(n for n in a if n in b and a[n] != b[n]); added = sorted(set(b) - set(a)); removed = sorted(set(a) - set(b))
tree_ok = all((st / 'pack' / n).read_bytes() == d for n, d in b.items())
expect_changed, expect_added = ['shaders/gbuffers_weather.fsh'], ['shaders/lib/weather_light.glsl']
keep = {n: sha(a[n]) == sha(b[n]) for n in ['shaders/gbuffers_weather.vsh', 'shaders/shaders.properties', 'shaders/lib/rain_material.glsl', 'shaders/gbuffers_terrain.fsh', 'shaders/lib/local_lighting.glsl', 'shaders/lib/shadows.glsl']}
ok = changed == expect_changed and added == expect_added and not removed and tree_ok and all(keep.values()) and sha(rc3.read_bytes()) == '2c81439353053f7adb12700eb3fb4ea9b9991169ee165a7963e182e9cb0ab4d9'
out = {'ok': ok, 'rc3_sha256': sha(rc3.read_bytes()), 'staging_zip': str(new.relative_to(repo)), 'staging_zip_sha256': sha(new.read_bytes()),
       'zip_entries': len(b), 'changed': changed, 'added': added, 'removed': removed, 'unchanged_vertex_and_support_files': keep, 'tree_matches_zip': tree_ok,
       'file_sha256': {n: sha(b[n]) for n in changed + added + ['shaders/gbuffers_weather.vsh']},
       'rc3_file_sha256': {n: sha(a[n]) for n in changed + ['shaders/gbuffers_weather.vsh']}}
(here / 'package.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('ok', 'staging_zip_sha256', 'changed', 'added')}))
sys.exit(0 if ok else 1)
