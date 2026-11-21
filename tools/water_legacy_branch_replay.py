"""Double reconstruction from declared raw vectors; no renderer/energy claim."""
import math

EPS = 2**-23
BITS = {0:'none',1:'finiteCovariance',2:'nonnegativeDiagonal',4:'SchurRemainder',8:'rankZeroCross',
        16:'vertical',32:'meanProjected',64:'facing',128:'reflectedHemisphere',
        256:'transmittedHemisphere',512:'transmittedOpaqueReceiver',1024:'reflectedOpaqueReceiver'}
FIELDS = ('normal','view','covariance','status','failure','transmitted','reflected')

def require(ok,why):
    if not ok:raise ValueError(why)

def forward(n,v,c,phase):
    require(phase in (0,45),'Phase0/45 required')
    require(all(len(a)==3 and all(math.isfinite(x) for x in a) for a in (n,v,c)),'Finite vec3 inputs')
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    rootX=math.sqrt(max(c[0],0));cross=c[1]/rootX if rootX>0 else 0
    remainder=c[2]-cross*cross;rootZ=math.sqrt(max(remainder,0))
    vertical=abs(n[1]);projected=dot(n,v)/max(vertical,1e-5)
    mean=[-n[0]/n[1],-n[2]/n[1]] if vertical>1e-5 else [0,0]
    side=-1 if n[1]<0 else 1
    mask=sum(bit for bit,ok in ((2,c[0]>=0 and c[2]>=0),(4,remainder>=0),(8,rootX>0 or c[1]==0),
                              (16,vertical>.5),(32,projected>1e-5)) if not ok)
    first=mask&-mask;firstNode=-1 if mask else -2
    nodes=[];failed=0;minimum=1
    for x,u in enumerate((-math.sqrt(3),0,math.sqrt(3))):
        for z,w in enumerate((-math.sqrt(3),0,math.sqrt(3))):
            if phase==45:a,b=(u-w)/math.sqrt(2),(u+w)/math.sqrt(2)
            else:a,b=u,w
            sx=mean[0]+rootX*a;sz=mean[1]+cross*a+rootZ*b
            length=math.sqrt(sx*sx+1+sz*sz);facet=[side*(-sx)/length,side/length,side*(-sz)/length]
            facing=dot(facet,v);minimum=min(minimum,facing)
            k=1-1.333**2*(1-facing*facing)
            t=[0,0,0] if k<0 else [-1.333*v[i]+(1.333*facing-math.sqrt(k))*facet[i] for i in range(3)]
            tir=dot(t,t)<1e-6
            r=[-v[i]+2*facing*facet[i] for i in range(3)]
            issue=(64 if not facing>0 else 0)|(128 if not r[1]<0 else 0)|(256 if not(tir or t[1]>0) else 0)
            if issue:
                failed+=1
                if first==0:first=issue&-issue;firstNode=3*x+z
            mask|=issue
            nodes.append(dict(index=3*x+z,facet=facet,facing=facing,transmitted=t,reflected=r,tir=tir,k=k,mask=issue))
    return dict(mask=mask,first=first,firstNode=firstNode,failedNodes=failed,minimumFacing=minimum,
                meanProjected=projected,nodes=nodes)

def replay(point,phase):
    for field in FIELDS:
        a=point.get(field)
        require(type(a) is list and len(a)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in a),'Finite vec4 '+field)
    n,v,c,st,m,t,r=[point[f] for f in FIELDS]
    require(n[3] in (0,1) and st[0] in (0,1) and st[1] in (0,1),'Boolean source state')
    require(16<=m[3]<=25 and m[3]==int(m[3]),'Called ledger and bounded failed-node count required')
    mask,first,node=[int(x) for x in m[:3]]
    require(m[:3]==[mask,first,node] and 0<=mask<=2047 and first in BITS,'Integer failure metadata')
    require(st[0]==int(mask==0) and st[1]==int(mask==0 and n[3]==1),'Original valid/applied correspondence')
    require(abs(sum(x*x for x in n[:3])-1)<2e-5 and abs(sum(x*x for x in v[:3])-1)<2e-5,'Raw unit n/v bound; not repaired')
    model=forward(n[:3],v[:3],c[:3],phase)
    require(abs(c[3]-abs(n[1]))<=8*EPS and abs(v[3]-model['meanProjected'])<=32*EPS,'Mean prerequisites disagree')
    require(abs(st[2]-model['minimumFacing'])<=32*EPS,'Recorded minimum facing differs')
    require(st[3]>=0 and st[3]==int(st[3]) and st[3]<=18,'Receiver count malformed')
    if mask==0:
        require(first==0 and node==-2 and m[3]==16 and t==r==[0,0,0,0],'No fake first-node state')
    else:
        require(first>0 and mask&first and -1<=node<=8,'First predicate must be in union')
        require((node==-1)==bool(mask&63),'Prerequisite/node priority differs')
    certain=True
    if st[3]==0:
        require(not(mask&1536),'Unobserved receiver failure')
        # Double reconstruction is not an exact-binary32 critical oracle.
        # Preserve marginal samples as inconclusive rather than drop/repair them.
        certain=all(abs(q['k'])>32*EPS and abs(q['facing'])>32*EPS
            and abs(q['reflected'][1])>32*EPS
            and (q['tir'] or abs(q['transmitted'][1])>32*EPS) for q in model['nodes'])
        if certain:
            require((mask,first,node,int(m[3])-16)==(model['mask'],model['first'],model['firstNode'],model['failedNodes']),'Independent support mask differs')
    else:certain=False
    maximum=0
    if node>=0:
        q=model['nodes'][node]
        if certain:
            require(t[3]==int(q['tir']),'First-node TIR differs')
            maximum=max(abs(t[i]-q['transmitted'][i]) for i in range(3))
            maximum=max(maximum,max(abs(r[i]-q['reflected'][i]) for i in range(3)),abs(r[3]-q['facing']))
            require(maximum<=32*EPS,'First-node forward direction differs')
        if first==64:require(not r[3]>0,'Claimed facing failure is positive')
        if first==128:require(not r[1]<0,'Claimed reflected hemisphere is negative')
        if first==256:require(t[3]==0 and not t[1]>0,'Claimed transmitted hemisphere is valid')
    return dict(firstPredicate=BITS[first],unionMask=mask,firstNode=node,
        failedNodeCount=int(m[3])-16,forwardRayCorrespondenceQualified=certain,
        maximumFirstRayComponentError=maximum if certain else None,
        reconstructionBound=32*EPS,rawInputVectorsNormalizedOrRepaired=False,
        firstFacetDerivedNotObserved=model['nodes'][node]['facet'] if node>=0 else None,
        physicalAccepted=False,visualAccepted=False,opticalFixImplemented=False,
        marginalBoundaryPolicy='retain record; double sign/first-ray reconstruction inconclusive when within32 binary32 epsilon of any tested boundary')
