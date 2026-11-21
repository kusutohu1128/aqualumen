"""Independent dense/source replay of panel probability MAIN, not adoption.

Retained public auditor checks every saved role/input/geometry/source pair.
Extra dense tests use ACTUAL n/v/C/eta, not producer flags or fitted weights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import water_supported_sources_audit as retained
import water_supported_probability_rule as cpu


def audit(root, source):
    root, source = Path(root), Path(source)
    # This includes the original tight diffuse gate that rejects fast64.
    result = retained.audit(root)
    metadata = json.loads((source/'probability-rule.json').read_text())
    order = metadata['order']
    assert order in (8,12,16) and not metadata['panelMassFitted']
    assert not metadata['physicalCovarianceChanged']
    for role in retained.ROLES:
        assert (root/f'{role}.fsh').read_bytes() == (source/f'{role}.fsh').read_bytes()
    comparisons=[]
    for case, channel, amplitude in (('diffuse',0,.25), ('wide-opaque',1,.125)):
        point=16*(128*257+128)
        def pixel(slot):
            return struct.unpack_from('<4f',(root/case/f'enabled-slot{slot}.rgba32f').read_bytes(),point)
        n,v,c,t=[pixel(i) for i in (1,2,3,6)]
        p=cpu.c.t.prepare(n[:3],v[:3],c[:3],c[3])
        coarse=cpu.c.t.integrate_light(p,128)['value']
        dense=cpu.c.t.integrate_light(p,256)['value']
        finite=cpu.integrate(p,order)
        measured=t[channel]/amplitude
        gate=2e-6+2e-4*abs(dense)
        error=abs(measured-dense)
        assert error<=gate,(case,measured,dense,error,gate)
        # Independent double forward panel rule vs the actual binary32 port.
        replay_error=abs(measured-finite['transmission'])
        assert replay_error<=gate,(case,'port',replay_error,gate)
        comparisons.append(dict(case=case,actualRawNormal=n,actualRawView=v,
            actualRawCovarianceEta=c,measuredUnitCoefficient=measured,
            denseReference=dense,denseRefinementDifference=abs(dense-coarse),
            absoluteError=error,unchangedGate=gate,
            finiteCPU=finite,finitePortDifference=replay_error,
            actualSourceKinds=next(x['airKinds'] for x in result['selected'] if x['case']==case)))
    return dict(schema='aqualumen-probability-main-audit-v1',
        retainedSourceAudit=result,order=order,denseComparisons=comparisons,
        fragmentSHA256={r:hashlib.sha256((source/f'{r}.fsh').read_bytes()).hexdigest() for r in retained.ROLES},
        actualOriginalMAINExecuted=True,denseSelectedTransmissionGatesPassed=True,
        CPUGeneratedX=True,reflectionConstantSourceGPUAccepted=False,
        firstObjectVisibilityProven=False,intervalCertified=False,
        IrisAccepted=False,temporalAccepted=False,shippingAccepted=False,fullGoalAchieved=False,
        scope='Ten actual source cases, full saved raw/control replay, two dense selected transmission gates. Not all contexts, directional-source convergence, natural scenes or full-frame performance.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('source')
    args=parser.parse_args();print(json.dumps(audit(args.root,args.source),indent=2,sort_keys=True))
