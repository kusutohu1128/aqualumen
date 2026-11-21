#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import water_optical_probe as probe


BASE = "reports/2026-10-22-underwater-rim-fix/hit1"
ARCHIVE_PINS = {
    "control": "31540e3de53edec87d73087b1217072a45aee3a04f2b9e2ab7e93d4d6a06231e",
    "paired": "9bf027a4905a420a43a6e67eb48155e545a210eb2e654fe7b69fb692e92490a2",
}
SOURCE_PINS = {
    "dev/aqualumen/paired/CaptureRules.java": "c88385ca8956981a486ec964760be7ff874ac0327b2af04b3b7eccbafbd8100d",
    "dev/aqualumen/paired/GlReadback.java": "1f78b08abdc208e526469b4b98ec79df0506b895377da85f1b1b03ea953136fe",
    "dev/aqualumen/paired/PairedObserver.java": "c1430e1ba831adecd0b0335babb255b60ba73e2ba3357b4846d26b7bf1d9b8e7",
    "dev/aqualumen/paired/mixin/PairedMixin.java": "ded3e6b44d48a65d2707bf37cdff8a8441ff503abd60f130d82229c10405ab13",
    "test/dev/aqualumen/paired/CaptureRulesTest.java": "4162cf6c83cbf13cbc131bc468678125845dc602d0e868b30781d2fa8ed65900",
    "fabric.mod.json": "fede80b6a62a121abe3231e798c22a435d5e2f8119ed7637e7150f72fd2ad12e",
    "aqualumen-paired-water.mixins.json": "b48fb9fd16a5817afe774cd48de812667cb6e5d67e6404fdbfb7b29d8fce8f9d",
}
VERSIONS = {"baseline": "0.1.0-hit1d", "candidate": "0.1.0-depth1"}
CHANNELS = dict(probe.CHANNELS)
CHANNELS[2] = ("distanceToEye", "transmission.r", "transmission.g", "transmission.b")
CHANNELS[3] = ("opticalPoint.x", "opticalPoint.y", "opticalPoint.z", "projectedDepthOrNegativeStatus")
DEPTH_CHANNELS = {
    "depthtex0": ("survivingTranslucentDepth",),
    "depthtex1": ("preTranslucentOpaqueDepth",),
}


def water_depth(entries: dict[str, bytes], helper: str, mode: str, paired: bool) -> dict[str, bytes]:
    candidate = mode == "candidate"
    if mode not in VERSIONS:
        raise ValueError("unknown depth mode")
    result = dict(entries)
    if not candidate and not paired:
        return result
    f = result["shaders/gbuffers_water.fsh"].decode()
    f = probe.replace_one(f, "void main() {", helper + "\nvoid main() {")
    if candidate:
        f = probe.replace_one(f, "void main() {", "void main() {\n    gl_FragDepth=gl_FragCoord.z;")
    anchor = "    int continuousStatus=-1;"
    f = probe.replace_one(f, anchor, anchor + "\n    WaterPrimaryHit primaryHit=waterPrimaryHit(worldPosition,worldPosition,-1);")
    anchor = "                if(continuousStatus==0)opticalPoint=solved;"
    replacement = "                primaryHit=waterPrimaryHit(worldPosition,solved,continuousStatus);\n"
    replacement += "                if(primaryHit.accepted)opticalPoint=primaryHit.point;" if candidate else anchor
    f = probe.replace_one(f, anchor, replacement)
    if candidate:
        anchor = "    vec3 opticalViewPos=(gbufferModelView*vec4(opticalPoint,1.0)).xyz;"
        f = probe.replace_one(f, anchor, """    vec3 opticalViewPos=primaryHit.viewPoint;
    if(primaryHit.accepted) {
        gl_FragDepth=primaryHit.windowDepth;
        straightPath=opaqueDepth<0.999999?clamp(length(opaquePosition-opticalViewPos),0.0,48.0):48.0;
    }""")
        f = probe.replace_one(f, "shadowVisibility(worldPosition,n)*skyAccess", "shadowVisibility(opticalPoint,n)*skyAccess")
    if paired:
        f = probe.replace_one(f, "gl_FragData[4]=underwater?vec4(opticalPoint,float(continuousStatus)):vec4(0.0);",
                              "gl_FragData[4]=underwater?vec4(opticalPoint,continuousStatus==0?(primaryHit.accepted?primaryHit.windowDepth:-2.0):-1.0):vec4(0.0);")
    result["shaders/gbuffers_water.fsh"] = f.encode()
    return result


def passive_observation(entries: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(entries)
    f = result["shaders/composite.fsh"].decode()
    f = probe.replace_one(f, "/* DRAWBUFFERS:0 */", "/* RENDERTARGETS:0,2 */")
    f = probe.replace_one(f, "void main() {", "void main() {\n    gl_FragData[1]=vec4(0.0);")
    anchor = "        vec3 transmission=waterTransmission(distanceToEye);"
    f = probe.replace_one(f, anchor, anchor + "\n        gl_FragData[1]=vec4(distanceToEye,transmission);")
    result["shaders/composite.fsh"] = f.encode()
    f = result["shaders/final.fsh"].decode()
    f = probe.replace_one(f, "uniform sampler2D colortex15;", "uniform sampler2D colortex15;\nuniform sampler2D depthtex0;\nuniform sampler2D depthtex1;")
    anchor = "    if (aqualumenPairedView==7) gl_FragColor=texelFetch(colortex15,ivec2(gl_FragCoord.xy),0);"
    f = probe.replace_one(f, anchor, anchor + """
    if (aqualumenPairedView==8) gl_FragColor=vec4(vec3(texelFetch(depthtex0,ivec2(gl_FragCoord.xy),0).r),1.0);
    if (aqualumenPairedView==9) gl_FragColor=vec4(vec3(texelFetch(depthtex1,ivec2(gl_FragCoord.xy),0).r),1.0);""")
    result["shaders/final.fsh"] = f.encode()
    f = result["shaders/shaders.properties"].decode()
    if "blend.composite.colortex2=" in f:
        raise ValueError("composite observation blend key already present")
    result["shaders/shaders.properties"] = (f + "\nblend.composite.colortex2=off\n").encode()
    return result


DEPTH_READER = '''    public static Map<String,Object> depthSampler(int program,String name,int w,int h)throws Exception {
        int unit=uniform(program,name,35678);
        if(unit<0||unit>=integer(35661))throw new IllegalStateException("depth sampler unit");
        return preserving(REAL,()->{
            active(33984+unit);int texture=integer(32873);
            if(texture<=0||!(boolean)gl("GL11C","glIsTexture",new Class<?>[]{int.class},texture))
                throw new IllegalStateException("missing bound depth texture");
            int width=level(4096),height=level(4097),format=level(4099);
            if(width!=w||height!=h||!Set.of(33190,36012,35056,36013).contains(format)||parameter(33084)!=0)
                throw new IllegalStateException("unsupported depth sampler storage/base "+name+" "+width+"x"+height+" format="+format+" base="+parameter(33084));
            int sampler=(int)gl("GL30C","glGetIntegeri",new Class<?>[]{int.class,int.class},35097,unit);
            int compare=parameter(34892);
            int effectiveCompare=sampler==0?compare:(int)gl("GL33C","glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,34892);
            if(compare!=0||effectiveCompare!=0)throw new IllegalStateException("depth comparison mode must be NONE");
            Map<String,Object> out=new LinkedHashMap<>();out.put("name",name);out.put("unit",unit);out.put("texture",texture);
            out.put("width",width);out.put("height",height);out.put("format",format);out.put("baseLevel",parameter(33084));
            out.put("maxLevel",parameter(33085));out.put("minFilter",parameter(10241));out.put("magFilter",parameter(10240));
            out.put("wrapS",parameter(10242));out.put("wrapT",parameter(10243));out.put("samplerObject",sampler);
            out.put("compareMode",compare);out.put("effectiveCompareMode",effectiveCompare);
            for(var e:Map.of("effectiveMinFilter",10241,"effectiveMagFilter",10240,"effectiveWrapS",10242,"effectiveWrapT",10243).entrySet())
                out.put(e.getKey(),sampler==0?parameter(e.getValue()):gl("GL33C","glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,e.getValue()));
            return out;
        });
    }
    public static FloatBuffer rawDepth(Map<String,Object> sampler,int w,int h)throws Exception {
        return preserving(REAL,()->{
            active(33984+(int)sampler.get("unit"));
            if(integer(32873)!=(int)sampler.get("texture"))throw new IllegalStateException("depth binding changed");
            cleanPack();FloatBuffer data=poison(Math.multiplyExact(w,h));
            gl("GL11C","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},3553,0,6402,5126,data);
            for(int i=0;i<data.capacity();i++) {
                float value=data.get(i);
                if(!Float.isFinite(value)||value<0.0f||value>1.0f)throw new IllegalStateException("nonfinite, unwritten or out-of-range depth component");
            }
            return data;
        });
    }
'''

DEPTH_SAMPLERS = '''    private static Map<String,Map<String,Object>> depthSamplers(int program,int w,int h)throws Exception {
        Set<Integer> textures=new HashSet<>();
        for(String name:List.of("colortex0","colortex12","colortex1","colortex2","colortex3","colortex13","colortex14","colortex15"))
            textures.add((int)GlReadback.sampler(program,name,w,h).get("texture"));
        textures.add(GlReadback.attachment(36049));
        Map<String,Map<String,Object>> samplers=new LinkedHashMap<>();
        for(String name:List.of("depthtex0","depthtex1")) {
            Map<String,Object> sampler=GlReadback.depthSampler(program,name,w,h);
            if(!textures.add((int)sampler.get("texture")))throw new IllegalStateException("depth/color/output textures alias");
            samplers.put(name,sampler);
        }
        return samplers;
    }
'''


def observer_sources(sources: dict[str, bytes], mode: str) -> dict[str, bytes]:
    version = VERSIONS[mode]
    result = dict(sources)
    key = "dev/aqualumen/paired/GlReadback.java"
    f = result[key].decode()
    f = probe.replace_one(f, "    public static int uniform(int program,String name,int requiredType)throws Exception {", DEPTH_READER + "    public static int uniform(int program,String name,int requiredType)throws Exception {")
    result[key] = f.encode()
    key = "dev/aqualumen/paired/PairedObserver.java"
    f = result[key].decode()
    f = probe.replace_one(f, "Map<String,FloatBuffer> opticalData,Map<String,Object> manifest) {}",
                          "Map<String,FloatBuffer> opticalData,Map<String,Map<String,Object>> depthSamplers,Map<String,FloatBuffer> depthData,Map<String,Object> manifest) {}")
    anchor = '            manifest.put("opticalSamplers",opticalSamplers);'
    f = probe.replace_one(f, anchor, anchor + '''
            Map<String,Map<String,Object>> depthSamplers=depthSamplers(identity.program(),request.width(),request.height());
            Map<String,FloatBuffer> depthData=new LinkedHashMap<>();
            for(var entry:depthSamplers.entrySet())depthData.put(entry.getKey(),GlReadback.rawDepth(entry.getValue(),request.width(),request.height()));
            if(!depthSamplers.equals(depthSamplers(identity.program(),request.width(),request.height())))throw new IllegalStateException("depth samplers changed during input read");
            manifest.put("depthSamplers",depthSamplers);''')
    f = probe.replace_one(f, "pending=new Pending(game,out,config,request,identity,c0,c12,diagnostic,sourceC0,opticalSamplers,opticalData,manifest);",
                          "pending=new Pending(game,out,config,request,identity,c0,c12,diagnostic,sourceC0,opticalSamplers,opticalData,depthSamplers,depthData,manifest);")
    anchor = "            FloatBuffer beauty=GlReadback.beauty(after.fbo(),after.output(),after.width(),after.height());"
    check = '            if(!p.depthSamplers().equals(depthSamplers(after.program(),after.width(),after.height())))throw new IllegalStateException("depth samplers changed after FINAL");'
    f = probe.replace_one(f, anchor, check + "\n" + anchor + "\n" + check)
    anchor = '            m.put("opticalSamplerMapsMatchedAfterQuad",true);'
    f = probe.replace_one(f, anchor, anchor + '''
            for(var entry:p.depthData().entrySet())files.put("depth-"+entry.getKey(),write(p.out(),"depth-"+entry.getKey()+".r32f",CaptureRules.littleEndian(entry.getValue())));
            m.put("depthSamplerMapsMatchedAfterQuad",true);''')
    f = probe.replace_one(f, "    private static boolean scope(Path game,Properties config)throws Exception {", DEPTH_SAMPLERS + "    private static boolean scope(Path game,Properties config)throws Exception {")
    f = probe.replace_one(f, 'm.put("observerVersion","0.1.0-hit1");m.put("opticalSchema","aqualumen-water-interface-optics-v1");',
                          f'm.put("observerVersion","{version}");m.put("opticalSchema","aqualumen-water-hit-depth-v1");')
    f = probe.replace_one(f, '"colortex2",List.of("geometricNormal.x","geometricNormal.y","geometricNormal.z","upperSurface + 2*localColumnKnown")',
                          '"colortex2",List.of("distanceToEye","transmission.r","transmission.g","transmission.b")')
    f = probe.replace_one(f, '"colortex3",List.of("opticalPoint.x","opticalPoint.y","opticalPoint.z","continuousStatus")',
                          '"colortex3",List.of("opticalPoint.x","opticalPoint.y","opticalPoint.z","projectedDepthOrNegativeStatus")')
    anchor = '        m.put("routeNames",List.of('
    if f.count(anchor) != 1:
        raise ValueError("route metadata anchor differs")
    metadata = f'''        m.put("depthCandidateWritesAcceptedHit",{str(mode == "candidate").lower()});
        m.put("projectedDepthStatus",Map.of("ineligibleOrUnsolved",-1,"projectionRejected",-2));
        m.put("compositeObservation","C2 is the actual composite eye distance and single Beer transmission; zero outside underwater");
        m.put("depthChannels",Map.of("depthtex0",List.of("survivingTranslucentDepth"),"depthtex1",List.of("preTranslucentOpaqueDepth")));
        m.put("depthEncoding","one IEEE754 binary32 little-endian depth component per pixel; bottom-up x+y*width");
'''
    f = f.replace(anchor, metadata + anchor, 1)
    result[key] = f.encode()
    metadata = json.loads(result["fabric.mod.json"])
    metadata["version"] = version
    metadata["name"] = "Aqualumen TEST Hit Depth Same-FINAL Probe"
    result["fabric.mod.json"] = (json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return result


def generate(root: Path, out: Path, mode: str, build: bool = False) -> dict:
    if mode not in VERSIONS:
        raise ValueError("unknown depth mode")
    base = root / BASE
    archives = {}
    for label, pin in ARCHIVE_PINS.items():
        path = base / (label + ".zip")
        probe.read_pinned(path, pin)
        with zipfile.ZipFile(path) as archive:
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError("duplicate archive member")
            archives[label] = {name: archive.read(name) for name in archive.namelist()}
    sources = {name: probe.read_pinned(base / "observer-sources" / name, pin) for name, pin in SOURCE_PINS.items()}
    helper = Path(__file__).with_name("water_hit_depth_test.glsl").read_bytes()
    generated = observer_sources(sources, mode)
    packs = {label: water_depth(entries, helper.decode(), mode, label == "paired") for label, entries in archives.items()}
    packs["paired"] = passive_observation(packs["paired"])
    out.mkdir(parents=True, exist_ok=False)
    source_dir = out / "observer-sources"
    source_dir.mkdir()
    for name, data in generated.items():
        path = source_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
    for label, entries in packs.items():
        probe.write_zip(out / (label + ".zip"), entries)
    receipt = {
        "schema": "aqualumen-water-hit-depth-build-v1", "testOnly": True, "mode": mode, "observerVersion": VERSIONS[mode],
        "inputArchiveSHA256": ARCHIVE_PINS, "sourcePins": SOURCE_PINS,
        "helperSHA256": probe.sha(helper), "generatorSHA256": probe.sha(Path(__file__).read_bytes()),
        "generatedSourceSha256": {name: probe.sha(data) for name, data in generated.items()},
        "generatedPackSourceSha256": {label: {name: probe.sha(data) for name, data in entries.items()} for label, entries in packs.items()},
        "archives": {label: probe.sha((out / (label + ".zip")).read_bytes()) for label in packs},
        "outputOrder": [0, 12, 1, 2, 3, 13, 14, 15], "compositeOutputOrder": [0, 2],
        "opticalChannels": {f"colortex{i}": list(channels) for i, channels in CHANNELS.items()},
        "depthChannels": {name: list(channels) for name, channels in DEPTH_CHANNELS.items()},
        "observerBuild": probe.build_observer(root, out, source_dir, f"aqualumen-paired-water-probe-{VERSIONS[mode]}.jar") if build else None,
        "productionSourceModified": False, "gpuVerified": False, "physicalAccepted": False, "visualAccepted": False,
        "limitations": [
            "Frozen 17 s, zero ripples, known deep columns and .035 footprint only.",
            "Baseline retains hit1 shading and implicit raster depth. Candidate accepts finite same-pixel projected first hits and writes their depth.",
            "C3.w is projected optical depth, -1 ineligible or unsolved, -2 projection rejected. C2 is overwritten by the actual composite distance/transmission.",
            "Raster eligibility, derivatives, verticalDepth and source incidentDepth are unchanged. No opaque-depth or raster-winner guard.",
            "Native and actual Iris depth, occlusion, composite passivity, whole-scene visibility, visual and performance acceptance require separate evidence.",
        ],
    }
    with (out / "manifest.json").open("x") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exclusive hit1d baseline or depth1 TEST copies.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=VERSIONS, required=True)
    parser.add_argument("--build-observer", action="store_true")
    args = parser.parse_args()
    receipt = generate(args.root.resolve(), args.out.absolute(), args.mode, args.build_observer)
    print(json.dumps(receipt, indent=2))
    return 0 if not receipt["observerBuild"] else receipt["observerBuild"]["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
