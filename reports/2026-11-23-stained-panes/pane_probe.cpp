// Run the unmodified packaged pane function on the interval for each input ray.
#include "egl_probe_context.h"
int main(int argc,char **argv) try {
    if(argc!=4) throw std::runtime_error("shader directory, input and output paths required");
    std::ifstream input(argv[2],std::ios::binary|std::ios::ate);
    auto bytes=input.tellg();
    if(bytes<=0 || bytes%32!=0) throw std::runtime_error("invalid fixture");
    std::vector<float> entries(static_cast<size_t>(bytes)/sizeof(float));
    input.seekg(0); input.read(reinterpret_cast<char*>(entries.data()),bytes);
    context();
    fs::path root=argv[1];
    auto program=compute(root/"probe.csh",root);
    glUseProgram(program);
    GLuint buffers[2]; glGenBuffers(2,buffers);
    size_t count=entries.size()/8;
    std::vector<float> output(count,-1);
    for(int i=0;i<2;++i) {
        glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[i]);
        glBufferData(GL_SHADER_STORAGE_BUFFER,i?count*4:entries.size()*4,i?output.data():entries.data(),GL_DYNAMIC_DRAW);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER,i,buffers[i]);
    }
    glDispatchCompute((count+63)/64,1,1);
    glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
    glGetBufferSubData(GL_SHADER_STORAGE_BUFFER,0,count*4,output.data());
    if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("compute/readback failed");
    std::ofstream file(argv[3],std::ios::binary);
    file.write(reinterpret_cast<const char*>(output.data()),count*4);
    if(!file) throw std::runtime_error("cannot write readback");
    std::cout << glGetString(GL_RENDERER) << "\n";
} catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
