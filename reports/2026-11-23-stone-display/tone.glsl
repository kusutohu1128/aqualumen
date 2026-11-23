vec3 tone(vec3 scene,float exposure) {
    vec3 c=max(scene*exposure,vec3(0.));
    const vec3 luma=vec3(.2126,.7152,.0722);
    float peak=max(c.r,max(c.g,c.b));
    float key=mix(dot(c,luma),peak,.70);
    // Join the unmodified low-light response to the steeper diffuse range.
    // Cubic Hermite endpoints are (0.12,0.12,1) and (1,0.43,0.688).
    float drive=key;
    if(key>1.) {
        drive=.43*pow(key,1.6);
    } else if(key>.12) {
        float t=(key-.12)/.88;
        drive=.12+t*(.88+t*(-1.43544+.86544*t));
    }
    float value=drive/(1.+drive);
    vec3 rgb=c*(value/max(key,1.e-8));
    float y=dot(rgb,luma);
    vec3 delta=rgb-y;
    float span=max(delta.r,max(delta.g,delta.b))/max(1.-y,1.e-6);
    if(span>.85) {
        float excess=span-.85;
        float limited=.85+excess/(1.+excess/.15);
        rgb=y+delta*(limited/span);
    }
    return rgb;
}
