"""New-layout four-point legacy ledger; never an old Sun16 gate replacement."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import water_legacy_branch_pack as packer
import water_legacy_branch_replay as replay
import water_gh_phase_pack as gh
from water_residual_sun_iris_runtime import IDENTITY, exact_fields, guard_observation, json_file
from water_tessellation_runtime import STATE_KEYS

COORDS=((1114,181),(1114,169),(1114,155),(1114,151))
NAMES=tuple(f'colortex{i}' for i in range(9,16))

def audit(raw_file,pack,guard_file):
    pack=Path(pack);blob=gh._read(pack);data=gh._archive(blob)
    meta=json.loads(data[packer.MANIFEST]);parent=packer.recover(pack)
    replay.require(meta['parentSha256']==gh.sha(parent),'Canonical parent differs')
    phase,call=meta['phase'],meta['selectedCall']
    replay.require(pack.name==f'Aqualumen-ShoreProbe-world-legacy-branch-{phase}-{call}-v{packer.VERSION}.zip','Dedicated filename required')
    identity={**IDENTITY,'packName':pack.name,'packSha256':gh.sha(blob)}
    guard_observation(json_file(guard_file),identity)
    raw=json_file(raw_file)
    exact_fields(raw,{**identity,'available':True,'stateRestored':True,'scopeAuthorized':True,
        'observerVersion':'0.3.9','width':1600,'height':900,'tag':'DEBUG-shore-sampler',
        'maximumSelectedTexels':16,'selectedTexelsFiniteOnly':True,'timingAcceptanceExcluded':True,
        'texelCoordinateConvention':'integer level-zero texture coordinates; bottom-left origin',
        'samplingInterpretation':'unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
        'rawReadPolicy':'GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
        'seam':'FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push'},'Wrong fresh raw scope')
    replay.require('NVIDIA' in raw['renderer'] and type(raw['snapshotFrame']) is int,'Actual NVIDIA/counter required')
    replay.require(type(raw['program']) is int and raw['program']>0 and raw['program']==raw['expectedProgram'],'FINAL program mismatch')
    before,after=raw['stateBefore'],raw['stateAfter']
    replay.require(set(before)==set(after)==STATE_KEYS and before==after and all(type(x) is int for x in before.values()),'Eleven caller state fields differ')
    samplers,bounds=raw['samplers'],raw['samplerMetadata']
    replay.require(len(samplers)==len(bounds)==7 and tuple(s['name'] for s in samplers)==NAMES,'Seven fresh roles required')
    replay.require(len({s['unit'] for s in samplers})==len({s['textureId'] for s in samplers})==7,'Aliased raw roles')
    for s in samplers:
        exact_fields(s,dict(active=True,textureExists=True,type=35678,size=1,actualFormat=34836,width=1600,height=900),'RGBA32F scalar role required')
        replay.require(tuple((p['x'],p['y']) for p in s['samples'])==COORDS,'Four ordered new-layout pixels required; never padded to16')
        matches=[b for b in bounds if b['textureId']==s['textureId'] and b['unit']==s['unit']]
        replay.require(len(matches)==1,'Ambiguous read bound')
        exact_fields(matches[0],dict(wholeTargetReadbackBytes=1600*900*16,exportedTexelCount=4),'Unbounded or wrong read extent')
        for p in s['samples']:
            a=p['rgba'];replay.require(type(a) is list and len(a)==4 and all(type(x) in (float,int)
                and math.isfinite(x) and struct.unpack('<f',struct.pack('<f',x))[0]==x for x in a),'Actual binary32 vec4 required')
    points=[]
    for i,(x,y) in enumerate(COORDS):
        p={field:s['samples'][i]['rgba'] for field,s in zip(replay.FIELDS,samplers)}
        result=replay.replay(p,phase)
        points.append(dict(x=x,y=y,raw=p,**result))
    return dict(schema='aqualumen-water-legacy-branch-runtime-audit-v2',phase=phase,selectedCall=call,
        packSha256=identity['packSha256'],rawReadbackQualified=True,guardUniformQualified=True,
        sourceRecoveryQualified=True,selectedPoints=4,points=points,callerStateRestored=True,
        originalSixteenMinimumAppliedGateUnchanged=4,
        thisPacketIsOriginalSixteenQualification=False,SunCurrentApplicationObserved=False,
        producerFragmentInvocationDirectlyObserved=False,pngSameFrameProven=False,
        covarianceAndRawViewObserved=True,firstFacetDirectlyObserved=False,
        physicalAccepted=False,visualAccepted=False,motionAccepted=False,shippingAccepted=False,
        scope='Four NEW-layout raw legacy records at FINAL after separate prepared guard observation. '
              'Independent double forward reconstruction is bounded away from critical/marginal signs; '
              'no original Sun16 qualification, individual producer invocation, full-frame causal or physical/quality proof.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw');p.add_argument('pack');p.add_argument('guard')
    a=p.parse_args();print(json.dumps(audit(a.raw,a.pack,a.guard),indent=2,sort_keys=True,allow_nan=False))

if __name__=='__main__':main()
