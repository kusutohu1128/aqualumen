"""CPU independent-domain convergence at saved actual Iris inputs."""
import hashlib
import json
from pathlib import Path
import sys
import water_supported_transmission as model

ABSOLUTE=2e-6
RELATIVE=2e-4

def run(source):
    source=Path(source);raw=source.read_bytes();packet=json.loads(raw)
    assert packet['phase']==45 and packet['selectedCall']=='full' and packet['selectedPoints']==4
    results=[]
    for point in packet['points']:
        ctx=model.prepare(point['raw']['normal'][:3],point['raw']['view'][:3],point['raw']['covariance'][:3])
        light=[model.integrate_light(ctx,n) for n in (48,64,96)]
        slope=[model.integrate_slope_split(ctx,n) for n in (96,128,192)]
        gate=ABSOLUTE+RELATIVE*max(light[-1]['value'],slope[-1]['value'])
        cross=abs(light[-1]['value']-slope[-1]['value'])
        light_refinement=abs(light[-1]['value']-light[-2]['value'])
        slope_refinement=abs(slope[-1]['value']-slope[-2]['value'])
        qualified=(cross+slope[-1]['absoluteTailBound']<=gate and light_refinement<=gate and slope_refinement<=gate)
        results.append(dict(x=point['x'],y=point['y'],rawInput=point['raw'],
            light=light,slope=slope,absoluteRelativeGate=gate,crossDomainError=cross,
            lightRefinementError=light_refinement,slopeRefinementError=slope_refinement,
            numericallyQualified=qualified,referenceValue=light[-1]['value'],
            positiveLowerEstimateNotIntervalCertified=max(0.,min(light[-1]['value'],slope[-1]['value'])-gate),
            oldActualAdmissionApplied=point['raw']['status'][1],oldActualFirstPredicate=point['firstPredicate']))
        print(f"selected {point['x']},{point['y']} convergence {qualified}",file=sys.stderr,flush=True)
    return dict(schema='aqualumen-supported-transmission-cpu-reference-v1',
        actualIrisSourceSha256=hashlib.sha256(raw).hexdigest(),points=results,
        allNumericallyQualified=all(p['numericallyQualified'] for p in results),
        CPUArithmeticImplemented=True,shaderOpticalFixImplemented=False,
        nativeMainRegressionRun=False,physicalEnergyAccepted=False,visualAccepted=False,motionAccepted=False,
        source='unit constant upward air radiance, black water reflection; legacy source units unchanged',
        visibility='height-correlated Smith closure for correlated Gaussian world-slope heightfield; not explicit geometry/multiscattering',
        rigorousQuadratureIntervalCertified=False,
        numericalScope='Dual-domain full supported air / forward slope-square refinement plus analytic omitted Gaussian tail bound. Positive lower estimate is empirical, NOT a rigorous quadrature interval enclosure.',
        unitConversion='No eta-squared calibration; separate radiance/etendue goals remain open.')

if __name__=='__main__':
    print(json.dumps(run(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
