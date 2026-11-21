import json
from pathlib import Path
import sys
root=Path('/home/kusutohu/repos/aqualumen');sys.path.insert(0,str(root/'tools'))
from water_hit_depth_run import sha,save,run
report=root/'reports/2026-10-22-water-hit-depth'
for mode in ('baseline','candidate'):
    original=json.loads((report/mode/'manifest.json').read_text())
    current=json.loads((report/(mode+'2')/'manifest.json').read_text())
    assert current['observerBuild']['exitCode']==0
    assert original['archives']==current['archives']
    for role in ('control','paired'):
        assert sha(report/mode/(role+'.zip'))==sha(report/(mode+'2')/(role+'.zip'))
    save(report/(mode+'2')/'reused-native-proof.json',dict(
        shaderArchivesByteIdentical=True,previousQualification=str(report/'native-depth2'/(mode+'-qualification.json')),
        previousQualificationSHA256=sha(report/'native-depth2'/(mode+'-qualification.json')),
        observerBuildSHA256=sha(report/(mode+'2')/'manifest.json'),actualIrisReadbackPending=True))
prism=Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher')
jar=prism/'instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar'
assert sha(jar)=='b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5'
run([prism/'java/java-runtime-delta/bin/javap','-c','-p','-classpath',jar,
    'net.irisshaders.iris.targets.DepthTexture','net.irisshaders.iris.gl.texture.DepthBufferFormat'],report/'depth-storage-probe','iris-decompile')
print('Observer2 archives exactly match previously qualified shader ZIPs; actual Iris capture remains pending')
