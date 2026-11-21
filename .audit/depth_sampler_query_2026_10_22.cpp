#define main aqualumen_paired_native_unused_main
#include "../tools/water_paired_native.cpp"
#undef main
int main() {
    try {
        Context context;GLuint sampler=0;glGenSamplers(1,&sampler);glBindSampler(3,sampler);glActiveTexture(GL_TEXTURE3);
        GLint active=-1,indexed=-1;
        glGetIntegerv(GL_SAMPLER_BINDING,&active);GLenum activeError=glGetError();
        glGetIntegeri_v(GL_SAMPLER_BINDING,3,&indexed);GLenum indexedError=glGetError();
        std::cout<<"nonzero_sampler="<<sampler<<" active_query="<<active<<" indexed_query="<<indexed
            <<" active_error="<<activeError<<" indexed_error="<<indexedError<<'\n';
        require(sampler>0&&active==GLint(sampler)&&indexed==GLint(sampler)&&activeError==0&&indexedError==0,"sampler query mismatch");
        glBindSampler(3,0);glDeleteSamplers(1,&sampler);return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
