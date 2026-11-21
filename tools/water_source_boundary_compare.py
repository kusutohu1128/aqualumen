"""Strict old/fixed source-node controls and receiver retention, not full goal."""
import argparse
import json
from pathlib import Path
import struct
from water_source_boundary_audit import audit,records,PIXEL


def compare(old,old_source,fixed,fixed_source):
    old,fixed=Path(old),Path(fixed)
    a=audit(old,old_source);b=audit(fixed,fixed_source)
    assert a['order']==b['order'] and a['observedPlaneMisses']>0
    assert b['observedPlaneMisses']==b['hitsOutsideOracleSafetyViewport']==0
    before=records(old/'green/observer-nodes.bin');after=records(fixed/'green/observer-nodes.bin')
    assert len(before)==len(after)
    unchanged=retained=recovered=0
    for x,y,old_node,new_node in zip(before,after,a['selected'],b['selected']):
        for slot in (0,1,2,3,4,5,8,9,10,11,12):
            assert struct.pack('<4f',*x[slot])==struct.pack('<4f',*y[slot]);unchanged+=1
        if old_node['actualHit']:
            assert new_node['actualHit'];retained+=1
            assert x[6]==y[6] and x[7]==y[7]
        elif old_node['visibleMiss']:
            assert new_node['actualHit'];recovered+=1
        else:assert not new_node['actualHit']
    for tag in ('black','green'):
        x={p.name:p.read_bytes() for p in (old/tag/'observer-actual-inputs').glob('input-sampler*.f32')}
        y={p.name:p.read_bytes() for p in (fixed/tag/'observer-actual-inputs').glob('input-sampler*.f32')}
        assert len(x)==len(y)==8 and x==y;unchanged+=8
        assert (old/tag/'observer-actual-inputs/state.json').read_bytes()==(fixed/tag/'observer-actual-inputs/state.json').read_bytes()
        assert (old/tag/'observer-depth.f32').read_bytes()==(fixed/tag/'observer-depth.f32').read_bytes();unchanged+=1
        # Opaque source, geometry coordinates, raw context/status and diffuse
        # transmission at the exact corrected TEST evaluation point stay fixed.
        for slot in (1,2,3,4,5,6):
            x=(old/tag/f'observer-slot{slot}.rgba32f').read_bytes()
            y=(fixed/tag/f'observer-slot{slot}.rgba32f').read_bytes()
            assert x[PIXEL:PIXEL+16]==y[PIXEL:PIXEL+16];unchanged+=1
    return dict(schema='aqualumen-source-boundary-compare-v1',order=a['order'],
        exactSelectedAndInputComparisons=unchanged,unchangedNodeCount=len(before),
        oldPositiveReceiversRetained=retained,knownPlaneMissesRecovered=recovered,
        newOutsideOrPreviouslyAbsentHitCount=0,
        oldGreen=a['capturedGreen'],fixedGreen=b['capturedGreen'],
        firstPlaneGeometryQualified=True,physicalKernelWeightsUnitsChanged=False,
        wholeC0NeutralityClaimed=False,arbitraryGeometryAccepted=False,
        IrisAccepted=False,temporalAccepted=False,shippingAccepted=False,
        scope='Exact same input/geometry/optical-node fields, original positives retained and ONLY independently known observed-plane misses recovered. Original MAIN still one TEST pixel; no general source-convergence/first-object or full-goal acceptance.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('old','old_source','fixed','fixed_source'):parser.add_argument(name)
    args=parser.parse_args();print(json.dumps(compare(args.old,args.old_source,args.fixed,args.fixed_source),indent=2,sort_keys=True))
