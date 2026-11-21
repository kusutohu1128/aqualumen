"""Root's selected fresh-capture RED adjudication; NOT native pixel-AA proof."""
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools'))
from water_residual_sun_integral import solar_beam,sun_integral

packet=Path(__file__).resolve().parent
native=packet/'native-stub-v1'
report=json.loads((native/'result.json').read_text())
assert report['exportComplete'] and report['telemetryAccepted'] and report['legacyDomainQualified']
assert report['renderer'].startswith('NVIDIA GeForce RTX 3080 Ti') and len(report['cases'])==16
cases={case['path']:case for case in report['cases']}
fixed=[(128,128),(132,131),(123,127),(132,135),(132,127),(142,134)]
checks=[]
for case in report['cases']:
    assert case['domainQualified'] and case['telemetryQualified'] and case['ROI_points']==5025
    assert case['ROI_feature_applied_points']==0
    if not case['positive_cache'] or case['enabled']!=1:continue
    zero=cases[case['path'].replace('cachepositive','cachezero')]
    inputs=json.loads((native/case['path']/'actual-inputs.json').read_text())
    beam=solar_beam(inputs['solarCacheRGB'],case['rainStrength'])
    axis=inputs['sunDirectionDerivedFromActualUniforms']
    assert axis==[0,1,0] and inputs['solarCacheRGB']==[.5,.625,.75]
    assert [tuple(s['pixel']) for s in case['samples']]==fixed
    for positive,negative in zip(case['samples'],zero['samples']):
        assert positive['pixel']==negative['pixel']
        fixture=dict(mean_normal=positive['normal_requested'][:3],
                     view_to_eye=positive['eye_eligible'][:3],
                     covariance=positive['covariance_footprint'][:3])
        fine=sun_integral(fixture,axis,beam,radial_order=12,azimuth_order=48)
        previous=sun_integral(fixture,axis,beam,radial_order=8,azimuth_order=24)
        assert fine['domain_qualified'] and previous['domain_qualified']
        expected=fine['source_difference_C0']
        assert all(abs(a-b)<=2e-8+2e-6*abs(b) for a,b in zip(previous['source_difference_C0'],expected))
        assert positive['WR_status'][0:2]==[1,1] and positive['WR_status'][3]==0
        assert positive['WR_coefficients']==negative['WR_coefficients']
        assert positive['normal_requested'][3]==1 and positive['scatter_applied'][3]==0
        reflection=positive['WR_coefficients'][1]
        scatter=[reflection*(a-b) for a,b in zip(positive['scatter_applied'][:3],negative['scatter_applied'][:3])]
        for mode in ('pureTotalC0','observerTotalC0'):
            delta=[a-b-c for a,b,c in zip(positive[mode][:3],negative[mode][:3],scatter)]
            errors=[abs(a-b) for a,b in zip(delta,expected)]
            bounds=[2e-6+2e-4*abs(b) for b in expected]
            checks.append(dict(case=case['path'],pixel=positive['pixel'],mode=mode,
                               isolated_solar=delta,sharp_cap_reference=expected,
                               absolute_errors=errors,bounds=bounds,
                               numeric_red=any(e>b for e,b in zip(errors,bounds))))
assert len(checks)==48 and all(c['numeric_red'] for c in checks)
print(json.dumps(dict(status='DIAGNOSTIC_RED',checks=checks,
    result_sha256=hashlib.sha256((native/'result.json').read_bytes()).hexdigest(),
    all48_numeric_failures=True,all16_domains_qualified=True,
    nativePixelFilterEquivalenceAccepted=False,nativeFilteredBugProven=False,
    scope='Six fixed fresh vectors per2apertures/2weather, pure+observer, measured R*scatter reduction versus converged central sharp-cap reference. Genuine numeric RED, not merely absent implementation flag. Not exact legacy filtered-Sun integral failure, pixel-AA, global physical, Iris or quality proof.'),indent=2,allow_nan=False))
