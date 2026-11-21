"""One-invocation coast attribution, TEST ONLY; never changes production files."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-coast-attribution'
PACK = 'Aqualumen-CoastAttribution-TEST-v2.zip'
INFO = 'pack-v2.json'
BEGIN, END = '// DEBUG-coast-attribution-BEGIN\n', '// DEBUG-coast-attribution-END\n'


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def block(text):
    return BEGIN + text + END


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def transform(original):
    files = dict(original)
    uniforms = files['shaders/lib/uniforms.glsl'].decode()
    files['shaders/lib/uniforms.glsl'] = once(uniforms, 'uniform float frameTimeCounter;\n',
        'uniform float frameTimeCounter;\n' + block('#define frameTimeCounter 120.0\n')).encode()
    fs = files['shaders/gbuffers_water.fsh'].decode()
    fs = once(fs, '/* DRAWBUFFERS:0 */', '/* RENDERTARGETS:0,9,10,11 */')
    guard = '    localColumnKnown=localColumnKnown && waterUnknownWeight==0.0;\n'
    fs = once(fs, guard, block('    bool attributionRawColumnKnown=localColumnKnown;\n') + guard)
    nonwater = '        gl_FragData[0]=vec4(lit,tex.a);\n'
    fs = once(fs, nonwater, nonwater + block(''.join(
        f'        gl_FragData[{i}]=vec4(0.0);\n' for i in (1, 2, 3))))
    tail = '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
    fs = once(fs, tail, tail + block(
        '    gl_FragData[1]=vec4(attributionRawColumnKnown?1.0:0.0,localColumnKnown?1.0:0.0,waterUnknownWeight,1.0);\n'
        '    gl_FragData[2]=vec4(fresnel,float(receiverKind),receiverConfidence,thickness);\n'
        '    gl_FragData[3]=vec4(reflectedHit.a,upperSurface?1.0:0.0,worldNormal.y,1.0);\n'))
    files['shaders/gbuffers_water.fsh'] = fs.encode()
    prepare = files['shaders/prepare.fsh'].decode()
    annotation = ''.join(f'const int colortex{i}Format = RGBA32F;\n'
        f'const bool colortex{i}Clear = true;\n'
        f'const vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);\n' for i in (9, 10, 11))
    files['shaders/prepare.fsh'] = once(prepare, '/*\nconst int colortex0Format',
        '/*\n' + block(annotation) + 'const int colortex0Format').encode()
    files['shaders/shaders.properties'] += ('\n' + block(''.join(
        f'blend.gbuffers_water.colortex{i}=off\n' for i in (9, 10, 11)))).encode()
    final = files['shaders/final.fsh'].decode()
    final = once(final, 'uniform sampler2D colortex0;\n', 'uniform sampler2D colortex0;\n' + block(
        ''.join(f'uniform sampler2D colortex{i};\n' for i in (9, 10, 11))))
    final = once(final, 'void main() {\n', 'void main() {\n' + block('''    vec2 q=fract(texcoord*vec2(2.0));
    ivec2 size=textureSize(colortex9,0);
    ivec2 p=clamp(ivec2(q*vec2(size)),ivec2(0),size-1);
    vec4 knowledge=texelFetch(colortex9,p,0);
    vec4 transmission=texelFetch(colortex10,p,0);
    vec4 reflection=texelFetch(colortex11,p,0);
    int x=int(floor(texcoord.x*2.0)),y=int(floor(texcoord.y*2.0));
    vec3 panel=vec3(0.0);
    if (x==0 && y==1) panel=pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2));
    else if (knowledge.a>0.5) {
        if (y==1) panel=vec3(knowledge.z,knowledge.y,knowledge.x);
        else if (x==0) panel=vec3(transmission.z,transmission.y==1.0?1.0:0.0,transmission.x);
        else panel=reflection.x>0.0?vec3(0.0,1.0,0.0):vec3(1.0,0.0,1.0);
    }
    gl_FragColor=vec4(clamp(panel,0.0,1.0),1.0);
    return;
'''))
    files['shaders/final.fsh'] = final.encode()
    return files


def strip(text):
    while BEGIN in text:
        start = text.index(BEGIN)
        end = text.index(END, start) + len(END)
        text = text[:start] + text[end:]
    return text


def verify(original, files):
    changed = {n for n in original if files[n] != original[n]}
    assert changed == {'shaders/lib/uniforms.glsl', 'shaders/gbuffers_water.fsh',
        'shaders/prepare.fsh', 'shaders/shaders.properties', 'shaders/final.fsh'}
    for name in changed:
        recovered = strip(files[name].decode())
        if name.endswith('gbuffers_water.fsh'):
            recovered = once(recovered, '/* RENDERTARGETS:0,9,10,11 */', '/* DRAWBUFFERS:0 */')
        if name.endswith('shaders.properties'):
            recovered = recovered[:-1]  # exactly the added leading newline
        assert recovered.encode() == original[name], name
    assert files['shaders/gbuffers_water.vsh'] == original['shaders/gbuffers_water.vsh']
    return sorted(changed)


def build():
    assert not (OUT/PACK).exists() and not (OUT/INFO).exists()
    original = {p.relative_to(ROOT).as_posix(): p.read_bytes()
        for p in sorted([*(ROOT/'shaders').rglob('*'), ROOT/'LICENSE']) if p.is_file()}
    files = transform(original)
    changed = verify(original, files)
    OUT.mkdir(exist_ok=True)
    sources = OUT / 'diagnostic-source-v2'
    assert not sources.exists()
    for name, blob in files.items():
        target = sources / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(blob)
    packet = dict(files)
    packet.update({'original/' + n: b for n, b in original.items()})
    with (OUT/PACK).open('xb') as f, ZipFile(f, 'w', compression=ZIP_DEFLATED) as z:
        for name, blob in sorted(packet.items()):
            entry = ZipInfo(name, (2026, 10, 6, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, blob)
    record = dict(schema='aqualumen-coast-attribution-pack-v1', pack=PACK,
        packSHA256=sha((OUT/PACK).read_bytes()), changedFiles=changed,
        originalSHA256={n: sha(b) for n, b in original.items()},
        diagnosticSHA256={n: sha(b) for n, b in files.items()},
        exactOriginalRecoveryPassed=True, productionFilesModified=False,
        phaseSeconds=120.0, phaseScope='common analytic clock ONLY; not bathymetry/contact/weather',
        stores='same original water MAIN invocation, after C0 store; no second ray trace',
        C9=['raw column known', 'final column known', 'vertex unknown weight', 'water mask'],
        C10=['Fresnel', 'receiver kind:0 miss/1 opaque/2 sky', 'receiver confidence', 'optical path metres'],
        C11=['SSR path metres or negative miss', 'upper interface', 'input normal Y', 'water mask'],
        atlas='TL:original C0 tone/gamma NO final AA; TR:R vertex unknown/G final known/B raw known; BL:R receiver confidence/G opaque hit/B Fresnel; BR:green SSR hit/magenta miss',
        shipping=False, packEnforcesWorldGuard=False, nativeNeutralityProven=False,
        actualIrisAccepted=False, naturalAppearanceAccepted=False, fullGoalAchieved=False)
    with (OUT/INFO).open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
    print(json.dumps({k: record[k] for k in ('pack', 'packSHA256', 'changedFiles', 'exactOriginalRecoveryPassed')}, indent=2))


if __name__ == '__main__':
    build()
