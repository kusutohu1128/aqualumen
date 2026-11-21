"""Selected new-layout GH phase telemetry; not a physical acceptance oracle."""
import math
import struct
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile

from water_sun_support_runtime import decode_counts
from water_residual_sun_iris_runtime import (IDENTITY, COORDINATES, exact_fields,
    json_file, guard_observation)
from water_tessellation_runtime import STATE_KEYS
from water_gh_phase_pack import _read, _archive, _files, MANIFEST, PARENT_ARCHIVE

FIELDS=('reasons','sun_status','outer_state','stage','full_wr','base_wr','c0_called')
NAMES=tuple('colortex'+str(n) for n in range(9,16))
BUILDER_SHA256='8c7966183672ce0006a37703f2892d8ec97db5b07943189304acbf775bcbf6b3'


def require(value,message):
    if not value:
        raise ValueError(message)


def qualify_points(points,authorized=1):
    """Public selected-point interpretation, separate from file/binding identity.

    Status/color values are producer telemetry, not independently calculated
    physical truth. Covariance is not in this layout. No pixel is dropped.
    """
    require(type(authorized) is int and authorized in (0,1),'Scalar guard0/1 required')
    require(type(points) is list and len(points)==16,'All sixteen points required')
    total=dict(zero=0,support=0,unknown=0,calls=0)
    applied=full_applied=base_applied=called=0
    for p in points:
        require(type(p) is dict and all(type(p.get(k)) is int for k in ('x','y')),
                'Typed selected coordinates required')
        for field in FIELDS:
            v=p.get(field)
            require(type(v) is list and len(v)==4 and all(type(x) in (int,float)
                and math.isfinite(x) for x in v),'Finite vec4 required: '+field)
        reasons,status,outer,stage,full,base,color=[p[k] for k in FIELDS]
        flags,grazing,receiver,ssr=outer
        require(flags==int(flags) and 0<=flags<=15,'C11 is flags, not covariance')
        flags=int(flags)
        require(not flags&8 or flags&7==7,'Eligibility lacks original domain flags')
        require(0<=grazing<=1 and receiver in (0,1,2),'Malformed outer handoff')
        require(all(x>=0 for x in color[:3]) and color[3] in (0,1),'Malformed C0/call marker')
        require(color[3]<=authorized,'Observed call lacks authorization')
        for wr in (full,base):
            require(wr[0] in (0,1) and wr[1] in (0,1) and wr[1]<=wr[0]
                and -1-8*2**-23<=wr[2]<=1+8*2**-23 and wr[3]==int(wr[3])
                and 0<=wr[3]<=18,'Malformed raw legacy WR status')
            require(not wr[1] or (flags&8 and wr[2]>0 and wr[3]==0),
                    'Legacy application lacks eligibility/facing/receiver admission')
            require(wr[1]==int(bool(flags&8 and wr[0])),
                    'Legacy applied differs from unchanged eligible-and-valid rule')
        counts=decode_counts(status[2])
        require(status[0] in (0,1) and status[1] in (0,1) and status[1]<=status[0]
            and status[3]==int(status[3]) and 0<=status[3]<=48,'Malformed WNS status')
        require(status[0]==int(bool(color[3] and flags&8)),
                'WNS request differs from actual guarded caller eligibility')
        require(not counts['calls'] or status[0]==1,'Calls lack Sun request')
        require(reasons[0]==int(reasons[0]) and 0<=reasons[0]<=9
            and all(x==int(x) and 0<=x<=48 for x in reasons[1:])
            and sum(reasons[1:])<=status[3]
            and sum(reasons[1:])<=48-counts['zero'],'Malformed Sun reason accounting')
        if sum(reasons[1:]):
            group=1 if reasons[0] in (3,9) else 2 if reasons[0] in (6,7) else 3
            require(reasons[0]>0 and reasons[group]>0 and sum(reasons[1:])==status[3],
                'First reason/group or complete loop rejection sum contradicts')
        else:
            require(reasons[0]==0 and status[3]<=1,'Unclassified rejection must remain pre/post-loop only')
        require(counts['unknown']<=status[3] and counts['unknown']<=reasons[3],
                'Unknown outcomes must retain rejection/fallback accounting')
        if status[1]:
            require(color[3]==1 and full[1]==base[1]==1 and status[3]==0
                and reasons==[0,0,0,0] and counts['calls']==48 and counts['unknown']==0,
                'Sun application lacks complete admitted legacy/control domain')
        if not color[3]:
            require(status==reasons==full==base==[0,0,0,0],
                    'Inactive caller carries active/stale operator state')
        if stage==[0,0,0,0]:
            require(outer==color==[0,0,0,0] and status==reasons==full==base==[0,0,0,0],
                    'Nonwater output is not explicitly zero')
        else:
            require(abs(stage[3]-1)<=8*2**-23 and all(-2e-5<=x<=1+2e-5 for x in stage[:3])
                and abs(sum(stage[:3])-1)<=2e-5,'Malformed TES simplex')
        for k in total:
            total[k]+=counts[k]
        called+=int(color[3]);applied+=int(status[1])
        full_applied+=int(full[1]);base_applied+=int(base[1])
    require(len({(p['x'],p['y']) for p in points})==16,'Duplicate selected points')
    return dict(selectedPoints=16,qualifiedAppliedPoints=applied,
        fullAppliedPoints=full_applied,baseAppliedPoints=base_applied,actualCalledPoints=called,
        certificateCounts=total,minimumQualifiedAppliedPoints=4,
        operatorActiveQualified=applied>=4,covarianceObserved=False,
        sameInvocationColorProducerDeclared=True,sameFrameProven=False,
        drawIssuedProven=False,fragmentFetchProven=False,observerPassivityAccepted=False,
        physicalAccepted=False,visualAccepted=False,motionAccepted=False,
        pixelAAAccepted=False,FPSFloorAccepted=False,shippingAccepted=False)


def compare_points(before,after):
    """Keep every ordered selected point; admission change is not color alias.

    Separate saved frames do not prove a controlled original-world comparison.
    This descriptive seam never selects a prettier image as physical acceptance.
    """
    old=qualify_points(before);new=qualify_points(after)
    require([(p['x'],p['y']) for p in before]==[(p['x'],p['y']) for p in after],
            'Paired selected point order differs')
    def bits(v):
        return tuple(struct.pack('<f',x) for x in v)
    changed_color=changed_admission=stable_color=flipped_color=outer_changed=0
    for a,b in zip(before,after):
        color=bits(a['c0_called'][:3])!=bits(b['c0_called'][:3])
        admission=a['full_wr'][:2]+a['base_wr'][:2]!=b['full_wr'][:2]+b['base_wr'][:2]
        changed_color+=color;changed_admission+=admission
        stable_color+=color and not admission;flipped_color+=color and admission
        outer_changed+=bits(a['outer_state'])!=bits(b['outer_state'])
    return dict(before=old,after=new,selectedPoints=16,changedColorPoints=changed_color,
        changedLegacyAdmissionPoints=changed_admission,
        changedColorWithStableLegacyAdmissionPoints=stable_color,
        changedColorWithChangedLegacyAdmissionPoints=flipped_color,
        changedOuterStatePoints=outer_changed,
        finiteQuadratureCauseProven=False,visualAccepted=False,
        physicalAccepted=False,sameFrameProven=False,shippingAccepted=False)


def _source_policy(encoded,name):
    require(hashlib.sha256(Path(__file__).with_name('water_gh_phase_pack.py').read_bytes()).hexdigest()
        ==BUILDER_SHA256,'Approved GH construction source changed')
    files=_archive(encoded)
    metadata=json.loads(files[MANIFEST])
    require(type(metadata) is dict and metadata.get('role')=='diagnostic','Diagnostic GH role only')
    phase=metadata.get('phase_degrees')
    require(type(phase) is int and phase in (0,45),'Fixed integer GH phase required')
    require(name==f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip',
        'Dedicated diagnostic filename required')
    expected,_=_files(files[PARENT_ARCHIVE],phase,'diagnostic')
    require(files==expected,'Source/manifest/embedded-parent recovery differs')
    return metadata


def _readback(raw,identity):
    """Seven real active roles, never an old-layout raw mutation/alias."""
    exact_fields(raw,{**identity,'observerVersion':'0.3.9','width':1600,'height':900,
        'available':True,'stateRestored':True,'scopeAuthorized':True,'tag':'DEBUG-shore-sampler',
        'seam':'FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
        'rawReadPolicy':'GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
        'samplingInterpretation':'unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
        'texelCoordinateConvention':'integer level-zero texture coordinates; bottom-left origin',
        'maximumSelectedTexels':16,'selectedTexelsFiniteOnly':True,'timingAcceptanceExcluded':True},
        'Wrong FINAL identity/protocol')
    require(type(raw.get('renderer')) is str and 'NVIDIA' in raw['renderer'],'NVIDIA capture required')
    require(type(raw.get('snapshotFrame')) is int and raw['snapshotFrame']>=0,'Actual snapshot frame required')
    require(type(raw.get('program')) is int and raw['program']>0
        and type(raw.get('expectedProgram')) is int and raw['program']==raw['expectedProgram'],'FINAL program mismatch')
    before,after=raw.get('stateBefore'),raw.get('stateAfter')
    require(type(before) is dict and type(after) is dict and set(before)==set(after)==STATE_KEYS
        and all(type(v) is int for v in [*before.values(),*after.values()]) and before==after,'Unrestored typed eleven-state snapshot')
    samplers,bounds=raw.get('samplers'),raw.get('samplerMetadata')
    require(type(samplers) is list and len(samplers)==7 and all(type(s) is dict for s in samplers)
        and tuple(s.get('name') for s in samplers)==NAMES,'Exactly seven ordered C9-C15 roles required')
    require(type(bounds) is list and len(bounds)==7 and all(type(s) is dict for s in bounds),'Seven readback bounds required')
    require(len({s.get('unit') for s in samplers})==len({s.get('textureId') for s in samplers})==7,'Aliased seven-role bindings')
    for sampler in samplers:
        exact_fields(sampler,dict(active=True,textureExists=True,type=35678,size=1,
            actualFormat=34836,width=1600,height=900),'Active scalar RGBA32F role required')
        require(all(type(sampler.get(k)) is int and sampler[k]>=0 for k in ('location','unit'))
            and type(sampler.get('textureId')) is int and sampler['textureId']>0,'Invalid typed role binding')
        samples=sampler.get('samples')
        require(type(samples) is list and len(samples)==16,'Sixteen samples per role required')
        coordinates=[]
        for point in samples:
            require(type(point) is dict and type(point.get('x')) is int and type(point.get('y')) is int,'Typed texel coordinates required')
            values=point.get('rgba')
            require(type(values) is list and len(values)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in values),'Finite RGBA required')
            coordinates.append((point['x'],point['y']))
        require(tuple(coordinates)==COORDINATES,'Fixed sixteen-point role order required')
        matches=[b for b in bounds if b.get('unit')==sampler['unit'] and b.get('textureId')==sampler['textureId']]
        require(len(matches)==1,'Ambiguous or missing role readback bounds')
        exact_fields(matches[0],dict(unit=sampler['unit'],textureId=sampler['textureId'],
            wholeTargetReadbackBytes=1600*900*16,exportedTexelCount=16),'Incorrect readback extent')
    return [dict(x=x,y=y,**{field:sampler['samples'][i]['rgba']
        for field,sampler in zip(FIELDS,samplers)}) for i,(x,y) in enumerate(COORDINATES)]


def audit(raw_file,pack,guard_raw):
    """Public immutable saved-file seam; guard and FINAL are separate frames."""
    pack=Path(pack);encoded=_read(pack);metadata=_source_policy(encoded,pack.name)
    identity={**IDENTITY,'packName':pack.name,'packSha256':hashlib.sha256(encoded).hexdigest()}
    guard=json_file(guard_raw);guard_observation(guard,identity)
    raw=json_file(raw_file);points=_readback(raw,identity)
    report=qualify_points(points,authorized=1)
    stages=[p['stage'] for p in points if p['stage'][3]!=0]
    triples={tuple(round(v,4) for v in s[:3]) for s in stages}
    require(len(stages)>=4 and len(triples)>=2,'Vacuous/constant TES selection')
    report.update(schema='aqualumen-water-gh-phase-runtime-audit-v1',phase_degrees=metadata['phase_degrees'],
        role='diagnostic',readbackQualified=True,guardUniformQualified=True,sourceRecoveryQualified=True,
        actualSevenRoleBindingsQualified=True,stagePresentPoints=len(stages),distinctBarycentricTriples=len(triples),
        packSha256=identity['packSha256'],sourceSha256=metadata['current_sha256'],
        builderSha256=BUILDER_SHA256,guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],
        applicationVerdict='QUALIFIED_SELECTED_APPLICATION' if report['operatorActiveQualified'] else 'NEGATIVE_INSUFFICIENT_APPLICATION',
        points=points,stageAttachmentQueryObserved=False,all48InputIdentityProven=False,
        performanceAccepted=False,energyAccepted=False,reciprocityAccepted=False,
        scope='Seven selected FINAL roles and separate prepared int1 guard; source recovery only, no actual-stage/draw/fetch/pixel/visual or physical proof')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    arguments=parser.parse_args()
    try:
        report=audit(arguments.raw,arguments.pack,arguments.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected GH phase observation: '+type(failure).__name__+'\n')
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    if not report['operatorActiveQualified']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
