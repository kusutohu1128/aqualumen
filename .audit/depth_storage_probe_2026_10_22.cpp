#define main aqualumen_paired_native_unused_main
#include "../tools/water_paired_native.cpp"
#undef main

int main() {
    try {
        Context context;GLuint texture=0;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
        glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT,16,16,0,GL_DEPTH_COMPONENT,GL_UNSIGNED_SHORT,nullptr);
        GLint format=0,bits=0,type=0;
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_DEPTH_SIZE,&bits);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_DEPTH_TYPE,&type);
        std::cout<<"format="<<format<<" depthBits="<<bits<<" depthType="<<type<<'\n';
        require(glGetError()==GL_NO_ERROR,"depth storage query GL error");
        glDeleteTextures(1,&texture);return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
