#define main aqualumen_paired_native_unused_main
#include "water_paired_native.cpp"
#undef main
#include <algorithm>

namespace continuous {
constexpr int width=1600,height=900,count=width*height;
constexpr size_t elements=size_t(count)*4;
using V3=std::array<double,3>;
std::vector<float> read(const fs::path& path) {
    require(fs::file_size(path)==elements*sizeof(float),"input extent differs: "+path.string());
    std::vector<float> result(elements);std::ifstream file(path,std::ios::binary);
    file.read(reinterpret_cast<char*>(result.data()),std::streamsize(elements*sizeof(float)));
    require(bool(file),"input read failed");for(float x:result)require(std::isfinite(x),"nonfinite input");return result;
}
V3 fitEye(const std::vector<float>& p,const std::vector<float>& v,const std::vector<float>& c,double& maxError) {
    double a[3][4]={};size_t used=0;
    for(int i=0;i<count;i++){const int t=i*4;if(c[t+3]!=1)continue;++used;
        double length=0;for(int j=0;j<3;j++)length+=double(v[t+j])*v[t+j];
        require(std::abs(length-1)<2e-5,"input view direction not unit");
        for(int j=0;j<3;j++)for(int k=0;k<3;k++){
            const double m=(j==k?1.0:0.0)-double(v[t+j])*v[t+k];a[j][k]+=m;a[j][3]+=m*p[t+k];
        }
    }
    require(used>1000,"insufficient water eye lines");
    for(int j=0;j<3;j++){int pivot=j;for(int k=j+1;k<3;k++)if(std::abs(a[k][j])>std::abs(a[pivot][j]))pivot=k;
        require(std::abs(a[pivot][j])>1e-6,"eye fit singular");for(int k=0;k<4;k++)std::swap(a[j][k],a[pivot][k]);
        const double scale=a[j][j];for(int k=j;k<4;k++)a[j][k]/=scale;
        for(int k=0;k<3;k++)if(k!=j){const double factor=a[k][j];for(int l=j;l<4;l++)a[k][l]-=factor*a[j][l];}
    }
    V3 eye={a[0][3],a[1][3],a[2][3]};maxError=0;
    for(int i=0;i<count;i++){const int t=i*4;if(c[t+3]!=1)continue;double dot=0,err=0;
        for(int j=0;j<3;j++)dot+=(eye[j]-p[t+j])*v[t+j];
        for(int j=0;j<3;j++)err+=std::pow(eye[j]-p[t+j]-dot*v[t+j],2);
        maxError=std::max(maxError,std::sqrt(err));
    }
    require(maxError<2e-4,"stored rays lack common eye within 0.2 mm");return eye;
}
std::string fragment(const fs::path& root,bool flat) {
    std::string text="#version 330 compatibility\n"+source(root/"lib/settings.glsl",root);
    if(flat)text+="\n#undef WAVE_HEIGHT\n#define WAVE_HEIGHT 0.0\n";
    text+=source(root/"lib/waves.glsl",root);
    text+=R"GLSL(
uniform sampler2D positions, actualNormals, views, flags, classes;
uniform vec3 eye;
uniform vec2 cameraXZ;
uniform float rootDistanceOffset;
uniform int boundsOnly;
const float footprint=0.035;
vec3 state(vec2 x) { vec3 c;float u;return waveSurfaceLocal(x,17.0,footprint,16.0,vec2(0.0),1.0,c,u); }
vec2 bounds() {
    float variance=0.0,heightBound=0.0,slopeBound=0.0;
    for(int i=0;i<WAVE_COMPONENTS;i++) {
        vec2 d;float k,w,p;waveMode(i,d,k,w,p);variance+=0.5*w*w;
        float amplitude=abs(w)*exp(-0.25*pow(k*footprint,2.0));
        heightBound+=amplitude;slopeBound+=amplitude*k;
    }
    return vec2(heightBound,slopeBound)*(0.5*abs(WAVE_HEIGHT)/sqrt(max(variance,1e-6)));
}
float residual(float distance,vec3 ray,float meanY) {
    vec3 point=eye+distance*ray;return point.y-meanY-state(point.xz+cameraXZ).x;
}
float root(float lo,float hi,vec3 ray,float meanY,int steps) {
    for(int i=0;i<48;i++) {if(i>=steps)break;float mid=lo+(hi-lo)*0.5;
        if(residual(mid,ray,meanY)>0.0)hi=mid;else lo=mid;
    }
    return lo+(hi-lo)*0.5;
}
float fresnel(float ci,float k) {
    if(k<=0.0)return 1.0;float ct=sqrt(k);
    float rs=(1.333*ci-ct)/(1.333*ci+ct),rp=(ci-1.333*ct)/(ci+1.333*ct);
    return clamp(0.5*(rs*rs+rp*rp),0.0,1.0);
}
void main() {
    ivec2 at=ivec2(gl_FragCoord.xy);
    vec4 p=texelFetch(positions,at,0),c=texelFetch(classes,at,0);
    vec3 nActual=texelFetch(actualNormals,at,0).xyz,v=texelFetch(views,at,0).xyz;
    gl_FragData[0]=vec4(0.0);gl_FragData[1]=vec4(0.0);gl_FragData[2]=vec4(0.0);gl_FragData[3]=vec4(1.0,0.0,0.0,0.0);
    if(boundsOnly==1){gl_FragData[0]=vec4(bounds(),WAVE_HEIGHT,float(WAVE_COMPONENTS));return;}
    if(c.w!=1.0)return;
    vec3 ray=-v,delta=eye-p.xyz;
    float lineError=length(delta-dot(delta,v)*v);
    vec3 storedWave=state(p.xz+cameraXZ);
    vec3 storedNormal=normalize(vec3(storedWave.y,-1.0,storedWave.z));
    float normalDiff=length(storedNormal-nActual);
    vec2 bound=bounds();float margin=ray.y-bound.y*length(ray.xz);
    gl_FragData[2]=vec4(normalDiff,0.0,margin,0.0);
    gl_FragData[3]=vec4(2.0,lineError,0.0,p.y-p.w-storedWave.x);
    if(texelFetch(flags,at,0).w!=3.0)return;
    gl_FragData[3].x=3.0;if(lineError>0.0002)return;
    gl_FragData[3].x=4.0;if(ray.y<=0.0 || margin<=0.00001)return;
    float lo=max(0.0,(p.w-bound.x-eye.y)/ray.y),hi=(p.w+bound.x-eye.y)/ray.y;
    gl_FragData[3].x=5.0;if(hi<lo || residual(lo,ray,p.w)>0.00001 || residual(hi,ray,p.w)<-0.00001)return;
    float s32=root(lo,hi,ray,p.w,32),s48=root(lo,hi,ray,p.w,48);
    vec3 point=eye+(s48+rootDistanceOffset)*ray,wave=state(point.xz+cameraXZ);
    vec3 n=normalize(vec3(wave.y,-1.0,wave.z));
    float ci=max(dot(n,v),0.0),k=1.0-1.333*1.333*(1.0-ci*ci);
    gl_FragData[0]=vec4(n,k);gl_FragData[1]=vec4(refract(ray,n,1.333),fresnel(ci,k));
    gl_FragData[2]=vec4(normalDiff,abs(residual(s48+rootDistanceOffset,ray,p.w)),margin,point.y-p.y);
    gl_FragData[3]=vec4(rootDistanceOffset==0.0?0.0:6.0,lineError,abs(s48-s32),p.y-p.w-storedWave.x);
}
)GLSL";return text;
}
struct Pass {
    std::array<GLuint,9> textures={};GLuint fbo=0;
    Pass(const std::array<const std::vector<float>*,5>& inputs){
        glGenTextures(textures.size(),textures.data());glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
        for(int i=0;i<9;i++){glActiveTexture(GL_TEXTURE0+i);glBindTexture(GL_TEXTURE_2D,textures[i]);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,i<5?inputs[i]->data():nullptr);
            if(i>=5)glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0+i-5,GL_TEXTURE_2D,textures[i],0);
        }
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"reference framebuffer incomplete");
        for(GLenum cap:{GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD})glDisable(cap);
        glViewport(0,0,width,height);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    }
    ~Pass(){glDeleteTextures(textures.size(),textures.data());glDeleteFramebuffers(1,&fbo);}
    std::array<std::vector<float>,4> draw(GLuint p,V3 eye,float cameraX,float cameraZ,float offset=0,int boundsOnly=0){
        glUseProgram(p);const char* names[]={"positions","actualNormals","views","flags","classes"};
        for(int i=0;i<5;i++){const auto location=glGetUniformLocation(p,names[i]);require(location>=0,"reference input inactive");glUniform1i(location,i);}
        glUniform3f(glGetUniformLocation(p,"eye"),eye[0],eye[1],eye[2]);glUniform2f(glGetUniformLocation(p,"cameraXZ"),cameraX,cameraZ);
        glUniform1f(glGetUniformLocation(p,"rootDistanceOffset"),offset);glUniform1i(glGetUniformLocation(p,"boundsOnly"),boundsOnly);
        const GLenum targets[]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1,GL_COLOR_ATTACHMENT2,GL_COLOR_ATTACHMENT3};glDrawBuffers(4,targets);
        glBegin(GL_TRIANGLES);for(int i:{0,1,2,0,2,3})glVertex2f(i==1||i==2?1:-1,i>=2?1:-1);glEnd();
        std::array<std::vector<float>,4> result;
        for(int i=0;i<4;i++){result[i].assign(elements,std::numeric_limits<float>::quiet_NaN());glReadBuffer(targets[i]);
            glReadPixels(0,0,width,height,GL_RGBA,GL_FLOAT,result[i].data());for(float v:result[i])require(std::isfinite(v),"reference nonfinite readback");}
        require(glGetError()==GL_NO_ERROR,"reference GL draw/read error");return result;
    }
};
}
int main(int argc,char** argv){
    try {
        using namespace continuous;
        require(argc==6 || (argc==7&&std::string(argv[6])=="--cpu-input-check"),"usage: water-continuous-reference FROZEN_SHADER_ROOT CAPTURE_ROOT NEW_OUTPUT CAMERA_X CAMERA_Z [--cpu-input-check]");
        const fs::path root=argv[1],capture=argv[2],out=argv[3];require(!fs::exists(out),"output must not exist");
        const float cameraX=std::stof(argv[4]),cameraZ=std::stof(argv[5]);require(std::isfinite(cameraX)&&std::isfinite(cameraZ),"nonfinite camera");
        const uint32_t endian=1;require(*reinterpret_cast<const unsigned char*>(&endian)==1,"little endian host required");
        const auto p=read(capture/"optics-colortex1.rgba32f"),n=read(capture/"optics-colortex13.rgba32f"),v=read(capture/"optics-colortex14.rgba32f"),
            flags=read(capture/"optics-colortex2.rgba32f"),c=read(capture/"classification.rgba32f");
        double maxLine=0;const V3 eye=fitEye(p,v,c,maxLine);
        if(argc==7){std::cout.precision(17);std::cout<<"cpu_only=1\neye_relative="<<eye[0]<<","<<eye[1]<<","<<eye[2]<<"\nmax_input_eye_line_error="<<maxLine<<"\n";return 0;}
        require(fs::create_directories(out),"output directory was not exclusively created");
        Context context;Pass pass({&p,&n,&v,&flags,&c});
        const std::string vs="#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
        const auto flatSource=fragment(root,true),waveSource=fragment(root,false);
        const GLuint flatProgram=program(vs,flatSource),waveProgram=program(vs,waveSource);
        const auto boundPass=pass.draw(waveProgram,eye,cameraX,cameraZ,0,1);
        const float heightBound=boundPass[0][0],slopeBound=boundPass[0][1];
        require(heightBound>0&&slopeBound>0,"wave amplitude/slope bounds not positive");
        auto flat=pass.draw(flatProgram,eye,cameraX,cameraZ);size_t flatValid=0;
        for(int i=0;i<count;i++){const int t=i*4;if(flat[3][t]!=0)continue;++flatValid;
            const float ci=std::max(-v[t+1],0.0f),k=1-1.333f*1.333f*(1-ci*ci);
            require(std::abs(flat[0][t+3]-k)<1e-5,"flat Snell discriminant differs");
            require(flat[2][t+1]<1e-5&&flat[3][t+2]<1e-5,"flat root residual/stability failed");
            require(k>0 || flat[1][t+3]==1,"flat TIR Fresnel differs");
            if(k>0.0001f){const float ct=std::sqrt(k),rs=(1.333f*ci-ct)/(1.333f*ci+ct),rp=(ci-1.333f*ct)/(ci+1.333f*ct);
                require(std::abs(flat[1][t]+1.333f*v[t])<2e-4&&std::abs(flat[1][t+1]-ct)<2e-4&&std::abs(flat[1][t+2]+1.333f*v[t+2])<2e-4,"flat transmitted direction differs");
                require(std::abs(flat[1][t+3]-0.5f*(rs*rs+rp*rp))<2e-4,"flat exact Fresnel differs");
            }
        }
        require(flatValid>1000,"flat control lacks qualified pixels");
        auto wave=pass.draw(waveProgram,eye,cameraX,cameraZ);
        auto shifted=pass.draw(waveProgram,eye,cameraX,cameraZ,0.05f);
        const char* names[]={"normal-k.rgba32f","transmitted-fresnel.rgba32f","qualification.rgba32f","status.rgba32f"};
        std::array<size_t,6> statuses={};for(int i=0;i<count;i++){const float status=wave[3][i*4];require(status>=0&&status<6&&status==std::floor(status),"invalid reference status");++statuses[size_t(status)];}
        for(int i=0;i<4;i++){raw(out/names[i],wave[i]);raw(out/(std::string("flat-")+names[i]),flat[i]);raw(out/(std::string("shifted-5cm-")+names[i]),shifted[i]);}
        std::ofstream report(out/"report.txt");report.precision(17);
        report<<"scope=TEST continuous filtered spectrum; no secondary visibility, radiance, fluid simulation, Iris or FPS acceptance\n"
            <<"viewport=1600x900\nraw_origin=bottom-left\nfloat_encoding=IEEE754-binary32-little-endian\n"
            <<"renderer="<<glGetString(GL_RENDERER)<<"\nversion="<<glGetString(GL_VERSION)<<"\n"
            <<"camera_x="<<cameraX<<"\ncamera_z="<<cameraZ<<"\neye_relative="<<eye[0]<<","<<eye[1]<<","<<eye[2]<<"\nmax_input_eye_line_error="<<maxLine<<"\n"
            <<"footprint=0.035\ndepth=16\ndepth_gradient=0,0\ndetail=1\nphase=17\nripples=0\n"
            <<"height_bound="<<heightBound<<"\nslope_lipschitz_bound="<<slopeBound<<"\nnegative_control_root_distance_offset=0.05\n"
            <<"normal_k=reference downward normal xyz, Snell discriminant\ntransmitted_fresnel=reference transmitted xyz, exact dielectric Fresnel\n"
            <<"qualification=stored normal L2 difference, root residual, uniqueness margin, reference minus stored height\n"
            <<"status=status code, input eye line error, 48 minus 32 root distance absolute, stored height residual\n"
            <<"status_codes=0 valid,1 nonwater,2 unknown/non-top,3 eye-line failure,4 no monotonic guarantee,5 bracket failure,6 forced 5cm root offset negative control\n"
            <<"flat_valid="<<flatValid<<"\nflat_snell_angular_diameter_degrees="<<2*std::asin(1.0/1.333)*180/3.14159265358979323846<<"\n";
        for(int i=0;i<6;i++)report<<"status_"<<i<<"="<<statuses[i]<<"\n";
        require(glGetError()==GL_NO_ERROR,"reference pre-report GL error");report<<"gl_error=0\n";require(bool(report),"report write failed");glDeleteProgram(flatProgram);glDeleteProgram(waveProgram);
        require(glGetError()==GL_NO_ERROR,"reference cleanup GL error");std::cout<<"reference_complete=1\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
