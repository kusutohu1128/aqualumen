"""Generate canonical new TEST artifacts and native sources; no installation/GL."""
import json
from pathlib import Path
import water_legacy_branch_pack as b
import water_gh_phase_pack as gh


def main():
    root=b.OUTPUT / f'cpu-pack-v{b.VERSION}'
    source=b.OUTPUT / f'native-sources-v{b.VERSION}'
    if root.exists() or source.exists():
        raise FileExistsError('New outputs required')
    source.mkdir(parents=True)
    records=[]
    for phase in (0,45):
        parent=gh.ROOT / f'reports/2026-10-06-water-band-atlas/cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip'
        original=gh._archive(gh._read(parent))
        expanded=gh._expand(original,gh.WATER)
        assert expanded==original['GH-PHASE-observed-expanded.fsh']
        (source / f'phase{phase}-parent.fsh').write_bytes(expanded)
        for call in ('full','base'):
            output=root / f'Aqualumen-ShoreProbe-world-legacy-branch-{phase}-{call}-v{b.VERSION}.zip'
            metadata=b.build(parent,call,output)
            files=gh._archive(gh._read(output))
            assert b.recover(output)==gh._read(parent)
            (source / f'phase{phase}-{call}.fsh').write_bytes(files['LEGACY-BRANCH-expanded.fsh'])
            records.append(metadata)
        for stage in range(3):
            blob=original[f'GH-PHASE-geometry-stage{stage}.glsl']
            target=source / f'geometry-stage{stage}.glsl'
            if target.exists():
                assert target.read_bytes()==blob
            else:
                target.write_bytes(blob)
    print(json.dumps(dict(schema='aqualumen-legacy-branch-cpu-packs-v1',packs=records,
        GLExecuted=False,IrisAccepted=False,physicalAccepted=False),indent=2,sort_keys=True))


if __name__=='__main__':
    main()
