// Integrate the cloudy sky at the air/water critical angle. Unresolved wind
// slopes are approximated by an isotropic Gaussian in the tangent plane.
// Each facet contributes transmitted radiance or total internal reflection.
vec3 underwaterSkyFootprint(vec3 v,vec3 n,vec3 vx,vec3 vy,vec3 nx,vec3 ny,
                            float slopeSigma,vec3 reflection,vec3 ambient,float access) {
    const float node[3]=float[3](-1.7320508,0.0,1.7320508);
    const float mass[3]=float[3](1.0/6.0,2.0/3.0,1.0/6.0);
    vec3 sum=vec3(0.0);
    float total=0.0;
    for(int pixel=0;pixel<4;++pixel) {
        // Two Gauss-Legendre nodes along each pixel axis integrate the
        // locally reconstructed view and normal field over the square pixel.
        vec2 xy=(vec2(pixel%2,pixel/2)*2.0-1.0)*0.288675135;
        vec3 eye=normalize(v+vx*xy.x+vy*xy.y);
        vec3 normal=normalize(n+nx*xy.x+ny*xy.y);
        float ci=dot(eye,normal);
        vec3 tangent=normalize(eye-normal*ci);
        vec3 across=cross(normal,tangent);
        for(int a=0;a<3;++a) {
            for(int b=0;b<3;++b) {
                vec3 slope=normal+slopeSigma*(node[a]*tangent+node[b]*across);
                vec3 facet=normalize(slope);
                // Project the slope-normal distribution onto the camera.
                float weight=mass[a]*mass[b]*max(dot(eye,slope),0.0)/max(ci,0.0001);
                vec3 ray=refract(-eye,facet,1.333);
                vec3 light=reflection;
                if(dot(ray,ray)>0.0) {
                    vec3 sky=mix(ambient,sampleSky(colortex6,ray),access);
                    float admitted=1.0-waterFresnel(dot(eye,facet),1.333,1.0);
                    light=mix(reflection,sky*(1.333*1.333),admitted);
                }
                sum+=weight*light;
                total+=weight;
            }
        }
    }
    return sum/max(total,0.000001);
}
