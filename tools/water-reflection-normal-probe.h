#ifndef AQUALUMEN_REFLECTION_NORMAL_PROBE
#define AQUALUMEN_REFLECTION_NORMAL_PROBE

inline void waterReflectionNormalProbe(const std::filesystem::path& root) {
    const std::string source=expand(root/"lib/water.glsl",root,0);
    const auto start=source.find("vec3 waterReflectionNormal(");
    if(start==std::string::npos)throw std::runtime_error("Missing production reflection normal helper");
    const auto body=source.find('{',start);
    std::size_t end=body;int depth=0;
    do {if(source[end]=='{')++depth;else if(source[end]=='}')--depth;++end;}
    while(depth>0&&end<source.size());
    if(depth!=0)throw std::runtime_error("Unbalanced production normal helper");
    aqualumenSolarProbeDetail::Fixture fixture;
    const std::string fragment="#version 330 compatibility\n"+source.substr(start,end-start)+R"(
void main() {
    float theta=radians(-80.0+10.0*floor(gl_FragCoord.y));
    float phi=radians(-80.0+10.0*floor(gl_FragCoord.x));
    vec3 view=vec3(sin(theta),0,cos(theta));
    vec3 optical=vec3(sin(phi),0,cos(phi));
    vec3 corrected=waterReflectionNormal(optical,vec3(0,0,1),view);
    gl_FragColor=vec4(corrected,dot(reflect(-view,corrected),vec3(0,0,1)));
})";
    fixture.programs[0]=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"production-reflection-normal",nullptr);
    glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,fixture.textures[0]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,17,17,0,GL_RGBA,GL_FLOAT,nullptr);
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,fixture.textures[0],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Normal fixture framebuffer incomplete");
    glViewport(0,0,17,17);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);
    glUseProgram(fixture.programs[0]);
    glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
    std::array<float,17*17*4> output{};
    glReadPixels(0,0,17,17,GL_RGBA,GL_FLOAT,output.data());
    int corrected=0,unchanged=0;
    for(int row=0;row<17;row++)for(int column=0;column<17;column++) {
        const double theta=(-80+10*row)*aqualumenSolarProbeDetail::pi/180;
        const double phi=(-80+10*column)*aqualumenSolarProbeDetail::pi/180;
        if(std::cos(phi-theta)<=0)continue;
        const int pixel=(row*17+column)*4;
        const double original=std::cos(2*phi-theta);
        if(std::abs(original)<1e-6)continue;
        double expected=phi;
        if(original<0) {
            expected=(theta+(phi>theta?1:-1)*aqualumenSolarProbeDetail::pi/2)/2;
            ++corrected;
        } else ++unchanged;
        const double tolerance=original<0?.001:1e-6;
        if(!std::isfinite(output[pixel+3])||output[pixel+3]<-1e-6
           ||std::abs(output[pixel]-std::sin(expected))>tolerance
           ||std::abs(output[pixel+1])>tolerance
           ||std::abs(output[pixel+2]-std::cos(expected))>tolerance)
            throw std::runtime_error("GPU normal differs from independent angular hemisphere oracle");
    }
    if(glGetError()!=GL_NO_ERROR||corrected<20||unchanged<20)
        throw std::runtime_error("Normal fixture GL error or vacuous coverage");
    std::cout<<"PASS production reflection-normal GPU hemisphere: corrected="<<corrected
             <<" unchanged="<<unchanged<<"; not natural-rim or physical transport acceptance\n";
}
inline void waterInterfaceNormalProbe(const std::filesystem::path& root) {
    const std::string source=expand(root/"lib/water.glsl",root,0);
    const auto start=source.find("bool waterInterfaceNormalAdmitted(");
    const auto end=source.find("bool waterRefractionFootprintContinuous(",start);
    if(start==std::string::npos||end==std::string::npos)
        throw std::runtime_error("Missing coupled interface normal helpers");
    aqualumenSolarProbeDetail::Fixture fixture;
    const std::string fragment="#version 330 compatibility\n"+source.substr(start,end-start)+R"(
void main() {
    float theta=radians(-89.0+178.0*floor(gl_FragCoord.y)/178.0);
    float phi=radians(-89.0+178.0*floor(gl_FragCoord.x)/178.0);
    vec3 view=vec3(sin(theta),0,cos(theta));
    vec3 optical=vec3(sin(phi),0,cos(phi));
    vec3 geometry=vec3(0,0,1);
    vec3 corrected=waterInterfaceNormal(optical,geometry,view,1.333);
    vec3 transmitted=refract(-view,corrected,1.333);
    bool original=waterInterfaceNormalAdmitted(optical,geometry,view,1.333);
    gl_FragColor=vec4(dot(reflect(-view,corrected),geometry),dot(transmitted,geometry),
                     original?length(corrected-optical):length(corrected),dot(corrected,view));
})";
    fixture.programs[0]=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}",fragment,"coupled-interface-normal",nullptr);
    glBindTexture(GL_TEXTURE_2D,fixture.textures[0]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,179,179,0,GL_RGBA,GL_FLOAT,nullptr);
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffers[0]);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,fixture.textures[0],0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Interface fixture framebuffer incomplete");
    glViewport(0,0,179,179);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);
    glUseProgram(fixture.programs[0]);
    glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
    std::vector<float> output(179*179*4);
    glReadPixels(0,0,179,179,GL_RGBA,GL_FLOAT,output.data());
    for(std::size_t pixel=0;pixel<output.size();pixel+=4) {
        for(std::size_t component=0;component<4;component++)
            if(!std::isfinite(output[pixel+component]))throw std::runtime_error("Nonfinite interface normal");
        if(output[pixel]<-1e-6||output[pixel+1]>1e-6||output[pixel+3]<=0
           ||(output[pixel+2]>1e-6&&std::abs(output[pixel+2]-1)>1e-6))
            throw std::runtime_error("Coupled interface normal violates geometric side or preservation");
    }
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("Interface fixture GL error");
    std::cout<<"PASS coupled underwater normal: 32041 GPU samples, geometric sides and admitted-normal preservation; not visual acceptance\n";
}
#endif
