import os
from pathlib import Path
import sys
root=Path('/home/kusutohu/repos/aqualumen');sys.path.insert(0,str(root/'tools'))
from water_hit_depth_run import run,sha,save
out=root/'reports/2026-10-22-water-hit-depth/sampler-query-probe';out.mkdir(exist_ok=False)
source=root/'.audit/depth_sampler_query_2026_10_22.cpp';binary=out/'probe'
run(['g++','-std=c++17','-O2',source,'-o',binary,'-lepoxy','-lEGL'],out,'build')
result,_=run([binary],out,'native',dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json'))
print(result.stdout)
save(out/'receipt.json',dict(sourceSHA256=sha(source),binarySHA256=sha(binary),
    errorFlagsConsumedOnlyInOwnedNativeContext=True,actualIrisBindingMutation=False))
