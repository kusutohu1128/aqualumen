"""NEW CPU native sharp-Sun source integral; no GL or adoption claims."""
import math
import hashlib
import argparse
import json
from pathlib import Path
from water_residual_light_integral import light_kernel

RADIUS=.00465
SOLAR=(18.,17.6,17.)
FROZEN_MATH_SHA='f5b6db7013907ab4baf6e28df0542a2f2066ddaef1c8cdb6e8a28fc4e352de92'
FROZEN_FIXTURES_SHA='f8ec3ab6a5e330abdad8e493d913e54f2481a308dc1612fdf1c5106987d9d2c5'
MAIN_ABSOLUTE,MAIN_RELATIVE=2e-6,2e-4
CONVERGENCE_ABSOLUTE,CONVERGENCE_RELATIVE=2e-8,2e-6


def solar_beam(cached_transmission,rain):
    if len(cached_transmission)!=3 or not all(math.isfinite(x) and x>=0 for x in cached_transmission) or not math.isfinite(rain) or not 0<=rain<=1:
        raise ValueError('finite nonnegative cached transmission / rain[0,1] required')
    return [solar*t*(1-.85*rain) for solar,t in zip(SOLAR,cached_transmission)]


def legendre_rule(order):
    """Positive Gauss-Legendre rule for dq on[0,1]; no mass normalization."""
    if not isinstance(order,int) or not 1<=order<=24:raise ValueError('integer radial order1..24 required')
    def polynomial(x):
        previous,current=1.,x
        for degree in range(2,order+1):
            previous,current=current,((2*degree-1)*x*current-(degree-1)*previous)/degree
        return current,order*(x*current-previous)/(x*x-1)
    result=[]
    for i in range(order):
        x=math.cos(math.pi*(i+.75)/(order+.5))
        for _ in range(20):
            value,derivative=polynomial(x);change=value/derivative;x-=change
            if abs(change)<=2e-16:break
        else:raise ArithmeticError('Legendre root did not converge')
        _,derivative=polynomial(x)
        result.append(((1+x)/2,1/((1-x*x)*derivative*derivative)))
    result.sort()
    if any(not 0<q<1 or w<=0 for q,w in result):raise ArithmeticError('invalid positive radial rule')
    return result


def _unit(value):
    if len(value)!=3 or not all(math.isfinite(x) for x in value):raise ValueError('finite generated Sun axis required')
    length=math.sqrt(math.fsum(x*x for x in value))
    if not math.isfinite(length) or length<=0:raise ValueError('nonzero generated Sun axis required')
    return tuple(x/length for x in value)


def _cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def sharp_cap_rule(sun_direction,radius=RADIUS,radial_order=4,azimuth_order=12):
    """Generated unit directions/solid-angle weights, no observed n/v mutation."""
    if not math.isfinite(radius) or not 0<radius<math.pi/2 or not isinstance(azimuth_order,int) or not 1<=azimuth_order<=256:
        raise ValueError('radius(0,pi/2) and integer azimuth order1..256 required')
    axis=_unit(sun_direction);auxiliary=(0.,1.,0.) if abs(axis[1])<.95 else (1.,0.,0.)
    tangent=_unit(_cross(axis,auxiliary));bitangent=_cross(axis,tangent)
    delta=2*math.sin(radius/2)**2;result=[]
    for q,weight in legendre_rule(radial_order):
        cosine=1-delta*q;sine=math.sqrt(delta*q*(2-delta*q))
        for j in range(azimuth_order):
            phi=2*math.pi*(j+.5)/azimuth_order;c,s=math.cos(phi),math.sin(phi)
            direction=tuple(cosine*a+sine*(c*t+s*b) for a,t,b in zip(axis,tangent,bitangent))
            result.append((direction,weight*delta*2*math.pi/azimuth_order))
    return result


def cap_projected_irradiance(beam,sun_direction,radius=RADIUS,radial_order=4,azimuth_order=12):
    axis=_unit(sun_direction)
    projected=math.fsum(weight*math.fsum(a*b for a,b in zip(direction,axis))
                       for direction,weight in sharp_cap_rule(sun_direction,radius,radial_order,azimuth_order))
    return [x*projected/(math.pi*math.sin(radius)**2) for x in beam]


def sun_integral(fixture,sun_direction,beam,radius=RADIUS,radial_order=4,azimuth_order=12):
    """Finite sharp-source integral; any bad node rejects the entire result.

    The public hash-pinned light_kernel preserves observed n/v and legacy
    nonunit-view refract/Fresnel conventions. No eta compensation is added.
    """
    if hashlib.sha256(Path(__file__).with_name('water_residual_light_integral.py').read_bytes()).hexdigest()!=FROZEN_MATH_SHA:
        raise ValueError('frozen light-kernel dependency changed')
    if len(beam)!=3 or not all(math.isfinite(x) and x>=0 for x in beam):raise ValueError('finite nonnegative three-component beam required')
    nodes=sharp_cap_rule(sun_direction,radius,radial_order,azimuth_order)
    terms=[];minimum_facing=1.;maximum_error=0.
    for direction,weight in nodes:
        try:node=light_kernel(fixture,direction)
        except ValueError as error:
            return dict(domain_qualified=False,source_difference_C0=None,invalid_reason=str(error),
                        evaluated_nodes=len(terms)+1,invalid_nodes=1,no_renormalization=True)
        terms.append(weight*node['kernel']);minimum_facing=min(minimum_facing,node['facing'])
        maximum_error=max(maximum_error,node['reconstruction_error'])
    solid_integral=math.fsum(terms);projected_area=math.pi*math.sin(radius)**2
    return dict(domain_qualified=True,source_difference_C0=[x*solid_integral/projected_area for x in beam],
        kernel_solid_angle_integral=solid_integral,beam=list(beam),disk_radiance=[x/projected_area for x in beam],
        sun_direction_input=list(sun_direction),generated_unit_sun_axis=_unit(sun_direction),radius=radius,
        radial_order=radial_order,azimuth_order=azimuth_order,evaluated_nodes=len(terms),invalid_nodes=0,
        minimum_facing=minimum_facing,maximum_inverse_reconstruction_error=maximum_error,
        raw_inputs_preserved=True,no_renormalization=True,frozen_light_kernel_sha256=FROZEN_MATH_SHA,
        scope='Finite sharp source nodes, original raw-v light kernel only; not screen pixel-filtered sunDisk, receiver/visibility/critical/global physical model, GLSL/Iris or adoption.')


def _write_new(output,report):
    if output.exists() or output.is_symlink():raise ValueError('NEW output required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')


def export_rules(output):
    rules={}
    for order in (4,8,12):
        rule=legendre_rule(order)
        errors=[abs(math.fsum(w*q**degree for q,w in rule)-1/(degree+1)) for degree in range(2*order)]
        rules[str(order)]=dict(nodes=[q for q,_ in rule],weights=[w for _,w in rule],
            moment_degrees=list(range(2*order)),maximum_moment_absolute_error=max(errors),accepted=max(errors)<=2e-14)
    report=dict(schema='aqualumen-positive-sun-cap-rules-v1',rules=rules,radius=RADIUS,
        delta=2*math.sin(RADIUS/2)**2,projected_solid_angle=math.pi*math.sin(RADIUS)**2,
        candidate_rule=[4,12],refined_rules=[[8,24],[12,48]],azimuth='phi=2*pi*(j+.5)/M',
        measure='dq on[0,1]; solid weight=radial_weight*delta*2*pi/M; delta=2*sin(radius/2)^2',
        moment_absolute_gate=2e-14,no_mass_renormalization=True,
        scope='Positive rule/moment export only; not light-kernel/native Sun source response, GLSL, pixel-AA or physical adoption.')
    _write_new(output,report);return report


def _comparison(a,b,absolute,relative):
    if not a['domain_qualified'] or not b['domain_qualified']:return dict(accepted=False,status='INCONCLUSIVE')
    x,y=a['source_difference_C0'],b['source_difference_C0']
    errors=[abs(u-v) for u,v in zip(x,y)];bounds=[absolute+relative*max(abs(u),abs(v)) for u,v in zip(x,y)]
    return dict(accepted=all(e<=g for e,g in zip(errors,bounds)),absolute_errors=errors,bounds=bounds)


def analyze(saved,output,cached_transmission=(1.,1.,1.),rain=0.,sun_direction=(0.,1.,0.)):
    raw=saved.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=FROZEN_FIXTURES_SHA:raise ValueError('frozen six raw-vector oracle changed')
    packet=json.loads(raw);selected=[x for x in packet['dense_references'] if x['source']=='narrow']
    fixed={(128,128),(132,131),(123,127),(132,135),(132,127),(142,134)}
    if len(selected)!=6 or {tuple(x['pixel']) for x in selected}!=fixed:raise ValueError('fixed six saved fixtures required')
    fixtures=[dict(name='saved-'+str(x['pixel']),pixel=x['pixel'],vectors=x['actual_fixture'],axis=sun_direction,
                   provenance='Previously observed raw binary32 n/v/C; sharp-Sun radiance is a NEW controlled source') for x in selected]
    fixtures.append(dict(name='synthetic-normal-incidence-up-Sun',pixel=None,axis=(0.,1.,0.),
        vectors=dict(mean_normal=(0.,-1.,0.),view_to_eye=(0.,-1.,0.),covariance=selected[0]['actual_fixture']['covariance']),
        provenance='Explicit synthetic normal/view using frozen observed covariance; not an actual driver sample'))
    beam=solar_beam(cached_transmission,rain);samples=[]
    for item in fixtures:
        results=[sun_integral(item['vectors'],item['axis'],beam,radial_order=n,azimuth_order=m)
                 for n,m in ((4,12),(8,24),(12,48))]
        candidate=_comparison(results[0],results[2],MAIN_ABSOLUTE,MAIN_RELATIVE)
        convergence=_comparison(results[1],results[2],CONVERGENCE_ABSOLUTE,CONVERGENCE_RELATIVE)
        projected=cap_projected_irradiance(beam,item['axis'])
        units_errors=[abs(a-b) for a,b in zip(projected,beam)]
        units_accepted=all(e<=2e-13*abs(b) for e,b in zip(units_errors,beam))
        qualified=all(r['domain_qualified'] for r in results)
        samples.append(dict(**item,results=results,candidate_to_refined=candidate,refinement_convergence=convergence,
            projected_irradiance=projected,beam_unit_absolute_errors=units_errors,beam_units_accepted=units_accepted,
            status='INCONCLUSIVE' if not qualified else 'PASS' if candidate['accepted'] and convergence['accepted'] and units_accepted else 'RED'))
    qualified=all(s['status']!='INCONCLUSIVE' for s in samples);accepted=all(s['status']=='PASS' for s in samples)
    report=dict(schema='aqualumen-cpu-native-sharp-sun-integral-v1',saved_input_path=str(saved.resolve()),
        saved_input_sha256=FROZEN_FIXTURES_SHA,light_kernel_sha256=FROZEN_MATH_SHA,
        source_units=dict(SOLAR=SOLAR,cached_transmission_input=cached_transmission,rain_input=rain,
            rain_factor=1-.85*rain,beam=beam,radiance=[x/(math.pi*math.sin(RADIUS)**2) for x in beam],
            projected_solid_angle=math.pi*math.sin(RADIUS)**2,weather_cache_factors_applied_once=True,eta_compensation=False),
        radius=RADIUS,IOR=1.333,main_absolute=MAIN_ABSOLUTE,main_relative=MAIN_RELATIVE,
        convergence_absolute=CONVERGENCE_ABSOLUTE,convergence_relative=CONVERGENCE_RELATIVE,
        beam_units_relative_gate=2e-13,samples=samples,accepted=accepted,
        status='INCONCLUSIVE' if not qualified else 'PASS' if accepted else 'RED',
        actual_GPU_qualified=False,physical_accepted=False,Iris_accepted=False,shipping_accepted=False,
        scope='Pre-GPU sharp-cap source integration and units, six fixed saved vectors plus labeled synthetic up-Sun case. Finite-rule local convergence only; not equivalence to derivative-filtered stock sunDisk, receiver/visibility/critical/full physical model, energy, native execution, Iris or adoption.')
    _write_new(output,report);return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export-rules',type=Path)
    parser.add_argument('--cache',type=float,nargs=3,default=(1.,1.,1.));parser.add_argument('--rain',type=float,default=0.)
    parser.add_argument('--sun',type=float,nargs=3,default=(0.,1.,0.))
    parser.add_argument('saved',type=Path,nargs='?');parser.add_argument('output',type=Path,nargs='?');args=parser.parse_args()
    if args.export_rules:
        if args.saved or args.output:parser.error('export and analyze are exclusive')
        export_rules(args.export_rules);print('CPU positive Sun cap rule export: '+str(args.export_rules));return 0
    if not args.saved or not args.output:parser.error('SAVED-ORACLE.json NEW.json required')
    report=analyze(args.saved,args.output,args.cache,args.rain,args.sun)
    print(report['status']+' CPU sharp Sun '+str(sum(x['status']=='PASS' for x in report['samples']))+'/7; '+str(args.output))
    return 0 if report['accepted'] else 2


if __name__=='__main__':raise SystemExit(main())
