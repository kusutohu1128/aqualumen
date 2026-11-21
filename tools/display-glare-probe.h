#ifndef AQUALUMEN_DISPLAY_GLARE_PROBE
#define AQUALUMEN_DISPLAY_GLARE_PROBE
void displayGlareProbe(const fs::path& root,int size=65) {
    const size_t values=size*size*4;
    GLuint programs[2]={link(expand(root/"composite1.vsh",root),expand(root/"composite1.fsh",root),"glare-horizontal"),
                        link(expand(root/"composite2.vsh",root),expand(root/"composite2.fsh",root),"glare-vertical")};
    GLuint textures[3],framebuffer;
    glGenTextures(3,textures);glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    glViewport(0,0,size,size);
    for (GLuint texture:textures) {
        glBindTexture(GL_TEXTURE_2D,texture);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,size,size,0,GL_RGBA,GL_FLOAT,nullptr);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    }
    auto render=[&](const std::vector<float>& input) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[0]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,size,size,GL_RGBA,GL_FLOAT,input.data());
        for (int pass=0;pass<2;++pass) {
            glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,textures[pass+1],0);
            glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
            if (glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
                throw std::runtime_error("Glare framebuffer incomplete");
            glUseProgram(programs[pass]);
            glUniform1i(glGetUniformLocation(programs[pass],"colortex0"),0);
            if (pass==1) {
                glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,textures[1]);
                glUniform1i(glGetUniformLocation(programs[pass],"colortex9"),1);
            }
            glUniform1f(glGetUniformLocation(programs[pass],"viewWidth"),size);
            glUniform1f(glGetUniformLocation(programs[pass],"viewHeight"),size);
            glBegin(GL_QUADS);
            glTexCoord2f(0,0);glVertex2f(-1,-1);glTexCoord2f(1,0);glVertex2f(1,-1);
            glTexCoord2f(1,1);glVertex2f(1,1);glTexCoord2f(0,1);glVertex2f(-1,1);
            glEnd();
        }
        std::vector<float> output(values);glReadPixels(0,0,size,size,GL_RGBA,GL_FLOAT,output.data());
        return output;
    };
    const double scale=std::clamp(double(size)/225.0,1.0,8.0);
    const int radius=int(std::ceil(24.0*scale));
    std::vector<float> weights(2*radius+1);
    double normalization=0;
    for (int offset=-radius;offset<=radius;++offset) {
        weights[offset+radius]=std::exp(-double(offset*offset)/(32.0*scale*scale));normalization+=weights[offset+radius];
    }
    for (float& weight:weights) weight/=normalization;
    auto verify=[&](int sourceX,int sourceY,float brightness) {
        std::vector<float> input(values,0.0f);
        const size_t source=(sourceY*size+sourceX)*4;
        input[source]=brightness;input[source+1]=brightness*0.5f;
        auto output=render(input);
        const double excess=std::max(double(brightness)-8.0,0.0);
        double total=0,maxError=0;
        for (int row=0;row<size;++row) for (int column=0;column<size;++column) {
            const int deltaX=column-sourceX,deltaY=row-sourceY;
            double spread=std::abs(deltaX)<=radius && std::abs(deltaY)<=radius
                ?0.02*excess*weights[deltaX+radius]*weights[deltaY+radius]:0.0;
            double expected=spread+(column==sourceX && row==sourceY?brightness-0.02*excess:0.0);
            const size_t pixel=(row*size+column)*4;
            for (int channel=0;channel<4;++channel)
                if (!std::isfinite(output[pixel+channel]) || output[pixel+channel]<0)
                    throw std::runtime_error("Glare produced nonfinite/negative output");
            maxError=std::max(maxError,std::abs(output[pixel]-expected));
            if (std::abs(output[pixel+1]-0.5f*output[pixel])>0.001f || output[pixel+2]!=0 || output[pixel+3]!=1)
                throw std::runtime_error("Glare changes RGB ratio, zero channel or alpha");
            total+=output[pixel];
        }
        if (maxError>std::max(0.001,double(brightness)*1e-6))
            throw std::runtime_error("Glare disagrees with independent normalized convolution");
        if (sourceX==size/2 && std::abs(total-brightness)>std::max(0.001,double(brightness)*1e-6))
            throw std::runtime_error("Interior glare does not conserve radiance");
        if (sourceX==0 && excess>0 && !(total<brightness && total>=brightness*0.98))
            throw std::runtime_error("Edge glare repeats or adds out-of-viewport radiance");
        if (excess>0 && output[source+4]<=0)
            throw std::runtime_error("Glare has no positive neighboring response");
        if (excess>0 && sourceX==size/2) {
            const double boundary=0.02*excess*weights.back()*weights[radius];
            if(boundary>0.00001)throw std::runtime_error("Solar HDR glare remains visible at its truncation boundary");
        }
        std::cout<<"PASS GPU display glare: size="<<size<<" radius="<<radius<<" source="<<sourceX<<","<<sourceY<<" peak="<<brightness
                 <<" sum="<<total<<" maxOracleError="<<maxError<<"\n";
    };
    verify(size/2,size/2,0);verify(size/2,size/2,4);
    verify(size/2,size/2,264984);verify(0,0,264984);
    glUseProgram(0);glBindFramebuffer(GL_FRAMEBUFFER,0);glActiveTexture(GL_TEXTURE0);
    glDeleteProgram(programs[0]);glDeleteProgram(programs[1]);
    glDeleteTextures(3,textures);glDeleteFramebuffers(1,&framebuffer);
}
#endif
