from pathlib import Path
import json
import subprocess
import tempfile
import zipfile

here=Path(__file__).resolve().parent
root=here.parents[2]
runtime=json.loads((root/'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
jar=root/'build/aqualumen-door-frameclock-v2-test.jar'
with tempfile.TemporaryDirectory(prefix='aqualumen-frameclock-') as build:
    subprocess.run([str(Path(runtime['java']).with_name('javac')),'-proc:none','-cp',':'.join(runtime['cp']),'-d',build,
                    str(here/'Recorder.java'),str(root/'tools/benchmark-mod/dev/aqualumen/bench/FrameMixin.java')],check=True)
    with zipfile.ZipFile(jar,'w') as out:
        for file in sorted(Path(build).rglob('*.class')):
            out.write(file,file.relative_to(build))
        out.writestr('fabric.mod.json',json.dumps(dict(schemaVersion=1,id='aqualumen_house_frameclock',version='1.0.1',
                     name='Aqualumen private house frame clock',environment='client',mixins=['houseclock.mixins.json'],depends=dict(minecraft='1.21.1'))))
        out.writestr('houseclock.mixins.json',json.dumps(dict(required=True,package='dev.aqualumen.bench.mixin',
                     compatibilityLevel='JAVA_21',client=['FrameMixin'],injectors=dict(defaultRequire=1))))
print(jar)
