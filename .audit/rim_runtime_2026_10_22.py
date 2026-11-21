import sys
from pathlib import Path
ROOT = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(ROOT / 'tools'))
import water_paired_runtime as runtime
runtime.OUT = ROOT / 'reports/2026-10-22-underwater-rim-fix/runtime-optics1'
runtime.PROBE = ROOT / 'reports/2026-10-22-underwater-rim-fix/optical/aqualumen-paired-water-probe-0.1.0-optics1.jar'
runtime.RUN_SUFFIX = 'rimoptics1-20261022'
runtime.main()
