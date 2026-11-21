from pathlib import Path
import sys
root=Path('/home/kusutohu/repos/aqualumen');sys.path.insert(0,str(root/'tools'))
from water_hit_depth_run import run
out=root/'reports/2026-10-22-water-hit-depth/final-checks';out.mkdir(exist_ok=False)
python='/tmp/aqualumen-optics-python.7uUOLF/bin/python'
run([python,'-m','unittest',*[f'tools/test_{name}.py' for name in (
    'water_depth_candidate','water_hit_depth_runtime','water_continuous_candidate','water_optical_probe',
    'water_paired_diagnostic','water_paired_runtime','water_hit_depth_ownership','water_hit_depth_audit')],'-q'],out,'unit-regression')
print('Recorded all focused test exits and raw outputs')
