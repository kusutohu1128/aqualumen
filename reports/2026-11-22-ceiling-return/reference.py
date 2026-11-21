"""Two diffuse reflections inside a black lamp hood and behind a coloured wall."""
import json
from pathlib import Path
import numpy as np

here=Path(__file__).resolve().parent
P=np.array([1.5,1.44,2.5])
C=np.array([[6.25,4,3.25],[6.75,4,3.75],[7.25,4,4.25]])
# Half-open unit blocks. A faces west. B faces north. C is the underside of a ceiling.
A=((6,0,0),(7,3,4))
B=((3,0,5),(6,4,6))
H=[((0,0,1),(1,3,4)),((1,0,1),(4,3,2)),((1,0,3),(4,3,4)),
   ((1,0,2),(4,1,3)),((1,2,2),(4,3,3))]
BOXES=[A,B,*H]
# The three independent shutters cover the aperture, A -> B, or the ceiling.
SHUTTERS=[((4,1,2),(5,2,3)),((3,0,4),(7,4,5)),((6,3,3),(8,4,5))]

def blocked(start,end,boxes):
    d=end-start
    enter=np.zeros(d.shape[:-1]);leave=np.ones(d.shape[:-1])
    hit=np.zeros(d.shape[:-1],bool)
    for lo,hi in boxes:
        enter.fill(0.);leave.fill(1.)
        valid=np.ones(d.shape[:-1],bool)
        for axis in range(3):
            da=d[...,axis];a=start[...,axis]
            parallel=np.abs(da)<1e-13
            safe=np.where(parallel,1.,da)
            t0,t1=(lo[axis]-a)/safe,(hi[axis]-a)/safe
            valid &= ~parallel | ((a>lo[axis]) & (a<hi[axis]))
            np.maximum(enter,np.where(parallel,-np.inf,np.minimum(t0,t1)),out=enter)
            np.minimum(leave,np.where(parallel,np.inf,np.maximum(t0,t1)),out=leave)
        hit |= valid & (leave>enter+1e-10)
    return hit

def plane(res,box,axis):
    lo,hi=map(np.array,box)
    axes=[i for i in range(3) if i!=axis]
    uv=np.meshgrid(*[np.arange(lo[j]+.5/res,hi[j],1/res) for j in axes],indexing="ij")
    points=np.zeros((uv[0].size,3))
    for j,coord in zip(axes,uv):
        points[:,j]=coord.ravel()
    points[:,axis]=lo[axis]
    return points

def transport(res,shutters=(),source=P):
    blocks=BOXES+list(shutters)
    # Clip the emitter's exact rectangular aperture onto the west face of A.
    # Binning across this hard light edge otherwise dominates the error.
    footprint=(A[0][0]-source[0])/(4.-source[0])
    start=source[1:]+(np.array([1.,2.])-source[1:])*footprint
    side=int(np.ceil(res*footprint))
    grid=(np.arange(side)+.5)*(footprint/side)
    y,z=np.meshgrid(start[0]+grid,start[1]+grid,indexing="ij")
    a=np.column_stack((np.full(y.size,6.),y.ravel(),z.ravel()))
    b=plane(res,B,2)
    dr=a-source
    direct_a=np.maximum(0.,dr[:,0])/np.linalg.norm(dr,axis=1)**3
    direct_a[blocked(source,a,blocks)]=0
    good=direct_a>0
    a,direct_a=a[good],direct_a[good]
    # The lamp cannot directly see B or C through its east-facing tunnel.
    assert np.all(blocked(source,b,blocks)) and np.all(blocked(source,C,blocks))
    # All receiver points are behind the west-facing plane A.
    assert np.all(C[:,0]>A[0][0])
    if len(a)==0:
        return np.zeros(len(C))
    l_b=np.zeros(len(b))
    for i in range(0,len(b),24):
        start=b[i:i+24,None,:]
        delta=a[None,:,:]-start
        r2=np.sum(delta*delta,axis=2)
        cos_product=np.maximum(delta[...,0],0.)*np.maximum(-delta[...,2],0.)
        kernel=(cos_product/r2**2)*(~blocked(start,a[None,:,:],blocks))
        l_b[i:i+len(start)]=(kernel@direct_a)*(footprint/side)**2/np.pi**2
    result=[]
    for c in C:
        v=c-b
        h=np.maximum(0.,-v[:,2])*np.maximum(0.,v[:,1])/np.sum(v*v,axis=1)**2
        result.append(float((h*(~blocked(c,b,blocks)))@l_b/res**2))
    return np.array(result)

def main():
    values={str(n):transport(n) for n in (8,16,32)}
    final=values["32"]
    gates=[transport(8,[s]).tolist() for s in SHUTTERS]
    assert np.min(final)>0 and not np.any(gates)
    convergence=max(abs(values["16"]/final-1))
    assert convergence<.025
    db=json.loads((here.parent/"2026-11-21-indirect-light/transport.json").read_text())["meanLinearDiffuse"]
    white=np.array(db["white_concrete"]);red=np.array(db["red_concrete"])
    warm=np.array([1.,.49,.19])
    result=dict(model="CPU reference, unit point intensity, irradiance at the ceiling after exactly two Lambertian reflections; perfect black hood and other faces",
                source=P.tolist(),ceiling=C.tolist(),wallA=A,wallB=B,hood=H,shutters=SHUTTERS,
                unitReflectance={k:v.tolist() for k,v in values.items()},relativeChange16To32=float(convergence),closed=gates,
                whiteWhite=(final[:,None]*white*white*warm).tolist(),redWhite=(final[:,None]*red*white*warm).tolist(),
                directCeiling=0,firstReturnViaA=0,directToB=0)
    (here/"reference.json").write_text(json.dumps(result,indent=2)+"\n")
    lantern_source=np.array([1.5,1.5,2.5])
    extended={str(n):transport(n,source=lantern_source) for n in (16,32)}
    unit=extended["32"]
    doors=[transport(8,[s],source=lantern_source).tolist() for s in SHUTTERS]
    assert np.all(unit>0) and not np.any(doors)
    data=dict(model="standing lantern source centre height; unit point intensity; identical black hood and walls",
              source=lantern_source.tolist(),ceiling=C.tolist(),unitReflectance={k:v.tolist() for k,v in extended.items()},
              relativeChange16To32=float(max(abs(extended["16"]/unit-1))),closed=doors)
    (here/"lantern-reference.json").write_text(json.dumps(data,indent=2)+"\n")
    screen=((6,0,4),(7,4,5))
    masked=transport(32,[screen],source=lantern_source)
    assert masked[0]>0 and np.all(masked[1:]==0)
    # The blocker is wholly on the far side of A. Every A-to-B segment
    # has x < 6 away from its endpoint, so the light reaching B is unchanged.
    (here/"side-screen.json").write_text(json.dumps(dict(screen=screen,open=unit.tolist(),
        screened=masked.tolist(),fractions=(masked/unit).tolist(),originalCeilingFaceStillExposed=True),indent=2)+"\n")
    print(final,convergence,"standing lantern",unit,"side screen",masked)
if __name__=="__main__":
    main()
