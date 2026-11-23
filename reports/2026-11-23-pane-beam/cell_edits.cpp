// Exercise both cache passes on consecutive frames, including material-to-material edits.
#include "original_cache_helpers.h"

static void upload(GLuint texture, GLenum format, int y, int w, int h, const std::vector<float>& words) {
    glBindTexture(GL_TEXTURE_2D,texture);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,y,w,h,format,GL_FLOAT,words.data());
}
static int word(GLuint texture, int band, int index) {
    float value=-1;
    glGetTextureSubImage(texture,0,index%512,band+index/512,0,1,1,1,GL_RED,GL_FLOAT,sizeof(value),&value);
    return int(value);
}
int main(int argc,char** argv) try {
    if(argc!=2) throw std::runtime_error("shader root required");
    context();
    fs::path dir=argv[1];
    GLuint reset=compute(dir/"setup2.csh",dir), changes=compute(dir/"shadowcomp5.csh",dir);
    GLuint classify=compute(dir/"shadowcomp6.csh",dir);
    GLuint field=image(0,1,512,15521),list=image(1,4,16,512);
    float poison=37.;
    glClearTexImage(field,0,GL_RED,GL_FLOAT,&poison);
    Point cam={0,0,0};
    run(reset,1,1,cam);
    std::cout<<"renderer "<<glGetString(GL_RENDERER)<<"\n";
    int red=46, blue=43;
    int frames=0;
    auto frame=[&](const char* name,int first,int second,bool on,int expectedState,int expectedShape,bool reuse=false) {
        Point origin;
        for(int k=0;k<3;k++) origin[k]=int(std::floor(cam[k]/8.))*8-32;
        Point receiver=add({0,0,0},origin,-1),torch=add({0,0,6},origin,-1);
        std::vector<float> cells(64*64*64),bricks(32*32*32),sources(16*512*4);
        for(auto [z,w]:{std::pair<int,int>{3,first},{4,second}}) {
            if(!w) continue;
            Point p=add({0,0,z},origin,-1);
            cells[linear(p,64)]=float(w);
            int bit=linear(ring(p,1),2)+(w==1?0:8);
            for(auto& c:p) c/=2;
            auto& occupied=bricks[linear(p,32)];
            occupied=float(int(occupied)|(1<<bit));
        }
        Point tile=receiver;
        for(auto& c:tile)c/=8;
        int li=linear(tile,8)*16*4;
        if(on) {
            sources[li]=1;
            sources[li+4]=float(torch[0])+.5f; sources[li+5]=float(torch[1])+.64f;
            sources[li+6]=float(torch[2])+.5f; sources[li+7]=float(14*64+1);
        }
        upload(list,GL_RGBA,0,16,512,sources);
        upload(field,GL_RED,0,512,512,cells);
        upload(field,GL_RED,2048,512,64,bricks);
        glMemoryBarrier(GL_ALL_BARRIER_BITS);
        run(changes,8,8,cam);run(classify,8,8,cam);
        int state=word(field,2112,0)&4097;
        int shape=state==4097?word(field,8864,0):-1;
        int box=state==4097?word(field,2720,0):0;
        int dirty=word(field,2688,18);
        if(on && (state!=expectedState || shape!=expectedShape || (state==4097 && box<=0) || (reuse && dirty!=0)))
            throw std::runtime_error(std::string(name)+" flags="+std::to_string(state)+" shape="+std::to_string(shape)+" dirty="+std::to_string(dirty));
        if(glGetError()!=GL_NO_ERROR) throw std::runtime_error("failed GL readback");
        std::cout<<++frames<<" "<<name<<" enabled="<<on<<" state="<<state<<" shape="<<shape<<" box="<<box<<" dirty="<<dirty<<"\n";
    };
    frame("initial",0,0,true,1,-1);
    frame("post",red,0,true,4097,254);
    frame("unchanged",red,0,true,4097,254,true);
    frame("dye-only",blue,0,true,4097,251);
    frame("arms-only",blue+(3<<6),0,true,4097,171);
    frame("thick-glass",16+11,0,true,0,-1);
    frame("two-joined",red+(12<<6),red+(12<<6),true,4097,94);
    frame("recolour-one",red+(12<<6),blue+(12<<6),true,0,-1);
    frame("add-trunk",red,1,true,0,-1);
    frame("cut-trunk",red,0,true,4097,254);
    frame("lamp-out",red,0,false,0,-1);
    frame("edit-in-dark",blue,0,false,0,-1);
    frame("relight",blue,0,true,4097,251);
    cam[0]=-9;
    frame("camera-tile",blue,0,true,4097,251);
    frame("take-out-window",0,0,true,1,-1);
    return 0;
} catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
