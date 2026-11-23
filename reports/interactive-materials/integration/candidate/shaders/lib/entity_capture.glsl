#ifndef AQUALUMEN_ENTITY_CAPTURE
#define AQUALUMEN_ENTITY_CAPTURE
#include "/lib/entity_grid.glsl"
// Geometry-stage capture of the animated triangles drawn by shadow_entities.
// Iris draws entity, name-tag, beacon-beam and lightning geometry with this
// program; only ids from entity.properties' caster lists are stored.
layout(r32ui) uniform coherent uimage2D entityMetaImage;
layout(r32ui) uniform coherent uimage2D entityHeadImage;
layout(rgba32ui) uniform writeonly uimage2D entityNodeImage;
layout(rgba32ui) uniform writeonly uimage2D entityTriangleImage;
uniform int entityId;

// Separating-axis overlap of a triangle and an axis-aligned box given relative
// to the box centre. Box face normals are handled by the caller's bounds.
bool entityTriangleBox(vec3 a,vec3 b,vec3 c,vec3 halfSize,vec3 normal) {
    if(abs(dot(normal,a))>dot(abs(normal),halfSize)) return false;
    vec3 edges[3]=vec3[3](b-a,c-b,a-c);
    for(int e=0;e<3;e++) for(int k=0;k<3;k++) {
        vec3 axis=k==0?vec3(0.0,-edges[e].z,edges[e].y):k==1?vec3(edges[e].z,0.0,-edges[e].x):vec3(-edges[e].y,edges[e].x,0.0);
        float pa=dot(axis,a),pb=dot(axis,b),pc=dot(axis,c);
        float r=dot(abs(axis),halfSize);
        if(min(pa,min(pb,pc))>r || max(pa,max(pb,pc))<-r) return false;
    }
    return true;
}

void entityInsertCell(ivec3 cell,int triangle,vec3 centre,float radius,bool self) {
    int node=int(imageAtomicAdd(entityMetaImage,ivec2(entityMetaNodes,0),1u));
    if(node>=entityNodeCapacity) { imageAtomicOr(entityMetaImage,ivec2(entityMetaOverflow,0),2u); return; }
    uint next=imageAtomicExchange(entityHeadImage,entityHeadAddress(cell),uint(node+1));
    imageStore(entityNodeImage,entityNodeAddress(node),entityPackNode(triangle,next,centre,radius,self));
    int brick=entityBrickIndex(cell/entityBrickCells);
    imageAtomicOr(entityMetaImage,ivec2(entityMetaBricks+(brick>>5),0),1u<<uint(brick&31));
}

// p: camera-relative metres; uv: atlas coordinates; alpha: vertex alpha.
void captureEntityTriangle(vec3 p0,vec3 p1,vec3 p2,vec2 uv0,vec2 uv1,vec2 uv2,float alpha,sampler2D atlas) {
    bool self=entityId==entitySelfId;
    if((entityId!=entityCasterId && !self) || alpha<0.1) {
        imageAtomicAdd(entityMetaImage,ivec2(entityMetaRejected,0),1u);
        return;
    }
    vec3 e1=p1-p0,e2=p2-p0,normal=cross(e1,e2);
    if(dot(normal,normal)<1e-12) return;
    vec3 g0=entityGridPosition(p0),g1=entityGridPosition(p1),g2=entityGridPosition(p2);
    ivec3 lo=max(ivec3(floor(min(g0,min(g1,g2))-0.002)),ivec3(0));
    ivec3 hi=min(ivec3(floor(max(g0,max(g1,g2))+0.002)),ivec3(entityCells-1));
    if(any(greaterThan(lo,hi))) return;
    // Alpha cutout: one texel test per lattice cell, taken at its centroid.
    uvec2 mask=uvec2(0u);
    vec2 duv1=uv1-uv0,duv2=uv2-uv0;
    for(int bit=0;bit<64;bit++) {
        vec2 b=entityMaskCentroid(bit);
        if(textureLod(atlas,uv0+b.x*duv1+b.y*duv2,0.0).a>=0.1) mask[bit>>5]|=1u<<uint(bit&31);
    }
    if(mask==uvec2(0u)) return;
    int triangle=int(imageAtomicAdd(entityMetaImage,ivec2(entityMetaTriangles,0),1u));
    if(triangle>=entityTriangleCapacity) { imageAtomicOr(entityMetaImage,ivec2(entityMetaOverflow,0),1u); return; }
    uint flags=(self?entityFlagSelf:0u)|(mask==uvec2(0xffffffffu)?entityFlagOpaque:0u);
    imageStore(entityTriangleImage,entityTriangleAddress(triangle,0),uvec4(floatBitsToUint(p0),flags));
    imageStore(entityTriangleImage,entityTriangleAddress(triangle,1),uvec4(floatBitsToUint(e1),mask.x));
    imageStore(entityTriangleImage,entityTriangleAddress(triangle,2),uvec4(floatBitsToUint(e2),mask.y));
    if(self) imageAtomicAdd(entityMetaImage,ivec2(entityMetaSelf,0),1u);
    vec3 centre=(p0+p1+p2)/3.0;
    float radius=sqrt(max(dot(p0-centre,p0-centre),max(dot(p1-centre,p1-centre),dot(p2-centre,p2-centre))));
    // Visit cell columns along the two minor axes of the plane normal; each
    // column only spans the plane's height range across its footprint.
    vec3 n=abs(normal);
    int w=n.x>n.y && n.x>n.z?0:(n.y>n.z?1:2),u=(w+1)%3,v=(w+2)%3;
    float planeOffset=dot(normal,g0);
    float gMin=min(g0[w],min(g1[w],g2[w])),gMax=max(g0[w],max(g1[w],g2[w]));
    vec3 halfSize=vec3(0.5+0.002);
    int columns=0;
    ivec3 used0=ivec3(entityCells),used1=ivec3(-1);
    for(int cu=lo[u];cu<=hi[u];cu++) for(int cv=lo[v];cv<=hi[v];cv++) {
        if(++columns>entityMaxColumns) { imageAtomicOr(entityMetaImage,ivec2(entityMetaOverflow,0),4u); break; }
        float h0=1e9,h1=-1e9;
        for(int k=0;k<4;k++) {
            float su=float(cu+(k&1)),sv=float(cv+(k>>1));
            float h=(planeOffset-normal[u]*su-normal[v]*sv)/normal[w];
            h0=min(h0,h);h1=max(h1,h);
        }
        int w0=max(lo[w],int(floor(max(h0,gMin)-0.002))),w1=min(hi[w],int(floor(min(h1,gMax)+0.002)));
        for(int cw=w0;cw<=w1;cw++) {
            ivec3 cell;cell[u]=cu;cell[v]=cv;cell[w]=cw;
            vec3 centre=vec3(cell)+0.5;
            if(!entityTriangleBox(g0-centre,g1-centre,g2-centre,halfSize,normal)) continue;
            entityInsertCell(cell,triangle,centre,radius,self);
            used0=min(used0,cell);used1=max(used1,cell);
        }
    }
    if(used1.x<0) return;
    for(int k=0;k<3;k++) {
        imageAtomicMax(entityMetaImage,ivec2(entityMetaMin+k,0),uint(entityCells-used0[k]));
        imageAtomicMax(entityMetaImage,ivec2(entityMetaMax+k,0),uint(used1[k]+1));
    }
}
#endif
