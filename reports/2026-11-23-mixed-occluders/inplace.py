"""Try one polygon work array, preserving the checked two-array solver as a control."""
from hashlib import sha256
import json
import os
import subprocess
from zipfile import ZipFile

from grid import HERE, WORK, np


def single_array(source):
    assert source.count("vec2 poly[28],clipped[28];") == 1
    source = source.replace("vec2 poly[28],clipped[28];","vec2 poly[28];")
    start = source.index("        for(int k=0;k<count;k++) {\n            vec2 b=poly[k];")
    end = source.index("    }\n    float area=",start)
    return source[:start] + """        // A convex polygon enters and leaves a halfplane at most once.
        // Its output can lead the input by one vertex. Preserve the next
        // input before writing an intersection into the same array.
        vec2 b=poly[0];
        for(int k=0;k<count;k++) {
            vec2 following=poly[min(k+1,count-1)];
            float db=dot(h.xy,b)+h.z;
            if((da<0.)!=(db<0.)) poly[next++]=mix(a,b,da/(da-db));
            if(db>=0.) poly[next++]=b;
            a=b;da=db;b=following;
        }
        if(next<3) return 1.;
        count=next;
""" + source[end:]


def build():
    source = WORK / "ordinary/Aqualumen-Placed-Torch-Shadows.zip"
    assert sha256(source.read_bytes()).hexdigest() == "9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1"
    output = WORK / "Aqualumen-Two-Shadows-Inplace.zip"
    with ZipFile(source) as original, ZipFile(output,"w") as trial:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename == "shaders/lib/local_lighting.glsl":
                data = single_array(data.decode()).encode()
            trial.writestr(entry,data)
    assert sha256(output.read_bytes()).hexdigest() == "d904689ca01215253e1728083e1d5e9fbfb006a7a90caf4b613aa3c37c056e36"
    return output


def compare():
    shader = WORK / "inplace.csh"
    shader.write_text(single_array((WORK / "polygon.csh").read_text()))
    answer = {}
    for vendor in ("10_nvidia","50_mesa"):
        target = WORK / (vendor + "-inplace.f32")
        env = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/" + vendor + ".json")
        subprocess.run(["flock","/tmp/aql-render21-1000.lock",WORK / "evaluate",shader,WORK / "with-room.f32",target],
                       env=env,check=True)
        new = np.fromfile(target,np.float32)
        old = np.fromfile(WORK / (vendor + "-polygon-with-room.f32"),np.float32)
        assert new.shape == old.shape == (67599,) and np.isfinite(new).all()
        errors = abs(new-old)
        answer[vendor] = dict(inputs=len(new), different=int((errors > 0).sum()), maxDifference=float(errors.max()))
    return answer


if __name__ == "__main__":
    print(build())
    (HERE / "inplace.json").write_text(json.dumps(compare(), indent=2) + "\n")
