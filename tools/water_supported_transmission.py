"""CPU supported Gaussian rough-interface transmission and Smith visibility.

Declared model: correlated Gaussian *world-horizontal projected-area* slopes
around a tilted local mean plane, open upward constant air source / black water.
Height-correlated Smith single scattering is a statistical closure, not explicit
wave intersection or a multiple-scattering/energy proof. Legacy source units
stay fixed (NO eta-squared radiance calibration in this causal model).
Raw observed n/v are preserved. Support excludes a contribution, never the
whole integral. Forward slope and inverse light kernels are separate arithmetic.
"""
import math

def dot(a,b):
    return math.fsum(x*y for x,y in zip(a,b))

def vector(v):
    if len(v)!=3 or not all(type(x) in (int,float) and math.isfinite(x) for x in v):
        raise ValueError('Finite three-vector required')
    return tuple(v)

def prepare(normal,view,covariance,eta=1.3329999446868896):
    n,v,c=map(vector,(normal,view,covariance))
    if abs(dot(n,n)-1)>2e-5 or abs(dot(v,v)-1)>2e-5:
        raise ValueError('Observed near-unit inputs required; never normalized')
    if n[1]>=-.5 or v[1]>=0 or not math.isfinite(eta) or eta<=1:
        raise ValueError('Underwater mean/view/index domain required')
    xx,xz,zz=c;det=xx*zz-xz*xz
    if xx<=0 or zz<=0 or det<=0:
        raise ValueError('Positive-definite covariance required; no repair')
    slope=(-n[0]/n[1],-n[2]/n[1])
    projected=dot(n,v)/abs(n[1]);k2=1+eta*eta*(dot(v,v)-1)
    if projected<=1e-5 or k2<=0:raise ValueError('Positive mean projection/outgoing norm required')
    return dict(normal=n,view=v,covariance=c,eta=eta,det=det,meanSlope=slope,
        projected=projected,k2=k2,k=math.sqrt(k2),rootX=math.sqrt(xx),
        cross=xz/math.sqrt(xx),rootZ=math.sqrt(det/xx))

def masking_lambda(context,direction):
    """Exact Gaussian positive-projection Smith Lambda; no survivor mass fit.

    q(w,s)=side*(w_y-w_x*s_x-w_z*s_z) is Gaussian. Its signed mean is
    local-macroplane projected area. Lambda=E[q_+]/|E[q]|-1 after choosing
    the incident medium's side. This is phi(a)/a-Phi(-a), a=|mean|/sigma.
    Correlation is retained in directional variance, not replaced by GGX.
    """
    w=vector(direction);sx,sz=context['meanSlope'];xx,xz,zz=context['covariance']
    mean=abs(w[1]-w[0]*sx-w[2]*sz)
    variance=xx*w[0]**2+2*xz*w[0]*w[2]+zz*w[2]**2
    if mean==0:return math.inf
    if variance==0:return 0.
    if variance<0:raise ArithmeticError('Negative directional variance')
    a=mean/math.sqrt(variance)
    # Subtraction can round the positive far-tail Lambda to -0/tiny negative.
    # Clamping that numerical result does not alter the covariance/distribution.
    return max(0.,math.exp(-.5*a*a)/(a*math.sqrt(2*math.pi))-.5*math.erfc(a/math.sqrt(2)))

def visibility(context,target):
    return 1/(1+masking_lambda(context,context['view'])+masking_lambda(context,target))

def fresnel_transmission(cosine,eta,stable_cost=None):
    ci=min(1.,max(0.,cosine))
    if stable_cost is not None and ci==cosine:
        ct=stable_cost
    else:
        k=1-eta*eta*(1-ci*ci)
        if k<=0:return 0.
        ct=math.sqrt(k)
    rs=(eta*ci-ct)/(eta*ci+ct)
    rp=(ci-eta*ct)/(ci+eta*ct)
    return 1-.5*(rs*rs+rp*rp)

def absent(reason):
    return dict(kernel=0.,transfer=0.,supported=False,reason=reason)

def inverse_kernel(context,target):
    """Air solid-angle integrand, including Gaussian slope/angle Jacobian."""
    t=vector(target)
    if abs(dot(t,t)-1)>1e-12:raise ValueError('Unit generated target required; not normalized')
    v=context['view'];eta=context['eta'];k=context['k']
    if t[1]<=0:return absent('not upward air source')
    # Homogeneous inverse-branch support, independent of forward sqrt(k).
    b=dot(v,t)
    if k*t[1]+eta*v[1]>=0 or k+eta*b>=0:
        return absent('absent downward/forward inverse branch')
    if dot(context['normal'],t)>=0:return absent('not opposite macro hemisphere')
    axis=tuple(k*t[i]+eta*v[i] for i in range(3));a2=dot(axis,axis)
    if a2<=0:return absent('singular inverse axis')
    m=tuple(x/math.sqrt(a2) for x in axis)
    facing=dot(m,v);tm=dot(t,m)
    if m[1]>=0 or facing<=0 or tm>=0:return absent('backfacing inverse facet')
    # Inverse branch already proves ct=-k*dot(t,m)>0. Avoid subtracting nearly
    # equal numbers to recover ct² close to the critical boundary.
    ct=-k*tm
    transmitted=tuple(-eta*v[i]+(eta*facing-ct)*m[i] for i in range(3))
    error=max(abs(transmitted[i]-k*t[i]) for i in range(3))
    if error>1e-10:raise ArithmeticError('Inverse branch reconstruction failed')
    sx,sz=-m[0]/m[1],-m[2]/m[1]
    dx,dz=sx-context['meanSlope'][0],sz-context['meanSlope'][1]
    xx,xz,zz=context['covariance']
    density=math.exp(-.5*(zz*dx*dx-2*xz*dx*dz+xx*dz*dz)/context['det'])/(2*math.pi*math.sqrt(context['det']))
    projected=facing/(abs(m[1])*context['projected'])
    g=visibility(context,t)
    transfer=projected*fresnel_transmission(facing,eta,ct)*g
    jacobian=context['k2']*(-tm)/(a2*abs(m[1])**3)
    return dict(kernel=density*transfer*jacobian,supported=True,transfer=transfer,
        slope=(sx,sz),facet=m,target=t,maskingShadowing=g,jacobian=jacobian,
        reconstructionError=error)

def forward_kernel(context,x,z):
    """Standard-normal slope integrand, including its untruncated density."""
    if not all(math.isfinite(a) for a in (x,z)):raise ValueError('Finite slope coordinates required')
    sx=context['meanSlope'][0]+context['rootX']*x
    sz=context['meanSlope'][1]+context['cross']*x+context['rootZ']*z
    length=math.sqrt(1+sx*sx+sz*sz)
    m=(sx/length,-1/length,sz/length)
    v=context['view'];eta=context['eta'];facing=dot(m,v)
    radicand=1-eta*eta*(1-facing*facing)
    if facing<=0 or radicand<=0:return absent('backface or TIR')
    transmitted=tuple(-eta*v[i]+(eta*facing-math.sqrt(radicand))*m[i] for i in range(3))
    if transmitted[1]<=0 or dot(context['normal'],transmitted)>=0:
        return absent('air source or macro hemisphere absent')
    t=tuple(a/context['k'] for a in transmitted) # analytical outgoing norm, NOT input repair
    g=visibility(context,t)
    transfer=facing/(abs(m[1])*context['projected'])*fresnel_transmission(facing,eta)*g
    density=math.exp(-.5*(x*x+z*z))/(2*math.pi)
    return dict(kernel=density*transfer,transfer=transfer,supported=True,
        facet=m,target=t,slope=(sx,sz),maskingShadowing=g)

def legendre(order):
    if type(order) is not int or order<2 or order>1024:raise ValueError('Legendre order2..1024 required')
    rule=[]
    for i in range(1,order+1):
        x=math.cos(math.pi*(i-.25)/(order+.5))
        for _ in range(40):
            p0,p1=1.,x
            for j in range(2,order+1):p0,p1=p1,((2*j-1)*x*p1-(j-1)*p0)/j
            derivative=order*(x*p1-p0)/(x*x-1)
            change=p1/derivative;x-=change
            if abs(change)<2e-15:break
        rule.append((x,2/((1-x*x)*derivative**2)))
    return sorted(rule)

def interval_nodes(rule,lo,hi):
    return ((.5*((hi-lo)*x+hi+lo),.5*(hi-lo)*w) for x,w in rule)

def air_domain(context,u):
    """Exact azimuth support arcs, split additionally at mean-plane horizon."""
    v=context['view'];horizontal=math.hypot(v[0],v[2]);r=math.sqrt(max(0.,1-u*u))
    center=math.atan2(-v[2],-v[0]) if horizontal else 0.
    if horizontal*r==0:
        if context['k']/context['eta']+v[1]*u>=0:return []
        half=math.pi
    else:
        threshold=(context['k']/context['eta']+v[1]*u)/(horizontal*r)
        if threshold>=1:return []
        half=math.pi if threshold<=-1 else math.acos(threshold)
    n=context['normal'];a=n[0]*math.cos(center)+n[2]*math.sin(center)
    b=-n[0]*math.sin(center)+n[2]*math.cos(center)
    amplitude=math.hypot(a,b);bounds=[-half,half]
    if amplitude*r>0:
        ratio=-n[1]*u/(amplitude*r)
        if -1<ratio<1:
            offset=math.atan2(b,a);angle=math.acos(ratio)
            for j in range(-2,3):
                for root in (offset-angle+2*math.pi*j,offset+angle+2*math.pi*j):
                    if -half<root<half:bounds.append(root)
    bounds.sort();arcs=[]
    for lo,hi in zip(bounds,bounds[1:]):
        mid=.5*(lo+hi)
        if n[1]*u+r*(a*math.cos(mid)+b*math.sin(mid))<0:
            arcs.append((center+lo,center+hi))
    return arcs

def integrate_light(context,order=64):
    """Full supported constant-air-source hemisphere; no survivor normalization."""
    rule=legendre(order);v=context['view'];m2=dot(v,v);a=context['k']/context['eta']
    upper=min(1.,-context['eta']*v[1]/context['k'])
    bounds=[0.,upper]
    discriminant=math.hypot(v[0],v[2])*math.sqrt(max(0.,m2-a*a))
    for root in ((-a*v[1]-discriminant)/m2,(-a*v[1]+discriminant)/m2):
        if 0<root<upper:bounds.append(root)
    # The tilted macroplane horizon changes arc topology at this latitude.
    macro_break=math.hypot(context['normal'][0],context['normal'][2])/math.sqrt(dot(context['normal'],context['normal']))
    if 0<macro_break<upper:bounds.append(macro_break)
    bounds=sorted(set(bounds));terms=[];evaluations=0
    for lo,hi in zip(bounds,bounds[1:]):
        for u,wu in interval_nodes(rule,lo,hi):
            r=math.sqrt(1-u*u)
            for pl,ph in air_domain(context,u):
                for phi,wp in interval_nodes(rule,pl,ph):
                    node=inverse_kernel(context,(r*math.cos(phi),u,r*math.sin(phi)))
                    terms.append(wu*wp*node['kernel']);evaluations+=1
    return dict(value=math.fsum(terms),evaluations=evaluations,order=order,
        measure='dOmega=du*dphi on supported upward air directions; full Gaussian slopes via Jacobian',
        survivorRenormalization=False)

def slope_tail_bound(context,extent):
    """Union-bound omitted absolute source response on standard-normal square."""
    tail=math.erfc(extent/math.sqrt(2));phi=math.exp(-.5*extent*extent)/math.sqrt(2*math.pi)
    v=context['view']
    a=abs((v[0]*context['rootX']+v[2]*context['cross'])/context['projected'])
    b=abs(v[2]*context['rootZ']/context['projected'])
    return 2*tail+(a+b)*(2*phi+math.sqrt(2/math.pi)*tail)

def integrate_slope(context,order=256,extent=8.):
    """Independent forward integration with explicit non-renormalized tail bound."""
    if not math.isfinite(extent) or extent<=0:raise ValueError('Positive finite extent required')
    rule=legendre(order);nodes=list(interval_nodes(rule,-extent,extent));terms=[]
    for x,wx in nodes:
        for z,wz in nodes:terms.append(wx*wz*forward_kernel(context,x,z)['kernel'])
    return dict(value=math.fsum(terms),evaluations=order*order,order=order,
        extent=extent,absoluteTailBound=slope_tail_bound(context,extent),
        measure='standard bivariate normal dx*dz; original Gaussian density; no mass normalization',
        survivorRenormalization=False)

def quadratic_roots(coefficients):
    c,b,a=coefficients
    if a==0:return [] if b==0 else [-c/b]
    discriminant=b*b-4*a*c
    if discriminant<0:return []
    root=math.sqrt(discriminant);q=-.5*(b+math.copysign(root,b))
    if q==0:return [-b/(2*a)]
    return [q/a,c/q]

def slope_intervals(context,x,extent):
    """Partition z at all analytic critical/source/macro-horizon roots.

    p=v·(sx,-1,sz), h=1+sx²+sz², d=nMean·(sx,-1,sz).
    Critical: (1-eta²)h+eta²p²=0. Any directional horizon of a refracted
    ray w has squared numerator h*[eta²(v·w)²h-2eta²(v·w)p*d_w
    +(eta²-1)d_w²]. It is quadratic, not a sampled boundary search.
    Extraneous roots introduced by squaring merely split an interval; the
    independent forward branch decides inclusion at each interval midpoint.
    """
    sx=context['meanSlope'][0]+context['rootX']*x
    sz=context['meanSlope'][1]+context['cross']*x;b=context['rootZ']
    v=context['view'];e2=context['eta']**2
    p=(v[0]*sx-v[1]+v[2]*sz,v[2]*b)
    h=(1+sx*sx+sz*sz,2*sz*b,b*b)
    def product(a,b):return (a[0]*b[0],a[0]*b[1]+a[1]*b[0],a[1]*b[1])
    def add(*parts):return tuple(math.fsum(p[i] for p in parts) for i in range(3))
    def scale(k,a):return tuple(k*x for x in a)
    polynomials=[(p[0],p[1],0),add(scale(1-e2,h),scale(e2,product(p,p)))]
    for w in ((0,1,0),context['normal']):
        d=(w[0]*sx-w[1]+w[2]*sz,w[2]*b);a=dot(v,w)
        polynomials.extend([(d[0],d[1],0),
            add(product(p,d),scale(-a,h)),
            add(scale(e2*a*a,h),scale(-2*e2*a,product(p,d)),scale(e2-1,product(d,d)))])
    bounds=[-extent,extent]
    for polynomial in polynomials:
        for root in quadratic_roots(polynomial):
            if -extent<root<extent:bounds.append(root)
    bounds=sorted(set(bounds))
    return [(lo,hi) for lo,hi in zip(bounds,bounds[1:])
            if forward_kernel(context,x,.5*(lo+hi))['supported']]

def integrate_slope_split(context,order=128,extent=8.):
    """Forward-domain integration split at exact polynomial support boundaries."""
    if not math.isfinite(extent) or extent<=0:raise ValueError('Positive finite extent required')
    rule=legendre(order);terms=[];evaluations=0;intervals=0
    for x,wx in interval_nodes(rule,-extent,extent):
        for lo,hi in slope_intervals(context,x,extent):
            intervals+=1
            # Square-root endpoint behavior at critical incidence is integrated
            # with a smooth cosine map, not changed or blurred optically.
            for t,wt in interval_nodes(rule,0.,math.pi):
                z=.5*(lo+hi)-.5*(hi-lo)*math.cos(t)
                wz=wt*.5*(hi-lo)*math.sin(t)
                terms.append(wx*wz*forward_kernel(context,x,z)['kernel']);evaluations+=1
    return dict(value=math.fsum(terms),evaluations=evaluations,intervals=intervals,
        order=order,extent=extent,absoluteTailBound=slope_tail_bound(context,extent),
        measure='standard Gaussian dx*dz; analytic support-boundary split and cosine quadrature map',
        survivorRenormalization=False)
