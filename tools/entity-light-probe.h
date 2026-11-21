// Independent NVIDIA EGL QA for the optional entity-light pass (mob shadows from local lights).
//
// Runs the pack's REAL sources: shadow_entities.vsh/.gsh/.fsh capture animated triangles (producer), and
// lib/entity_occlusion.glsl entityTransmission() plus lib/local_lighting.glsl lampLighting() read them (consumer).
// Image formats, sizes and clear flags come from shaders.properties; field layout constants and the caster ids
// come from lib/entity_grid.glsl. No path outside the pack root is used.
//
// Checked: caster stores / filtered ids and cut-outs store nothing; segments between receiver and lamp are
// blocked, beside / behind / beyond are lit (double-precision CPU oracle on the same triangles); a mob that
// moved or despawned leaves no ghost although node/triangle images are never cleared (only clear=true images
// are, as Iris does); own body ignores a held light but shadows a placed one; the solar shadow targets are
// identical for stored and filtered ids (geometry stage passes every primitive through); the real lampLighting()
// casts a cow-shaped shadow on a wall; ENTITY_LIGHT_SHADOWS=0 still compiles, links and passes primitives.
//
// Not covered: Iris patching and entity id attributes, real mob meshes, Minecraft frame time. This is an
// analytic/CPU-oracle fixture on synthetic cuboids, not a Minecraft or visual acceptance.
#pragma once
#include <regex>
#include <map>
#include <random>
namespace aqualumenEntityLight {
struct V {double x=0,y=0,z=0;};
inline V operator+(V a,V b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline V operator-(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline V operator*(V a,double s){return {a.x*s,a.y*s,a.z*s};}
inline double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline V cross(V a,V b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
inline double length(V a){return std::sqrt(dot(a,a));}
inline V yaw(V p,double a){const double c=std::cos(a),s=std::sin(a);return {c*p.x+s*p.z,p.y,-s*p.x+c*p.z};}
inline void ensure(bool ok,const std::string& message){if(!ok) throw std::runtime_error("entity-light QA FAIL: "+message);}
inline void pass(const std::string& message){std::cout<<"PASS entity-light: "<<message<<'\n';}

struct Vertex {float p[3],uv[2],c[4],n[3];};
struct Tri {V p[3];bool self=false;};
struct Mesh {
    std::vector<Vertex> vertices;  // GL_TRIANGLES; Minecraft quads split 0,1,2 / 2,3,0
    std::vector<Tri> triangles;
    void quad(const std::array<V,4>& q,float u0,float u1,float alpha=1.0f) {
        V n=cross(q[1]-q[0],q[2]-q[0]);n=n*(1.0/std::max(length(n),1e-12));
        const float uv[4][2]={{u0,0},{u0,1},{u1,1},{u1,0}};
        const int order[6]={0,1,2,2,3,0};
        for(int k:order) vertices.push_back({{float(q[k].x),float(q[k].y),float(q[k].z)},{uv[k][0],uv[k][1]},{1,1,1,alpha},{float(n.x),float(n.y),float(n.z)}});
        for(int t=0;t<2;++t) {   // the oracle sees the float positions the GPU receives
            Tri tri;
            for(int k=0;k<3;++k) {const Vertex& v=vertices[vertices.size()-6+3*t+k];tri.p[k]={v.p[0],v.p[1],v.p[2]};}
            triangles.push_back(tri);
        }
    }
    void box(V lo,V hi,const std::function<V(V)>& place,float u0,float u1) {
        auto P=[&](int x,int y,int z){return place({x?hi.x:lo.x,y?hi.y:lo.y,z?hi.z:lo.z});};
        quad({P(0,0,0),P(0,1,0),P(1,1,0),P(1,0,0)},u0,u1);quad({P(1,0,1),P(1,1,1),P(0,1,1),P(0,0,1)},u0,u1);
        quad({P(0,0,1),P(0,1,1),P(0,1,0),P(0,0,0)},u0,u1);quad({P(1,0,0),P(1,1,0),P(1,1,1),P(1,0,1)},u0,u1);
        quad({P(0,1,0),P(0,1,1),P(1,1,1),P(1,1,0)},u0,u1);quad({P(0,0,1),P(0,0,0),P(1,0,0),P(1,0,1)},u0,u1);
    }
    void markSelf(){for(auto& t:triangles) t.self=true;}
};
// Opaque atlas texel is u in [0,0.5), the transparent one u in [0.5,1].
constexpr float kOpaqueU0=0.05f,kOpaqueU1=0.45f,kClearU0=0.55f,kClearU1=0.95f;
// Six cuboids (72 triangles): body, head, four legs, facing +x.
inline Mesh cow(V feet,double angle,float u0=kOpaqueU0,float u1=kOpaqueU1,float alpha=1.0f) {
    Mesh m;
    auto place=[=](V p){return yaw(p,angle)+feet;};
    m.box({-0.6,0.55,-0.45},{0.6,1.15,0.45},place,u0,u1);
    m.box({0.6,0.85,-0.3},{1.1,1.45,0.3},place,u0,u1);
    for(double x:{-0.45,0.35}) for(double z:{-0.35,0.2}) m.box({x,0,z},{x+0.2,0.55,z+0.2},place,u0,u1);
    if(alpha!=1.0f) for(auto& v:m.vertices) v.c[3]=alpha;
    return m;
}

// Any-hit oracle with the shader's contract: both ends trimmed by 1 cm, two-sided, held light skips own body.
// eps>0 grows and eps<0 shrinks every triangle, so a segment only counts when it is decisive either way.
inline bool oracleHit(const std::vector<Tri>& tris,V s,V t,bool carried,double eps) {
    const V d=t-s;const double dist=length(d);
    if(dist<=0.02) return false;
    const double tMin=0.01/dist+eps/dist,tMax=1.0-0.01/dist-eps/dist;
    for(const Tri& tri:tris) {
        if(carried && tri.self) continue;
        const V e1=tri.p[1]-tri.p[0],e2=tri.p[2]-tri.p[0],p=cross(d,e2);const double det=dot(e1,p);
        if(std::abs(det)<1e-12) continue;
        const V q0=s-tri.p[0];const double u=dot(q0,p)/det;if(u<-eps||u>1+eps) continue;
        const V q=cross(q0,e1);const double v=dot(d,q)/det;if(v<-eps||u+v>1+eps) continue;
        const double tt=dot(e2,q)/det;if(tt>tMin && tt<tMax) return true;
    }
    return false;
}
struct Ray {V s,t;bool carried=false;};

struct Image {std::string name,sampler;GLenum internal=0,format=0,type=GL_UNSIGNED_INT;bool clear=false;int w=0,h=0;GLuint texture=0;};
inline std::string slurp(const fs::path& file) {std::ifstream in(file);ensure(bool(in),"cannot read "+file.string());std::ostringstream s;s<<in.rdbuf();return s.str();}
inline double sourceConstant(const fs::path& root,const char* file,const char* name) {
    std::smatch m;const std::string text=slurp(root/file);
    ensure(std::regex_search(text,m,std::regex(std::string("const\\s+(?:int|float)\\s+")+name+"\\s*=\\s*([-0-9.]+)")),std::string(file)+" has no constant "+name);
    return std::stod(m[1]);
}
inline bool shipped(const fs::path& root) {
    const char* parts[]={"shadow_entities.vsh","shadow_entities.gsh","shadow_entities.fsh","lib/entity_capture.glsl","lib/entity_grid.glsl","lib/entity_occlusion.glsl","entity.properties"};
    int present=0;for(const char* part:parts) present+=fs::exists(root/part);
    if(present!=0 && present!=int(std::size(parts))) throw std::runtime_error("Partial entity-light pass: all of shadow_entities.{vsh,gsh,fsh}, lib/entity_{capture,grid,occlusion}.glsl and entity.properties must ship together");
    return present!=0;
}

struct Rig {
    fs::path root;
    std::map<std::string,Image> images;           // by image uniform name, parsed from shaders.properties
    GLuint atlas=0,fbo=0,color0=0,color1=0,depth=0,vbo=0,rayBuffer=0,resultBuffer=0,lightList=0,lightField=0;
    GLuint capture=0,query=0,lighting=0;
    int size=256,metaTriangles=0,metaOverflow=0,metaRejected=0,metaSelf=0,casterId=0,selfId=0;
    float camera[3]={1203.37f,71.62f,-388.91f};   // far from the origin: positions below are camera-relative
};
inline const float* shadowView() {  // column-major rotation for a low oblique Sun
    static const float m[16]={0.8660254f,0.25f,-0.4330127f,0, 0,0.8660254f,0.5f,0, 0.5f,-0.4330127f,0.75f,0, 0,0,0,1};
    return m;
}
inline void loadImages(Rig& r) {
    std::istringstream in(slurp(r.root/"shaders.properties"));
    const std::map<std::string,std::array<GLenum,3>> formats={
        {"r32ui",{GL_R32UI,GL_RED_INTEGER,GL_UNSIGNED_INT}},{"rgba32ui",{GL_RGBA32UI,GL_RGBA_INTEGER,GL_UNSIGNED_INT}},
        {"r32f",{GL_R32F,GL_RED,GL_FLOAT}},{"rg32f",{GL_RG32F,GL_RG,GL_FLOAT}},{"rgba32f",{GL_RGBA32F,GL_RGBA,GL_FLOAT}},{"rgba16f",{GL_RGBA16F,GL_RGBA,GL_FLOAT}}};
    const std::regex line("^image\\.(\\w+)=(\\w+)\\s+\\w+\\s+(\\w+)\\s+\\w+\\s+(true|false)\\s+(?:true|false)\\s+(\\d+)\\s+(\\d+)\\s*$");
    for(std::string text;std::getline(in,text);) {
        std::smatch m;if(!std::regex_match(text,m,line)) continue;
        auto f=formats.find(m[3]);if(f==formats.end()) continue;   // unsupported formats are only an error if a program needs them
        Image image;image.name=m[1];image.sampler=m[2];image.internal=f->second[0];image.format=f->second[1];image.type=f->second[2];
        image.clear=m[4]=="true";image.w=std::stoi(m[5]);image.h=std::stoi(m[6]);
        glGenTextures(1,&image.texture);glBindTexture(GL_TEXTURE_2D,image.texture);glTexStorage2D(GL_TEXTURE_2D,1,image.internal,image.w,image.h);
        glClearTexImage(image.texture,0,image.format,image.type,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        r.images[image.name]=image;
    }
    for(const char* sampler:kEntityFieldSamplers) {
        bool found=false;for(auto& [name,image]:r.images) found|=image.sampler==sampler;
        ensure(found,std::string("shaders.properties declares no image for ")+sampler);
    }
}
inline Image& entityImage(Rig& r,const char* sampler) {
    for(auto& [name,image]:r.images) if(image.sampler==sampler) return image;
    throw std::runtime_error(std::string("no image for ")+sampler);
}
// Iris clears only the images flagged clear=true, once per frame before the shadow pass.
inline void irisFrameClear(Rig& r) {
    for(auto& [name,image]:r.images) if(image.clear) glClearTexImage(image.texture,0,image.format,image.type,nullptr);
}
inline void bindImages(Rig& r,GLuint program) {
    GLint count=0;glGetProgramInterfaceiv(program,GL_UNIFORM,GL_ACTIVE_RESOURCES,&count);
    int unit=0;
    for(GLint i=0;i<count;++i) {
        char name[256];GLsizei n=0;glGetProgramResourceName(program,GL_UNIFORM,i,sizeof(name),&n,name);
        const GLenum prop=GL_TYPE;GLint type=0;glGetProgramResourceiv(program,GL_UNIFORM,i,1,&prop,1,nullptr,&type);
        if(!isImageType(type)) continue;
        auto it=r.images.find(name);
        ensure(it!=r.images.end(),std::string("image uniform ")+name+" is not declared in shaders.properties (or has an unsupported format)");
        glBindImageTexture(unit,it->second.texture,0,GL_FALSE,0,GL_READ_WRITE,it->second.internal);
        glProgramUniform1i(program,glGetProgramResourceLocation(program,GL_UNIFORM,name),unit++);
    }
}
inline void setCommonUniforms(Rig& r,GLuint program) {
    float inverse[16];for(int c=0;c<4;++c) for(int row=0;row<4;++row) inverse[c*4+row]=(row<3&&c<3)?shadowView()[row*4+c]:(row==c?1.0f:0.0f);
    GLint l;
    if((l=glGetUniformLocation(program,"shadowModelViewInverse"))>=0) glProgramUniformMatrix4fv(program,l,1,GL_FALSE,inverse);
    if((l=glGetUniformLocation(program,"cameraPosition"))>=0) glProgramUniform3fv(program,l,1,r.camera);
    if((l=glGetUniformLocation(program,"isEyeInWater"))>=0) glProgramUniform1i(program,l,0);
    if((l=glGetUniformLocation(program,"gtexture"))>=0) glProgramUniform1i(program,l,0);
}
inline void clearTargets(Rig& r) {
    glBindFramebuffer(GL_FRAMEBUFFER,r.fbo);const float zero[4]={0,0,0,0},one=1.0f;
    glClearBufferfv(GL_COLOR,0,zero);glClearBufferfv(GL_COLOR,1,zero);glClearBufferfv(GL_DEPTH,0,&one);
}
// One shadow-pass draw of `mesh` through `program` with the given Iris entity id.
inline void drawShadow(Rig& r,GLuint program,const Mesh& mesh,int entityId) {
    glBindFramebuffer(GL_FRAMEBUFFER,r.fbo);glViewport(0,0,r.size,r.size);
    glDisable(GL_BLEND);glDisable(GL_SCISSOR_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_ALPHA_TEST);glDisable(GL_CULL_FACE);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glDepthMask(GL_TRUE);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
    glUseProgram(program);setCommonUniforms(r,program);bindImages(r,program);
    GLint l=glGetUniformLocation(program,"entityId");if(l>=0) glProgramUniform1i(program,l,entityId);
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,r.atlas);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(-30,30,-30,30,-60,60);
    glMatrixMode(GL_MODELVIEW);glLoadMatrixf(shadowView());
    for(int unit=0;unit<2;++unit) {glActiveTexture(GL_TEXTURE0+unit);glMatrixMode(GL_TEXTURE);glLoadIdentity();}
    glActiveTexture(GL_TEXTURE0);glMatrixMode(GL_MODELVIEW);
    glMultiTexCoord2f(GL_TEXTURE1,0.03f,0.97f);glVertexAttrib4f(10,-1,0,0,0);glVertexAttrib4f(11,0,0,0,0);
    glBindBuffer(GL_ARRAY_BUFFER,r.vbo);
    glBufferData(GL_ARRAY_BUFFER,mesh.vertices.size()*sizeof(Vertex),mesh.vertices.data(),GL_STREAM_DRAW);
    glEnableClientState(GL_VERTEX_ARRAY);glVertexPointer(3,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,p));
    glClientActiveTexture(GL_TEXTURE0);glEnableClientState(GL_TEXTURE_COORD_ARRAY);glTexCoordPointer(2,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,uv));
    glEnableClientState(GL_COLOR_ARRAY);glColorPointer(4,GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,c));
    glEnableClientState(GL_NORMAL_ARRAY);glNormalPointer(GL_FLOAT,sizeof(Vertex),(void*)offsetof(Vertex,n));
    glDrawArrays(GL_TRIANGLES,0,GLsizei(mesh.vertices.size()));
    glDisableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);glDisableClientState(GL_COLOR_ARRAY);glDisableClientState(GL_NORMAL_ARRAY);
    glBindBuffer(GL_ARRAY_BUFFER,0);glUseProgram(0);
    glMemoryBarrier(GL_ALL_BARRIER_BITS);
    ensure(glGetError()==GL_NO_ERROR,"GL error in shadow draw");
}
inline std::vector<uint32_t> readMeta(Rig& r) {
    const auto& image=entityImage(r,"aqualumenEntityMeta");
    std::vector<uint32_t> meta(size_t(image.w)*image.h);
    glBindTexture(GL_TEXTURE_2D,image.texture);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,meta.data());
    meta.resize(image.w); // Other rows belong to the rain-height atlas.
    return meta;
}
inline std::vector<float> readTargets(Rig& r) {   // shadowcolor0, shadowcolor1, depth
    const size_t n=size_t(r.size)*r.size;std::vector<float> all(n*9);
    glBindTexture(GL_TEXTURE_2D,r.color0);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,all.data());
    glBindTexture(GL_TEXTURE_2D,r.color1);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,all.data()+n*4);
    glBindTexture(GL_TEXTURE_2D,r.depth);glGetTexImage(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,GL_FLOAT,all.data()+n*8);
    return all;
}
inline size_t coveredTexels(Rig& r,const std::vector<float>& targets) {
    const size_t n=size_t(r.size)*r.size;size_t covered=0;
    for(size_t i=0;i<n;++i) covered+=targets[n*8+i]<1.0f;
    return covered;
}
inline GLuint computeProgram(const std::string& source,const std::string& name) {
    GLuint shader=compile(GL_COMPUTE_SHADER,source,name);GLuint program=glCreateProgram();glAttachShader(program,shader);glLinkProgram(program);glDeleteShader(shader);
    GLint ok=0;glGetProgramiv(program,GL_LINK_STATUS,&ok);
    if(!ok){char log[16384];glGetProgramInfoLog(program,sizeof(log),nullptr,log);throw std::runtime_error(name+": "+log);}
    return program;
}
inline void bindSampler(GLuint program,const char* name,int unit,GLuint texture) {
    glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,texture);
    GLint l=glGetUniformLocation(program,name);if(l>=0) glProgramUniform1i(program,l,unit);
}
// Consumer: results[i] = program(rays[2i], rays[2i+1]) on the real field samplers.
inline std::vector<float> runConsumer(Rig& r,GLuint program,const std::vector<float>& input,size_t count) {
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,r.rayBuffer);glBufferData(GL_SHADER_STORAGE_BUFFER,input.size()*4,input.data(),GL_STREAM_DRAW);
    glBindBuffer(GL_SHADER_STORAGE_BUFFER,r.resultBuffer);glBufferData(GL_SHADER_STORAGE_BUFFER,count*4,nullptr,GL_STREAM_READ);
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,r.rayBuffer);glBindBufferBase(GL_SHADER_STORAGE_BUFFER,1,r.resultBuffer);
    glUseProgram(program);setCommonUniforms(r,program);
    int unit=1;for(const char* sampler:kEntityFieldSamplers) bindSampler(program,sampler,unit++,entityImage(r,sampler).texture);
    bindSampler(program,"aqualumenLightList",unit++,r.lightList);bindSampler(program,"aqualumenLightField",unit++,r.lightField);
    glProgramUniform1i(program,glGetUniformLocation(program,"rayCount"),GLint(count));
    glDispatchCompute(GLuint((count+63)/64),1,1);glMemoryBarrier(GL_ALL_BARRIER_BITS);
    std::vector<float> out(count);glBindBuffer(GL_SHADER_STORAGE_BUFFER,r.resultBuffer);glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,count*4,out.data());
    glUseProgram(0);glActiveTexture(GL_TEXTURE0);
    ensure(glGetError()==GL_NO_ERROR,"GL error in consumer dispatch");
    return out;
}
// 1 = lit, 0 = blocked by an entity triangle.
inline std::vector<float> transmissions(Rig& r,const std::vector<Ray>& rays) {
    std::vector<float> in(rays.size()*8,0.0f);
    for(size_t i=0;i<rays.size();++i) {
        float* a=&in[i*8];a[0]=float(rays[i].s.x);a[1]=float(rays[i].s.y);a[2]=float(rays[i].s.z);a[3]=rays[i].carried?1.0f:0.0f;
        a[4]=float(rays[i].t.x);a[5]=float(rays[i].t.y);a[6]=float(rays[i].t.z);
    }
    return runConsumer(r,r.query,in,rays.size());
}
inline bool blocked(Rig& r,V s,V t,bool carried=false) {return transmissions(r,{{s,t,carried}})[0]<0.5f;}
// Real lampLighting() (red channel) at camera-relative receivers with normals, one lamp record in every list row.
inline std::vector<float> lampRed(Rig& r,const std::vector<std::pair<V,V>>& receivers,V lamp,int record) {
    auto glslMod=[](float x){return x-8.0f*std::floor(x/8.0f);};
    std::vector<float> list(16*512*4,0.0f);
    const float g[3]={float(lamp.x)+glslMod(r.camera[0])+32.0f,float(lamp.y)+glslMod(r.camera[1])+32.0f,float(lamp.z)+glslMod(r.camera[2])+32.0f};
    for(int row=0;row<512;++row){float* a=&list[row*16*4];a[0]=1;a[4]=g[0];a[5]=g[1];a[6]=g[2];a[7]=float(record);}
    glBindTexture(GL_TEXTURE_2D,r.lightList);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,512,GL_RGBA,GL_FLOAT,list.data());
    std::vector<float> in(receivers.size()*8,0.0f);
    for(size_t i=0;i<receivers.size();++i) {
        float* a=&in[i*8];a[0]=float(receivers[i].first.x);a[1]=float(receivers[i].first.y);a[2]=float(receivers[i].first.z);
        a[4]=float(receivers[i].second.x);a[5]=float(receivers[i].second.y);a[6]=float(receivers[i].second.z);
    }
    return runConsumer(r,r.lighting,in,receivers.size());
}

inline void probe(const fs::path& root) {
    std::cout<<"ENTITY-LIGHT QA renderer: "<<glGetString(GL_RENDERER)<<" | production sources: shadow_entities.{vsh,gsh,fsh}, lib/entity_occlusion.glsl, lib/local_lighting.glsl lampLighting()\n";
    ensure(glInteger(GL_MAJOR_VERSION)*10+glInteger(GL_MINOR_VERSION)>=43,"needs an OpenGL 4.3+ context (compute, image atomics)");
    if(slurp(root/"lib/settings.glsl").find("#define ENTITY_LIGHT_SHADOWS 1")==std::string::npos) {
        std::cout<<"INFO entity-light QA skipped: ENTITY_LIGHT_SHADOWS does not default to 1 in this pack\n";return;
    }
    while(glGetError()!=GL_NO_ERROR) {}
    Rig r;r.root=root;
    r.metaTriangles=int(sourceConstant(root,"lib/entity_grid.glsl","entityMetaTriangles"));
    r.metaOverflow=int(sourceConstant(root,"lib/entity_grid.glsl","entityMetaOverflow"));
    r.metaRejected=int(sourceConstant(root,"lib/entity_grid.glsl","entityMetaRejected"));
    r.metaSelf=int(sourceConstant(root,"lib/entity_grid.glsl","entityMetaSelf"));
    r.casterId=int(sourceConstant(root,"lib/entity_grid.glsl","entityCasterId"));
    r.selfId=int(sourceConstant(root,"lib/entity_grid.glsl","entitySelfId"));
    loadImages(r);
    // Producer: the real three-stage program. Consumers: the real lib sources behind two thin compute entry points.
    r.capture=linkPackProgram(root,"shadow_entities");
    const std::string rayMain=
        "layout(local_size_x=64) in;\n"
        "layout(std430,binding=0) readonly buffer Rays { vec4 rays[]; };\n"
        "layout(std430,binding=1) writeonly buffer Results { float results[]; };\n"
        "uniform int rayCount;\n";
    r.query=computeProgram("#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/entity_occlusion.glsl",root)+rayMain+
        "void main(){uint i=gl_GlobalInvocationID.x;if(i>=uint(rayCount))return;\n"
        " EntityBounds b=entityBounds();vec4 s=rays[2u*i],t=rays[2u*i+1u];int work=entityWorkBudget;\n"
        " results[i]=entityTransmission(b,s.xyz,t.xyz,s.w>0.5,work);}\n","entity-query");
    r.lighting=computeProgram("#version 430 compatibility\n"+expand(root/"lib/settings.glsl",root)+expand(root/"lib/uniforms.glsl",root)+
        expand(root/"lib/local_lighting.glsl",root)+rayMain+
        "void main(){uint i=gl_GlobalInvocationID.x;if(i>=uint(rayCount))return;\n"
        " results[i]=lampLighting(rays[2u*i].xyz,rays[2u*i+1u].xyz,vec3(0),0.0,0.0,false).r;}\n","entity-lighting");
    auto texture=[](GLenum internal,int w,int h){GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexStorage2D(GL_TEXTURE_2D,1,internal,w,h);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return t;};
    {   // 2x1 atlas: texel 0 opaque, texel 1 fully transparent
        const uint8_t px[8]={200,120,90,255, 200,120,90,0};
        r.atlas=texture(GL_RGBA8,2,1);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,2,1,GL_RGBA,GL_UNSIGNED_BYTE,px);
    }
    {   // Bind the record images at their DECLARED sizes (a lava pack appends rows below the 16x512 / 512x512
        // lamp layout). No blocks and no lava: block occlusion is not under test, every extra row is zero.
        const std::string props=slurp(root/"shaders.properties");
        const auto list=aqualumenLocalLights::parseImage(props,"lampListImage"),field=aqualumenLocalLights::parseImage(props,"lampFieldImage");
        ensure(list.w==16&&list.h>=512&&field.w==512&&field.h>=512,"lampList/lampField images must keep the 16x512 / 512x512 lamp layout in their first rows");
        r.lightList=texture(GL_RGBA32F,list.w,list.h);r.lightField=texture(GL_R32F,field.w,field.h);
        const float zero[4]={0,0,0,0};
        glClearTexImage(r.lightList,0,GL_RGBA,GL_FLOAT,zero);glClearTexImage(r.lightField,0,GL_RED,GL_FLOAT,zero);
    }
    r.color0=texture(GL_RGBA32F,r.size,r.size);r.color1=texture(GL_RGBA32F,r.size,r.size);r.depth=texture(GL_DEPTH_COMPONENT32F,r.size,r.size);
    glGenFramebuffers(1,&r.fbo);glBindFramebuffer(GL_FRAMEBUFFER,r.fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,r.color0,0);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT1,GL_TEXTURE_2D,r.color1,0);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,r.depth,0);
    const GLenum buffers[2]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};glDrawBuffers(2,buffers);
    ensure(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"shadow framebuffer incomplete");
    glGenBuffers(1,&r.vbo);glGenBuffers(1,&r.rayBuffer);glGenBuffers(1,&r.resultBuffer);
    {   // Stale garbage in the never-cleared record images must be harmless.
        Image& nodes=entityImage(r,"aqualumenEntityNodes");Image& tris=entityImage(r,"aqualumenEntityTriangles");
        const GLuint junk=0xA5A5A5A5u;
        glClearTexImage(nodes.texture,0,nodes.format,GL_UNSIGNED_INT,&junk);glClearTexImage(tris.texture,0,tris.format,GL_UNSIGNED_INT,&junk);
    }
    const V A={0,0,0};
    const Mesh mob=cow(A,0);
    const size_t mobTriangles=mob.triangles.size();
    auto frame=[&](const Mesh& mesh,int id){irisFrameClear(r);clearTargets(r);drawShadow(r,r.capture,mesh,id);return readMeta(r);};

    // 1. Producer stores casters, rejects everything else.
    {
        auto meta=frame(mob,r.casterId);
        ensure(meta[r.metaTriangles]==mobTriangles && meta[r.metaOverflow]==0,"caster stored "+std::to_string(meta[r.metaTriangles])+" of "+std::to_string(mobTriangles)+" triangles, overflow "+std::to_string(meta[r.metaOverflow]));
        pass("caster id "+std::to_string(r.casterId)+" stores all "+std::to_string(mobTriangles)+" triangles, overflow 0");
        for(int id:{-1,0,r.casterId+2}) {
            meta=frame(mob,id);
            ensure(meta[r.metaTriangles]==0 && meta[r.metaRejected]==mobTriangles,"unlisted id "+std::to_string(id)+" stored "+std::to_string(meta[r.metaTriangles])+", rejected "+std::to_string(meta[r.metaRejected]));
        }
        pass("unlisted ids -1, 0 and "+std::to_string(r.casterId+2)+" store nothing and are counted as rejected");
        meta=frame(cow(A,0,kOpaqueU0,kOpaqueU1,0.05f),r.casterId);
        ensure(meta[r.metaTriangles]==0,"nearly invisible vertex alpha must store nothing");
        meta=frame(cow(A,0,kClearU0,kClearU1),r.casterId);
        ensure(meta[r.metaTriangles]==0,"fully transparent texels must store nothing");
        pass("vertex alpha 0.05 and an all-transparent cut-out store nothing");
    }

    // 2. The geometry stage passes every primitive through, stored or not.
    {
        frame(mob,r.casterId);auto stored=readTargets(r);
        frame(mob,0);auto filtered=readTargets(r);
        const size_t covered=coveredTexels(r,stored);
        ensure(covered>200,"shadow map coverage "+std::to_string(covered)+" texels is too small: geometry stage dropped primitives");
        ensure(stored==filtered,"stored and filtered ids rasterise differently into the solar shadow targets");
        pass("depth/shadowcolor0/shadowcolor1 identical for stored and filtered ids over "+std::to_string(covered)+" covered texels (geometry stage forwards every primitive)");
    }

    // 3. Producer -> consumer against the double-precision oracle.
    {
        frame(mob,r.casterId);
        const double y=0.85;
        const std::vector<std::pair<std::string,Ray>> cases={
            {"between receiver and lamp blocks",{{0,y,-3},{0,y,3},false}},
            {"beside the caster is lit",{{2.5,y,-3},{2.5,y,3},false}},
            {"caster behind the receiver is ignored",{{0,y,1.0},{0,y,4},false}},
            {"caster beyond the lamp is ignored",{{0,y,-4},{0,y,-1},false}},
            {"segment ending 0.12 m before the caster is lit",{{0,y,-3},{0,y,-0.57},false}},
            {"leg is a separate occluder from the body (gap under the belly)",{{0.1,0.30,-3},{0.1,0.30,3},false}}};
        const bool expectBlocked[]={true,false,false,false,false,false};
        std::vector<Ray> rays;for(auto& c:cases) rays.push_back(c.second);
        auto result=transmissions(r,rays);
        for(size_t i=0;i<cases.size();++i) ensure((result[i]<0.5f)==expectBlocked[i],cases[i].first);
        pass("targeted segments: between blocks; beside, behind receiver, beyond lamp, 0.12 m short and under the belly are lit");

        std::mt19937 rng(21);std::uniform_real_distribution<double> U(0,1);
        std::vector<Ray> random;
        for(int i=0;i<4000;++i) {
            const V s={-2.5+5*U(rng),-0.2+2*U(rng),-2.5+5*U(rng)};V d;   // around the mob so that a useful share is blocked
            do d={U(rng)*2-1,U(rng)*2-1,U(rng)*2-1};while(length(d)>1||length(d)<0.05);
            random.push_back({s,s+d*(5.0*U(rng)/length(d)),false});
        }
        auto gpu=transmissions(r,random);
        size_t decisive=0,mismatch=0,hits=0;
        for(size_t i=0;i<random.size();++i) {
            const bool grown=oracleHit(mob.triangles,random[i].s,random[i].t,false,1e-4),shrunk=oracleHit(mob.triangles,random[i].s,random[i].t,false,-1e-4);
            if(grown!=shrunk) continue;   // within 0.1 mm of an edge: float and double may legitimately disagree
            ++decisive;hits+=grown;mismatch+=(gpu[i]<0.5f)!=grown;
        }
        ensure(decisive>3000 && hits>150 && decisive-hits>150,"random segments are not a meaningful mix (decisive "+std::to_string(decisive)+", blocked "+std::to_string(hits)+")");
        ensure(mismatch==0,std::to_string(mismatch)+" of "+std::to_string(decisive)+" GPU/CPU any-hit mismatches");
        pass("GPU any-hit == CPU oracle on "+std::to_string(decisive)+" decisive random segments ("+std::to_string(hits)+" blocked), 0 mismatches");
    }

    // 4. Clear / absence: moved and despawned mobs leave nothing although node/triangle images keep stale data.
    {
        const V B={4,0,0};
        const Ray throughA={{0,0.85,-3},{0,0.85,3},false},throughB={{4,0.85,-3},{4,0.85,3},false};
        frame(mob,r.casterId);
        auto t=transmissions(r,{throughA,throughB});
        ensure(t[0]<0.5f && t[1]>0.5f,"frame 1: mob at A must block A only");
        auto meta=frame(cow(B,0),r.casterId);
        t=transmissions(r,{throughA,throughB});
        ensure(meta[r.metaTriangles]==mobTriangles,"frame 2 must hold only this frame's triangles ("+std::to_string(meta[r.metaTriangles])+")");
        ensure(t[0]>0.5f && t[1]<0.5f,"frame 2: mob moved A->B, A must be lit (ghost) and B blocked");
        meta=frame(Mesh{},r.casterId);   // despawn: nothing is drawn, images are cleared as Iris does
        t=transmissions(r,{throughA,throughB});
        ensure(meta[r.metaTriangles]==0,"empty frame reports triangles");
        ensure(t[0]>0.5f && t[1]>0.5f,"frame 3: despawned mob still blocks (ghost)");
        Image& nodes=entityImage(r,"aqualumenEntityNodes");std::vector<uint32_t> stale(16);
        glGetTextureSubImage(nodes.texture,0,0,0,0,4,1,1,GL_RGBA_INTEGER,GL_UNSIGNED_INT,GLsizei(stale.size()*4),stale.data());
        bool nonzero=false;for(auto w:stale) nonzero|=w!=0;
        ensure(nonzero,"control failed: node image was cleared, so this test does not prove stale-record safety");
        pass("move A->B and despawn: no ghost; heads/meta cleared, node/triangle images deliberately stale");
        // Consumers against an explicitly empty field (what a legacy fixture binds).
        irisFrameClear(r);
        ensure(!blocked(r,{0,0.85,-3},{0,0.85,3}),"cleared field must never block");
    }

    // 5. Own body versus held and placed lights.
    {
        Mesh self=cow(A,0);self.markSelf();
        auto meta=frame(self,r.selfId);
        ensure(meta[r.metaSelf]==mobTriangles && meta[r.metaTriangles]==mobTriangles,"self caster id "+std::to_string(r.selfId)+" stores and flags every triangle");
        const V s={0,0.85,-3},t={0,0.85,3};
        ensure(blocked(r,s,t,false),"own body must shadow a placed lamp");
        ensure(!blocked(r,s,t,true),"own body must not shadow a held light");
        frame(cow(A,0),r.casterId);
        ensure(blocked(r,s,t,true),"another mob must shadow a held light");
        pass("self id "+std::to_string(r.selfId)+": own body shadows placed lamps, never the held light; other mobs shadow both");
    }

    // 6. Real lampLighting(): a lantern behind the cow casts the cow's shape on a wall.
    {
        const int record=15*64+15;const V lamp={0,1.1,-3};const double wallZ=2.5;
        std::vector<std::pair<V,V>> wall;std::vector<std::pair<int,int>> cell;
        for(int row=11;row>=0;--row) for(int col=0;col<33;++col) {wall.push_back({{-4+0.25*col,0.1+0.25*row,wallZ},{0,0,-1}});cell.push_back({col,row});}
        irisFrameClear(r);
        const auto clear=lampRed(r,wall,lamp,record);
        frame(mob,r.casterId);
        const auto lit=lampRed(r,wall,lamp,record);
        size_t shadowed=0,open=0,partial=0;std::string picture;
        for(size_t i=0;i<wall.size();++i) {
            ensure(clear[i]>0.0f && std::isfinite(clear[i]),"lamp must reach every wall receiver without the mob");
            // Emitter disk taps move with the receiver; classify with a dense ball of points (step 0.06 m, finer than any
            // 0.2 m limb) that contains every tap (radius 0.42*0.66 = 0.28 m), so only decisive receivers are asserted.
            int blockedTaps=0,total=0;
            const V start=wall[i].first+wall[i].second*0.025;
            for(int ix=-5;ix<=5;++ix) for(int iy=-5;iy<=5;++iy) for(int iz=-5;iz<=5;++iz) {
                if(ix*ix+iy*iy+iz*iz>25) continue;
                ++total;blockedTaps+=oracleHit(mob.triangles,start,lamp+V{0.06*ix,0.06*iy,0.06*iz},false,0.0);
            }
            const bool allBlocked=blockedTaps==total,allOpen=blockedTaps==0;
            if(allBlocked) {++shadowed;ensure(lit[i]==0.0f,"fully occluded wall receiver "+std::to_string(i)+" must be dark, got "+std::to_string(lit[i]));}
            else if(allOpen) {++open;ensure(std::abs(lit[i]-clear[i])<=1e-4f*clear[i],"open wall receiver "+std::to_string(i)+" changed by the mob: "+std::to_string(lit[i])+" vs "+std::to_string(clear[i]));}
            else ++partial;
            picture+=lit[i]<=0.0f?'#':(lit[i]<clear[i]*0.999f?'+':'.');
            if(cell[i].first==32) picture+='\n';
        }
        ensure(shadowed>=20 && open>=100,"wall test is not meaningful (shadowed "+std::to_string(shadowed)+", open "+std::to_string(open)+")");
        pass("real lampLighting(): wall receivers fully behind the cow are dark ("+std::to_string(shadowed)+"), open ones unchanged ("+std::to_string(open)+"), penumbra/mixed "+std::to_string(partial));
        std::cout<<"INFO entity-light wall (# umbra, + penumbra, . lit; lantern z=-3, cow at origin facing +x, wall z=2.5):\n"<<picture;
    }

    // 7. ENTITY_LIGHT_SHADOWS=0: everything still compiles and links, the geometry stage still forwards primitives.
    {
        const SourceEdit off=[](const std::string& text){
            const std::string on="#define ENTITY_LIGHT_SHADOWS 1";const auto at=text.find(on);
            if(at==std::string::npos) return text;
            std::string edited=text;edited.replace(at,on.size(),"#define ENTITY_LIGHT_SHADOWS 0");return edited;};
        int programs=0;
        std::vector<std::string> stems;
        for(auto& entry:fs::directory_iterator(root)) if(entry.path().extension()==".vsh") stems.push_back(entry.path().stem().string());
        std::sort(stems.begin(),stems.end());
        GLuint offCapture=0;
        for(auto& stem:stems) {
            GLuint program=linkPackProgram(root,stem,off);++programs;
            if(stem=="shadow_entities") offCapture=program;else glDeleteProgram(program);
        }
        ensure(offCapture!=0,"shadow_entities missing from the pack");
        auto meta=frame(mob,r.casterId);auto stored=readTargets(r);
        irisFrameClear(r);clearTargets(r);drawShadow(r,offCapture,mob,r.casterId);auto offMeta=readMeta(r);auto passthrough=readTargets(r);
        ensure(offMeta[r.metaTriangles]==0,"ENTITY_LIGHT_SHADOWS=0 must not capture");
        ensure(stored==passthrough,"ENTITY_LIGHT_SHADOWS=0 geometry stage must still forward every primitive");
        (void)meta;glDeleteProgram(offCapture);
        pass("ENTITY_LIGHT_SHADOWS=0: "+std::to_string(programs)+" programs compile/link with the geometry stage kept; no capture, shadow targets unchanged");
    }
    ensure(glGetError()==GL_NO_ERROR,"GL error during entity-light QA");
    std::cout<<"PASS entity-light QA complete on "<<glGetString(GL_RENDERER)<<": real shadow_entities capture, real occlusion consumer and lampLighting(); CPU-oracle fixture, not Minecraft/Iris or visual acceptance.\n";
}
}  // namespace aqualumenEntityLight
