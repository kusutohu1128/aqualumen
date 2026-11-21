#ifndef AQUALUMEN_SUPPORTED_SOURCES_TEST
#define AQUALUMEN_SUPPORTED_SOURCES_TEST
// TEST adapter, not installed production code. Tracers/stock sky precede this.
// Known radiance, physical absence and unobserved geometry are distinct.
// Proxies retain the legacy convention only when explicitly permitted; their
// use is counted, and does not establish actual offscreen light transport.
vec3 WSA_position,WSA_origin,WSA_scatter,WSA_cave;
float WSA_access=0.0;
bool WSA_allowProxies=true,WSA_proxyUsed=false;
float WSA_airSky=0.0,WSA_airOpaque=0.0,WSA_airUnknown=0.0;
float WSA_reflectionHits=0.0,WSA_reflectionMisses=0.0;
vec4 WSA_sunLedger=vec4(0.0),WSA_moonLedger=vec4(0.0);
vec3 WSA_solar=vec3(0.0),WSA_lunar=vec3(0.0);

vec3 WSA_checked(vec3 radiance) {
    if(!WST_finite(radiance)||any(lessThan(radiance,vec3(0.0)))) {
        WRT_sourceKnown=false;
        return vec3(0.0);
    }
    return radiance;
}
int WSA_airTrace(vec3 ray,out vec2 uv) {
    if(!WST_finite(ray)||ray.y<=0.0||dot(ray,ray)<1e-6) {
        WRT_sourceKnown=false;uv=vec2(0.0);return -1;
    }
    float path=48.0,confidence=0.0;int kind=0;
    uv=refractionTrace(WSA_origin,mat3(gbufferModelView)*ray,
        gl_FragCoord.xy/vec2(viewWidth,viewHeight),48.0,48.0,false,
        WSA_position.y+cameraPosition.y,path,kind,confidence);
    if(kind==2)WSA_airSky+=1.0;
    else if(kind==1)WSA_airOpaque+=1.0;
    else {WSA_airUnknown+=1.0;WSA_proxyUsed=true;
        if(!WSA_allowProxies)WRT_sourceKnown=false;}
    return kind;
}
vec3 WRT_airSource(vec3 ray) {
    vec2 uv;int kind=WSA_airTrace(ray,uv);
    if(kind<0)return vec3(0.0);
    // C4 is a real visible receiver's existing shaded radiance. Do not add a
    // separate solar disk to that receiver. Eye-water attenuation occurs later.
    if(kind==1)return WSA_checked(texture(colortex4,uv).rgb);
    vec3 sky=sampleSky(colortex6,ray);
    return WSA_checked(kind==2?sky:mix(WSA_cave,sky,WSA_access*WSA_access));
}
vec3 WRT_waterSource(vec3 ray) {
    if(!WST_finite(ray)||ray.y>=0.0||dot(ray,ray)<1e-6) {
        WRT_sourceKnown=false;return vec3(0.0);
    }
    // Forward reflected ray has the retained raw view length. Its half-vector
    // recovers the generating facet; no raw view/normal/covariance repair.
    vec3 axis=WRT_seenV+ray;
    if(dot(axis,axis)<=0.0){WRT_sourceKnown=false;return vec3(0.0);}
    vec3 facet=axis/sqrt(dot(axis,axis));
    vec4 hit=reflectionTrace(WSA_origin+mat3(gbufferModelView)*facet*0.06,
        mat3(gbufferModelView)*ray,WSA_scatter,false,WSA_position.y);
    if(hit.a>0.0) {
        WSA_reflectionHits+=1.0;
        vec3 trans=waterTransmission(hit.a);
        return WSA_checked(hit.rgb*trans+WSA_scatter*(1.0-trans));
    }
    WSA_reflectionMisses+=1.0;WSA_proxyUsed=true;
    if(!WSA_allowProxies)WRT_sourceKnown=false;
    return WSA_checked(WSA_scatter);
}
float WSA_cap(WST_Context p,vec3 axis,float radius,out vec4 ledger) {
    ledger=vec4(0.0);
    float axis2=dot(axis,axis);
    if(!WST_finite(axis)||axis2<=0.0||radius<=0.0) {
        WRT_sourceKnown=false;return 0.0;
    }
    // Normalize generated source directions only, not observed n/v.
    axis=axis/sqrt(axis2);
    vec3 auxiliary=abs(axis.y)<0.95?vec3(0.0,1.0,0.0):vec3(1.0,0.0,0.0);
    vec3 tangent=normalize(cross(axis,auxiliary)),bitangent=cross(axis,tangent);
    float capDelta=2.0*pow(sin(0.5*radius),2.0);
    const float radial[4]=float[4](0.06943184420297371,0.33000947820757187,
        0.6699905217924281,0.9305681557970262);
    const float weights[4]=float[4](0.17392742256872687,0.32607257743127305,
        0.32607257743127305,0.17392742256872687);
    float sum=0.0,correction=0.0;
    for(int r=0;r<4;++r)for(int j=0;j<12;++j) {
        float offset=capDelta*radial[r],cosine=1.0-offset;
        float sine=sqrt(offset*(2.0-offset)),phi=TAU*(float(j)+0.5)/12.0;
        vec3 target=normalize(cosine*axis+sine*(cos(phi)*tangent+sin(phi)*bitangent));
        vec4 node=WST_kernel(p,target);
        ledger.w+=1.0;
        if(node.y==0.0){ledger.x+=1.0;continue;}
        ledger.y+=1.0;
        if(!WST_finite(node.xyz)||isnan(node.w)||isinf(node.w)||node.x<0.0) {
            WRT_sourceKnown=false;continue;
        }
        if(node.x==0.0)continue;
        vec2 uv;int kind=WSA_airTrace(target,uv);
        // A known opaque receiver blocks this sharp source; its C4 radiance
        // already enters the diffuse/receiver integral. Unknown is a counted
        // access proxy, never a declaration of unobstructed physical sky.
        if(kind==1){ledger.z+=1.0;continue;}
        if(kind<0)continue;
        float access=kind==2?1.0:WSA_access*WSA_access;
        float term=weights[r]*node.x*access;
        float adjusted=term-correction,total=sum+adjusted;
        correction=(total-sum)-adjusted;sum=total;
    }
    return sum*(capDelta*TAU/12.0);
}
vec3 WSA_interface(vec3 originalColor,vec3 n,vec3 v,vec3 c,
    vec3 position,vec3 origin,float access,vec3 cave,vec3 scatter,
    bool eligible,bool allowProxies) {
    WSA_position=position;WSA_origin=origin;WSA_access=access;
    WSA_cave=cave;WSA_scatter=scatter;WSA_allowProxies=allowProxies;
    WSA_proxyUsed=false;WSA_airSky=0.0;WSA_airOpaque=0.0;WSA_airUnknown=0.0;
    WSA_reflectionHits=0.0;WSA_reflectionMisses=0.0;
    WSA_sunLedger=vec4(0.0);WSA_moonLedger=vec4(0.0);
    WSA_solar=vec3(0.0);WSA_lunar=vec3(0.0);
    WST_Context p=WST_prepare(n,v,c,1.333);
    vec3 result=WRT_interface(originalColor,n,v,c,eligible);
    if(!eligible||!p.valid)return originalColor;
    if(WRT_status.y!=1.0)return originalColor;
    if(earthAtmosphere()) {
        vec3 sun=sunDirection();
        vec3 beam=SOLAR*cachedSolarTransmission(colortex6)*(1.0-0.85*rainStrength);
        beam=WSA_checked(beam);
        if(any(greaterThan(beam,vec3(0.0)))) {
            float solarIntegral=WSA_cap(p,sun,SUN_ANGULAR_RADIUS,WSA_sunLedger);
            WSA_solar=beam*(solarIntegral/(PI*pow(sin(SUN_ANGULAR_RADIUS),2.0)));
        }
        // Retain fixed full-Moon source amplitude/radius, not derivative AA.
        // Lunar phase, absolute lunar calibration and pixel footprint are open.
        vec3 lunarRadiance=vec3(0.12,0.16,0.24)*smoothstep(0.0,0.08,-sun.y);
        if(any(greaterThan(lunarRadiance,vec3(0.0))))
            WSA_lunar=lunarRadiance*WSA_cap(p,-sun,0.0045,WSA_moonLedger);
    }
    result+=WSA_solar+WSA_lunar;
    if(!WRT_sourceKnown||!WST_finite(result)||any(lessThan(result,vec3(0.0)))) {
        WRT_status.yz=vec2(0.0);WRT_lastT=vec3(0.0);WRT_lastR=vec3(0.0);
        return originalColor;
    }
    WRT_lastT+=WSA_solar+WSA_lunar;
    return result;
}
#endif
