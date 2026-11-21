#ifndef AQUALUMEN_SOLAR_TIR_FOOTPRINT_PROBE
#define AQUALUMEN_SOLAR_TIR_FOOTPRINT_PROBE
void solarTirFootprintProbe(const fs::path& root) {
    const std::string fragment="#version 330 compatibility\n"+expand(root/"lib/settings.glsl",root)
        +expand(root/"lib/uniforms.glsl",root)+expand(root/"lib/atmosphere.glsl",root)+expand(root/"lib/water.glsl",root)+R"(
uniform float phase;
uniform bool guardFootprint;
uniform bool obliqueSun;
uniform bool zenithControl;
void main() {
    float critical=asin(1.0/1.333);
    float angle=(zenithControl?0.0:critical)+(gl_FragCoord.x+gl_FragCoord.y-64.0+phase)*0.0003;
    float azimuth=gl_FragCoord.y*0.01;
    vec3 incident=vec3(sin(angle)*cos(azimuth),cos(angle),sin(angle)*sin(azimuth));
    vec3 transmitted=refract(incident,vec3(0.0,-1.0,0.0),1.333);
    bool valid=dot(transmitted,transmitted)>0.000001;
    vec3 ray=valid?transmitted:vec3(0.0,1.0,0.0);
    float discriminant=1.0-1.333*1.333*(1.0-cos(angle)*cos(angle));
    bool continuous=waterRefractionFootprintContinuous(discriminant);
    vec3 sun=obliqueSun?normalize(vec3(.92,.42,.25)):vec3(0,1,0);
    float coverage=solarDiskCoverage(ray,sun,!guardFootprint || continuous);
    gl_FragColor=vec4(valid?coverage:0.0,float(valid),dot(ray,sun),1.0);
}
)";
    GLuint program=link("#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n",fragment,"solar-tir-footprint");
    GLuint texture,framebuffer;
    glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,64,64,0,GL_RGBA,GL_FLOAT,nullptr);
    glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
        throw std::runtime_error("Solar TIR footprint framebuffer incomplete");
    glViewport(0,0,64,64);glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glUseProgram(program);
    auto draw=[&](float phase) {
        glUniform1f(glGetUniformLocation(program,"phase"),phase);
        glBegin(GL_QUADS);glVertex2f(-1,-1);glVertex2f(1,-1);glVertex2f(1,1);glVertex2f(-1,1);glEnd();
        std::vector<float> pixels(64*64*4);
        glReadPixels(0,0,64,64,GL_RGBA,GL_FLOAT,pixels.data());
        return pixels;
    };
    float peak=0,unguardedPeak=0;int validCount=0,tirCount=0;
    // With a zenith Sun the unguarded footprint only grazes the disk. Some
    // drivers give almost exactly zero even with the guard deliberately off.
    // An oblique Sun lies inside the discontinuous footprint, while every
    // real transmitted ray stays well outside the disk.
    for(int oblique:{0,1}) for(int guarded:{0,1}) {
        glUniform1i(glGetUniformLocation(program,"obliqueSun"),oblique);
        glUniform1i(glGetUniformLocation(program,"guardFootprint"),guarded);
        for(float phase:{-0.7f,-0.3f,0.0f,0.3f,0.7f}) {
            auto pixels=draw(phase);
            for(size_t i=0;i<pixels.size();i+=4) {
                if(!std::isfinite(pixels[i]))throw std::runtime_error("Nonfinite solar coverage at TIR");
                if(!guarded) {
                    if(oblique)unguardedPeak=std::max(unguardedPeak,pixels[i]);
                    continue;
                }
                peak=std::max(peak,pixels[i]);
                if(pixels[i+1]>.5f) {
                    ++validCount;
                    if(pixels[i+2]>(oblique?.99f:.5f))
                        throw std::runtime_error("Solar TIR fixture admits a near-Sun transmitted ray");
                } else ++tirCount;
            }
        }
    }
    glUniform1i(glGetUniformLocation(program,"obliqueSun"),0);
    glUniform1i(glGetUniformLocation(program,"guardFootprint"),1);
    glUniform1i(glGetUniformLocation(program,"zenithControl"),1);
    auto positive=draw(0.f);
    float positivePeak=0;
    for(size_t i=0;i<positive.size();i+=4)positivePeak=std::max(positivePeak,positive[i]);
    glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);
    glDeleteProgram(program);glDeleteTextures(1,&texture);glDeleteFramebuffers(1,&framebuffer);
    std::cout<<"GPU solar TIR footprint: maxFalseCoverage="<<peak<<" valid="<<validCount<<" TIR="<<tirCount<<"\n";
    std::cout<<"GPU solar TIR controls: unguardedFalseCoverage="<<unguardedPeak<<" positiveSunCoverage="<<positivePeak<<"\n";
    if(unguardedPeak<=1e-6f || positivePeak<0.5f || positivePeak>1.0f)
        throw std::runtime_error("Solar TIR footprint controls lack sensitivity or suppress the real Sun");
    if(validCount==0||tirCount==0)throw std::runtime_error("Solar footprint fixture lacks both domains");
    if(peak>1e-10f)throw std::runtime_error("Solar coverage invents sunlight near the TIR boundary");
}
#endif
