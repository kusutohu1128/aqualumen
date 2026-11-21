"""Actual MAIN witnesses plus finite-proposal replay and unchanged dense gates.

Passing the finite estimator replay is NOT passing convergence. Preserve both
results independently, including a tight dense-coefficient rejection.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import water_supported_conditioned as c
import water_supported_rotated as r
import water_supported_sources_audit as prior


def audit(root,source):
    root=Path(root);source=Path(source)
    result=json.loads((root/'result.json').read_text())
    assert result['schema']=='aqualumen-supported-sources-main-v1' and result['size']==257
    assert 'RTX 3080 Ti' in result['renderer']
    proposal=json.loads((source/'proposal.json').read_text())['coordinates'];assert len(proposal)==64
    center=16*(128*257+128);checks=0;selected=[];numeric=[];references={}
    geometry=[hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    canonical=c.ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    assert geometry==[hashlib.sha256((canonical/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    assert len(result['sourceQueries'])==4
    for pair_index,pair in enumerate(result['sourceQueries']):
        assert len(pair)==2
        for index,item in enumerate(pair):
            role='enabled' if index==0 else prior.ROLES[pair_index+1]
            assert (root/f'{role}.fsh').read_bytes()==(source/f'{role}.fsh').read_bytes()
            assert [s['sha256'] for s in item['stages'][:3]]==geometry
            assert item['stages'][3]['sha256']==hashlib.sha256((root/f'{role}.fsh').read_bytes()).hexdigest()
            assert item['currentProgramBefore']==item['currentProgramAfter']

    def close(field,actual,want,absolute=2e-6):
        error=abs(actual-want);gate=absolute+2e-4*abs(want)
        if error>gate:numeric.append(dict(field=field,actual=actual,expected=want,error=error,gate=gate))

    for case in prior.CASES:
        maps={};inputs={};states={};baseline={}
        for role in prior.ROLES:
            frame=[]
            for slot in range(8):
                blob=(root/case/f'{role}-slot{slot}.rgba32f').read_bytes()
                assert len(blob)==257*257*16 and blob==(root/case/f'{role}-repeat-slot{slot}.rgba32f').read_bytes();checks+=1
                prior.values(blob);frame.append(struct.unpack_from('<4f',blob,center))
                if role=='enabled':baseline[slot]=blob
                else:
                    if slot==4:assert blob==baseline[4];checks+=1
                    if slot==0:
                        assert blob[:center]==baseline[0][:center] and blob[center+16:]==baseline[0][center+16:]
                        if role=='disabled':disabled=blob
                        if role in ('strict','invalid'):assert blob==disabled;checks+=1
                        if role=='ledger':assert blob==baseline[0];checks+=1
            depth=(root/case/f'{role}-depth.f32').read_bytes()
            assert len(depth)==257*257*4 and depth==(root/case/f'{role}-repeat-depth.f32').read_bytes();checks+=1
            if role=='enabled':depth_reference=depth
            else:assert depth==depth_reference;checks+=1
            maps[role]=frame
            inp={p.name:p.read_bytes() for p in (root/case/f'{role}-actual-inputs').glob('input-sampler*.f32')};assert len(inp)==8
            state=json.loads((root/case/f'{role}-actual-inputs/state.json').read_text())
            assert state['TESTAuthorized']==1 and [s['unit'] for s in state['samplers']]==list(range(8))
            assert state['rainStrength']==(.5 if case=='rain' else 0.)
            inputs[role]=inp;states[role]=state
            if role!='enabled':assert inp==inputs['enabled'] and state==states['enabled'];checks+=9
        frame=maps['enabled'];ledger=maps['ledger'];state=states['enabled']
        assert frame[1][3]==1. and frame[5][:3]==(1.,1.,1.)
        assert maps['disabled'][1][3]==0 and maps['strict'][5][:3]==(1.,0.,0.)
        assert maps['invalid'][5][0]==0 and maps['invalid'][3][:3]==(0.,0.,0.)
        iris=json.loads((c.ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points'][2]['raw']
        assert frame[1][:3]==tuple(iris['normal'][:3]) and frame[2][:3]==tuple(iris['view'][:3])
        for j in range(3):assert struct.pack('<f',frame[6][j]+frame[7][j])==struct.pack('<f',frame[0][j])
        p=c.t.prepare(frame[1][:3],frame[2][:3],frame[3][:3],frame[3][3]);q,b=r.basis(p)
        finite=[]
        for branch in range(2):
            terms=[]
            for x,u in proposal:
                z,mass=c.conditional_z(r.intervals(p,q,b,x,branch),u)
                node=r.node(p,q,x,z,branch) if mass else dict(supported=False)
                terms.append(mass*node['transfer'] if node['supported'] else 0.)
            finite.append(math.fsum(terms)/len(proposal))
        if case=='diffuse':close('finite-diffuse-T',frame[6][0],.25*finite[0])
        if case=='wide-opaque':close('finite-opaque-T',frame[6][1],.125*finite[0])
        inv=state['matrices']['gbufferModelViewInverse'];sun=state['sunPosition']
        axis=prior.normalize(tuple(sum(inv[k*4+j]*sun[k] for k in range(3)) for j in range(3)))
        cap=prior.cap(p,axis,.00465)
        sky=prior.values(inputs['enabled']['input-sampler2.f32']);cache=sky[(31*64)*4:(31*64)*4+3]
        expected=[solar*value*(1-.85*state['rainStrength'])*cap['value']/(math.pi*math.sin(.00465)**2) for solar,value in zip((18,17.6,17),cache)]
        if case in ('cave','wide-opaque'):expected=[0.,0.,0.]
        for got,want in zip(ledger[6][:3],expected):close(case+'-Sun48',got,want)
        if case=='moon':
            moon=prior.cap(p,tuple(-a for a in axis),.0045)
            for got,amplitude in zip(ledger[7][:3],(.12,.16,.24)):close('Moon48',got,amplitude*moon['value'],2e-8)
            assert ledger[7][0]>0
        if case=='sun-absent':assert ledger[1]==(48.,0.,0.,48.)
        if case=='wide-sun':assert ledger[2][0]>0 and ledger[6][0]>0
        if case=='wide-opaque':assert ledger[2][1]>0 and ledger[1][2]==cap['supported']>0
        assert ledger[3][1]>0 and ledger[2][3]==1 # Explicit unobserved reflection proxy, never black-geometry proof.
        if case.startswith('wide-'):assert ledger[2][2]==0
        else:assert ledger[2][2]>0
        if case=='zero':assert frame[6][:3]==frame[7][:3]==(0.,0.,0.)
        dense=None
        if case in ('diffuse','wide-opaque'):
            key=tuple(frame[3])
            if key not in references:
                a=c.t.integrate_light(p,128);d=c.t.integrate_light(p,256)
                references[key]=dict(value=d['value'],refinementDifference=abs(d['value']-a['value']),intervalCertified=False)
            dense=references[key];gate=2e-6+2e-4*abs(dense['value']);error=abs(finite[0]-dense['value'])
            dense=dict(dense,finiteEstimate=finite[0],absoluteError=error,gate=gate,meetsUnchangedGate=error<=gate)
        selected.append(dict(case=case,transmitted=frame[6],reflected=frame[7],solar=ledger[6],lunar=ledger[7],
            finiteCPUUnitCoefficients=finite,denseTransmissionReference=dense,airKinds=ledger[2],reflectionKinds=ledger[3][:2]))
    dry=next(a for a in selected if a['case']=='sun')['solar'];wet=next(a for a in selected if a['case']=='rain')['solar']
    # Fourth component is the capture alpha marker, not source radiance.
    for a,b in zip(dry[:3],wet[:3]):close('rain factor',b,.575*a)
    return dict(schema='aqualumen-conditioned-source-audit-v1',renderer=result['renderer'],GL=result['GL'],
        exactRawComparisons=checks,selected=selected,finiteProposalAndCapFailures=numeric,
        finiteProposalAndCapGatesPassed=not numeric,
        denseCoefficientGatesPassed=all(a['denseTransmissionReference']['meetsUnchangedGate'] for a in selected if a['denseTransmissionReference']),
        actualOriginalMAINExecuted=True,CPUGeneratedProposal=True,temporalAccepted=False,IrisAccepted=False,shippingAccepted=False,
        scope='Actual source adapter and finite64 proposal replay, separately reported dense convergence. Not a practical temporal renderer or offscreen/energy/visual acceptance.')


if __name__=='__main__':
    result=audit(sys.argv[1],sys.argv[2]);print(json.dumps(result,indent=2,sort_keys=True))
    sys.exit(0 if result['finiteProposalAndCapGatesPassed'] else 1)
