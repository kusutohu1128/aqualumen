// A persistent linear 2-D wave-height PDE, not a block-fluid or Navier-Stokes solver.
uniform vec4 aqualumenGrid;
uniform vec4 aqualumenShift;
uniform float aqualumenDelta;
uniform int aqualumenActive;
uniform vec4 aqualumenContact0;
uniform vec4 aqualumenContact1;
uniform vec4 aqualumenContact2;
uniform vec4 aqualumenContact3;
uniform vec4 aqualumenContact4;
uniform vec4 aqualumenContact5;
uniform vec4 aqualumenContact6;
uniform vec4 aqualumenContact7;
const float CELL=0.125;
const float SPEED=2.5;
vec2 readCell(ivec2 p) {
    if(any(lessThan(p,ivec2(0))) || any(greaterThanEqual(p,ivec2(512)))) return vec2(0);
    return imageLoad(rippleInput,p).rg;
}
float contactForce(vec2 position,vec4 source) {
    float r2=dot(position-source.xy,position-source.xy)/max(source.w*source.w,0.01);
    // Mexican-hat force has zero planar integral; no permanently pumped mean water level.
    return source.z*(1.0-0.5*r2)*exp(-0.5*r2);
}
void main() {
    ivec2 p=ivec2(gl_GlobalInvocationID.xy);
    ivec2 q=p;
#ifdef REPROJECT
    q+=ivec2(round(aqualumenShift.xy));
    if(aqualumenShift.z>0.5) {imageStore(rippleOutput,p,vec4(0));return;}
#endif
    float dt=clamp(aqualumenDelta,0.0,0.05)*0.5;
    vec2 state=readCell(q);
    float lap=readCell(q+ivec2(1,0)).x+readCell(q-ivec2(1,0)).x+readCell(q+ivec2(0,1)).x+readCell(q-ivec2(0,1)).x-4.0*state.x;
    vec2 position=aqualumenGrid.xy+(vec2(p)+0.5)*CELL;
    float force=0.0;
    if(aqualumenActive==1) {
        force=contactForce(position,aqualumenContact0)+contactForce(position,aqualumenContact1)+contactForce(position,aqualumenContact2)+contactForce(position,aqualumenContact3)
             +contactForce(position,aqualumenContact4)+contactForce(position,aqualumenContact5)+contactForce(position,aqualumenContact6)+contactForce(position,aqualumenContact7);
    }
    float edge=min(min(float(p.x),float(p.y)),min(float(511-p.x),float(511-p.y)))*CELL;
    float damping=0.8+8.0*(1.0-smoothstep(0.0,4.0,edge));
    float velocity=(state.y+(SPEED*SPEED*lap/(CELL*CELL)+force)*dt)*exp(-damping*dt);
    float height=state.x+velocity*dt;
    // Fail-closed safeguard; linear model is valid only for small amplitudes.
    if(isnan(height) || isinf(height) || abs(height)>0.5) {height=0;velocity=0;}
    imageStore(rippleOutput,p,vec4(height,velocity,0,0));
}
