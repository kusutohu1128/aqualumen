// Shared EGL setup and shader compilation are supplied by the fixture builder.
int main(int argc,char** argv) try {
    if(argc!=4) throw std::runtime_error("expected shader, query table, output");
    std::ifstream file(argv[2],std::ios::binary|std::ios::ate);
    size_t bytes=file.tellg();
    if(!file || bytes==0 || bytes%(28*sizeof(float))!=0) throw std::runtime_error("query table length");
    size_t count=bytes/(28*sizeof(float));
    std::vector<float> table(bytes/sizeof(float)),result(count);
    file.seekg(0);file.read(reinterpret_cast<char*>(table.data()),bytes);
    context();
    std::cout<<"Renderer: "<<glGetString(GL_RENDERER)<<"\n";
    fs::path shader=argv[1];
    GLuint program=compute(shader,shader.parent_path());
    GLuint buffers[2];glGenBuffers(2,buffers);
    for(int i=0;i<2;i++) {
        glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[i]);
        glBufferData(GL_SHADER_STORAGE_BUFFER,i==0?bytes:count*sizeof(float),i==0?table.data():nullptr,GL_DYNAMIC_COPY);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER,i,buffers[i]);
    }
    glUseProgram(program);
    glDispatchCompute((count+63)/64,1,1);
    glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
    glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,count*sizeof(float),result.data());
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("readback failed");
    std::ofstream out(argv[3],std::ios::binary);
    out.write(reinterpret_cast<char*>(result.data()),count*sizeof(float));
    return out?0:2;
} catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
