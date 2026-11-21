package dev.aqualumen.physics;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.opengl.*;

public final class ReceiverPlantCellDecoderGLTest {
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
    private static int shader(int type, String source) {
        int shader = GL20.glCreateShader(type); GL20.glShaderSource(shader,source); GL20.glCompileShader(shader);
        check(GL20.glGetShaderi(shader,GL20.GL_COMPILE_STATUS) != 0,GL20.glGetShaderInfoLog(shader)); return shader;
    }
    private static void rejected(Runnable action) {
        try { action.run();throw new AssertionError("Upload capacity policy bypassed"); }
        catch(IllegalArgumentException expected) {}
    }
    private static void largeUpload(Runnable guard) {
        var ordinary=new ReceiverRadianceTextureUpload(guard);
        rejected(()->ordinary.create(256,257,new float[256*257*4]));
        rejected(()->new ReceiverRadianceTextureUpload(guard,1048577));
        var plants=new ReceiverRadianceTextureUpload(guard,1048576);
        rejected(()->plants.create(257,4096,new float[257*4096*4]));
        float[] pixels=new float[256*4096*4];
        pixels[0]=.125f;pixels[pixels.length/2]=.5f;pixels[pixels.length-1]=.75f;
        int previous=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        int texture=plants.create(256,4096,pixels);
        try {
            check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==previous,"Large upload restores texture binding");
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
            float[] readback=new float[pixels.length];
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,readback);
            check(GL11.glGetError()==GL11.GL_NO_ERROR && Arrays.equals(pixels,readback),"1048576-texel RGBA32F allocation/upload/readback exact");
        } finally { GL11.glBindTexture(GL11.GL_TEXTURE_2D,previous);plants.delete(texture); }
        System.out.println("PASS NVIDIA plant-only 1048576-texel upload/readback; ordinary 65536 limit unchanged; over-capacity negatives");
    }
    private static void materialDecoder(ReceiverPlantPublisher publisher,ReceiverRadianceTextureUpload upload,
            int count,int previousProgram) throws Exception {
        int vertex=shader(GL20.GL_VERTEX_SHADER,"#version 330 compatibility\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}");
        int fragment=shader(GL20.GL_FRAGMENT_SHADER,"#version 330 compatibility\n"+
                Files.readString(Path.of("shaders/lib/water_plant_material.glsl"))+
                Files.readString(Path.of("shaders/lib/water_plant_intersection.glsl"))+
                "\n#define attributes aqualumenPlantMaterial\n#define primitives aqualumenPlantPrimitives\n"+
                "uniform sampler2D attributes,primitives,aqualumenPlantHeaders,aqualumenPlantIndices,testAtlas;"+
                "uniform int bindingMode;uniform vec3 weights;uniform int primitive,count,hitMode;"+
                "uniform vec3 rayOrigin,rayDirection;uniform float hitTravel;uniform vec2 hitUv;"+
                "layout(location=0)out vec4 color;void main(){WaterPlantMaterial value;"+
                "bool ready=hitMode==1?waterPlantMaterialHit(attributes,primitives,count,primitive,rayOrigin,rayDirection,hitTravel,hitUv,value):"+
                "waterPlantMaterialAt(attributes,primitives,count,primitive,weights,value);color=ready?vec4(value.uv,value.light):vec4(-1.0);"+
                "if(hitMode==2){WaterPlantHit hit=waterPlantFirstSelection(primitives,testAtlas,aqualumenPlantIndices,count,ivec2(0,1),true,"+
                "rayOrigin,rayDirection,0.0,8.0,0.0,0,true);color=vec4(float(hit.status),float(hit.primitive),hit.travel,0);}"+
                "if(bindingMode==1)color=texture(aqualumenPlantHeaders,vec2(0))+texture(aqualumenPlantIndices,vec2(0));}");
        int program=GL20.glCreateProgram();GL20.glAttachShader(program,vertex);GL20.glAttachShader(program,fragment);
        GL20.glLinkProgram(program);check(GL20.glGetProgrami(program,GL20.GL_LINK_STATUS)!=0,GL20.glGetProgramInfoLog(program));
        GL20.glDeleteShader(vertex);GL20.glDeleteShader(fragment);GL20.glUseProgram(program);
        GL13.glActiveTexture(GL13.GL_TEXTURE0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,publisher.materialTexture());
        GL13.glActiveTexture(GL13.GL_TEXTURE1);GL11.glBindTexture(GL11.GL_TEXTURE_2D,publisher.texture(2));
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantMaterial"),0);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantPrimitives"),1);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantHeaders"),2);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantIndices"),3);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"testAtlas"),4);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),count);
        int target=upload.create(1,1,new float[4]),framebuffer=GL30.glGenFramebuffers();
        GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,framebuffer);
        GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0,GL11.GL_TEXTURE_2D,target,0);
        GL11.glDrawBuffer(GL30.GL_COLOR_ATTACHMENT0);GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0);
        check(GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER)==GL30.GL_FRAMEBUFFER_COMPLETE,"Material framebuffer");
        GL11.glViewport(0,0,1,1);int vao=GL30.glGenVertexArrays();GL30.glBindVertexArray(vao);
        float[] result=new float[4];
        for(int test=0;test<7;test++) {
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"primitive"),test==5?count:0);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"weights"),test==0?1:test==1?0:test==4?-1:.25f,
                    test==1?1:test==0?0:test==6?Float.NaN:.25f,test<2?0:test==3?.75f:.5f);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            check(GL11.glGetError()==GL11.GL_NO_ERROR,"Material decoder draw/readback");
            if(test>=3)check(Arrays.equals(result,new float[]{-1,-1,-1,-1}),"Invalid weights or primitive rejected");
            else {
                float expectedU=test==0?0:test==1?1:.75f,expectedV=test<2?0:.5f;
                check(Math.abs(result[0]-expectedU)<.000001 && Math.abs(result[1]-expectedV)<.000001
                        && result[2]==.4f && result[3]==.8f,"GPU barycentric material reconstruction");
            }
        }
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"hitMode"),1);
        for(int test=0;test<6;test++) {
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"primitive"),0);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"rayOrigin"),test==3?1.5f:.7f,.5f,0);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"rayDirection"),0,0,test==4?2:1);
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"hitTravel"),test==1?2.1f:test==5?Float.NaN:2);
            GL20.glUniform2f(GL20.glGetUniformLocation(program,"hitUv"),test==2?.7f:.75f,.5f);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            check(GL11.glGetError()==GL11.GL_NO_ERROR,"Hit material decoder draw/readback");
            if(test==0)check(Math.abs(result[0]-.75f)<.000001 && Math.abs(result[1]-.5f)<.000001
                    && Math.abs(result[2]-.4f)<.000001 && Math.abs(result[3]-.8f)<.000001,
                    "Actual ray hit reconstructs corresponding material: "+Arrays.toString(result));
            else check(Arrays.equals(result,new float[]{-1,-1,-1,-1}),"Foreign hit/travel/UV/direction rejected");
        }
        GL13.glActiveTexture(GL13.GL_TEXTURE0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,target);
        int hostileSampler=GL33.glGenSamplers();GL33.glBindSampler(0,hostileSampler);
        try(var binding=ReceiverPlantTextureBinding.open(publisher,()->{})) {
            check(binding!=null,"Material draw contract available");
            check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==publisher.materialTexture()
                    && GL11.glGetInteger(GL33.GL_SAMPLER_BINDING)==0,"Material data bound without hostile sampler");
        }
        check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==target
                && GL11.glGetInteger(GL33.GL_SAMPLER_BINDING)==hostileSampler,"Material binding restores caller state");
        GL33.glBindSampler(0,0);GL33.glDeleteSamplers(hostileSampler);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantMaterial"),1);
        rejected(()->ReceiverPlantTextureBinding.open(publisher,()->{}));
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantMaterial"),0);
        var geometry=publisher.packet();var publication=publisher.publication();
        float[] originalAttributes=new float[count*24];
        GL13.glActiveTexture(GL13.GL_TEXTURE0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,publisher.materialTexture());
        GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,originalAttributes);
        int largeCount=20001;
        float[] largeAttributes=new float[largeCount*24],largePrimitives=new float[largeCount*16];
        float[] originalPrimitives=geometry.triangles();
        for(int primitive=0;primitive<largeCount;primitive++) {
            System.arraycopy(originalAttributes,0,largeAttributes,primitive*24,24);
            System.arraycopy(originalPrimitives,0,largePrimitives,primitive*16,16);
        }
        for(int corner=0;corner<3;corner++) {
            largeAttributes[(largeCount-1)*24+corner*8+2]=.31f;
            largeAttributes[(largeCount-1)*24+corner*8+3]=.63f;
            largePrimitives[(largeCount-1)*16+corner*4+2]=3;
        }
        var materialPayload=ReceiverPlantPacket.texturePayload(6,largeAttributes);
        var geometryPayload=ReceiverPlantPacket.texturePayload(4,largePrimitives);
        int largeMaterial=upload.create(materialPayload.width(),materialPayload.height(),materialPayload.values());
        int largeGeometry=upload.create(geometryPayload.width(),geometryPayload.height(),geometryPayload.values());
        float[] selectedLink=new float[1024];selectedLink[0]=largeCount-1;
        int largeLinks=upload.create(256,1,selectedLink),testAtlas=upload.create(1,1,new float[]{1,1,1,1});
        try {
            GL13.glActiveTexture(GL13.GL_TEXTURE0);GL11.glBindTexture(GL11.GL_TEXTURE_2D,largeMaterial);
            GL33.glBindSampler(0,0);
            GL13.glActiveTexture(GL13.GL_TEXTURE1);GL11.glBindTexture(GL11.GL_TEXTURE_2D,largeGeometry);
            GL33.glBindSampler(1,0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"hitMode"),0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"primitive"),largeCount-1);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"weights"),1,0,0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),largeCount);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            check(Arrays.equals(result,new float[]{0,0,.31f,.63f}),"Tiled final partial-row primitive retains its distinct attributes");
            GL13.glActiveTexture(GL13.GL_TEXTURE3);GL11.glBindTexture(GL11.GL_TEXTURE_2D,largeLinks);GL33.glBindSampler(3,0);
            GL13.glActiveTexture(GL13.GL_TEXTURE4);GL11.glBindTexture(GL11.GL_TEXTURE_2D,testAtlas);GL33.glBindSampler(4,0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"hitMode"),2);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"rayOrigin"),.2f,.15f,0);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"rayDirection"),0,0,1);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            check(result[0]==1 && result[1]==largeCount-1 && Math.abs(result[2]-3)<1e-5 && result[3]==0,
                    "Indexed ray hits the distinct final tiled primitive, not another row: "+Arrays.toString(result));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"hitMode"),0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),131073);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            check(Arrays.equals(result,new float[]{-1,-1,-1,-1}),"Over-capacity material remains rejected");
            check(GL11.glGetError()==GL11.GL_NO_ERROR,"Large material decoder GL state");
        } finally { upload.delete(largeMaterial);upload.delete(largeGeometry);upload.delete(largeLinks);upload.delete(testAtlas); }
        publisher.publish(geometry,publication);
        try {
            ReceiverPlantTextureBinding.open(publisher,()->{});
            throw new AssertionError("Material draw admitted geometry-only publication");
        } catch(IllegalStateException expected) {}
        GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,0);GL30.glDeleteFramebuffers(framebuffer);
        GL30.glDeleteVertexArrays(vao);upload.delete(target);GL20.glUseProgram(previousProgram);GL20.glDeleteProgram(program);
        System.out.println("PASS NVIDIA material interpolation/ray-hit reconstruction and atomic draw texture binding/restoration; invalid weights/primitive/travel/UV/direction, sampler alias and absent material rejected; not radiance shading");
    }
    public static void main(String[] arguments) throws Exception {
        check(GLFW.glfwInit(),"GLFW init"); GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE,GLFW.GLFW_FALSE);
        long window = GLFW.glfwCreateWindow(16,16,"Plant cell decoder",0,0); check(window != 0,"GLFW context");
        try {
            GLFW.glfwMakeContextCurrent(window); GL.createCapabilities();
            System.out.println("Renderer: "+GL11.glGetString(GL11.GL_RENDERER));
            check(GL11.glGetString(GL11.GL_VENDOR).contains("NVIDIA"),"NVIDIA required");
            largeUpload(()->check(GLFW.glfwGetCurrentContext()==window,"Large upload context owner"));
            var epoch = new ReceiverRadianceVolume.Epoch(new Object(),1,1);
            var quad = new ReceiverQuadIntersection.Quad(new ReceiverQuadIntersection.Point(.1,.1,2,0,0),
                    new ReceiverQuadIntersection.Point(.9,.1,2,1,0),new ReceiverQuadIntersection.Point(.9,.9,2,1,1),
                    new ReceiverQuadIntersection.Point(.1,.9,2,0,1),(textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
            var packet = ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true);
            var bounds = new ReceiverPlantCellIndex.Window(-1,-1,0,4,3,4);
            var index = ReceiverPlantCellIndex.capture(packet,bounds,epoch,1000);
            var water = new ReceiverWaterVolume.Observation(true,"minecraft:water","water",true,1,true);
            var publication = ReceiverPlantCellPublication.capture(index,epoch,new ReceiverPlantCellPublication.World() {
                public ReceiverRadianceVolume.Epoch epoch() { return epoch; }
                public void beginValidation() {}
                public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) {
                    return new ReceiverPlantCellPublication.Proof(x<0 ? List.of() : List.of(water,water,water),y>=0);
                }
            });
            String kernel = Files.readString(Path.of("shaders/lib/water_plant_cells.glsl"));
            kernel += Files.readString(Path.of("shaders/lib/water_plant_intersection.glsl"));
            kernel += Files.readString(Path.of("shaders/lib/water_plant_publication.glsl"))
                    .replace("#include \"/lib/water_plant_cells.glsl\"","")
                    .replace("#include \"/lib/water_plant_intersection.glsl\"","");
            kernel += Files.readString(Path.of("shaders/lib/water_plant_backend.glsl"))
                    .replace("#include \"/lib/water_plant_publication.glsl\"","");
            int vertex = shader(GL20.GL_VERTEX_SHADER,"#version 330 compatibility\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}");
            int fragment = shader(GL20.GL_FRAGMENT_SHADER,"#version 330 compatibility\n#define AQUALUMEN_PLANT_RECEIVER\n"+kernel+
                    "\nuniform sampler2D headers,indices,primitives,atlas,foreign[2];uniform ivec3 size,testReceiverShift;uniform vec3 testCamera;uniform int memberships,triangles,intersectionMode;uniform bool atlasOwned;"+
                    "layout(location=0)out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy);ivec3 cell=ivec3(p.x,p.y/size.z,p.y%size.z);"+
                    "ivec2 span;bool water,complete;bool valid=waterPlantCellSpan(headers,indices,size,cell,memberships,triangles,span,water,complete);"+
                    "color=valid?vec4(span,float(water),float(complete)):vec4(-1.0);"+
                    "if(intersectionMode==1){WaterPlantHit hit=waterPlantPublishedFirst(headers,indices,primitives,atlas,size,cell,memberships,triangles,true,vec3(.25,.5,0),vec3(0,0,1),1.0,2.0,0.0,0,atlasOwned);color=vec4(hit.status,hit.travel,hit.primitive,0);}"+
                    "if(intersectionMode==2){ivec3 mapped=cell-testReceiverShift;WaterPlantHit hit=waterPlantCellWaterQualified(mapped)?waterPlantCellFirst(mapped,vec3(.25,.5,0)-testCamera,vec3(0,0,1),1.0,2.0):WaterPlantHit(2,-1,0,vec2(0),vec3(0));color=vec4(hit.status,hit.travel,hit.primitive,0);}"+
                    "if(intersectionMode==3)color=texture(foreign[0],vec2(0))+texture(foreign[1],vec2(0));}");
            int program = GL20.glCreateProgram(); GL20.glAttachShader(program,vertex); GL20.glAttachShader(program,fragment);
            GL20.glLinkProgram(program); check(GL20.glGetProgrami(program,GL20.GL_LINK_STATUS) != 0,GL20.glGetProgramInfoLog(program));
            GL20.glDeleteShader(vertex); GL20.glDeleteShader(fragment); GL20.glUseProgram(program);
            var upload = new ReceiverRadianceTextureUpload(() -> check(GLFW.glfwGetCurrentContext()==window,"Context owner"),1048576);
            float[] headers = publication.headers(epoch), links = publication.indices(epoch);
            var publisher = new ReceiverPlantPublisher(upload,()->epoch);
            var vertices=List.of(quad.first(),quad.second(),quad.third(),quad.fourth()).stream()
                    .map(point->new ReceiverMaterialTriangle.Vertex(point.x(),point.y(),point.z(),
                            new ReceiverVertexShader.Output((float)point.u(),(float)point.v(),.4f,.8f,.2f,.3f,.5f,1))).toList();
            var material=ReceiverPlantMaterialPacket.capture(packet,List.of(
                    new ReceiverMaterialTriangle(epoch,vertices.get(0),vertices.get(1),vertices.get(2)),
                    new ReceiverMaterialTriangle(epoch,vertices.get(0),vertices.get(2),vertices.get(3))),epoch);
            publisher.publish(packet,publication,material);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,publisher.materialTexture());
            check(GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH)==6
                    && GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT)==packet.count(),
                    "Material texture layout matches geometry primitive IDs");
            float[] materialReadback=new float[packet.count()*24];
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,materialReadback);
            check(GL11.glGetError()==GL11.GL_NO_ERROR && Arrays.equals(material.attributes(epoch),materialReadback),
                    "All vertex material attributes survive atomic GPU publication exactly");
            System.out.println("PASS NVIDIA atomic geometry/material publication and exact attribute texture readback; not per-hit shading");
            materialDecoder(publisher,upload,packet.count(),program);
            publisher.publish(packet,publication);
            check(publisher.ready(),"Atomic publication ready");
            int headerTexture = publisher.texture(0), indexTexture = publisher.texture(1);
            GL13.glActiveTexture(GL13.GL_TEXTURE0); GL11.glBindTexture(GL11.GL_TEXTURE_2D,headerTexture);
            GL13.glActiveTexture(GL13.GL_TEXTURE1); GL11.glBindTexture(GL11.GL_TEXTURE_2D,indexTexture);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"headers"),0); GL20.glUniform1i(GL20.glGetUniformLocation(program,"indices"),1);
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"size"),bounds.width(),bounds.height(),bounds.depth());
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"memberships"),publication.memberships());
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"triangles"),packet.count());
            int output = upload.create(bounds.width(),bounds.height()*bounds.depth(),new float[bounds.width()*bounds.height()*bounds.depth()*4]);
            int framebuffer = GL30.glGenFramebuffers(); GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,framebuffer);
            GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0,GL11.GL_TEXTURE_2D,output,0);
            GL11.glDrawBuffer(GL30.GL_COLOR_ATTACHMENT0); GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0);
            check(GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER)==GL30.GL_FRAMEBUFFER_COMPLETE,"Framebuffer");
            int vao = GL30.glGenVertexArrays(); GL30.glBindVertexArray(vao); GL11.glViewport(0,0,bounds.width(),bounds.height()*bounds.depth());
            float[] result = new float[bounds.width()*bounds.height()*bounds.depth()*4];
            Runnable draw = () -> {
                GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3); GL11.glReadPixels(0,0,bounds.width(),bounds.height()*bounds.depth(),GL11.GL_RGBA,GL11.GL_FLOAT,result);
                check(GL11.glGetError()==GL11.GL_NO_ERROR,"GL draw/readback");
            };
            draw.run(); check(Arrays.equals(result,Arrays.copyOf(headers,result.length)),"Every Java-published header/flag survives GPU decoder exactly");
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"size"),2,6,4);
            draw.run(); check(result[0]==-1,"Same-product wrong window dimensions rejected");
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"size"),bounds.width(),bounds.height(),bounds.depth());
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"triangles"),packet.count()+1);
            draw.run(); check(result[0]==-1,"Forged primitive count rejected by payload metadata");
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"triangles"),packet.count());
            int populated = -1;
            for (int offset=0;offset<result.length;offset+=4) if (headers[offset+1]>0) { populated=offset;break; }
            check(populated>=0,"Populated fixture required");
            int first = (int)headers[populated];
            int footer = bounds.width()*bounds.height()*bounds.depth()*4;
            for (int negative=0;negative<14;negative++) {
                float[] badHeaders = headers.clone(), badLinks = links.clone();
                if (negative==0) badHeaders[populated]+=.5f;
                if (negative==1) badHeaders[populated+1]=513;
                if (negative==2) badHeaders[populated+2]=2;
                if (negative==3) badLinks[first*4]=packet.count();
                if (negative==4) badLinks[first*4+1]=1;
                if (negative==5) badLinks[first*4]=Float.NaN;
                if (negative==6) badLinks[(first+1)*4]=badLinks[first*4];
                if (negative==7) badHeaders[footer]=Float.NaN;
                if (negative==8) badHeaders[footer+3]++;
                if (negative==9) badHeaders[footer+5]=1;
                if (negative==10) badHeaders[populated+3]=2;
                if (negative==11) badHeaders[populated]=-1;
                if (negative==12) badHeaders[populated]=publication.memberships();
                if (negative==13) {
                    float primitive = badLinks[first*4];
                    badLinks[first*4]=badLinks[(first+1)*4];
                    badLinks[(first+1)*4]=primitive;
                }
                GL13.glActiveTexture(GL13.GL_TEXTURE0); GL11.glBindTexture(GL11.GL_TEXTURE_2D,headerTexture);
                GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,256,badHeaders.length/1024,GL11.GL_RGBA,GL11.GL_FLOAT,badHeaders);
                GL13.glActiveTexture(GL13.GL_TEXTURE1); GL11.glBindTexture(GL11.GL_TEXTURE_2D,indexTexture);
                GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,256,badLinks.length/1024,GL11.GL_RGBA,GL11.GL_FLOAT,badLinks);
                draw.run(); check(result[populated]==-1,"Malformed span/link rejected: "+negative);
                GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),1);
                draw.run(); check(result[populated]==2,"Malformed publication cannot bypass intersection qualification: "+negative);
                GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),0);
            }
            GL13.glActiveTexture(GL13.GL_TEXTURE0); GL11.glBindTexture(GL11.GL_TEXTURE_2D,headerTexture);
            GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,256,headers.length/1024,GL11.GL_RGBA,GL11.GL_FLOAT,headers);
            GL13.glActiveTexture(GL13.GL_TEXTURE1); GL11.glBindTexture(GL11.GL_TEXTURE_2D,indexTexture);
            GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,256,links.length/1024,GL11.GL_RGBA,GL11.GL_FLOAT,links);
            int primitiveTexture = publisher.texture(2);
            int atlasTexture = upload.create(1,1,new float[]{1,1,1,1});
            GL13.glActiveTexture(GL13.GL_TEXTURE2); GL11.glBindTexture(GL11.GL_TEXTURE_2D,primitiveTexture);
            GL13.glActiveTexture(GL13.GL_TEXTURE3); GL11.glBindTexture(GL11.GL_TEXTURE_2D,atlasTexture);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"primitives"),2);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"atlas"),3);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),1);
            String[] plantNames={"aqualumenPlantHeaders","aqualumenPlantIndices","aqualumenPlantPrimitives","aqualumenPlantAtlas"};
            int guardedSampler=GL33.glGenSamplers();
            for(int unit=0;unit<4;unit++) {
                GL20.glUniform1i(GL20.glGetUniformLocation(program,plantNames[unit]),10+unit);
                GL13.glActiveTexture(GL13.GL_TEXTURE0+10+unit);
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,output);GL33.glBindSampler(10+unit,guardedSampler);
            }
            GL13.glActiveTexture(GL13.GL_TEXTURE3);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"foreign[0]"),4);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"foreign[1]"),5);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantMemberships"),17);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantMaximumLod"),7);
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"aqualumenPlantSize"),7,8,9);
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"aqualumenPlantReceiverOffset"),1,2,3);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"aqualumenPlantReference"),4,5,6);
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"aqualumenPlantLod"),1.5f);
            var receiverWindow=new ReceiverRunPublisher.Window(bounds.x(),bounds.y(),bounds.z(),bounds.width(),bounds.height(),bounds.depth());
            for (int variant=0;variant<3;variant++) {
                GL20.glUniform1i(GL20.glGetUniformLocation(program,"atlasOwned"),variant==2?0:1);
                GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,new float[]{1,1,1,variant==1?0:1});
                draw.run();
                float[] unscoped=result.clone();
                GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),2);
                try(var binding=ReceiverPlantDrawBinding.open(publisher,receiverWindow,0,0,0,atlasTexture,0,0,0,variant!=2,
                        ()->check(GLFW.glfwGetCurrentContext()==window,"Binding context owner"))) {
                    check(binding!=null,"Plant scope opens");draw.run();
                    check(Arrays.equals(result,unscoped),"Scoped plant texture draw matches direct publication");
                }
                check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenPlantReady"))==0
                        && GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenPlantMemberships"))==17
                        && GL20.glGetUniformf(program,GL20.glGetUniformLocation(program,"aqualumenPlantLod"))==1.5f,
                        "Plant metadata and readiness restore");
                int[] restored=new int[3];
                GL20.glGetUniformiv(program,GL20.glGetUniformLocation(program,"aqualumenPlantSize"),restored);
                check(Arrays.equals(restored,new int[]{7,8,9}),"Plant window metadata restores");
                for(int unit=10;unit<14;unit++) {
                    GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                    check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==output
                            && GL11.glGetInteger(GL33.GL_SAMPLER_BINDING)==guardedSampler,"Plant scope restores texture/sampler");
                }
                GL13.glActiveTexture(GL13.GL_TEXTURE3);
                GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),1);
                for (int offset=0;offset<result.length;offset+=4) {
                    boolean qualified = headers[offset+2]==1 && headers[offset+3]==1;
                    boolean occupied = headers[offset+1]>0;
                    int expected = !qualified?2:!occupied || variant==1?0:variant==2?2:1;
                    check(result[offset]==expected,"Published cell intersection status: "+variant+" cell "+offset/4);
                    if (expected==1) {
                        check(Math.abs(result[offset+1]-2)<1e-5,"Published entry/exit boundary hit distance: "+result[offset+1]);
                        check(result[offset+2]>=0 && result[offset+2]<packet.count(),"Global primitive ID");
                    }
                }
            }
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantIndices"),10);
            rejected(()->ReceiverPlantTextureBinding.open(publisher,()->{}));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantIndices"),11);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"headers"),10);
            rejected(()->ReceiverPlantTextureBinding.open(publisher,()->{}));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"headers"),0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"foreign[1]"),12);
            rejected(()->ReceiverPlantTextureBinding.open(publisher,()->{}));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"foreign[1]"),5);
            int[] guardCalls={0};
            rejected(()->ReceiverPlantTextureBinding.open(publisher,()->{
                if(++guardCalls[0]==3)throw new IllegalArgumentException("Injected post-bind guard failure");
            }));
            for(int unit=10;unit<13;unit++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==output
                        && GL11.glGetInteger(GL33.GL_SAMPLER_BINDING)==guardedSampler,"Failed open restores texture/sampler");
            }
            rejected(()->ReceiverPlantDrawBinding.open(publisher,receiverWindow,Double.NaN,0,0,atlasTexture,0,0,0,true,()->{}));
            rejected(()->ReceiverPlantDrawBinding.open(publisher,receiverWindow,0,0,0,atlasTexture,0,1,0,true,()->{}));
            rejected(()->ReceiverPlantDrawBinding.open(publisher,receiverWindow,10000,0,0,atlasTexture,0,0,0,true,()->{}));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantAtlas"),10);
            rejected(()->ReceiverPlantDrawBinding.open(publisher,receiverWindow,0,0,0,atlasTexture,0,0,0,true,()->{}));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"aqualumenPlantAtlas"),13);
            check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenPlantMemberships"))==17,
                    "Failed complete draw open restores metadata");
            GL13.glActiveTexture(GL13.GL_TEXTURE3);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"atlasOwned"),1);
            draw.run();float[] beforeCameraShift=result.clone();
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"intersectionMode"),2);
            GL20.glUniform3f(GL20.glGetUniformLocation(program,"testCamera"),10,0,-7);
            GL20.glUniform3i(GL20.glGetUniformLocation(program,"testReceiverShift"),0,1,0);
            var shiftedReceiver=new ReceiverRunPublisher.Window(bounds.x(),bounds.y()+1,bounds.z(),bounds.width(),bounds.height(),bounds.depth());
            var complete=ReceiverPlantDrawBinding.open(publisher,shiftedReceiver,10,0,-7,atlasTexture,0,0,0,true,()->{});
            check(complete!=null,"Translated complete binding");draw.run();
            check(Arrays.equals(result,beforeCameraShift),"Camera reference and shifted receiver window preserve exact draw");
            GL20.glUseProgram(0);complete.close();complete.close();
            check(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)==0,"Complete close preserves changed program");
            GL20.glUseProgram(program);
            check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenPlantMemberships"))==17,
                    "Complete close restores captured program metadata");
            int[] programGuardCalls={0};
            try {
                ReceiverPlantDrawBinding.open(publisher,receiverWindow,0,0,0,atlasTexture,0,0,0,true,()->{
                    if(++programGuardCalls[0]==5)GL20.glUseProgram(0);
                });
                throw new AssertionError("Changed program enabled plant readiness");
            } catch(IllegalStateException expected) {}
            check(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)==0,"Failed complete open preserves changed program");
            GL20.glUseProgram(program);
            check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenPlantMemberships"))==17,
                    "Failed complete open restores original metadata after program change");
            for(int unit=10;unit<14;unit++)GL33.glBindSampler(unit,0);
            GL33.glDeleteSamplers(guardedSampler);
            upload.delete(atlasTexture);
            GL20.glDeleteProgram(program); GL30.glDeleteVertexArrays(vao); GL30.glDeleteFramebuffers(framebuffer);
            publisher.close();upload.delete(output);
            System.out.println("PASS GPU complete plant draw binding/backend: exact Java cells/proofs; metadata/atlas/data/sampler restoration; camera/window transforms and changed-program close; alias/camera/LOD/rollback controls; not live ownership");
        } finally { GLFW.glfwDestroyWindow(window); GLFW.glfwTerminate(); }
    }
}
