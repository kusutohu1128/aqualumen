"""Saved prepared-context TEST telemetry; no physics/appearance acceptance."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import BadZipFile

from water_tessellation_runtime import require
from water_residual_sun_iris_runtime import (IDENTITY, json_file, zip_files,
                                           guard_observation, readback_points)
from water_sun_support_runtime import pack_policy as support_policy, analyze_reason_point
from water_residual_sun_reason_runtime import CATEGORIES

SOURCE_PINS = {
    'water_sun_prepared_pack.py': '6120f584a3d2307f95ec063248dd312f56a30feecca8786aa46d04c0363d2eef',
    'water_sun_support_runtime.py': 'f7d37236671e4333ac12312dae32cd6cdec39023dee01622f12258d7bc680d31',
    'water_residual_sun_iris_runtime.py': 'a18e8f7c9bfb4ace2b1e3d5ac5ddfabf4dc46ef115f4e0f334f21d90da91e977',
    'water_residual_sun_reason_runtime.py': '4782c027ee1f2a5683f702ed631cc73217bd178a7cc5a7597f102c0e92b2d84d',
    'water_snell_main_runtime.py': 'dc1fabf8706821f7f9a5e813bdfd45c2092a6317841ed09ffafd2237860f5ad8'}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def pack_policy(pack):
    """Exact candidate-member recovery, then the unchanged old zero policy."""
    for name, pin in SOURCE_PINS.items():
        require(sha(Path(__file__).with_name(name).read_bytes()) == pin,
                'Pinned construction/validator changed')
    from water_sun_prepared_pack import recover_pack, MANIFEST
    with tempfile.TemporaryDirectory(prefix='prepared-runtime-recovery-') as temporary:
        parent = Path(temporary) / 'parent.zip'
        receipt = recover_pack(pack, parent)
        metadata = json_file_bytes(zip_files(pack)[MANIFEST])
        role = metadata['role']
        require(receipt['role'] == role and
                Path(pack).name == f'Aqualumen-ShoreProbe-world-sun-prepared-{role}-v1.zip',
                'Wrong prepared role/installed alias')
        require(role in ('reasons', 'inputs'), 'Physical FINAL has no qualified selected telemetry')
        old = support_policy(parent)
        require(old['mode'] == 'zero', 'Prepared parent must retain certified-zero policy')
    return metadata, old


def json_file_bytes(encoded):
    from water_residual_sun_reason_runtime import metadata_object
    return metadata_object(encoded)


def reason_report(points):
    for point in points:
        point['reasonTuple'] = point.pop('coefficients')
    points = [analyze_reason_point(point, 'zero') for point in points]
    triples = {tuple(round(v, 4) for v in p['stage'][:3]) for p in points if p['stage'][3] != 0}
    present = sum(p['stage'][3] != 0 for p in points)
    require(present >= 4 and len(triples) >= 2, 'Vacuous/constant actual TES output')
    applied = sum(p['sun_status'][1] == 1 for p in points)
    return dict(points=points, stagePresentPoints=present, distinctBarycentricTriples=len(triples),
        qualifiedAppliedPoints=applied, requestedPoints=sum(p['sun_status'][0] == 1 for p in points),
        loopRejectedPoints=sum(sum(p['reasonTuple'][1:]) > 0 for p in points),
        unclassifiedRejectedPoints=sum(sum(p['reasonTuple'][1:]) == 0 and p['sun_status'][3] > 0 for p in points),
        firstReasonHistogram={str(k): sum(p['reasonTuple'][0] == k for p in points) for k in range(1, 10)},
        firstReasonCategories={**CATEGORIES, '2': 'certificate_unknown_or_inverse_node_status_rejection'},
        groupedRejectedNodes={name: sum(p['reasonTuple'][i] for p in points)
                              for i, name in enumerate(('hemisphere', 'receiver', 'other'), 1)},
        certificateCounts={name: sum(p['certificateCounts'][name] for p in points)
                           for name in ('zero', 'support', 'unknown', 'calls')},
        certificateCountsCollected=True,
        complete48CertificateLoopPoints=sum(p['all48CertificateCallsObserved'] for p in points),
        reasonEvidenceQualified=True, TESObserved=True, applicationObserved=True,
        operatorActiveQualified=applied >= 4, minimumQualifiedAppliedPoints=4,
        applicationVerdict='QUALIFIED_SELECTED_APPLICATION' if applied >= 4 else 'NEGATIVE_INSUFFICIENT_APPLICATION',
        perCategoryNodeCountsObserved=False, coefficientClosureObserved=False,
        reasonCountsScope='First category per texel; grouped counts combine3/9 and6/7, not every individual node category.')


def input_report(points):
    from water_snell_main_runtime import analyze_record
    from water_sun_support_reference import classify, ETA
    records = [dict(x=p['x'], y=p['y'], mean_called=p['coefficients'], view_requested=p['sun_status'],
                    covariance_flags=p['covariance_flags'], first_target_reason=p['stage']) for p in points]
    points = [analyze_record(record) for record in records]
    for point in points:
        point['exactSupportReference'] = (classify(point['view_requested'][:3],
            point['first_target_reason'][:3], ETA) if point['firstNodeIndex'] is not None else None)
    return dict(points=points, inputEvidenceQualified=True,
        firstReasonHistogram={str(k): sum(p['firstReason'] == k for p in points) for k in range(10)},
        firstTargetExactSupportClasses=dict(Counter(str(p['exactSupportReference']['class'])
            for p in points if p['exactSupportReference'] is not None)),
        helperCalledPoints=sum(p['helperCalled'] for p in points), requestedPoints=sum(p['requested'] for p in points),
        recordedFirstTargets=sum(p['firstNodeIndex'] is not None for p in points),
        targetAndFirstReasonStoredTogether=True, TESObserved=False, applicationObserved=False,
        certificateCountsCollected=False, minimumApplicationGateUnchanged=4,
        applicationVerdict='APPLICATION_NOT_OBSERVED')


def audit(raw_file, pack, guard_raw):
    """Public read-only files: NEW identity, existing strict observation gates."""
    pack = Path(pack)
    metadata, old = pack_policy(pack)
    role = metadata['role']
    require(role in ('reasons', 'inputs'), 'Physical FINAL has no qualified selected telemetry')
    identity = {**IDENTITY, 'packName': pack.name, 'packSha256': sha(pack.read_bytes())}
    guard = json_file(guard_raw)
    guard_observation(guard, identity)
    raw = json_file(raw_file)
    points = readback_points(raw, identity)
    report = reason_report(points) if role == 'reasons' else input_report(points)
    report.update(schema='aqualumen-water-sun-prepared-runtime-v1', role=role, mode='zero',
        observe=role, selectedPoints=len(points), readbackQualified=True, guardUniformQualified=True,
        sourceRecoveryQualified=True, actualFourRoleBindingsQualified=True,
        packName=pack.name, packSha256=identity['packSha256'], parentPackSha256=metadata['parent_pack_sha256'],
        oldSourceSha256=dict(helper=old['helper_sha256'], observerWaterFS=old['observer_water_fs_sha256']),
        sourceSha256=dict(metadata['current_sha256']), validatorSourceSha256=dict(SOURCE_PINS),
        oldExpandedMainSha256=metadata['old_expanded_main_sha256'],
        preparedExpandedMainSha256=metadata['prepared_expanded_main_sha256'],
        guardFrame=guard['frameBefore'], finalSnapshotFrame=raw['snapshotFrame'],
        sameFrameProven=False, drawIssuedProven=False, fragmentFetchProven=False,
        observerPassivityAccepted=False, all48NodePhysicalClassificationsProven=False,
        all48RawInputsObserved=False, GPUArithmeticCauseProven=False, actualSunUniformObserved=False,
        continuousCapZeroProven=False, FresnelOrTIRZeroProven=False,
        geometryAccepted=False, physicalAccepted=False, pixelAAAccepted=False,
        visualAccepted=False, motionAccepted=False, performanceAccepted=False,
        energyAccepted=False, reciprocityAccepted=False, shippingAccepted=False,
        scope='Exact prepared pack recovery plus separate saved guard and fixed16 FINAL telemetry. '
              'Counts or first target are not an all48 raw arithmetic oracle; no PNG, motion, physics or shipping acceptance.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('pack', type=Path)
    parser.add_argument('guard_raw', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.raw, args.pack, args.guard_raw)
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, RuntimeError, OverflowError, UnicodeError) as failure:
        parser.exit(1, 'Rejected prepared Sun observation: ' + type(failure).__name__ + '\n')
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    if report['applicationVerdict'] == 'NEGATIVE_INSUFFICIENT_APPLICATION':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
