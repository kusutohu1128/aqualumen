import sys
from pathlib import Path
ROOT = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(ROOT / 'tools'))
import water_paired_runtime as runtime
runtime.OUT = ROOT / 'reports/2026-10-22-underwater-rim-fix/runtime-hit1'
runtime.PROBE = ROOT / 'reports/2026-10-22-underwater-rim-fix/hit1/aqualumen-paired-water-probe-0.1.0-hit1.jar'
runtime.RUN_SUFFIX = 'rimhit1-20261022'
runtime.main()
