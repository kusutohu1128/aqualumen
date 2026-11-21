"""Independent CPU audit of saved original-MAIN readback; no GPU/game operations."""
import array
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-occluded-main"
DATA=OUT/"native-v4"
BOXES=[([-8,-4,-4],[8,-1,0],1),([-8,-4,-24],[8,-3,-4],2)]


def field(name):
    values=array.array("f"); values.frombytes((DATA/name).read_bytes())
    if len(values)!=129*129*4 or not all(math.isfinite(v) for v in values):
        raise ValueError("Finite field shape does not qualify: "+name)
    return values


def unit(v):
    length=math.sqrt(sum(c*c for c in v))
    return [c/length for c in v]


def first(origin,ray):
    hits=[]
    for lo,hi,identity in BOXES:
        entry=-math.inf; exit=math.inf
        for axis in range(3):
            if ray[axis]==0:
                if not lo[axis]<=origin[axis]<=hi[axis]: exit=-math.inf
                continue
            a,b=(lo[axis]-origin[axis])/ray[axis],(hi[axis]-origin[axis])/ray[axis]
            entry=max(entry,min(a,b)); exit=min(exit,max(a,b))
        if 0<entry<=exit: hits.append((entry,identity,[o+r*entry for o,r in zip(origin,ray)]))
    if not hits: raise ValueError("Independent first intersection missing")
    return min(hits)


def visible(hit):
    distance=math.sqrt(sum(c*c for c in hit[2]))
    camera=first([0,0,0],unit(hit[2]))
    return camera[1]==hit[1] and abs(camera[0]-distance)<1e-6


def fresnel(c):
    n=1.333; t=math.sqrt(1-(1-c*c)/(n*n))
    return .5*((c-n*t)/(c+n*t))**2+.5*((n*c-t)/(n*c+t))**2


def main():
    receipt=json.loads((OUT/"native-v4-receipt.json").read_text())
    if receipt["exitCode"]!=2 or receipt["compilerExitCode"]!=0 or not receipt["synchronousExclusiveBinaryBuild"]:
        raise ValueError("Qualified expected native RED/build not proven")
    log=(OUT/"native-v4.log").read_text()
    if "RTX 3080 Ti" not in log or "pixel65,53" not in log or log.count("RED:")!=2:
        raise ValueError("Actual renderer/fixed seam/two distinct REDs missing")
    for name,digest in receipt["sourceSHA256"].items():
        if hashlib.sha256((OUT/"frozen-source-v4"/name).read_bytes()).hexdigest()!=digest:
            raise ValueError("Frozen source digest changed")
    if (DATA/"camera-source-neutral.rgba32f").read_bytes()!=(DATA/"camera-source-hidden-tag.rgba32f").read_bytes():
        raise ValueError("Hidden material leaked into camera input")
    neutral=field("neutral-C0.rgba32f");hidden=field("hidden-tag-C0.rgba32f");far=field("visible-tag-C0.rgba32f")
    witness=field("witness-C0.rgba32f")
    states=[field(f"witness-state{i}.rgba32f") for i in range(1,8)]
    observer_delta=max(abs(a-b) for a,b in zip(neutral,witness))
    if observer_delta>1e-6: raise ValueError("Observer changed C0")
    controls=[]
    for role,x,y in [("hidden-first",65,53),("visible-first",65,60),("near-first",65,41)]:
        q=(y*129+x)*4
        origin=list(states[0][q:q+3]); ray=unit(list(states[3][q:q+3])); incident=unit(origin)
        snell=[incident[0]/1.333,-math.sqrt(1-(1-incident[1]**2)/1.333**2),incident[2]/1.333]
        if max(abs(a-b) for a,b in zip(ray,snell))>1e-6 or max(abs(states[2][q+i]-v) for i,v in enumerate([0,1,0]))>1e-6:
            raise ValueError("Original-MAIN actual flat normal/Snell ray not confirmed")
        hit=first(origin,ray)
        expected=(float(array.array("f",[.43])[0])-float(array.array("f",[.25])[0]))*math.exp(-.085*hit[0])*(1-fresnel(-incident[1]))
        delta=[(hidden if role=="hidden-first" else far)[q+i]-neutral[q+i] for i in range(3)]
        controls.append(dict(role=role,pixel=[x,y],origin=origin,ray=ray,firstBox=hit[1],
                             firstPoint=hit[2],firstTravel=hit[0],cameraVisible=visible(hit),
                             actualRGBDelta=delta,expectedGreen=0 if role=="near-first" else expected,
                             worldSourceTagAvailableToCurrentShader=False,screenReceiverKind=states[4][q+3],
                             screenConfidence=states[3][q+3],originalProxyPath=states[1][q+3],
                             shaderOutgoingPath=states[2][q+3]))
    h,v,n=controls
    if h["firstBox"]!=2 or h["cameraVisible"] or h["actualRGBDelta"]!=[0,0,0]: raise ValueError("Hidden first-floor RED qualification changed")
    if v["firstBox"]!=2 or not v["cameraVisible"] or abs(v["actualRGBDelta"][1]-v["expectedGreen"])>.02*v["expectedGreen"]:
        raise ValueError("Visible independent transport positive changed")
    if n["firstBox"]!=1 or n["actualRGBDelta"][1]<=1e-6: raise ValueError("Near first-floor farther-source RED changed")
    footprints=[]
    f=array.array("f",[1/math.tan(math.pi/6)])[0]
    for dx in [-.5,0,.5]:
        for dy in [-.5,0,.5]:
            i=unit([(2*(65.5+dx)/129-1)/f,(2*(53.5+dy)/129-1)/f,-1])
            point=[c*(-.5/i[1]) for c in i]
            r=[i[0]/1.333,-math.sqrt(1-(1-i[1]*i[1])/1.333**2),i[2]/1.333]
            hit=first(point,r)
            if hit[1]!=2 or visible(hit) or not (-2<hit[2][0]<2 and -9<hit[2][2]<-6):
                raise ValueError("Predeclared hidden pixel footprint unqualified")
            footprints.append(dict(pixelOffset=[dx,dy],firstPoint=hit[2],cameraVisible=False))
    result=dict(schema="aqualumen-occluded-main-audit-v1",actualRenderer="NVIDIA RTX 3080 Ti",
                actualNativeShaderReadback=True,observerC0MaxDifference=observer_delta,
                unchangedCameraInputForHiddenTag=True,independentOriginalInvocationGeometry=controls,
                independentNinePointFootprint=footprints,qualifiedRendererRedCount=2,
                currentWorldSourceInterfaceImplemented=False,newMinecraftRun=False,
                fullGoalAchieved=False,sourceAppearanceIsSyntheticFixtureNotVanilla=True)
    with (OUT/"independent-audit.json").open("x") as stream: json.dump(result,stream,indent=2,sort_keys=True)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__": main()
