"""Build the private frame observer. Kept outside all playable packs."""
import os
import json
import subprocess
import tempfile
from pathlib import Path

here=Path(__file__).resolve().parent
prism=Path(os.environ.get("AQUALUMEN_PRISM_ROOT",Path.home()/".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher"))
java=prism/"java/java-runtime-delta/bin"
libs=prism/"libraries/net/fabricmc"
target=here.parents[2]/"build/animal-light/frame-sample.jar"
with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
    classes=Path(tmp)/"classes"
    classes.mkdir()
    cp=os.pathsep.join(map(str,(libs/"fabric-loader/0.19.5/fabric-loader-0.19.5.jar",libs/"sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar")))
    subprocess.run([java/"javac","-proc:none","-cp",cp,"-d",classes,*sorted(here.glob("*.java"))],check=True)
    (classes/"fabric.mod.json").write_text(json.dumps(dict(schemaVersion=1,id="animal_frame_sample",version="1.0",name="Aqualumen private frame observer",environment="client",mixins=["frame.mixins.json"],depends=dict(minecraft="1.21.1",java=">=21"))))
    (classes/"frame.mixins.json").write_text(json.dumps(dict(required=True,package="dev.aqualumen.animalqa.mixin",compatibilityLevel="JAVA_21",client=["FrameMixin"],injectors=dict(defaultRequire=1))))
    out=Path(tmp)/target.name
    subprocess.run([java/"jar","--create","--file",out,"-C",classes,"."],check=True)
    os.replace(out,target)
