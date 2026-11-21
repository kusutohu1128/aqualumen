#!/usr/bin/python3
"""Build build/weather-light-staging/{pack,Aqualumen-weather-air.zip} from the immutable rc3 ZIP plus overlay/.
Writes only below build/weather-light-staging/ ; refuses to touch anything else."""
import hashlib, json, shutil, sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
here = Path(__file__).resolve().parent
repo = here.parents[2]
base = repo / 'build/Aqualumen-1.7.0-rain-rc3.zip'
out = repo / 'build/weather-light-staging'
pack = out / 'pack'
baseline = out / 'baseline-rc3'
BASE_SHA = '2c81439353053f7adb12700eb3fb4ea9b9991169ee165a7963e182e9cb0ab4d9'
sha = lambda b: hashlib.sha256(b).hexdigest()
if sha(base.read_bytes()) != BASE_SHA: sys.exit('rc3 archive hash mismatch: refusing')
for d in (pack, baseline):
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
names = {}
with ZipFile(base) as z:
    for info in z.infolist():
        if info.is_dir(): continue
        data = z.read(info)
        names[info.filename] = data
        t = baseline / info.filename; t.parent.mkdir(parents=True, exist_ok=True); t.write_bytes(data)
overlay = {p.relative_to(here / 'overlay').as_posix(): p.read_bytes() for p in sorted((here / 'overlay').rglob('*')) if p.is_file()}
changed = sorted(set(overlay) & set(names)); added = sorted(set(overlay) - set(names))
names.update(overlay)
for name, data in names.items():
    t = pack / name; t.parent.mkdir(parents=True, exist_ok=True); t.write_bytes(data)
target = out / 'Aqualumen-weather-air.zip'
with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
    for name in sorted(names):
        e = ZipInfo(name, (2026, 10, 23, 0, 0, 0)); e.compress_type = ZIP_DEFLATED; e.external_attr = 0o100644 << 16
        archive.writestr(e, names[name])
print(json.dumps({'zip': str(target.relative_to(repo)), 'sha256': sha(target.read_bytes()), 'changed': changed, 'added': added}))
