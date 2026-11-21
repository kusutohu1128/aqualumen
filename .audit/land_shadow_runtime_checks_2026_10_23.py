from pathlib import Path
import shutil
import sys

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import execute, save, sha

out = root / 'reports/2026-10-23-land-shadows/runtime-tool-checks2'
out.mkdir(exist_ok=False)
names = ('.audit/land_shadow_runtime_2026_10_23.py', '.audit/test_land_shadow_runtime_2026_10_23.py',
         'tools/water_paired_runtime.py', 'tools/water_hit_depth_runtime.py', 'tools/display_water_runtime.py',
         'tools/benchmark-control.py')
for name in names:
    target = out / 'sources' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
unit = execute([sys.executable, root / '.audit/test_land_shadow_runtime_2026_10_23.py', '-v'], out, 'unit')
assert unit.returncode == 0 and 'Ran 30 tests' in unit.stderr
save(out / 'receipt.json', dict(unitExit=unit.returncode, tests=30,
     sourcePins={name: sha(root / name) for name in names},
     actualMinecraft=False, runtimeMutation=False))
print('Canonical runtime helper passed30CPU safety/collection tests; no actual game mutation in these tests.')
