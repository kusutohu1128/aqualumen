#ifndef AQUALUMEN_CLOUDS
#define AQUALUMEN_CLOUDS
// Original bounded volumetric cloud rendering: a 750 m thick curved layer,
// filtered 3D density, Beer-Lambert transport and six-step light occlusion.
// Weather, multiple scattering and aerial transport are approximations;
// these clouds are not a thermodynamic weather/fluid simulation.
const float CLOUD_BASE = 1450.0;
const float CLOUD_TOP = 2200.0;
const float CLOUD_VIEW_DISTANCE = 95000.0;
const int CLOUD_VIEW_STEPS = 32;
const int CLOUD_LIGHT_STEPS = 6;
const mat3 CLOUD_ROTATION = mat3(0.0,0.8,0.6, -0.8,0.36,-0.48, -0.6,-0.48,0.64);

float cloudCell(vec3 cell) {
    // Integer arithmetic avoids large-coordinate sine-hash precision loss.
    uvec3 p=uvec3(ivec3(cell));
    uint h=p.x*1979279u+p.y*3131873u+p.z*7018193u+1013904223u;
    h=(h^(h>>13u))*1664525u;
    h=(h^(h>>17u))*22695477u;
    return float(h&16777215u)/16777215.0;
}
float cloudNoise3(vec3 point) {
    vec3 cell=floor(point), f=fract(point);
    f=f*f*f*(f*(f*6.0-15.0)+10.0);
    float a=mix(cloudCell(cell),cloudCell(cell+vec3(1.0,0.0,0.0)),f.x);
    float b=mix(cloudCell(cell+vec3(0.0,1.0,0.0)),cloudCell(cell+vec3(1.0,1.0,0.0)),f.x);
    float c=mix(cloudCell(cell+vec3(0.0,0.0,1.0)),cloudCell(cell+vec3(1.0,0.0,1.0)),f.x);
    float d=mix(cloudCell(cell+vec3(0.0,1.0,1.0)),cloudCell(cell+vec3(1.0)),f.x);
    return mix(mix(a,b,f.y),mix(c,d,f.y),f.z);
}
float cloudFilteredNoise(vec3 point, float footprint) {
    return mix(0.5,cloudNoise3(point),1.0-smoothstep(0.22,1.0,footprint));
}
vec3 cloudCoordinates(vec3 planetPosition) {
    vec2 wind=vec2(0.86,0.51)*frameTimeCounter*WIND_SPEED*5.0;
    return vec3(cameraPosition.x+planetPosition.x-wind.x,
                length(planetPosition)-PLANET_R,
                cameraPosition.z+planetPosition.z-wind.y);
}
float cloudDensity(vec3 planetPosition, float worldFootprint) {
    vec3 world=cloudCoordinates(planetPosition);
    float height=(world.y-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE);
    if (height<=0.0 || height>=1.0) return 0.0;
    vec3 p=world/520.0;
    float weather=cloudFilteredNoise(vec3(p.x*0.31,27.1,p.z*0.31),worldFootprint/1677.0);
    float coverage=smoothstep(0.22,0.77,weather+rainStrength*0.36);
    vec3 shapePoint=CLOUD_ROTATION*p;
    float shape=0.61*cloudFilteredNoise(shapePoint,worldFootprint/520.0);
    shape+=0.28*cloudFilteredNoise(shapePoint*2.03+vec3(8.1,17.7,31.4),worldFootprint/256.0);
    shape+=0.11*cloudFilteredNoise(shapePoint*4.17+vec3(37.2,11.3,4.6),worldFootprint/125.0);
    // Broad dry-air gaps separate fair-weather cloud banks. Shorter scales
    // erode their edges, while the storm deck can fill in between them.
    float gap=(1.0-rainStrength)*(1.0-smoothstep(0.27,0.66,weather));
    // In clear weather use separated, shallower cumulus. As the air cools
    // toward evening the small convective clouds dissipate first. Rain keeps
    // its broad high-coverage layer and longer optical path.
    float dry=1.0-rainStrength;
    float convection=smoothstep(0.18,0.80,sunDirection().y);
    float threshold=0.615-0.175*coverage+0.085*gap+dry*(0.110+0.035*(1.0-convection))-0.065*rainStrength;
    float erosion=cloudFilteredNoise(shapePoint*8.4+vec3(3.7,72.2,18.6),worldFootprint/62.0);
    shape-=0.085*(1.0-erosion)*smoothstep(0.0,0.15,threshold+0.17-shape);
    float top=mix(0.48,0.88,coverage)-dry*(0.13+0.04*(1.0-convection));
    float envelope=smoothstep(0.015,0.13,height)*(1.0-smoothstep(top,min(top+0.18,1.0),height));
    return smoothstep(threshold,threshold+0.16,shape)*envelope*mix(0.8,1.25,rainStrength);
}
vec2 cloudInterval(vec3 origin, vec3 direction, float maxDistance) {
    vec2 outer=sphereRoots(origin,direction,PLANET_R+CLOUD_TOP);
    if (outer.y<=0.0) return vec2(-1.0);
    float start=max(outer.x,0.0), end=outer.y;
    vec2 inner=sphereRoots(origin,direction,PLANET_R+CLOUD_BASE);
    if (length(origin)<PLANET_R+CLOUD_BASE) start=max(inner.y,0.0);
    else if (inner.x>start) end=min(end,inner.x);
    vec2 ground=sphereRoots(origin,direction,PLANET_R);
    if (ground.x>0.0) end=min(end,ground.x);
    end=min(end,maxDistance);
    return end>start?vec2(start,end):vec2(-1.0);
}
float cloudExtinction() { return mix(0.0065,0.010,rainStrength); }
float cloudLightDepth(vec3 position, vec3 lightDirection) {
    vec2 interval=cloudInterval(position,lightDirection,10000.0);
    if (interval.x<0.0) return 0.0;
    float opticalDepth=0.0;
    for (int i=0; i<CLOUD_LIGHT_STEPS; ++i) {
        float a=float(i)/float(CLOUD_LIGHT_STEPS), b=float(i+1)/float(CLOUD_LIGHT_STEPS);
        float start=mix(interval.x,interval.y,a*a), end=mix(interval.x,interval.y,b*b);
        float ds=end-start;
        opticalDepth+=cloudDensity(position+lightDirection*(start+end)*0.5,ds*0.2)*ds;
    }
    return opticalDepth*cloudExtinction();
}
float cloudSolarAt(vec3 sun,float altitude,vec2 localXZ) {
    if (!earthAtmosphere()) return 1.0;
    vec3 origin=vec3(0.0,PLANET_R+max(altitude,2.0),0.0);
    origin.xz=localXZ;
    vec2 interval=cloudInterval(origin,sun,CLOUD_VIEW_DISTANCE);
    if (interval.x<0.0) return 1.0;
    float ds=(interval.y-interval.x)/float(CLOUD_VIEW_STEPS), opticalDepth=0.0;
    for (int i=0; i<CLOUD_VIEW_STEPS; ++i) {
        float t=interval.x+(float(i)+0.5)*ds;
        opticalDepth+=cloudDensity(origin+sun*t,ds*0.2)*ds;
    }
    return exp(-opticalDepth*cloudExtinction());
}
float cloudSolarTransmission(vec3 sun,float altitude) {
    return cloudSolarAt(sun,altitude,vec2(0.0));
}
vec3 addCloudLayer(vec3 sky, vec3 ray, vec3 sun, float altitude, float angularFootprint) {
    if (!earthAtmosphere()) return sky;
    vec3 origin=vec3(0.0,PLANET_R+max(altitude,2.0),0.0);
    vec2 interval=cloudInterval(origin,ray,CLOUD_VIEW_DISTANCE);
    if (interval.x<0.0) return sky;
    float ds=(interval.y-interval.x)/float(CLOUD_VIEW_STEPS);
    angularFootprint=clamp(angularFootprint,0.00001,0.25);
    vec3 sunlight=SOLAR*solarTransmission(sun,(CLOUD_BASE+CLOUD_TOP)*0.5);
    bool hasSun=dot(sunlight,sunlight)>0.0001;
    vec3 lightDirection=hasSun?sun:-sun;
    vec3 irradiance=hasSun?sunlight:vec3(0.008,0.011,0.018)*smoothstep(0.0,0.12,-sun.y);
    float mu=dot(ray,lightDirection);
    // A normalized two-lobe phase approximation retains a soft backlit body.
    float phase=0.82*miePhase(mu,0.68)+0.18*miePhase(mu,-0.18);
    vec3 scatter=vec3(0.0);
    float transmission=1.0;
    for (int i=0; i<CLOUD_VIEW_STEPS; ++i) {
        float t=interval.x+(float(i)+0.5)*ds;
        vec3 position=origin+ray*t;
        float density=cloudDensity(position,max(t*angularFootprint,ds*0.2));
        if (density>0.0001) {
            float lightDepth=cloudLightDepth(position,lightDirection);
            float height=clamp((length(position)-PLANET_R-CLOUD_BASE)/(CLOUD_TOP-CLOUD_BASE),0.0,1.0);
            vec3 source=irradiance*(phase*exp(-lightDepth)+0.22/(4.0*PI)*exp(-0.28*lightDepth));
            // This inexpensive ambient closure is explicitly approximate;
            // no extra self-emitting daylight color is added to the volume.
            source+=max(sky*0.30,vec3(0.00012,0.00020,0.00034))*(0.28+0.72*sqrt(height));
            float segmentTransmission=exp(-density*cloudExtinction()*ds);
            scatter+=transmission*source*(1.0-segmentTransmission)*0.99;
            transmission*=segmentTransmission;
            if (transmission<0.003) break;
        }
    }
    vec3 cloud=sky*transmission+scatter;
    // Full atmosphere/cloud coupling is not solved. Aerial attenuation blends
    // unresolved distant bodies continuously into their existing sky radiance.
    vec2 density=airDensity(origin+ray*(0.5*interval.x));
    vec3 foregroundTrans=exp(-interval.x*(BETA_R*density.x+BETA_M*1.1*density.y));
    return sky+(cloud-sky)*foregroundTrans;
}
#endif
