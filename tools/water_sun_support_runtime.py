"""CPU support-count/reason interpretation; counts alone are not physics proof."""
import math
import struct
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from collections import Counter
from zipfile import BadZipFile

from water_tessellation_runtime import require
from water_residual_sun_reason_runtime import qualify_point,metadata_object,CATEGORIES
from water_residual_sun_iris_runtime import (IDENTITY,json_file,zip_files,guard_observation,
    readback_points)

ROOT=Path(__file__).resolve().parents[1]
SOURCE_PINS={
    'water_sun_support_pack.py':'c229872b2906003599181800ab6cf5ed8a61685a675ebb04fa06b9e3bfd81abb',
    'water_sun_support_reference.py':'90fa6e06cbef8b38cdcbc2471ba3f8b7bb4506c1216422253c84fd8b27b0bcff',
    'water_snell_boundary_reference.py':'511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0'}


def sha(value): return hashlib.sha256(value).hexdigest()


def pack_policy(pack):
    """NEW manifest/source contract, not inherited Snell/reason policy."""
    for filename,pin in SOURCE_PINS.items():
        require(sha(Path(__file__).with_name(filename).read_bytes())==pin,'Approved source/reference tool changed')
    from water_sun_support_pack import build_pack,MANIFEST
    files=zip_files(pack);metadata=metadata_object(files[MANIFEST])
    mode=metadata.get('mode');observe=metadata.get('observe')
    require(mode in ('reject','zero') and observe in ('reasons','inputs'),'Unsupported support observation')
    # Reproduce the approved source construction in an isolated CPU directory.
    # No caller file is edited. All parent pins/recoveries are enforced there.
    with tempfile.TemporaryDirectory(prefix='support-source-contract-') as temporary:
        expected=build_pack(ROOT,Path(temporary)/'expected.zip',mode,observe)
        require(files==zip_files(expected),'Current support source/manifest differs from approved construction')
    return metadata


def decode_counts(encoded):
    """Public same-draw base64 four-count lane, lossless binary32 only."""
    require(type(encoded) in (float,int) and math.isfinite(encoded)
        and encoded==int(encoded) and 0<=encoded<2**24
        and struct.unpack('<f',struct.pack('<f',encoded))[0]==encoded,
        'Finite exact binary32 certificate count lane required')
    remaining=int(encoded);result={}
    for name in ('zero','support','unknown','calls'):
        remaining,result[name]=divmod(remaining,64)
        require(result[name]<=48,'Certificate count outside declared48 nodes')
    require(remaining==0 and result['zero']+result['support']+result['unknown']==result['calls'],
        'Certificate outcomes must account every actual call')
    return result


def analyze_reason_point(point,mode):
    """Public NEW packed-lane interpretation; other reason/TES gates retained."""
    require(mode in ('reject','zero'),'Unknown support policy mode')
    counts=decode_counts(point['sun_status'][2])
    # Explicit sourceKind0 is a NEW authoritative metadata constant, not this
    # packed lane. Delegate only unchanged x/y/w, old reasons/C/flags/TES.
    qualified={**point,'sun_status':[*point['sun_status'][:2],0,point['sun_status'][3]]}
    qualify_point(qualified)
    if mode=='reject':
        require(counts['calls']==0,'Exact reject control cannot call certificate')
    elif point['sun_status'][1]:
        require(counts['calls']==48 and counts['unknown']==0,
            'Applied zero policy lacks complete certain certificate loop')
    require(not counts['calls'] or point['sun_status'][0]==1,
        'Certificate invoked without original request')
    if mode=='zero':
        require(counts['unknown']<=point['reasonTuple'][3]
            and counts['unknown']<=point['sun_status'][3],
            'Unknown certificate lacks original category2/other counted rejection')
        require(sum(point['reasonTuple'][1:])<=48-counts['zero'],
            'Certified absent nodes cannot count as rejected original nodes')
    return dict(**point,reasonClassification=qualified['reasonClassification'],
        certificateCounts=counts,certificateCountsCollected=mode=='zero',
        all48CertificateCallsObserved=mode=='zero' and counts['calls']==48,
        continuousCapZeroProven=False,FresnelOrTIRZeroProven=False,
        GPUArithmeticCauseProven=False,physicalAccepted=False,visualAccepted=False)


def audit(raw_file,pack,guard_raw):
    """Public saved-file audit; separate guard and fixed16 FINAL, read-only."""
    pack=Path(pack);metadata=pack_policy(pack)
    identity={**IDENTITY,'packName':pack.name,'packSha256':sha(pack.read_bytes())}
    guard=json_file(guard_raw);guard_observation(guard,identity)
    raw=json_file(raw_file);points=readback_points(raw,identity)
    if metadata['observe']=='inputs':
        from water_snell_main_runtime import analyze_record
        from water_sun_support_reference import classify,ETA
        records=[dict(x=p['x'],y=p['y'],mean_called=p['coefficients'],view_requested=p['sun_status'],
            covariance_flags=p['covariance_flags'],first_target_reason=p['stage']) for p in points]
        points=[analyze_record(record) for record in records]
        for point in points:
            point['exactSupportReference']=(classify(point['view_requested'][:3],
                point['first_target_reason'][:3],ETA) if point['firstNodeIndex'] is not None else None)
        return dict(schema='aqualumen-water-sun-support-input-audit-v1',mode=metadata['mode'],
            observe='inputs',selectedPoints=len(points),inputEvidenceQualified=True,readbackQualified=True,
            guardUniformQualified=True,sourceRecoveryQualified=True,
            firstReasonHistogram={str(k):sum(p['firstReason']==k for p in points) for k in range(10)},
            firstTargetExactSupportClasses=dict(Counter(str(p['exactSupportReference']['class'])
                for p in points if p['exactSupportReference'] is not None)),
            helperCalledPoints=sum(p['helperCalled'] for p in points),requestedPoints=sum(p['requested'] for p in points),
            recordedFirstTargets=sum(p['firstNodeIndex'] is not None for p in points),points=points,
            packSha256=identity['packSha256'],sourceSha256=dict(helper=metadata['helper_sha256'],
                observerWaterFS=metadata['observer_water_fs_sha256']),
            guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],minimumApplicationGateUnchanged=4,
            targetAndFirstReasonStoredTogether=True,TESObserved=False,applicationObserved=False,
            certificateCountsCollected=False,all48NodePhysicalClassificationsProven=False,
            continuousCapZeroProven=False,FresnelOrTIRZeroProven=False,
            actualSunUniformObserved=False,sameFrameGuardAndReadbackProven=False,GPUArithmeticCauseProven=False,
            physicalAccepted=False,visualAccepted=False,pixelAAAccepted=False,performanceAccepted=False,
            energyAccepted=False,reciprocityAccepted=False,shippingAccepted=False,
            scope='Same-draw first failed target/reason input only. Exact rational first-target CPU reference, not GPU certificate outcomes, TES, counts, application or appearance proof.')
    # Rename historical C9 before using any reason validator. C10.z is NEW.
    for point in points: point['reasonTuple']=point.pop('coefficients')
    points=[analyze_reason_point(point,metadata['mode']) for point in points]
    triples={tuple(round(v,4) for v in p['stage'][:3]) for p in points if p['stage'][3]!=0}
    stage_points=sum(p['stage'][3]!=0 for p in points)
    require(stage_points>=4 and len(triples)>=2,'Vacuous/constant actual TES output')
    applied=sum(p['sun_status'][1]==1 for p in points)
    histogram={str(k):sum(p['reasonTuple'][0]==k for p in points) for k in range(1,10)}
    groups={name:sum(p['reasonTuple'][i] for p in points)
        for i,name in enumerate(('hemisphere','receiver','other'),1)}
    counts={name:sum(p['certificateCounts'][name] for p in points)
        for name in ('zero','support','unknown','calls')}
    categories={**CATEGORIES,'2':'certificate_unknown_or_inverse_node_status_rejection'}
    return dict(schema='aqualumen-water-sun-support-reason-audit-v1',mode=metadata['mode'],
        observe='reasons',selectedPoints=len(points),stagePresentPoints=stage_points,
        qualifiedAppliedPoints=applied,requestedPoints=sum(p['sun_status'][0]==1 for p in points),
        loopRejectedPoints=sum(sum(p['reasonTuple'][1:])>0 for p in points),
        unclassifiedRejectedPoints=sum(sum(p['reasonTuple'][1:])==0 and p['sun_status'][3]>0 for p in points),
        firstReasonHistogram=histogram,firstReasonCategories=categories,groupedRejectedNodes=groups,
        category2Scope=('Stable inverse status!=1; reject control never calls support certificate'
            if metadata['mode']=='reject' else 'Certificate unknown OR unchanged inverse status!=1; compound category'),
        certificateCounts=counts,certificateCountsCollected=metadata['mode']=='zero',
        complete48CertificateLoopPoints=sum(p['all48CertificateCallsObserved'] for p in points),
        reasonEvidenceQualified=True,readbackQualified=True,guardUniformQualified=True,
        actualFourRoleBindingsQualified=True,sourceRecoveryQualified=True,
        operatorActiveQualified=applied>=4,minimumQualifiedAppliedPoints=4,
        applicationVerdict='QUALIFIED_SELECTED_APPLICATION' if applied>=4 else 'NEGATIVE_INSUFFICIENT_APPLICATION',
        packSha256=identity['packSha256'],sourceSha256=dict(helper=metadata['helper_sha256'],
            observerWaterFS=metadata['observer_water_fs_sha256'],physicalWaterFS=metadata['physical_water_fs_sha256']),
        guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],points=points,
        distinctBarycentricTriples=len(triples),continuousCapZeroProven=False,FresnelOrTIRZeroProven=False,
        all48NodePhysicalClassificationsProven=False,sameFrameProven=False,drawIssuedProven=False,
        fragmentFetchProven=False,observerPassivityAccepted=False,GPUArithmeticCauseProven=False,
        actualSunUniformObserved=False,energyAccepted=False,reciprocityAccepted=False,
        physicalAccepted=False,visualAccepted=False,pixelAAAccepted=False,motionAccepted=False,
        performanceAccepted=False,shippingAccepted=False,
        scope='Selected same-draw counts and first/group failures only. Prepared guard is separate; no individual all48 physics, continuum integral, TIR coefficient, arithmetic cause, visual or shipping proof.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    args=parser.parse_args()
    try: report=audit(args.raw,args.pack,args.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected water Sun support observation: '+type(failure).__name__+'\n')
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    if report['observe']=='reasons' and not report['operatorActiveQualified']: raise SystemExit(1)


if __name__=='__main__': main()
