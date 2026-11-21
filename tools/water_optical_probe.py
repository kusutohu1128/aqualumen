#!/usr/bin/env python3
"""Generate an exclusive optical TEST pack and pinned same-FINAL observer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

BASE = "reports/2026-10-22-joint-paired-water/packs/paired.zip"
BASE_SHA = "95bbbd6984e2aef7be8d94bf04742ce18aea2151fe44c6ed0cd55cb08b15ebb0"
VERSION = "0.1.0-optics3"
JAR = f"aqualumen-paired-water-probe-{VERSION}.jar"
CHANNELS = {
    1: ("worldPosition.x", "worldPosition.y", "worldPosition.z", "waterMeanSurfaceY"),
    2: ("geometricNormal.x", "geometricNormal.y", "geometricNormal.z", "upperSurface + 2*localColumnKnown"),
    3: ("orientedNormal.x", "orientedNormal.y", "orientedNormal.z", "grazingBlend"),
    13: ("n.x", "n.y", "n.z", "refractionDiscriminant"),
    14: ("v.x", "v.y", "v.z", "skyAccess"),
    15: ("transmitted.x", "transmitted.y", "transmitted.z", "receiverKind"),
}
SOURCE_PINS = {
    "dev/aqualumen/paired/CaptureRules.java": "c88385ca8956981a486ec964760be7ff874ac0327b2af04b3b7eccbafbd8100d",
    "dev/aqualumen/paired/GlReadback.java": "822c523c74c71a1fe26999a9b51368649a0e7ff3e092107c1cda4181996ad461",
    "dev/aqualumen/paired/PairedObserver.java": "7a564cd8a5772cfb6cc19e5ba98071ae11c8355aa50e45fbde1678bb585d372a",
    "dev/aqualumen/paired/mixin/PairedMixin.java": "ded3e6b44d48a65d2707bf37cdff8a8441ff503abd60f130d82229c10405ab13",
    "test/dev/aqualumen/paired/CaptureRulesTest.java": "4162cf6c83cbf13cbc131bc468678125845dc602d0e868b30781d2fa8ed65900",
    "fabric.mod.json": "0fc37b6c3055e2e44a1d38f72690515655a0df4e8b42309980d6f0aad3c74c82",
    "aqualumen-paired-water.mixins.json": "b48fb9fd16a5817afe774cd48de812667cb6e5d67e6404fdbfb7b29d8fce8f9d",
}
BENCHMARK = "build/aqualumen-benchmark-0.3.9-projection-guards.jar"
BENCHMARK_SHA = "ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_one(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"strict anchor count differs: {old[:100]!r}")
    return text.replace(old, new, 1)


def read_pinned(path: Path, expected: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or redirected input: {path}")
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f"input pin differs: {path}")
    return data


def optical_pack(entries: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(entries)
    f = result["shaders/gbuffers_water.fsh"].decode()
    f = replace_one(f, "/* RENDERTARGETS: 0,12 */", "/* RENDERTARGETS:0,12,1,2,3,13,14,15 */")
    declarations = "\n".join(
        f"/*\nconst int colortex{i}Format = RGBA32F;\n*/\nconst bool colortex{i}Clear = true;\nconst vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);"
        for i in CHANNELS
    )
    prepare = result["shaders/prepare.fsh"].decode()
    result["shaders/prepare.fsh"] = replace_one(prepare, "void main() {", declarations + "\nvoid main() {").encode()
    f = replace_one(f, "void main() {", "void main() {\n" + "\n".join(
        f"    gl_FragData[{slot}]=vec4(0.0);" for slot in range(2, 8)))
    f = replace_one(f, "    if (upperSurface) {\n        // A hidden analytic facet", "    vec3 opticalOrientedNormal=n;\n    float opticalGrazingBlend=1.0;\n    if (upperSurface) {\n        // A hidden analytic facet")
    f = replace_one(f, "        n=normalize(mix(geometricNormal,n,resolved));", "        opticalGrazingBlend=resolved;\n        n=normalize(mix(geometricNormal,n,resolved));")
    f = replace_one(f, "    vec3 refractedSky=vec3(0.0);", "    float opticalRefractionDiscriminant=0.0;\n    vec3 refractedSky=vec3(0.0);")
    anchor = "        bool continuousSkyFootprint=waterRefractionFootprintContinuous(refractionDiscriminant);"
    f = replace_one(f, anchor, "        opticalRefractionDiscriminant=refractionDiscriminant;\n" + anchor)
    stores = ["vec4(worldPosition,waterMeanSurfaceY)",
              "vec4(geometricNormal,(upperSurface?1.0:0.0)+2.0*(localColumnKnown?1.0:0.0))",
              "vec4(opticalOrientedNormal,opticalGrazingBlend)",
              "vec4(n,opticalRefractionDiscriminant)", "vec4(v,skyAccess)",
              "vec4(transmitted,float(receiverKind))"]
    anchor = "    gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);"
    f = replace_one(f, anchor, anchor + "\n" + "\n".join(
        f"    gl_FragData[{slot}]=underwater?{value}:vec4(0.0);"
        for slot, value in enumerate(stores, 2)))
    result["shaders/gbuffers_water.fsh"] = f.encode()
    f = result["shaders/final.fsh"].decode()
    f = replace_one(f, "uniform sampler2D colortex12;", "uniform sampler2D colortex12;\n" + "\n".join(f"uniform sampler2D colortex{i};" for i in CHANNELS))
    f = replace_one(f, "if (aqualumenPairedView!=0)", "if (aqualumenPairedView==1)")
    anchor = "        gl_FragColor=vec4(clamp(texelFetch(colortex12,ivec2(gl_FragCoord.xy),0).xyz*vec3(0.2,1.0,1.0/48.0),0.0,1.0),1.0);"
    f = replace_one(f, anchor, anchor + "\n" + "\n".join(
        f"    if (aqualumenPairedView=={view}) gl_FragColor=texelFetch(colortex{i},ivec2(gl_FragCoord.xy),0);"
        for view, i in enumerate(CHANNELS, 2)))
    result["shaders/final.fsh"] = f.encode()
    prop = result["shaders/shaders.properties"].decode()
    if any(f"blend.gbuffers_water.colortex{i}=" in prop for i in CHANNELS):
        raise ValueError("optical attachment blend key already exists")
    result["shaders/shaders.properties"] = (prop + "\n" + "\n".join(f"blend.gbuffers_water.colortex{i}=off" for i in CHANNELS) + "\n").encode()
    return result


def observer_sources(sources: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(sources)
    key = "dev/aqualumen/paired/GlReadback.java"
    s = result[key].decode()
    s = replace_one(s, 'throw new IllegalStateException("unsupported bound sampler storage/base");',
                    'throw new IllegalStateException("unsupported bound sampler storage/base "+name+" "+width+"x"+height+" format="+format+" base="+parameter(33084));')
    anchor = "    public static FloatBuffer beauty(int fbo,int texture,int w,int h)throws Exception {"
    addition = '''    public static FloatBuffer rawFloats(Map<String,Object> sampler,int w,int h)throws Exception {
        return preserving(REAL,()->{
            active(33984+(int)sampler.get("unit"));
            if(integer(32873)!=(int)sampler.get("texture"))throw new IllegalStateException("optical binding changed");
            cleanPack();FloatBuffer data=poison(Math.multiplyExact(Math.multiplyExact(w,h),4));
            gl("GL11C","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},3553,0,6408,5126,data);
            for(int i=0;i<data.capacity();i++)if(!Float.isFinite(data.get(i)))throw new IllegalStateException("nonfinite or unwritten optical component");
            return data;
        });
    }
'''
    result[key] = replace_one(s, anchor, addition + anchor).encode()
    key = "dev/aqualumen/paired/PairedObserver.java"
    s = result[key].decode()
    s = replace_one(s, "FloatBuffer diagnostic,Map<String,Object> manifest) {}", "FloatBuffer diagnostic,FloatBuffer sourceC0,Map<String,Map<String,Object>> opticalSamplers,Map<String,FloatBuffer> opticalData,Map<String,Object> manifest) {}")
    anchor = '            FloatBuffer diagnostic=GlReadback.diagnostic(c12,request.width(),request.height());'
    s = replace_one(s, anchor, anchor + '''
            Map<String,Map<String,Object>> opticalSamplers=opticalSamplers(identity.program(),request.width(),request.height());
            FloatBuffer sourceC0=GlReadback.rawFloats(c0,request.width(),request.height());
            Map<String,FloatBuffer> opticalData=new LinkedHashMap<>();
            for(var entry:opticalSamplers.entrySet())opticalData.put(entry.getKey(),GlReadback.rawFloats(entry.getValue(),request.width(),request.height()));
            if(!opticalSamplers.equals(opticalSamplers(identity.program(),request.width(),request.height())))throw new IllegalStateException("optical samplers changed during input read");
            manifest.put("opticalSamplers",opticalSamplers);''')
    s = replace_one(s, "pending=new Pending(game,out,config,request,identity,c0,c12,diagnostic,manifest);", "pending=new Pending(game,out,config,request,identity,c0,c12,diagnostic,sourceC0,opticalSamplers,opticalData,manifest);")
    anchor = "            FloatBuffer beauty=GlReadback.beauty(after.fbo(),after.output(),after.width(),after.height());"
    check = '            if(!p.opticalSamplers().equals(opticalSamplers(after.program(),after.width(),after.height())))throw new IllegalStateException("optical samplers changed after FINAL");'
    s = replace_one(s, anchor, check + "\n" + anchor + "\n" + check)
    anchor = '            files.put("classification",write(p.out(),"classification.rgba32f",CaptureRules.littleEndian(p.diagnostic())));'
    s = replace_one(s, anchor, anchor + '''
            files.put("sourceC0",write(p.out(),"source-C0.rgba32f",CaptureRules.littleEndian(p.sourceC0())));
            for(var entry:p.opticalData().entrySet())files.put("optics-"+entry.getKey(),write(p.out(),"optics-"+entry.getKey()+".rgba32f",CaptureRules.littleEndian(entry.getValue())));
            m.put("opticalSamplerMapsMatchedAfterQuad",true);''')
    s = replace_one(s, 'm.put("observerVersion","0.1.0");', f'm.put("observerVersion","{VERSION}");m.put("opticalSchema","aqualumen-water-interface-optics-v1");')
    channels_java = ",".join(f'"colortex{i}",List.of(' + ",".join(json.dumps(c) for c in channels) + ")" for i, channels in CHANNELS.items())
    anchor = '        m.put("routeNames",List.of('
    if s.count(anchor) != 1:
        raise ValueError("route metadata anchor differs")
    s = s.replace(anchor, '        m.put("opticalChannels",Map.of(' + channels_java + '));\n' + anchor)
    anchor = "    private static boolean scope(Path game,Properties config)throws Exception {"
    addition = '''    private static Map<String,Map<String,Object>> opticalSamplers(int program,int w,int h)throws Exception {
        Map<String,Map<String,Object>> samplers=new LinkedHashMap<>();
        for(String name:List.of("colortex1","colortex2","colortex3","colortex13","colortex14","colortex15"))samplers.put(name,GlReadback.sampler(program,name,w,h));
        Set<Integer> textures=new HashSet<>();
        for(var sampler:samplers.values())if(!textures.add((int)sampler.get("texture")))throw new IllegalStateException("optical textures alias");
        int c0=(int)GlReadback.sampler(program,"colortex0",w,h).get("texture"),c12=(int)GlReadback.sampler(program,"colortex12",w,h).get("texture");
        if(textures.contains(c0)||textures.contains(c12)||textures.contains(GlReadback.attachment(36049)))throw new IllegalStateException("optical input/output textures alias");
        return samplers;
    }
'''
    result[key] = replace_one(s, anchor, addition + anchor).encode()
    meta = json.loads(result["fabric.mod.json"])
    meta["version"] = VERSION
    meta["name"] = "Aqualumen TEST Optical Same-FINAL Probe"
    result["fabric.mod.json"] = (json.dumps(meta, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return result


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("unsafe archive entry")
            info = zipfile.ZipInfo(name, (2026, 10, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)


def build_observer(root: Path, out: Path, source_dir: Path, artifact_name: str = JAR) -> dict:
    if Path(artifact_name).name != artifact_name or not artifact_name.endswith('.jar'):
        raise ValueError('unsafe observer artifact name')
    prism = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher")
    java = prism / "java/java-runtime-delta/bin"
    benchmark = root / BENCHMARK
    read_pinned(benchmark, BENCHMARK_SHA)
    cp = ":".join(map(str, [prism / "libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar", prism / "libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar", benchmark]))
    classes, tests = out / "classes", out / "test-classes"
    classes.mkdir(); tests.mkdir()
    commands = [[str(java / "javac"), "-proc:none", "-cp", cp, "-d", str(classes), *map(str, sorted((source_dir / "dev").rglob("*.java")))],
                [str(java / "javac"), "-proc:none", "-cp", str(classes), "-d", str(tests), str(source_dir / "test/dev/aqualumen/paired/CaptureRulesTest.java")],
                [str(java / "java"), "-Djava.awt.headless=true", "-cp", f"{tests}:{classes}", "dev.aqualumen.paired.CaptureRulesTest"]]
    receipt = {"commands": commands, "benchmarkSha256": BENCHMARK_SHA, "exitCode": 0}
    for index, command in enumerate(commands):
        run = subprocess.run(command, capture_output=True, text=True)
        (out / f"build-{index}.stdout").write_text(run.stdout)
        (out / f"build-{index}.stderr").write_text(run.stderr)
        if run.returncode:
            receipt["exitCode"] = run.returncode
            return receipt
    entries = {str(p.relative_to(classes)): p.read_bytes() for p in classes.rglob("*.class")}
    for p in source_dir.glob("*.json"):
        entries[p.name] = p.read_bytes()
    write_zip(out / artifact_name, entries)
    receipt["observerSha256"] = sha((out / artifact_name).read_bytes())
    receipt["artifact"] = artifact_name
    return receipt


def generate(root: Path, out: Path, build: bool = False) -> dict:
    raw = read_pinned(root / BASE, BASE_SHA)
    with zipfile.ZipFile(root / BASE) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("duplicate base archive member")
        entries = {name: archive.read(name) for name in archive.namelist()}
    sources = {name: read_pinned(root / "tools/paired-water-probe" / name, pin) for name, pin in SOURCE_PINS.items()}
    pack = optical_pack(entries)
    generated = observer_sources(sources)
    out.mkdir(parents=True, exist_ok=False)
    source_dir = out / "observer-sources"
    source_dir.mkdir()
    for name, data in generated.items():
        path = source_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
    write_zip(out / "optical.zip", pack)
    receipt = {"schema": "aqualumen-optical-probe-build-v1", "basePackSha256": sha(raw),
               "pack": "optical.zip", "packSha256": sha((out / "optical.zip").read_bytes()),
               "outputOrder": [0, 12, *CHANNELS], "opticalChannels": {f"colortex{i}": list(v) for i, v in CHANNELS.items()},
               "sourcePins": SOURCE_PINS, "generatedSourceSha256": {name: sha(data) for name, data in generated.items()},
               "observerBuild": build_observer(root, out, source_dir) if build else None,
               "productionSourceModified": False, "gpuVerified": False, "physicalAccepted": False}
    with (out / "manifest.json").open("x") as output:
        json.dump(receipt, output, indent=2); output.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--build-observer", action="store_true")
    args = parser.parse_args()
    receipt = generate(args.root.resolve(), args.out.absolute(), args.build_observer)
    print(json.dumps(receipt, indent=2))
    return 0 if not receipt["observerBuild"] else receipt["observerBuild"]["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
