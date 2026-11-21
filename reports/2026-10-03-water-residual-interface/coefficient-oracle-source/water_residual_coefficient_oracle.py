"""Independent double-precision per-node CPU arithmetic, saved observations only.

No GLSL source/wave model is executed or copied. This tests declared finite GH3
coefficient arithmetic, not physical energy/flux, reciprocity, tails, sampled
source radiance or quadrature convergence. Same author, not third-party review.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import sys

SIZE=257
COEFFICIENT_ABSOLUTE=2e-5  # inherited native policy, not fitted to this audit
CENTRAL=((104,140),(152,116),(112,104),(144,152),(116,136),(136,108),(148,132))
RIGHT=((237,128),(235,128),(239,128),(237,126),(237,130))


def dot(a,b): return sum(x*y for x,y in zip(a,b))


def normalize(v):
    length=math.sqrt(dot(v,v))
    if not math.isfinite(length) or length<=0: raise ValueError('nonfinite/zero vector')
    return tuple(x/length for x in v)


def quadrature(mean_normal, covariance, view_to_eye):
    if not all(math.isfinite(x) for x in (*mean_normal,*covariance,*view_to_eye)):
        raise ValueError('nonfinite input')
    xx,xz,zz=covariance
    determinant=xx*zz-xz*xz
    if xx<0 or zz<0 or determinant<0 or (xx==0 and xz!=0):
        raise ValueError('indefinite covariance')
    root_x=math.sqrt(xx)
    cross=xz/root_x if root_x else 0
    # Determinant/xx is the Schur complement algebraically, calculated through
    # a separate double-precision expression rather than native subtraction.
    root_z=math.sqrt(determinant/xx if xx else zz)
    if abs(mean_normal[1])<=.5: raise ValueError('mean outside declared near-horizontal domain')
    projected_mean=dot(mean_normal,view_to_eye)/abs(mean_normal[1])
    if projected_mean<=0: raise ValueError('hidden mean')
    mean_slope=(-mean_normal[0]/mean_normal[1],-mean_normal[2]/mean_normal[1])
    side=-1 if mean_normal[1]<0 else 1
    nodes=(-math.sqrt(3),0,math.sqrt(3));probabilities=(1/6,2/3,1/6)
    coefficients=[0.,0.,0.,0.];table=[];valid=True
    eta=1.333
    for i,x in enumerate(nodes):
        for j,z in enumerate(nodes):
            slope=(mean_slope[0]+root_x*x,mean_slope[1]+cross*x+root_z*z)
            normal=tuple(side*t for t in normalize((-slope[0],1,-slope[1])))
            facing=dot(normal,view_to_eye)
            ratio=facing/abs(normal[1])/projected_mean
            weight=probabilities[i]*probabilities[j]*ratio
            ci=max(0.,min(1.,facing))
            snell=1-eta*eta*(1-ci*ci)
            tir=snell<0
            transmitted=None
            if tir:
                R=1.
            else:
                ct=math.sqrt(snell)
                perpendicular=(eta*ci-ct)/(eta*ci+ct)
                parallel=(ci-eta*ct)/(ci+eta*ct)
                R=.5*(perpendicular*perpendicular+parallel*parallel)
                transmitted=tuple(-eta*v+(eta*facing-ct)*n for v,n in zip(view_to_eye,normal))
            reflected=tuple(-v+2*facing*n for v,n in zip(view_to_eye,normal))
            valid=valid and facing>0 and weight>0 and reflected[1]<0 and (tir or transmitted[1]>0)
            terms=(1.,R,1-R,float(tir))
            for c in range(4): coefficients[c]+=weight*terms[c]
            table.append(dict(standard_normal_node=[x,z],slope=slope,normal=normal,
                facing=facing,projected_ratio=ratio,weight=weight,R=R,T=1-R,TIR=tir,
                reflected_world_y=reflected[1],transmitted_world_y=None if tir else transmitted[1],
                snell_discriminant=snell))
    return dict(coefficients=coefficients,domain_valid=bool(valid),nodes=table)


def read_raw(path,count):
    data=path.read_bytes()
    if sys.byteorder!='little' or len(data)!=count*4: raise ValueError('saved float format/size mismatch')
    values=array.array('f');values.frombytes(data)
    if not all(math.isfinite(x) for x in values): raise ValueError('nonfinite saved data')
    return values,hashlib.sha256(data).hexdigest()


def audit(run):
    recorded=json.loads((run/'result.json').read_text())
    if recorded['size']!=SIZE or recorded['quadrature_order']!=3: raise ValueError('wrong saved boundary size/order')
    result=[];passed=True
    for name,pixels in (('zero-residual-same-mean',CENTRAL),('nonzero-all-TIR',RIGHT)):
        directory=run/name
        native=next(c for c in recorded['cases'] if c['name']==name)
        if not native['fixture_qualified']: raise ValueError('selected native boundary fixture unqualified')
        projection,projection_sha=read_raw(directory/'actual-projection.f32',16)
        if projection[0]<=0 or projection[5]<=0: raise ValueError('invalid observed projection focal terms')
        images={};hashes={}
        for slot in (1,2,3,4,6):
            images[slot],hashes[str(slot)]=read_raw(directory/f'active-observer-slot{slot}.rgba32f',SIZE*SIZE*4)
        for pixel in pixels:
            index=(pixel[1]*SIZE+pixel[0])*4
            if list(images[6][index:index+4])!=[1.,1.,1.,1.]: raise ValueError('sample not known/upper/underwater/covered')
            if images[4][index]!=1 or images[4][index+1]!=1: raise ValueError('sample not finite-node valid/applied')
            # Pixel center -> perspective camera ray. The observed rigid up
            # inverse maps (x,y,z) to (x,-z,y); no eye/head/bob translation.
            ndc=(2*(pixel[0]+.5)/SIZE-1,2*(pixel[1]+.5)/SIZE-1)
            world_ray=(ndc[0]/projection[0],1.,ndc[1]/projection[5])
            view=tuple(-x for x in normalize(world_ray))
            normal=list(images[1][index:index+3]);cov=list(images[2][index:index+3])
            oracle=quadrature(normal,cov,view)
            observed=list(images[3][index:index+4]);errors=[abs(x-y) for x,y in zip(oracle['coefficients'],observed)]
            accepted=oracle['domain_valid'] and all(x<=COEFFICIENT_ABSOLUTE for x in errors)
            passed=passed and accepted
            result.append(dict(case=name,pixel=pixel,projection_sha256=projection_sha,
                observed_slot_sha256=hashes,observed_mean_normal=normal,observed_covariance=cov,
                reconstructed_view_to_eye=view,observed_coefficients=observed,
                double_coefficients=oracle['coefficients'],absolute_errors=errors,
                maximum_absolute_error=max(errors),domain_valid=oracle['domain_valid'],
                accepted=accepted,per_node=oracle['nodes']))
    return dict(schema='aqualumen-saved-gh3-double-coefficient-oracle-v1',run=str(run),
        coefficient_component_absolute_tolerance=COEFFICIENT_ABSOLUTE,
        qualified_selected_points=len(result),accepted=bool(passed),samples=result,
        assumptions=['Observed mean normal/covariance used directly; no recreated wave spectrum.',
            'Observed projection float readback and pixel-center raster coordinates.',
            'Known rigid up/inverse-up matrices and camera-relative eye origin0 from frozen native fixture; no head/bob translation.',
            'GH3 positive Gaussian plane-area projected weights; each finite node independently evaluated.',
            'Snell discriminant sign is used; selected points are far from critical boundary, not a critical-angle sweep.',
            'Only zero-known and nonzero all-TIR boundary points; native invalid/air/unknown controls are separate.',
            'Same author independent double arithmetic implementation, not third-party review.'],
        scope='Selected finite-node Fresnel/TIR coefficient regression, not sampled-source radiance, calibrated energy/flux, visibility tails, reciprocity, all-world error or quadrature-order convergence. Does not reclassify any whole native result.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('NEW output required')
    report=audit(args.run.resolve());args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as out:json.dump(report,out,indent=2,allow_nan=False);out.write('\n')
    print(('PASS' if report['accepted'] else 'FAIL')+' selected CPU double coefficient oracle; '+str(args.output))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
