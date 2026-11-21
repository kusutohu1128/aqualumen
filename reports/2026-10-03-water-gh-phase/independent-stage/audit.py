"""CPU replay of saved Iris linked stages and separate prepared int1 guard.

This does not reconstruct Iris rewriting or prove a draw/fragment/visual result.
The fixed ZIP pins identify source policy; queried rewritten geometry is compared
only with other actual queried rewritten geometry, never archive expansion.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools'))
from water_residual_sun_iris_runtime import (IDENTITY, exact_fields,
    guard_observation, json_file)

PARENT = 'b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452'
PACKS = {
    (0, 'physical'): 'cbfa626c253f658edec76de060d80820ab484ce19e94ca0128d8c4af3f0c38c7',
    (45, 'physical'): 'd0dbf90d3470eb6faac24a5e2077ce3cb1ef1b1fc56aa8debb6942015da6187b',
    (0, 'diagnostic'): '04b9e74db4d34d505ae3e385568cd6b720568c16df0f66809f2e664f975cfda8',
    (45, 'diagnostic'): '088866e780d0d86fd8b787dfd18e617a516658246b57f5fe962b2871b45ae88d',
}
STAGES = ((35633, 'vertex'), (36488, 'tess_control'),
          (36487, 'tess_evaluation'), (35632, 'fragment'))
VERSIONS = dict(aqualumen_water_stage_probe='0.1.0', aqualumen_benchmark='0.3.9',
    iris='1.8.8', sodium='0.6.9', minecraft='1.21.1', aqualumen_physics='0.3.0')
LIMITS = dict(drawIssuedProven=False, exclusiveWaterProgramProven=False,
    tessInvocationCountProven=False, fragmentFetchProven=False,
    allSixteenTexelsSameFrameProven=False, sameNodeCountProven=False,
    PNGSameFrameProven=False, visualCauseProven=False, physicalAccepted=False,
    shippingAccepted=False, GLExecutedByAuditor=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_pair(stage_file, guard_file, pack):
    """Public immutable-file interface; observations may be different events."""
    pack = Path(pack)
    match = re.fullmatch(r'Aqualumen-ShoreProbe-world-gh-phase-(0|45)-(physical|diagnostic)-v1.zip', pack.name)
    require(match is not None, 'Fixed GH alias required')
    phase, role = int(match[1]), match[2]
    digest = sha(pack)
    require(digest == PACKS[(phase, role)], 'Frozen ZIP differs')
    with ZipFile(pack) as archive:
        metadata = json.loads(archive.read('WATER-GH-PHASE.json'))
    exact_fields(metadata, dict(schema='aqualumen-water-gh-phase-v1', phase_degrees=phase,
        role=role, test_only=True, not_shipping=True, parent_pack_sha256=PARENT,
        geometry_factor=4, fixed_phase_seconds=120.0, guard_unchanged=True), 'Wrong frozen policy')
    identity = {**IDENTITY, 'packName': pack.name, 'packSha256': digest}
    guard = json_file(guard_file)
    guard_observation(guard, identity)
    stage = json_file(stage_file)
    exact_fields(stage, {**IDENTITY, 'schema':'aqualumen-water-stage-observation-v1',
        'observerVersion':'0.1.0', 'available':True, 'scope':'terrain-tessellation-stages',
        'readOnly':True, 'errorFlagConsumed':False, 'localIntegratedSinglePlayer':True,
        'scopeAccepted':True, 'currentPipelineMatches':True, 'afterSetupStateTail':True,
        'pass':'TRANSLUCENT', 'constructorContainsTessellation':True,
        'expectedPack':pack.name, 'expectedPackSha256':digest,
        'usingTessellationAtAdmission':True, 'sourceHashesRequested':True,
        'programAndFrameUnchanged':True, 'linkStatus':1, 'attachedShaderCount':4,
        'tesSourceMarkerPresent':True, 'tessControlOutputVertices':3, 'patchVertices':3,
        'naturalVisualAccepted':False, 'exclusiveWaterProgramProven':False,
        'drawIssuedProven':False, 'tessInvocationCountProven':False,
        'fragmentValueFetchProven':False, 'nativeOrNaturalAppearanceAccepted':False}, 'Wrong stage contract')
    require(stage.get('benchmarkState') in ('idle','complete','aborted'), 'Stage during measurement')
    require('errorClass' not in stage and 'reason' not in stage, 'Stage error retained')
    versions = stage.get('versions')
    require(type(versions) is dict and set(versions) == set(VERSIONS) and
        all(type(versions[k]) is str and (versions[k] == v or versions[k].startswith(v+'+'))
            for k,v in VERSIONS.items()), 'Version contract differs')
    for key in ('constructorProgram','programBefore','programAfter'):
        require(type(stage.get(key)) is int and stage[key] > 0, 'Invalid stage program')
    require(stage['constructorProgram'] == stage['programBefore'] == stage['programAfter'], 'Stage program changed')
    require(type(stage.get('frameBefore')) is int and stage['frameBefore'] >= 0 and
        type(stage.get('frameAfter')) is int and stage['frameBefore'] == stage['frameAfter'], 'Stage frame changed')
    caps = stage.get('capabilities')
    require(type(caps) is dict and type(caps.get('version')) is str and
        bool(caps['version'].strip()) and len(caps['version']) <= 256 and
        type(caps.get('renderer')) is str and len(caps['renderer']) <= 256 and 'NVIDIA' in caps['renderer'] and
        'RTX 3080 Ti' in caps['renderer'] and type(caps.get('OpenGL40')) is bool and
        type(caps.get('GL_ARB_tessellation_shader')) is bool and
        (caps['OpenGL40'] or caps['GL_ARB_tessellation_shader']), 'Actual renderer/capability missing')
    stages = stage.get('stages')
    require(type(stages) is list and len(stages) == 4 and all(type(s) is dict for s in stages), 'Four stages required')
    require(len({s.get('shader') for s in stages}) == 4, 'Aliased shaders')
    by_type = {}
    for entry in stages:
        require(type(entry.get('shader')) is int and entry['shader'] > 0 and
            type(entry.get('type')) is int and entry['type'] not in by_type, 'Typed unique shader required')
        require(type(entry.get('sourceBytes')) is int and 0 < entry['sourceBytes'] <= 262144 and
            type(entry.get('sourceSha256')) is str and re.fullmatch('[0-9a-f]{64}',entry['sourceSha256']), 'Source query bounds/hash missing')
        by_type[entry['type']] = entry
    require(set(by_type) == {x[0] for x in STAGES} and
        all(by_type[t].get('stage') == label for t,label in STAGES), 'Stage labels/types differ')
    times = []
    for observation in (guard, stage):
        require(type(observation.get('requestId')) is str and
            str(uuid.UUID(observation['requestId'])) == observation['requestId'], 'Request identity missing')
        value = observation.get('capturedUtc')
        require(type(value) is str and value.endswith('Z'), 'UTC capture time missing')
        times.append(datetime.fromisoformat(value.replace('Z','+00:00')))
    return dict(schema='aqualumen-gh-phase-stage-pair-audit-v1', phase=phase, role=role,
        preparedLinkedStagePairQualified=True, guardUniformQualified=True,
        stageTypes=[t for t,_ in STAGES], stageProgram=stage['programBefore'],
        stageFrame=stage['frameBefore'], guardProgram=guard['programBefore'], guardFrame=guard['frameBefore'],
        preparedProgramFrameCoordinatesMatch=(stage['programBefore'],stage['frameBefore']) ==
            (guard['programBefore'],guard['frameBefore']),
        separateObserverEvents=True, captureGapMilliseconds=(times[1]-times[0]).total_seconds()*1000,
        capturedUtc=dict(guard=guard['capturedUtc'],stage=stage['capturedUtc']),
        capabilities=caps, packName=pack.name, packSha256=digest,
        actualRewrittenSources={label:{'sha256':by_type[t]['sourceSha256'], 'bytes':by_type[t]['sourceBytes']}
            for t,label in STAGES},
        evidence=dict(stage={'file':Path(stage_file).name,'sha256':sha(stage_file)},
            guard={'file':Path(guard_file).name,'sha256':sha(guard_file)}), **LIMITS)


def audit(runtime, pack_directory):
    """Require all four saved pairs; compare queried source identities only."""
    runtime, pack_directory = Path(runtime), Path(pack_directory)
    pairs = []
    for phase,role in PACKS:
        stem = f'phase{phase}-{role}'
        pairs.append(audit_pair(runtime/(stem+'-stage.json'), runtime/(stem+'-guard.json'),
            pack_directory/f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-{role}-v1.zip'))
    geometry = [{k:p['actualRewrittenSources'][k] for k in ('vertex','tess_control','tess_evaluation')} for p in pairs]
    require(all(g == geometry[0] for g in geometry), 'Actual rewritten geometry changed')
    fragments = [p['actualRewrittenSources']['fragment']['sha256'] for p in pairs]
    return dict(schema='aqualumen-gh-phase-independent-stage-audit-v1', qualified=True,
        pairs=pairs, actualRewrittenGeometryThreeStagesIdentical=True,
        actualRewrittenFragmentDistinctHashes=len(set(fragments)),
        fragmentChangesAreExpected=True, archiveExpandedHashesComparedToIrisRewriting=False,
        actualRewritingReconstructedOrByteVerified=False, **LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair', nargs=3, metavar=('STAGE','GUARD','PACK'))
    parser.add_argument('directories', nargs='*', metavar='DIR')
    args = parser.parse_args()
    try:
        require(bool(args.pair) != bool(args.directories), 'Choose pair or runtime+pack directories')
        require(not args.directories or len(args.directories) == 2, 'Runtime and pack directories required')
        result = audit_pair(*args.pair) if args.pair else audit(*args.directories)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1, 'Rejected saved stage pair: '+type(error).__name__+'\n')
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
