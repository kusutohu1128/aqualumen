"""Actual same-quad encoded-output correspondence, not physical water acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import water_atlas_aligned_runtime as selected
import water_atlas_final_source as source_audit

FRAGMENT_SHA = 'd60d5452a18e5d6cdbbbc04477dfd4174b493ac5e19f9ccd6d6744f6d8ece656'
VERTEX_SHA = '2dea83d689facf9998d0af3cfaa1a975c45c440b4752841c48c31d64c18854a2'
ALIGNMENT = ((200,225),(100,225),(300,225),(200,125),(8,225),(16,225),(32,225),(48,225),
             (352,225),(368,225),(384,225),(392,225),(32,64),(368,64),(32,385),(368,385))
BANDS = ((278,90),(278,84),(278,77),(278,75))
OUTPUT_BOUND = 2/255  # RGBA8 quantization/dithering + FP evaluation, not radiance tolerance.


def require(ok, why):
    if not ok:
        raise ValueError(why)


def finite(v, n):
    return type(v) is list and len(v) == n and all(type(x) in (float,int) and math.isfinite(x) for x in v)


def exposure(uniforms):
    m=uniforms['gbufferModelViewInverse'];s=uniforms['sunPosition']
    require(m['type']==35676 and m['size']==1 and finite(m['values'],16), 'Actual matrix required')
    require(s['type']==35665 and s['size']==1 and finite(s['values'],3), 'Actual Sun required')
    m=m['values'];s=s['values'];v=[sum(m[4*j+i]*s[j] for j in range(3)) for i in range(3)]
    norm=math.sqrt(sum(x*x for x in v));require(norm>0,'Actual Sun zero')
    y=v[1]/norm;t=min(1,max(0,(y+.12)/.17));smooth=t*t*(3-2*t)
    require(type(uniforms['aqualumenDimension']) is int and uniforms['aqualumenDimension']==0,'Overworld dimension required')
    return 1+15*(1-smooth),y


def tone(rgb, e):
    c=[max(0,x*e) for x in rgb];peak=max(c)
    return [x/(1+peak) for x in c]


def physical(neighbors,e):
    values=[tone(p['rgba'][:3],e) for p in neighbors]
    luma=lambda c:sum(a*b for a,b in zip(c,[.2126,.7152,.0722]))
    spread=max(map(luma,values[1:]))-min(map(luma,values[1:]))
    t=min(1,max(0,(spread-.08)/.27));weight=t*t*(3-2*t)*.45
    return [max(0,(1-weight)*values[0][c]+weight*(2*values[0][c]+sum(v[c] for v in values[1:]))/6)**(1/2.2) for c in range(3)]


def encoded(value, source_y, tile, e):
    if tile==7:
        return [min(1,max(0,value[3]))]*3 if source_y+.5<112.5 else [x**(1/2.2) for x in tone(value[:3],e)]
    if source_y+.5<112.5:
        return [.5+.5*value[3]/(1+abs(value[3]))]*3
    return [.5+.5*x/(1+abs(x)) for x in value[:3]]


def audit(raw_file,pack,original16,guard,baseline_report=None):
    pack=Path(pack);blob=pack.read_bytes();meta=selected.source_policy(blob,pack.name)
    original=selected.audit(original16,pack,guard)
    require(original['operatorActiveQualified'] and original['qualifiedAppliedPoints']>=4,'Original sixteen/minimum4 required')
    r=json.loads(Path(raw_file).read_text());kind=r['kind'];wanted=ALIGNMENT if kind=='alignment' else BANDS if kind=='band' else ()
    require(wanted,'Unknown packet kind')
    identity=dict(schema='aqualumen-atlas-joint-output-v1',observerVersion='0.1.3',available=True,
        scopeAuthorized=True,world='AqualumenNaturalV2',worldId='b22dbccb-2970-41e6-847f-f183b1ec923d',seed=308060,
        dimension='minecraft:overworld',packName=pack.name,packSha256=hashlib.sha256(blob).hexdigest(),
        quadInvocationReturnedObserved=True,directShaderLocalAddressReadbackObserved=False)
    for key,value in identity.items():require(r.get(key)==value,'Joint identity: '+key)
    if kind=='band':
        require(baseline_report is not None,'Separately qualified alignment baseline required')
        baseline=json.loads(Path(baseline_report).read_text())
        require(baseline['encodedOutputCorrespondenceQualified'] and baseline['kind']=='alignment'
            and baseline['packSha256']==identity['packSha256'] and baseline['selectedPoints']==16,'Alignment prerequisite differs')
    require(type(r['beforeFrame']) is int and r['beforeFrame']==r['afterFrame'],'Same quad counter required')
    fs=r['final'];require(fs['available'] and fs['programFrameViewportUnchanged'] and fs['viewport']==[0,0,1600,900]
        and fs['programBefore']==fs['programAfter']==r['program'] and fs['frameBefore']==fs['frameAfter']==r['beforeFrame'],'Actual FINAL seam differs')
    for name,n in [('viewWidth',1600),('viewHeight',900)]:
        u=fs['viewUniforms'][name];require(u['size']==1 and u['type']==5126 and u['value']==n and u['location']>=0,'View scalar differs')
    require('NVIDIA' in fs['renderer'],'NVIDIA required')
    stages={s['type']:s for s in fs['stages']};require(len(fs['stages'])==2 and set(stages)=={35633,35632},'Actual linked stages required')
    for typ,pin in [(35633,VERTEX_SHA),(35632,FRAGMENT_SHA)]:
        s=stages[typ];b=s['source'].encode();require(hashlib.sha256(b).hexdigest()==s['sourceSha256']==pin and len(b)==s['sourceBytes'],'Pinned actual source differs')
    files=selected.aligned.gh._archive(blob)
    require(source_audit.main_tokens(files['shaders/final.fsh'].decode())==source_audit.main_tokens(stages[35632]['source'],True),'Actual main differs')
    addresses=r['addresses'];require([(a['localX'],a['localY']) for a in addresses]==list(wanted),'Bounded packet coordinates differ')
    n=len(wanted);coords=[(4*x+2,2*y+1) for x,y in wanted]
    require([(a['sourceX'],a['sourceY']) for a in addresses]==coords,'Integer address derivation differs')
    raw=r['raw'];require(raw['available'] and raw['stateRestored'] and raw['stateBefore']==raw['stateAfter']
        and raw['program']==raw['expectedProgram']==r['program'] and raw['width']==1600 and raw['height']==900,'Unrestored source state')
    samplers=raw['samplers'];require([s['name'] for s in samplers]==list(selected.original.NAMES),'Seven role order differs')
    require(len({s['unit'] for s in samplers})==len({s['textureId'] for s in samplers})==7,'Aliased source bindings')
    for s in samplers:
        require(s['active'] and s['textureExists'] and s['type']==35678 and s['size']==1 and s['actualFormat']==34836
            and s['width']==1600 and s['height']==900,'RGBA32F role differs')
        require([(p['x'],p['y']) for p in s['samples']]==coords and all(finite(p['rgba'],4) for p in s['samples']),'Ordered finite raw source required')
    c0=r['c0'];require(c0['available'] and c0['stateRestored'] and c0['actualFormat']==34836 and c0['width']==1600 and c0['height']==900,'C0 observation differs')
    require(c0['textureId'] not in {s['textureId'] for s in samplers} and c0['unit'] not in {s['unit'] for s in samplers},'C0 binding aliased')
    require(len(c0['samples'])==5*n,'Five taps per C0 point required')
    bounds=r['samplerMetadata'];require(len(bounds)==8,'Eight bounded source reads required')
    for s,count in [(s,n) for s in samplers]+[(c0,5*n)]:
        b=[b for b in bounds if b['unit']==s['unit'] and b['textureId']==s['textureId']]
        require(len(b)==1 and b[0]['wholeTargetReadbackBytes']==1600*900*16 and b[0]['exportedTexelCount']==count,'Read bound differs')
        require(b[0]['effectiveFilteringObserved'] and b[0]['effectiveMinFilter']==b[0]['effectiveMagFilter']==9729
            and b[0]['effectiveWrapS']==b[0]['effectiveWrapT']==33071,'Linear/clamp sampler differs')
    out=r['output'];require(out['available'] and out['stateRestored'] and out['stateBefore']==out['stateAfter']
        and out['colorEncoding']==9729 and not out['framebufferSrgbEnabled'],'Output restore/conversion differs')
    md=out['readMetadata'];require(md['width']==1600 and md['height']==900 and md['internalFormat']==32856
        and md['textureQueryBindingAndActiveRestored'] and md['targetReadBufferBefore']==md['targetReadBufferAfter'],'Actual output storage/state differs')
    output=out['pixels'];require(len(output)==8*n,'All eight tile outputs required')
    e,suny=exposure(r['transportUniforms']);maximum=0;points=[];per_tile=[0.0]*8
    for i,(lx,ly) in enumerate(wanted):
        sx,sy=coords[i];neighbors=c0['samples'][5*i:5*i+5]
        require([(p['x'],p['y']) for p in neighbors]==[(sx,sy),(sx,min(899,sy+1)),(sx,max(0,sy-1)),(min(1599,sx+1),sy),(max(0,sx-1),sy)]
            and all(finite(p['rgba'],4) for p in neighbors),'Actual C0 tap order differs')
        roles=[s['samples'][i]['rgba'] for s in samplers]
        for tile in range(8):
            p=output[8*i+tile];require((p['x'],p['y'])==(lx+400*(tile%4),ly+450*(tile//4)) and finite(p['rgba'],4),'Ordered actual output differs')
            want=physical(neighbors,e) if tile==0 else encoded(roles[tile-1],sy,tile,e)
            error=max(abs(a-b) for a,b in zip(p['rgba'][:3],want));maximum=max(maximum,error);per_tile[tile]=max(per_tile[tile],error)
            require(error<=OUTPUT_BOUND and abs(p['rgba'][3]-1)<=1/255,'Actual encoded output does not match current raw sample')
        points.append(dict(x=sx,y=sy,**{k:v for k,v in zip(selected.original.FIELDS,roles)},c0Center=neighbors[0]['rgba'],c0DisplayRgb=output[8*i]['rgba'][:3]))
    if kind=='alignment':
        telemetry=selected.original.qualify_points(points,authorized=1)
        require(telemetry['operatorActiveQualified'],'Additional baseline application is vacuous')
    else:
        for p in points:
            if p['sun_status'][1]==1:
                require(p['full_wr'][1]==p['base_wr'][1]==1 and p['reasons']==[0,0,0,0] and p['sun_status'][3]==0,'Actual raw Sun gate contradiction')
    return dict(schema='aqualumen-atlas-joint-correspondence-audit-v1',kind=kind,phase_degrees=meta['phase_degrees'],
        selectedPoints=n,packSha256=identity['packSha256'],rawSha256=hashlib.sha256(Path(raw_file).read_bytes()).hexdigest(),
        encodedOutputCorrespondenceQualified=True,actualQuadReturnObserved=True,sameQuadFrame=r['beforeFrame'],
        actualCoordinateAndFetchMainQualified=True,sourceAddressesDerivedFromVerifiedMain=True,
        directShaderLocalAddressReadbackObserved=False,originalSixteenQualifiedAppliedPoints=original['qualifiedAppliedPoints'],
        originalSixteenMinimumAppliedGate=4,maximumEncodedRgbError=maximum,perTileMaximumEncodedRgbError=per_tile,
        encodedRgbBound=OUTPUT_BOUND,exposureScale=e,actualWorldSunY=suny,points=points,
        producerFragmentInvocationDirectlyObserved=False,wholeBandCausalityAccepted=False,
        physicalAccepted=False,visualAccepted=False,motionAccepted=False,shippingAccepted=False,
        scope='Eight selected tile outputs after the same FINAL quad match pre-quad raw C9-C15/C0 taps. '
              'Addresses derived from verified integer main; no shader-local address readback, individual producer invocation, '
              'whole-frame/whole-band, energy, optical fix, or visual acceptance.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw');p.add_argument('pack');p.add_argument('original16');p.add_argument('guard');p.add_argument('--baseline-report')
    a=p.parse_args();print(json.dumps(audit(a.raw,a.pack,a.original16,a.guard,a.baseline_report),indent=2,sort_keys=True,allow_nan=False))
if __name__=='__main__':main()
