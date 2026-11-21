#ifndef AQUALUMEN_ENTITY_GRID
#define AQUALUMEN_ENTITY_GRID
// Camera-centred acceleration grid for the animated entity triangles that the
// shadow pass draws this frame. It is rebuilt from cleared heads every frame,
// so moving, despawning or re-centring cannot leave a stale caster.
//
// 96^3 cells of 0.5 m span +-24 m, the full support of lampLighting(): its
// receivers and sources both fade out between 19 and 24 m (Chebyshev), and a
// segment between two points inside the box stays inside it.
const float entityCellSize=0.5;
const int entityCells=96;
const float entityExtent=24.0;
const int entityBrickCells=4;              // 2 m bricks for empty-space skipping
const int entityBricks=entityCells/entityBrickCells;
const int entityTriangleCapacity=32768;    // 3 rgba32ui texels each, 1024x96
const int entityNodeCapacity=262144;       // rgba32ui cell-list nodes, 1024x256
const int entityMaxColumns=4096;           // cell columns per triangle (32 m x 32 m)

// Iris entity.properties ids (see entity.properties).
const int entityCasterId=21000;
const int entitySelfId=21001;

// Meta image words (r32ui, 512x1, cleared every frame).
const int entityMetaTriangles=0;
const int entityMetaNodes=1;
const int entityMetaOverflow=2;            // 1 triangles, 2 nodes, 4 columns
const int entityMetaMin=3;                 // 3..5: entityCells-min cell (0 = empty)
const int entityMetaMax=6;                 // 6..8: max cell + 1
const int entityMetaSelf=9;                // diagnostic: self triangles stored
const int entityMetaRejected=10;           // diagnostic: filtered primitives
const int entityMetaBricks=16;             // 16..447: one bit per brick

const uint entityFlagSelf=1u;
const uint entityFlagOpaque=2u;

vec3 entityGridPosition(vec3 relativePosition) {
    return (relativePosition+entityExtent)/entityCellSize;
}
bool entityInGrid(ivec3 cell) {
    return all(greaterThanEqual(cell,ivec3(0))) && all(lessThan(cell,ivec3(entityCells)));
}
int entityCellIndex(ivec3 cell) { return cell.x+entityCells*(cell.z+entityCells*cell.y); }
ivec2 entityHeadAddress(ivec3 cell) { int i=entityCellIndex(cell); return ivec2(i&1023,i>>10); }
ivec2 entityNodeAddress(int node) { return ivec2(node&1023,node>>10); }
ivec2 entityTriangleAddress(int triangle,int part) { int i=3*triangle+part; return ivec2(i&1023,i>>10); }
int entityBrickIndex(ivec3 brick) { return brick.x+entityBricks*(brick.z+entityBricks*brick.y); }

// 8x8 sub-triangle lattice for alpha cutouts: 36 upright cells + 28 inverted.
// (u,v) are the barycentric weights of edges e1 and e2 from vertex 0.
int entityMaskBit(float u,float v) {
    const float n=8.0;
    vec2 g=clamp(vec2(u,v),0.0,1.0)*n;
    ivec2 c=ivec2(min(floor(g),vec2(n-1.0)));
    if(c.x+c.y>7) { int s=c.x+c.y-7; if(c.x>=c.y) c.x-=s; else c.y-=s; }
    vec2 f=g-vec2(c);
    int j=c.y,i=c.x;
    if(f.x+f.y<1.0 || i+j>=7) return j*8-(j*(j-1))/2+i;
    return 36+j*7-(j*(j-1))/2+i;
}
vec2 entityMaskCentroid(int bit) {
    bool inverted=bit>=36;
    int k=inverted?bit-36:bit,width=inverted?7:8,j=0;
    while(k>=width-j) { k-=width-j; j++; }
    return (vec2(k,j)+(inverted?vec2(2.0/3.0):vec2(1.0/3.0)))/8.0;
}
// Cell-list node: triangle, next node + 1, and a conservative bounding
// sphere so most near-miss triangles are rejected from this fetch alone.
// Centre: 16-bit fixed point over the grid (< 0.4 mm per axis). Radius: 15-bit
// millimetres, rounded up, 0x7fff = always test. Bit 31 marks the holder.
uvec4 entityPackNode(int triangle,uint next,vec3 centre,float radius,bool self) {
    vec3 g=entityGridPosition(centre),gc=clamp(g,vec3(0.0),vec3(entityCells));
    float r=radius+length(g-gc)*entityCellSize;
    uvec3 q=uvec3(round(gc*(65535.0/float(entityCells))));
    uint rq=r>=32.0?0x7fffu:uint(ceil(r*1000.0))+1u;
    return uvec4(uint(triangle),next,q.x|(q.y<<16),q.z|(rq<<16)|(self?0x80000000u:0u));
}
bool entityNodeSelf(uvec4 node) { return (node.w&0x80000000u)!=0u; }
vec3 entityNodeCentre(uvec4 node) {
    vec3 g=vec3(uvec3(node.z&0xffffu,node.z>>16,node.w&0xffffu))*(float(entityCells)/65535.0);
    return g*entityCellSize-entityExtent;
}
float entityNodeRadius(uvec4 node) {
    uint rq=(node.w>>16)&0x7fffu;
    return rq==0x7fffu?1e9:float(rq)*0.001+0.002;
}
#endif
