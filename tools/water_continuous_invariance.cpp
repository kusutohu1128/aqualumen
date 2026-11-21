#define main aqualumen_paired_native_unused_main
#include "water_paired_native.cpp"
#undef main

std::vector<float> drawContinuousControl(Fixture& fixture,GLuint p,bool underwater,bool known,float material) {
    fixture.uniforms(p,0,underwater);
    glUniform1i(glGetUniformLocation(p,"aqualumenBathymetryReady"),known?1:0);
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);glDrawBuffer(GL_COLOR_ATTACHMENT0);
    const float zero[4]={};glClearBufferfv(GL_COLOR,0,zero);glDisablei(GL_BLEND,0);
    glVertexAttrib4f(10,material,0,0,0);
    const float extent=material==10000?.5f:2.0f;
    const std::array<std::array<float,3>,4> vertices={{{-extent,3.25f,-extent},{-extent,3.25f,extent},{extent,3.25f,extent},{extent,3.25f,-extent}}};
    glBegin(GL_TRIANGLES);for(int i:{0,1,2,0,2,3})glVertex3fv(vertices[i].data());glEnd();
    std::vector<float> result(pixels*4,std::numeric_limits<float>::quiet_NaN());
    glReadBuffer(GL_COLOR_ATTACHMENT0);glReadPixels(0,0,side,side,GL_RGBA,GL_FLOAT,result.data());
    for(float value:result)require(std::isfinite(value),"nonfinite invariant control read");
    require(glGetError()==GL_NO_ERROR,"invariant control GL error");return result;
}
int main(int argc,char** argv) {
    try {
        require(argc==4,"usage: water-continuous-invariance BASE_SHADER_ROOT CORRECTED_SHADER_ROOT NEW_OUTPUT");
        const fs::path base=argv[1],corrected=argv[2],out=argv[3];
        require(!fs::exists(out),"output exists");fs::create_directories(out);
        Context context;Fixture fixture;
        fixture.projection[0]*=3;fixture.projection[5]*=3;
        fixture.inverseProjection[0]/=3;fixture.inverseProjection[5]/=3;
        const auto before=program(source(base/"gbuffers_water.vsh",base),source(base/"gbuffers_water.fsh",base));
        const auto after=program(source(corrected/"gbuffers_water.vsh",corrected),source(corrected/"gbuffers_water.fsh",corrected));
        struct Case {const char* name;bool underwater,known;float material;bool exact;};
        for(const auto test:std::array<Case,4>{{{"air",false,true,10000,true},{"unknown-water",true,false,10000,true},{"nonwater",true,true,1,true},{"known-underwater",true,true,10000,false}}}) {
            const auto a=drawContinuousControl(fixture,before,test.underwater,test.known,test.material),
                b=drawContinuousControl(fixture,after,test.underwater,test.known,test.material);
            size_t changed=0;for(size_t i=0;i<a.size();i++)changed+=a[i]!=b[i];
            raw(out/(std::string(test.name)+"-base.rgba32f"),a);raw(out/(std::string(test.name)+"-corrected.rgba32f"),b);
            require(test.exact?equal(a,b):changed>0,std::string(test.name)+" invariance/nonvacuity failed");
            std::cout<<test.name<<" changed_components="<<changed<<" exact_expected="<<test.exact<<'\n';
        }
        glDeleteProgram(before);glDeleteProgram(after);std::cout<<"invariance_complete=1\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
