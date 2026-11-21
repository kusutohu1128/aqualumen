"""Aligned-v2 selected-role audit; atlas addresses/physical acceptance stay pending."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile

import water_atlas_aligned_pack as aligned
import water_gh_phase_runtime as original
from water_residual_sun_iris_runtime import IDENTITY, guard_observation, json_file

DEPENDENCY_PINS = {
    'water_atlas_aligned_pack.py': 'dbf582ce12177765280a557f97d26ffafec0ed465c3968c9b1ee72409c34221e',
    'water_gh_phase_runtime.py': '453117e5bdc4a24b93fa06f1a32ba7ce793840cbd4320993f130a536f80ebc36',
    'water_residual_sun_iris_runtime.py': 'a18e8f7c9bfb4ace2b1e3d5ac5ddfabf4dc46ef115f4e0f334f21d90da91e977',
    'water_tessellation_runtime.py': 'd5c02544f41eaf1dfe9e5f1845f2d6148f636baf1785fd74d9f833feafada20f',
    'water_sun_support_runtime.py': 'f7d37236671e4333ac12312dae32cd6cdec39023dee01622f12258d7bc680d31',
}
REMAINING_REQUIREMENTS = [
    'PENDING_ATLAS_ADDRESS_QUALIFICATION',
    'PENDING_ACTUAL_FINAL_LINKED_SOURCE_QUALIFICATION',
    'PENDING_SAME_INVOCATION_BAND_POINT_CAPTURE',
    'PENDING_OBSERVER_PASSIVITY_AND_DRAW_FRESHNESS',
    'PENDING_VISUAL_PHYSICAL_ENERGY_MOTION_ACCEPTANCE',
]


def source_policy(encoded, name):
    """Exact new archive recovery, without relaxing the frozen old auditor."""
    for dependency, pin in DEPENDENCY_PINS.items():
        original.require(hashlib.sha256(Path(__file__).with_name(dependency).read_bytes()).hexdigest()
                         == pin, 'Frozen audit dependency differs: ' + dependency)
    files = aligned.gh._archive(encoded)
    parent = files[aligned.PARENT_ARCHIVE]
    expected, metadata = aligned._files(parent)
    original.require(files == expected, 'Aligned source, manifest or unchanged member differs')
    original.require(encoded == aligned.gh._zip(expected), 'Canonical aligned archive differs')
    phase = metadata['phase_degrees']
    original.require(name == f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip',
                     'Dedicated aligned-v2 diagnostic filename required')
    return metadata


def audit(raw_file, pack, guard_file):
    """Immutable 900p original-sixteen-point seam; not atlas alignment proof.

    Inputs must be freshly collected for this exact pack. Passing synthetic
    protocol tests or swapping a historical capture's identity is not a run.
    """
    pack = Path(pack)
    encoded = aligned.gh._read(pack)
    metadata = source_policy(encoded, pack.name)
    identity = {**IDENTITY, 'packName':pack.name, 'packSha256':aligned.gh.sha(encoded)}
    guard = json_file(guard_file)
    guard_observation(guard, identity)
    raw = json_file(raw_file)
    # Preserve the original ordered16 coordinates, seven typed/distinct roles,
    # bounded level0 reads, original observer protocol and eleven-state checks.
    points = original._readback(raw, identity)
    report = original.qualify_points(points, authorized=1)
    stages = [p['stage'] for p in points if p['stage'][3] != 0]
    triples = {tuple(round(v,4) for v in stage[:3]) for stage in stages}
    original.require(len(stages)>=4 and len(triples)>=2, 'Vacuous/constant TES selection')
    report.update(
        schema='aqualumen-water-atlas-aligned-selected-readback-audit-v2',
        phase_degrees=metadata['phase_degrees'], role='diagnostic-aligned-v2',
        readbackQualified=True, guardUniformQualified=True, sourceRecoveryQualified=True,
        actualSevenRoleBindingsQualified=True, stagePresentPoints=len(stages),
        distinctBarycentricTriples=len(triples), packSha256=identity['packSha256'],
        currentFINALsha256=metadata['current_FINAL_sha256'],
        parentPackSha256=metadata['parent_pack_sha256'], dependencySha256=DEPENDENCY_PINS,
        guardFrame=guard['frameBefore'], finalSnapshotFrame=raw['snapshotFrame'], points=points,
        applicationVerdict=('QUALIFIED_SELECTED_APPLICATION' if report['operatorActiveQualified']
                            else 'NEGATIVE_INSUFFICIENT_APPLICATION'),
        atlasTexelAddressesObserved=False, atlasCoordinateQualified=False,
        viewUniformsObserved=False, actualFINALLinkedSourceQualified=False,
        alignedRuntimeAccepted=False, physicalBandFixAccepted=False,
        all48InputIdentityProven=False, energyAccepted=False, reciprocityAccepted=False,
        performanceAccepted=False, remainingRequirements=REMAINING_REQUIREMENTS,
        scope='Original sixteen raw selected roles and separate int1 guard only; '
              'no atlas fetch-address, actual FINAL linked-source, band-pixel, draw/freshness, '
              'pixel-AA, visual, physical or shipping proof',
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('pack', type=Path)
    parser.add_argument('guard_raw', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.raw, args.pack, args.guard_raw)
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, RuntimeError,
            OverflowError, UnicodeError) as failure:
        parser.exit(1, 'Rejected aligned selected readback: ' + type(failure).__name__ + '\n')
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    # Exit0 qualifies only the explicitly bounded selected-application scope.
    # alignedRuntimeAccepted deliberately remains false even with16 applications.
    if not report['operatorActiveQualified']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
