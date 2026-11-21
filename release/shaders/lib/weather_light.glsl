#ifndef AQUALUMEN_WEATHER_LIGHT
#define AQUALUMEN_WEATHER_LIGHT
// Illumination of precipitation particles by the pack's real light sources.
//
// A rain streak or snowflake is a small scatterer, not a surface: it receives the
// full irradiance of a source (no surface Lambert cosine) and re-radiates it
// toward the eye with a normalized angular phase function p(mu), sphere integral 1.
//   mu = dot(view ray eye->particle, direction particle->source)
// mu=+1 is forward scattering (the source lies beyond the particle as seen from the eye).
// Radiance leaving the particle toward the eye:   L = albedo * E * p(mu),  E = PI * e
// where e is the Lambert-equivalent irradiance/PI that terrain uses for the same source
// (terrain: radiance = albedo * e * cos), so a source has the same strength here and
// on walls. All photometric strengths below are heuristic, not measurements.
#include "/lib/local_lighting.glsl"
#ifndef WEATHER_LIGHT_SOURCES
#define WEATHER_LIGHT_SOURCES 4 // sources traced per particle fragment (bounded work)
#endif
const float weatherAlbedo=0.66;           // equals the mean of the former solar forward-scatter term at sun.y=1
const float weatherUnsupportedAmbient=0.08; // block light no listed source explains: weak, neutral
const vec3 weatherAmbientTint=vec3(0.92,0.96,1.0);
const float weatherLocalLimit=16.0;       // soft luminance ceiling for a streak that grazes a lamp

// Henyey-Greenstein lobe, integral over the sphere equals one.
float weatherHG(float mu,float g) {
    float d=max(1.0+g*g-2.0*g*mu,1e-4);
    return (1.0-g*g)/(4.0*PI*d*sqrt(d));
}
// Normalized mixtures (weights sum to one). Water drops: refraction-dominated forward lobe
// plus a weak glory-like back lobe. Ice crystals: broad, nearly diffuse.
float weatherRainPhase(float mu) {
    return 0.10*weatherHG(mu,0.85)+0.30*weatherHG(mu,0.50)+0.45*weatherHG(mu,0.0)+0.15*weatherHG(mu,-0.35);
}
float weatherSnowPhase(float mu) {
    return 0.20*weatherHG(mu,0.60)+0.50*weatherHG(mu,0.0)+0.30*weatherHG(mu,-0.30);
}
// liquid=1 rain, 0 snow; the texture classification already blends the two smoothly.
float weatherPhase(float mu,float liquid) {
    return mix(weatherSnowPhase(clamp(mu,-1.0,1.0)),weatherRainPhase(clamp(mu,-1.0,1.0)),liquid);
}

// Local-light radiance of one particle fragment. `position` is camera relative, `ray` the unit eye->particle direction.
// Not multiplied by Sun visibility, sky access or rain strength: lamps shine at night, in shadow and in rain.
vec3 weatherLampLight(vec3 position,vec3 ray,float blockLevel,float liquid,out int tracedSources) {
    tracedSources=0;
    // Block light no listed source explains (lava, fire, unlisted emitters, outside the grid): conservative, never orange.
    vec3 fallback=weatherAmbientTint*(weatherAlbedo*weatherUnsupportedAmbient*pow(clamp(blockLevel,0.0,1.0),3.0));
    vec3 p=lampGridPosition(position,cameraPosition);
    // Same camera-space feather as terrain: the 64 m grid always encloses 24 m around the eye.
    vec3 eyeDistance=abs(position);
    float coverage=1.0-smoothstep(19.0,24.0,max(eyeDistance.x,max(eyeDistance.y,eyeDistance.z)));
    if(coverage<=0.0 || textureSize(aqualumenLightList,0)!=ivec2(16,512)) return fallback;
    int row=lampLinear(ivec3(p)/8,8);
    int count=clamp(int(texelFetch(aqualumenLightList,ivec2(0,row),0).x),0,lampCapacity+2);
    // Pass 1 (cheap, no tracing): analytic ranking of every listed source for this particle.
    float bestWeight[WEATHER_LIGHT_SOURCES];int bestIndex[WEATHER_LIGHT_SOURCES];
    for(int k=0;k<WEATHER_LIGHT_SOURCES;k++) {bestWeight[k]=0.0;bestIndex[k]=-1;}
    float tracked=0.0;
    for(int i=0;i<count;i++) {
        vec4 lamp=texelFetch(aqualumenLightList,ivec2(1+i,row),0);
        int record=int(lamp.w);
        bool carried=(record & lampCarriedFlag)!=0;
        int code=record & (lampCarriedFlag-1),kind=code%64;
        float level=float(code/64);
        vec3 delta=lamp.xyz-p;
        float d2=dot(delta,delta);
        if(d2>=lampRange*lampRange) continue;
        float d=sqrt(max(d2,1e-6));
        vec3 sourceDistance=abs(position+delta);
        float strength=1.0-smoothstep(19.0,24.0,max(sourceDistance.x,max(sourceDistance.y,sourceDistance.z)));
        float falloff=1.0-smoothstep(0.7*lampRange,lampRange,d);
        if(!carried) {
            float taxicab=dot(abs(floor(lamp.xyz)-floor(p)),vec3(1));
            tracked=max(tracked,clamp((level+1.0-taxicab)/15.0,0.0,1.0)*strength);
        }
        float e=11.0*pow(level/14.0,2.0)*strength*falloff/(0.38+d2);
        float w=e*dot(lampColor(kind),vec3(0.2126,0.7152,0.0722))*weatherPhase(dot(ray,delta/d),liquid);
        if(w<=1e-4) continue;
        float carryW=w;int carryI=i;
        for(int k=0;k<WEATHER_LIGHT_SOURCES;k++) if(carryW>bestWeight[k]) {
            float tw=bestWeight[k];int ti=bestIndex[k];
            bestWeight[k]=carryW;bestIndex[k]=carryI;carryW=tw;carryI=ti;
        }
    }
    // Pass 2: trace the strongest sources through the real scene (blocks, doors, stained glass, mobs).
    LampOccluders occluders;
    occluders.entityTest=false;occluders.apertures=0;
    occluders.leafVolume=false;occluders.leafCell=ivec3(-1);
    occluders.work=entityWorkBudget;
    occluders.toRelative=-(mod(cameraPosition,8.0)+32.0);
#if ENTITY_LIGHT_SHADOWS == 1
    occluders.entities=entityBounds();
#else
    occluders.entities.valid=false;occluders.entities.lo=vec3(0);occluders.entities.hi=vec3(0);
#endif
    vec3 total=vec3(0);
    for(int k=0;k<WEATHER_LIGHT_SOURCES;k++) {
        if(bestIndex[k]<0) break;
        vec4 lamp=texelFetch(aqualumenLightList,ivec2(1+bestIndex[k],row),0);
        int record=int(lamp.w);
        bool carried=(record & lampCarriedFlag)!=0;   // carried: the trace never stops at the holder's own cell and mobs skip the holder
        int code=record & (lampCarriedFlag-1),kind=code%64;
        float level=float(code/64);
        vec3 delta=lamp.xyz-p;
        float d2=dot(delta,delta);
        float d=sqrt(max(d2,1e-6));
        vec3 l=delta/d;
        vec3 sourceDistance=abs(position+delta);
        float strength=1.0-smoothstep(19.0,24.0,max(sourceDistance.x,max(sourceDistance.y,sourceDistance.z)));
        float falloff=1.0-smoothstep(0.7*lampRange,lampRange,d);
        float radius=kind==15 || kind==16 || kind>=18?0.42:0.13;
        vec3 vis=lampVisibility(p+0.02*l,lamp.xyz,l,radius,carried,occluders);
        tracedSources++;
        if(max(vis.r,max(vis.g,vis.b))<=0.0) continue;
        // Same regularized point falloff and range feather as lampLighting(); no surface cosine.
        vec3 energy=lampColor(kind)*(11.0*pow(level/14.0,2.0)*strength*falloff*vis/(0.38+d2));
        total+=energy*(PI*weatherAlbedo*weatherPhase(dot(ray,l),liquid));
    }
    total/=1.0+dot(total,vec3(0.2126,0.7152,0.0722))/weatherLocalLimit;
    // Listed sources explain most vanilla block light (weak residual stays neutral); unexplained light uses the full fallback.
    float attribution=smoothstep(0.0,0.15,tracked)*clamp((tracked+0.065)/max(blockLevel,0.065),0.0,1.0);
    return mix(fallback,total+fallback*mix(1.0,0.35,attribution),coverage);
}
#endif
