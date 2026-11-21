#ifndef AQUALUMEN_BATHYMETRY_GRADIENT_PROBE_H
#define AQUALUMEN_BATHYMETRY_GRADIENT_PROBE_H

// Opt-in production-library math probe, NOT a water-main or live-Mod test.
// Include after water-optical-depth-probe.h. Only the caller may acquire/run
// the NVIDIA GL slot. The negative control is a diagnostic uniform override,
// not a shipping source/option change or a claim of historical RED evidence.
inline void productionBathymetryGradientProbe(const std::filesystem::path& root,
    const std::filesystem::path& artifacts="build/bathymetry-gradient") {
    namespace detail=aqualumenWaterOpticalDepthDetail;
    const auto* renderer=reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    if(!renderer||std::string(renderer).find("NVIDIA")==std::string::npos)
        throw std::runtime_error("Bathymetry gradient probe requires real NVIDIA GL");
    if(std::filesystem::exists(artifacts))
        throw std::runtime_error("Preserve previous bathymetry-gradient evidence; use a new directory");
    std::filesystem::create_directories(artifacts);
    const std::string vertex="#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
    const std::string fragment="#version 330 compatibility\n"
        +expand(root/"lib/settings.glsl",root,0)
        +expand(root/"lib/bathymetry.glsl",root,0)
        +expand(root/"lib/waves.glsl",root,0)+R"GLSL(
// DEBUG-bathymetry-gradient: invoke unchanged production helpers once.
uniform vec2 DEBUG_position;
uniform float DEBUG_detail;
uniform int DEBUG_zeroGradient;
void main() {
    vec3 column;
    bool known=localWaterColumn(DEBUG_position,-0.5,column);
    if(DEBUG_zeroGradient!=0) column.yz=vec2(0.0);
    float variance;
    vec3 state=localWaveState(DEBUG_position,1.25,0.08,column,DEBUG_detail,variance);
    gl_FragData[0]=vec4(state,float(known));
    gl_FragData[1]=vec4(column,variance);
}
)GLSL";
    for(const auto& entry:std::array<std::pair<std::string,std::string>,2>{{{"probe.vsh",vertex},{"production-library.fsh",fragment}}}) {
        std::ofstream file(artifacts/entry.first);file<<entry.second;
        if(!file) throw std::runtime_error("Cannot save bathymetry-gradient source evidence");
    }
    detail::Fixture fixture;
    fixture.programs[0]=link(vertex,fragment,"DEBUG-bathymetry-gradient-library",nullptr);
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);
    const GLenum buffers[2]={GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};
    for(int i=0;i<2;++i) {
        glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,fixture.textures[i+1]);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,1,1,0,GL_RGBA,GL_FLOAT,nullptr);
        glFramebufferTexture2D(GL_FRAMEBUFFER,buffers[i],GL_TEXTURE_2D,fixture.textures[i+1],0);
    }
    glDrawBuffers(2,buffers);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Bathymetry gradient framebuffer incomplete");
    // A 64m / 64-column map, with ONLY the four central neighbours valid.
    // Their exact cell centres are (-.5,+.5) in each axis. The independent
    // external depth plane is .4+.18*x+.15*z; no wave expression is copied.
    std::vector<float> map(64*64*4,0);
    for(int z=31;z<=32;++z) for(int x=31;x<=32;++x) {
        const float px=float(x)-31.5f,pz=float(z)-31.5f;
        const int i=(z*64+x)*4;
        map[i]=0.4f+0.18f*px+0.15f*pz;map[i+1]=-0.5f;map[i+2]=1;
    }
    detail::save(artifacts/"graded-input.rgba32f",map);
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,fixture.textures[0]);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,64,64,0,GL_RGBA,GL_FLOAT,map.data());
    glUseProgram(fixture.programs[0]);
    const GLint sampler=glGetUniformLocation(fixture.programs[0],"aqualumenBathymetry");
    const GLint grid=glGetUniformLocation(fixture.programs[0],"aqualumenBathymetryGrid");
    const GLint ready=glGetUniformLocation(fixture.programs[0],"aqualumenBathymetryReady");
    const GLint position=glGetUniformLocation(fixture.programs[0],"DEBUG_position");
    const GLint detailUniform=glGetUniformLocation(fixture.programs[0],"DEBUG_detail");
    const GLint zeroGradient=glGetUniformLocation(fixture.programs[0],"DEBUG_zeroGradient");
    if(sampler<0||grid<0||ready<0||position<0||detailUniform<0||zeroGradient<0)
        throw std::runtime_error("Production bathymetry-gradient interface was optimized away/missing");
    glUniform1i(sampler,0);glUniform4f(grid,-32,-32,64,-0.5f);glUniform1i(ready,1);
    glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisable(GL_BLEND);
    glDisable(GL_CULL_FACE);glDisable(GL_SCISSOR_TEST);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glViewport(0,0,1,1);glClearColor(0,0,0,0);
    std::ofstream samples(artifacts/"actual-samples.csv"),checks(artifacts/"derivative-checks.csv");
    samples<<std::setprecision(17)<<"sample,detail,x,z,zeroGradient,height,slopeX,slopeZ,known,depth,depthGradientX,depthGradientZ,variance\n";
    checks<<std::setprecision(17)<<"point,detail,axis,productionSlope,Dh,D2h,truncationEstimate,floatAllowance,bound,positiveError,zeroGradientSlope,negativeError\n";
    std::vector<float> rawSamples;
    int sampleIndex=0;
    auto evaluate=[&](float x,float z,float level,bool nullGradient) {
        glUniform2f(position,x,z);glUniform1f(detailUniform,level);glUniform1i(zeroGradient,nullGradient?1:0);
        glClear(GL_COLOR_BUFFER_BIT);glBegin(GL_QUADS);
        glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        std::array<float,8> result={};
        for(int i=0;i<2;++i) {glReadBuffer(buffers[i]);glReadPixels(0,0,1,1,GL_RGBA,GL_FLOAT,result.data()+4*i);}
        glReadBuffer(GL_COLOR_ATTACHMENT0);
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("Bathymetry gradient actual-helper GL error");
        for(float value:result) if(!std::isfinite(value)) throw std::runtime_error("Nonfinite gradient helper output");
        if(result[3]!=1) throw std::runtime_error("INCONCLUSIVE graded map: the actual helper did not use all valid neighbours");
        samples<<sampleIndex++<<","<<level<<","<<x<<","<<z<<","<<nullGradient;
        for(float value:result) samples<<","<<value;
        samples<<"\n";rawSamples.insert(rawSamples.end(),result.begin(),result.end());
        const double expectedDepth=0.4+0.18*double(x)+0.15*double(z);
        const double mapBound=64*std::numeric_limits<float>::epsilon();
        if(std::abs(double(result[4])-expectedDepth)>mapBound
            ||std::abs(double(result[5])-(nullGradient?0:0.18))>mapBound
            ||std::abs(double(result[6])-(nullGradient?0:0.15))>mapBound)
            throw std::runtime_error("Actual bilinear column disagrees with independent affine-depth input");
        return result;
    };
    constexpr float h=0.002f;
    const std::array<std::array<float,2>,3> points={{{0.125f,-0.125f},{-0.17f,0.13f},{0.23f,0.19f}}};
    bool allPositive=true,allNegativeRejected=true;
    for(int point=0;point<int(points.size());++point) for(float level:{0.0f,1.0f}) {
        const auto centre=evaluate(points[point][0],points[point][1],level,false);
        const auto repeated=evaluate(points[point][0],points[point][1],level,false);
        if(centre!=repeated) throw std::runtime_error("Bathymetry-gradient fixed-input helper is not deterministic");
        const auto negative=evaluate(points[point][0],points[point][1],level,true);
        if(negative[0]!=centre[0]) throw std::runtime_error("Diagnostic zero-gradient override changed height, not only derivative input");
        bool negativeRejected=false;
        for(int axis=0;axis<2;++axis) {
            float minusX=points[point][0],plusX=minusX,minusZ=points[point][1],plusZ=minusZ;
            if(axis==0) {minusX-=h;plusX+=h;} else {minusZ-=h;plusZ+=h;}
            const auto lo=evaluate(minusX,minusZ,level,false),hi=evaluate(plusX,plusZ,level,false);
            const double step=axis==0?double(plusX)-minusX:double(plusZ)-minusZ;
            const double Dh=(double(hi[0])-lo[0])/step;
            minusX=points[point][0];plusX=minusX;minusZ=points[point][1];plusZ=minusZ;
            if(axis==0) {minusX-=2*h;plusX+=2*h;} else {minusZ-=2*h;plusZ+=2*h;}
            const auto lo2=evaluate(minusX,minusZ,level,false),hi2=evaluate(plusX,plusZ,level,false);
            const double step2=axis==0?double(plusX)-minusX:double(plusZ)-minusZ;
            const double D2h=(double(hi2[0])-lo2[0])/step2;
            // Central differences have leading O(h^2) truncation. Use the
            // entire resolution discrepancy (not its /3 extrapolation) plus
            // a conservative float32 height-subtraction/phase allowance.
            // This is an estimated numerical error envelope, not a formal
            // symbolic bound or a fitted aesthetic tolerance.
            const double scale=std::max({0.01,std::abs(double(centre[0])),std::abs(double(lo[0])),std::abs(double(hi[0])),std::abs(double(lo2[0])),std::abs(double(hi2[0]))});
            const double truncation=std::abs(D2h-Dh);
            const double floatAllowance=64*std::numeric_limits<float>::epsilon()*scale/(step*0.5);
            const double bound=truncation+floatAllowance;
            const double error=std::abs(double(centre[axis+1])-Dh),negativeError=std::abs(double(negative[axis+1])-Dh);
            allPositive=allPositive && error<=bound;
            negativeRejected=negativeRejected || negativeError>2*bound;
            checks<<point<<","<<level<<","<<axis<<","<<centre[axis+1]<<","<<Dh<<","<<D2h<<","<<truncation<<","<<floatAllowance<<","<<bound<<","<<error<<","<<negative[axis+1]<<","<<negativeError<<"\n";
            std::cout<<std::setprecision(12)<<"DEBUG-bathymetry-gradient point="<<point<<" detail="<<level<<" axis="<<axis<<" slope="<<centre[axis+1]<<" central="<<Dh<<" twice-step="<<D2h<<" bound="<<bound<<" error="<<error<<" zero-gradient-error="<<negativeError<<"\n";
        }
        allNegativeRejected=allNegativeRejected && negativeRejected;
    }
    samples.close();checks.close();detail::save(artifacts/"actual-samples.rgba32f",rawSamples);
    if(!samples||!checks) throw std::runtime_error("Could not persist actual gradient evidence");
    if(!allNegativeRejected) throw std::runtime_error("INCONCLUSIVE gradient positive control: zero-gradient derivative omission was not distinguishable at every detail/point");
    if(!allPositive) throw std::runtime_error("Actual production localWaveState slopes disagree with finite differences of its own spatially tapered height");
    std::cout<<"PASS production bathymetry/waves libraries: affine-depth gradient, detail0/1 height derivative consistency and deliberately omitted-gradient negative control (not water-main/live-Mod acceptance)\n";
}
#endif
