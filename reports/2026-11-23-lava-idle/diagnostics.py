"""Build four diagnostic ZIPs with program-local changes from the pinned p3 archive."""
import difflib
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

R=Path(__file__).resolve().parent
ROOT=R.parents[1]
OUT=ROOT/'build/lava-idle'
P3=ROOT/'dist/Aqualumen-1.9.0-preview.3.zip'
STABLE=ROOT/'dist/Aqualumen-1.8.0.zip'
P8=ROOT/'dist/Aqualumen-1.9.0-preview.8.zip'
PINS={P3:'a5084110b9373db7240244b1953c24f2f1d42a6c9430d148a05901a9b210266b',
      STABLE:'c5d804e4a6776cf7df14b405f32a605d09451cab10aabb8b3fae4c5428c73af8',
      P8:'2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72'}
FACTORS = {'source': ('p3', 'comp-pragma', 'composite'),
           'pragma': ('comp-pragma', 'comp-default', 'composite'),
           'pending': ('p3', 'def-five', 'deferred'),
           'mrt': ('def-five', 'def-four', 'deferred')}


P9=OUT/'Aqualumen-1.9.0-preview.9.zip'
P9_SHA256='4184d8cdf12634f108e3379d5b600de5009349916dfea26f7ad59f9190748f0f'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def entries(path):
    if path in PINS and digest(path)!=PINS[path]:
        raise ValueError(f'unrecognized pack {path}')
    with ZipFile(path) as z:
        return {name:z.read(name) for name in z.namelist()}


def expanded(files, name):
    def visit(match):
        return expanded(files,match[1].lstrip('/'))
    return re.sub(r'^\s*#include\s+"([^"]+)"',visit,files['shaders/'+name].decode(),flags=re.M)


def replace_once(data, old, new):
    if data.count(old)!=1:
        raise ValueError(f'expected one source location for {old!r}')
    return data.replace(old,new)


def variants(p3,stable):
    # Use the existing compiler mod. Iris removes some source pragmas during processing;
    # a live function name preserves the predicate through to the real submitted GLSL.
    c='shaders/composite.fsh'
    d='shaders/deferred.fsh'
    illumination='shaders/lib/illumination.glsl'
    comp={**p3,'shaders/lib/idle_lamp_only.glsl':stable['shaders/lib/local_lighting.glsl'],
          'shaders/lib/idle_illumination.glsl':replace_once(p3[illumination],b'/lib/local_lighting.glsl',b'/lib/idle_lamp_only.glsl'),
          c:replace_once(p3[c],b'/lib/illumination.glsl',b'/lib/idle_illumination.glsl')}
    version=b'#version 330 compatibility\n'
    on=replace_once(comp[c],version,version+b'#define waterIncidentIrradiance aqualumenAreaSourceLightingIdleWater\n')
    original=p3[d].decode()
    # No-pending specialization is valid for the no-lava diagnostic scene only.
    start=original.index('    vec4 directSun=')
    stop=original.index('    gl_FragData[4]',start)
    lean=original[:start]+original[stop:]
    for name in ('local_lighting','bounce_receiver','leaf_transmittance','area_receiver'):
        lean=lean.replace(f'#include "/lib/{name}.glsl"\n','')
    lean=lean.replace('uniform sampler2D colortex15;\n','')
    lean=replace_once(lean,version.decode(),version.decode()+'#define environmentSkyRadiance aqualumenAreaSourceLighting_aqualumenLightField_IdleSky\n')
    four=lean.replace(',10,14 */',',10 */').replace('uniform sampler2D colortex14;\n','')
    four=four.replace('    float lampLuminance=texelFetch(colortex14,pixel,0).r;\n','').replace('    gl_FragData[4]=vec4(lampLuminance);\n','')
    return {'comp-pragma':{**comp,c:on},'comp-default':comp,'def-five':{**p3,d:lean.encode()},'def-four':{**p3,d:four.encode()}}


def build():
    sys.path.insert(0,str(ROOT/'tools'))
    from land_shadow_pack import ArchiveEntry,zip_bytes
    packs={'p3':entries(P3),'stable':entries(STABLE)}
    entries(P8)
    packs.update(variants(packs['p3'],packs['stable']))
    (OUT/'diag').mkdir(parents=True,exist_ok=True)
    receipt={}
    for name,files in packs.items():
        path={'p3':P3,'stable':STABLE}.get(name)
        if path is None:
            path=OUT/'diag'/f'Aqualumen-idle-{name}.zip'
            data=zip_bytes(tuple(ArchiveEntry(k,v) for k,v in sorted(files.items())))
            if path.exists() and path.read_bytes()!=data:
                raise ValueError(f'conflicting diagnostic {path}')
            if not path.exists(): path.write_bytes(data)
        receipt[name]={'file':str(path.relative_to(ROOT)),'sha256':digest(path),'vsP3':sorted(k for k in files.keys()|packs['p3'].keys() if files.get(k)!=packs['p3'].get(k))}
        source=OUT/'expanded'/name
        source.mkdir(parents=True,exist_ok=True)
        for program in ('composite.fsh','deferred.fsh','composite.vsh','deferred.vsh','shadowcomp2.csh'):
            text=expanded(files,program)
            (source/program).write_text(text)
            if name!='stable':
                before=expanded(packs['stable'],program)
                (source/(program+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='stable',tofile=name)))
    receipt['p8']={'file':str(P8.relative_to(ROOT)),'sha256':PINS[P8]}
    receipt['p9']={'file':str(P9.relative_to(ROOT)),'sha256':P9_SHA256}
    (R/'packs.json').write_text(json.dumps(receipt,indent=2)+'\n')


def verify_captures(reference, candidate):
    sys.path.insert(0,str(ROOT/'tools'))
    from release_pack import release_bytes
    layers=[ROOT/'release'/(name+'-preview') for name in ('lava','canopy','ground','animal','ceiling','eye','idle')]
    for folder,pack,trees in ((reference,P8,layers[:-1]),(candidate,P9,layers)):
        receipt=json.loads((R/'runs'/folder.name/'summary.json').read_text())
        expected=sha256(release_bytes(*trees)).hexdigest()
        assert receipt['validated'] and receipt['packSha256']==digest(pack)==expected
        assert all(digest(folder/name)==pin for name,pin in receipt['sources'].items())


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--verify-captures':
        verify_captures(Path(sys.argv[2]),Path(sys.argv[3]))
    elif len(sys.argv)==1:
        build()
    else:
        raise SystemExit('usage: diagnostics.py [--verify-captures REFERENCE CANDIDATE]')
