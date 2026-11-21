"""Independent passive/raw/weight/first-plane replay, never producer PASS trust."""
from array import array
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import water_source_boundary_oracle as oracle
import water_supported_conditioned as model
import water_supported_rotated as rotated

ROOT=Path(__file__).resolve().parents[1]
PIXEL=16*(128*257+128)


def records(path):
    raw=path.read_bytes();assert len(raw)==16+4096*22*16
    count,overflow,a,b=struct.unpack_from('<4I',raw)
    assert 0<count<=4096 and overflow==a==b==0
    nodes=[list(struct.iter_unpack('<4f',raw[16+i*352:16+(i+1)*352])) for i in range(count)]
    assert all(math.isfinite(x) for n in nodes for v in n for x in v)
    # Unused storage must retain initialization bits, not stale observations.
    assert raw[16+count*352:]==struct.pack('<I',0x7fc00000)*(4*22*(4096-count))
    return nodes


def close(actual,want,absolute=2e-6,relative=2e-4):
    assert abs(actual-want)<=absolute+relative*abs(want),(actual,want,absolute,relative)


def transform(matrix,vector):
    return tuple(math.fsum(matrix[k*4+j]*vector[k] for k in range(3)) for j in range(3))


def audit(root,source):
    root,source=Path(root),Path(source)
    report=json.loads((root/'result.json').read_text())
    assert report['schema']=='aqualumen-source-boundary-main-v1'
    assert 'RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['GL']
    assert report['recordStrideVec4']==22 and report['recordCapacity']==4096
    assert report['SSBOOffset']==report['SSBOArrayStride']==16 and report['SSBOType']==35666
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    canonical=ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    assert geometry==[hashlib.sha256((canonical/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    assert len(report['sourceQueries'])==1 and len(report['sourceQueries'][0])==2
    for role,item in zip(('baseline','observer'),report['sourceQueries'][0]):
        text=(root/f'{role}.fsh').read_bytes();assert text==(source/f'{role}.fsh').read_bytes()
        assert item['stages'][3]['sha256']==hashlib.sha256(text).hexdigest()
        assert [a['sha256'] for a in item['stages'][:3]]==geometry
        assert item['currentProgramBefore']==item['currentProgramAfter']
    rule=json.loads((source/'probability-rule.json').read_text());order=rule['order']
    comparisons=0;inputs={};states={};data={};frames={}
    for tag in ('black','green'):
        inputs[tag]={};states[tag]={};frames[tag]={}
        for role in ('baseline','observer'):
            frame=[]
            for slot in range(8):
                blob=(root/tag/f'{role}-slot{slot}.rgba32f').read_bytes()
                assert len(blob)==257*257*16 and blob==(root/tag/f'{role}-repeat-slot{slot}.rgba32f').read_bytes();comparisons+=1
                assert all(math.isfinite(x) for v in struct.iter_unpack('<4f',blob) for x in v)
                if role=='observer':
                    assert blob==(root/tag/f'baseline-slot{slot}.rgba32f').read_bytes();comparisons+=1
                frame.append(struct.unpack_from('<4f',blob,PIXEL))
            frames[tag][role]=frame
            depth=(root/tag/f'{role}-depth.f32').read_bytes()
            assert len(depth)==257*257*4 and depth==(root/tag/f'{role}-repeat-depth.f32').read_bytes();comparisons+=1
            if role=='observer':
                assert depth==(root/tag/'baseline-depth.f32').read_bytes();comparisons+=1
            inp={p.name:p.read_bytes() for p in (root/tag/f'{role}-actual-inputs').glob('input-sampler*.f32')}
            state=json.loads((root/tag/f'{role}-actual-inputs/state.json').read_text())
            assert len(inp)==8 and state['TESTAuthorized']==1
            assert [s['unit'] for s in state['samplers']]==list(range(8))
            inputs[tag][role]=inp;states[tag][role]=state
            if role=='observer':
                assert inp==inputs[tag]['baseline'] and state==states[tag]['baseline'];comparisons+=9
            else:
                raw=(root/tag/'baseline-nodes.bin').read_bytes()
                assert raw==b'\0'*16+struct.pack('<I',0x7fc00000)*(4096*22*4)
            assert (root/tag/f'{role}-nodes.bin').read_bytes()==(root/tag/f'{role}-repeat-nodes.bin').read_bytes();comparisons+=1
        assert frame[5][:3]==(1.,1.,1.)
        data[tag]=records(root/tag/'observer-nodes.bin')
    assert len(data['black'])==len(data['green'])==2*order*order
    for key in inputs['black']['observer']:
        if key!='input-sampler1.f32':
            assert inputs['black']['observer'][key]==inputs['green']['observer'][key];comparisons+=1
    assert states['black']==states['green']
    state=states['green']['observer'];matrix=state['matrices']['gbufferModelView']
    inverse=state['matrices']['gbufferModelViewInverse'];projection=state['matrices']['gbufferProjection']
    for row in range(4):
        for col in range(4):
            close(sum(matrix[k*4+row]*inverse[col*4+k] for k in range(4)),float(row==col),2e-7,0.)
    depth=array('f');depth.frombytes(inputs['green']['observer']['input-sampler3.f32'])
    assert len(set(depth))==1
    distance=state['planeViewDistance'];clipz=projection[10]*(-distance)+projection[14]
    close(depth[0],.5*(clipz/distance+1),1e-7,0.)
    for tag in ('black','green'):
        c4=list(struct.iter_unpack('<4f',inputs[tag]['observer']['input-sampler1.f32']))
        assert set(c4)=={(0.,.125 if tag=='green' else 0.,0.,1.)}
    selected=[];hit_count=miss_count=visible_miss=overshoot=outside_hits=0
    physical_terms=[];measured_terms=[];source_terms=[[],[],[]];weights=[]
    for index,(black,node) in enumerate(zip(data['black'],data['green'])):
        # Every field except the actual returned source RGB must be exact.
        for slot in range(22):
            if slot in (6,7):
                assert black[slot][3]==node[slot][3]
            else:assert black[slot]==node[slot];comparisons+=1
        assert black[7][:3]==(0.,0.,0.) and black[6][:3]==(0.,0.,0.)
        ray=node[0][:3];weight=node[0][3];facet=node[1][:3];mass=node[1][3]
        origin=node[3][:3];viewray=node[4][:3];hit=node[6];radiance=node[7][:3]
        n,v,c=node[10][:3],node[11][:3],node[12][:3]
        p=model.t.prepare(n,v,c,node[10][3]);q,b=rotated.basis(p)
        x,z,ix,iz=node[8];lo,hi,panel,record_mass=node[9]
        ix,iz=int(ix),int(iz)
        assert 0<=ix<order and 0<=iz<order and lo<=z<=hi and mass==record_mass
        assert x==rule['binary32Nodes'][ix][0]
        forward=rotated.node(p,q,x,z,1);assert forward['supported']
        for a,bv in zip(ray,forward['target']):close(a,bv,2e-5,0.)
        reference_mass=model.gaussian_mass(lo,hi)
        close(mass,reference_mass)
        want=rule['binary32Nodes'][ix][2]*rule['binary32Nodes'][iz][2]*reference_mass*forward['transfer']
        close(weight,want,2e-9,2e-4);assert weight>0
        direction=tuple(a+bv for a,bv in zip(v,ray));norm=math.sqrt(sum(a*a for a in direction))
        for a,bv in zip(facet,direction):close(a,bv/norm,2e-6,0.)
        for a,bv in zip(viewray,transform(matrix,ray)):close(a,bv,2e-6,0.)
        offset=transform(matrix,facet)
        for j in range(3):close(origin[j],node[2][j]+.06*offset[j],2e-6,0.)
        first=oracle.first_plane(origin,viewray,projection,distance)
        known=first['kind']=='observed-plane';actual=hit[3]>0
        if actual:
            hit_count+=1
            if not known:outside_hits+=1
            far=node[18][:3]
            close(hit[3],math.dist(far,origin),2e-5,0.)
            # Exact retained source convention, not an eta²/unit correction.
            for channel,sigma in enumerate((.32,.085,.035)):
                close(radiance[channel],hit[channel]*math.exp(-sigma*hit[3]),2e-7,2e-5)
        else:
            miss_count+=1;assert hit[3]==-1 and radiance==(0.,0.,0.)
        bracket=node[20]
        rejected_crossing=bracket[3]==1 and abs(bracket[2])>=bracket[1]
        if known and not actual:
            visible_miss+=1;overshoot+=rejected_crossing
        physical=weight*.125*math.exp(-.085*first['distance']) if known else 0.
        physical_terms.append(physical);measured_terms.append(weight*radiance[1]);weights.append(weight)
        for j in range(3):source_terms[j].append(weight*radiance[j])
        selected.append(dict(index=index,x=x,z=z,ix=ix,iz=iz,panel=panel,
            worldRay=ray,facet=facet,viewStart=origin,viewRay=viewray,weight=weight,
            returnedHit=hit,sourceRGB=radiance,firstPlane=first,
            terminalSSR=node[16],firstCrossing=bracket,
            actualHit=actual,visibleMiss=known and not actual,
            firstCrossingRejectedByWidth=rejected_crossing,
            constantC4TruePlaneContribution=physical))
    for j in range(3):close(math.fsum(source_terms[j]),frames['green']['observer'][7][j],1e-7,2e-5)
    assert hit_count+miss_count==len(selected)
    return dict(schema='aqualumen-source-boundary-audit-v1',renderer=report['renderer'],GL=report['GL'],
        order=order,exactRawComparisons=comparisons,passiveC0DepthAndAllMRTBits=True,
        nodes=len(selected),actualHits=hit_count,actualMisses=miss_count,
        observedPlaneMisses=visible_miss,firstCrossingWidthRejectedObservedMisses=overshoot,
        hitsOutsideOracleSafetyViewport=outside_hits,
        replayedGreen=math.fsum(measured_terms),capturedGreen=frames['green']['observer'][7][1],
        sameNodesTruePlaneGreen=math.fsum(physical_terms),unitCoefficient=math.fsum(weights),
        selected=selected,observerNumericWeightSourceReplayPassed=True,
        arbitraryGeometryVisibilityProven=False,offscreenGeometryProven=False,
        physicalFixClaimed=False,intervalCertified=False,IrisAccepted=False,
        temporalAccepted=False,shippingAccepted=False,fullGoalAchieved=False,
        scope='Passive original MAIN node records, same observed six-metre view plane, strict repeated maps/input/stages and independent geometric/radiometric/probability replay. Not a natural-world or general first-object/energy/temporal proof.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('source')
    args=parser.parse_args();print(json.dumps(audit(args.root,args.source),indent=2,sort_keys=True))
