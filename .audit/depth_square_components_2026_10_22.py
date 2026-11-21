import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage
root=Path('/home/kusutohu/repos/aqualumen');sys.path.insert(0,str(root/'tools'))
from water_hit_depth_audit import load
from water_hit_depth_run import save,sha,run
report=root/'reports/2026-10-22-water-hit-depth';result={}
for mode in ('baseline','candidate'):
    path=report/('runtime-'+mode+'2')/'underwater-up-deep-paired-capture'
    m,d,pin=load(path)
    points=d['optics-colortex'+('1' if mode=='baseline' else '3')][...,:3]
    error=d['optics-colortex2'][...,0]-np.linalg.norm(points,axis=-1)
    mask=np.abs(error)>.001;labels,count=ndimage.label(mask);sizes=np.bincount(labels.ravel())[1:]
    result[mode]=dict(manifestSHA256=pin,pixels=int(mask.sum()),components=int(count),sizes=sorted(map(int,sizes),reverse=True),
        allDistanceErrorsCloser=bool(np.all(error[mask]<0)),opaqueDepthIsSkyCount=int((d['depth-depthtex1'][...,0][mask]==1).sum()),
        errorMinimum=float(error[mask].min()),errorMaximum=float(error[mask].max()),
        exactProgramNotDirectlyWitnessed=True)
result['scriptSHA256']=sha(Path(__file__))
save(report/'generation2-square-components.json',result)
prism=Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher')
run([prism/'java/java-runtime-delta/bin/javap','-c','-p','-classpath',
    prism/'instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar',
    'net.irisshaders.iris.shaderpack.loading.ProgramId'],report/'native-ownership3','iris-program-ids')
print(json.dumps(result))
