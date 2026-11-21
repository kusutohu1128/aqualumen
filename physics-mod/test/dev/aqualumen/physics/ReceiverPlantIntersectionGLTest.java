package dev.aqualumen.physics;

import java.nio.file.Files;
import java.nio.file.Path;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.opengl.*;

public final class ReceiverPlantIntersectionGLTest {
    private static int program, atlas, primitives;
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
    private static int shader(int type, String source) {
        int shader = GL20.glCreateShader(type);
        GL20.glShaderSource(shader,source); GL20.glCompileShader(shader);
        check(GL20.glGetShaderi(shader,GL20.GL_COMPILE_STATUS) != 0,GL20.glGetShaderInfoLog(shader));
        return shader;
    }
    private static float[] plane(float depth, boolean mask, float ready) {
        float left = mask ? 0 : .75f, right = mask ? 1 : .75f;
        return new float[] {-1,-1,depth,left, 1,-1,depth,right, 1,1,depth,right, .5f,.5f,.5f,ready,
                -1,-1,depth,left, 1,1,depth,right, -1,1,depth,left, .5f,.5f,.5f,ready};
    }
    private static void models(float[]... planes) {
        float[] data = new float[planes.length*32];
        for (int index = 0; index < planes.length; index++) System.arraycopy(planes[index],0,data,index*32,32);
        GL13.glActiveTexture(GL13.GL_TEXTURE0);
        GL11.glBindTexture(GL11.GL_TEXTURE_2D,primitives);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,4,planes.length*2,0,GL11.GL_RGBA,GL11.GL_FLOAT,data);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),planes.length*2);
    }
    private static float[] draw(float x, float originZ, float directionZ, float range, float lod, boolean owned) {
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"origin"),x,0,originZ);
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"direction"),0,0,directionZ);
        GL20.glUniform1f(GL20.glGetUniformLocation(program,"range"),range);
        GL20.glUniform1f(GL20.glGetUniformLocation(program,"lod"),lod);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"owned"),owned ? 1 : 0);
        GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
        float[] result = new float[4]; GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
        check(GL11.glGetError() == GL11.GL_NO_ERROR,"GL error");
        return result;
    }
    private static void expect(float[] hit, int status, float distance, String label) {
        check(hit[0] == status && Math.abs(hit[1]-distance)<1e-5,label+" status="+hit[0]+" distance="+hit[1]);
    }
    public static void main(String[] arguments) throws Exception {
        check(GLFW.glfwInit(),"GLFW init");
        GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE,GLFW.GLFW_FALSE);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MAJOR,3);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MINOR,3);
        long window = GLFW.glfwCreateWindow(16,16,"Plant intersections",0,0);
        check(window != 0,"GLFW context");
        try {
            GLFW.glfwMakeContextCurrent(window); GL.createCapabilities();
            System.out.println("Renderer: "+GL11.glGetString(GL11.GL_RENDERER));
            check(GL11.glGetString(GL11.GL_VENDOR).contains("NVIDIA"),"NVIDIA required");
            int vertex = shader(GL20.GL_VERTEX_SHADER,"#version 330 compatibility\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}");
            String shared = Files.readString(Path.of("shaders/lib/water_plant_intersection.glsl"));
            int fragment = shader(GL20.GL_FRAGMENT_SHADER,"#version 330 compatibility\n"+shared+
                    "\nuniform sampler2D primitives,atlas,indices; uniform int count,normalOutput; uniform ivec2 span; uniform vec3 origin,direction; uniform float range,lod,minimumTravel; uniform bool owned,indexed;\n"+
                    "layout(location=0)out vec4 color;void main(){WaterPlantHit h=waterPlantFirstSelection(primitives,atlas,indices,count,span,indexed,origin,direction,minimumTravel,range,lod,1,owned);color=normalOutput==2?vec4(h.status,h.travel,h.primitive,0):normalOutput==1?vec4(h.normal,h.status):vec4(h.status,h.travel,h.uv);}");
            program = GL20.glCreateProgram(); GL20.glAttachShader(program,vertex); GL20.glAttachShader(program,fragment);
            GL20.glLinkProgram(program); check(GL20.glGetProgrami(program,GL20.GL_LINK_STATUS) != 0,GL20.glGetProgramInfoLog(program));
            GL20.glDeleteShader(vertex); GL20.glDeleteShader(fragment); GL20.glUseProgram(program);
            int vao = GL30.glGenVertexArrays(); GL30.glBindVertexArray(vao);
            int output = GL11.glGenTextures(); GL11.glBindTexture(GL11.GL_TEXTURE_2D,output);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,1,1,0,GL11.GL_RGBA,GL11.GL_FLOAT,(float[])null);
            int framebuffer = GL30.glGenFramebuffers(); GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,framebuffer);
            GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0,GL11.GL_TEXTURE_2D,output,0);
            GL11.glDrawBuffer(GL30.GL_COLOR_ATTACHMENT0); GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0);
            check(GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER) == GL30.GL_FRAMEBUFFER_COMPLETE,"Framebuffer");
            GL11.glViewport(0,0,1,1);
            primitives = GL11.glGenTextures(); GL11.glBindTexture(GL11.GL_TEXTURE_2D,primitives);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"primitives"),0);
            atlas = GL11.glGenTextures(); GL13.glActiveTexture(GL13.GL_TEXTURE1); GL11.glBindTexture(GL11.GL_TEXTURE_2D,atlas);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,2,1,0,GL11.GL_RGBA,GL11.GL_FLOAT,new float[]{1,1,1,0,1,1,1,1});
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,1,GL30.GL_RGBA32F,1,1,0,GL11.GL_RGBA,GL11.GL_FLOAT,new float[]{1,1,1,1});
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_MAX_LEVEL,1);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST_MIPMAP_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_WRAP_S,GL12.GL_CLAMP_TO_EDGE);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"atlas"),1);
            models(plane(4,false,1),plane(2,true,1));
            int indices = GL11.glGenTextures();
            GL13.glActiveTexture(GL13.GL_TEXTURE2); GL11.glBindTexture(GL11.GL_TEXTURE_2D,indices);
            float[] links = new float[1024]; links[0]=2;links[4]=3;
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,256,1,0,GL11.GL_RGBA,GL11.GL_FLOAT,links);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"indices"),2);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"indexed"),1);
            GL20.glUniform2i(GL20.glGetUniformLocation(program,"span"),0,2);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"normalOutput"),2);
            float[] selected = draw(.2f,0,1,10,0,true);
            expect(selected,1,2,"Indexed global packet leaf");
            check(selected[2]==2 || selected[2]==3,"Original global primitive ID retained");
            expect(draw(-.2f,0,1,10,0,true),0,10,"Excluded floor not borrowed by indexed hole");
            GL20.glUniform2i(GL20.glGetUniformLocation(program,"span"),0,0);
            expect(draw(.2f,0,1,10,0,true),0,10,"Empty qualified selection misses");
            GL20.glUniform2i(GL20.glGetUniformLocation(program,"span"),256,1);
            expect(draw(.2f,0,1,10,0,true),2,0,"Out-of-texture membership fails closed");
            float[][] globalPlanes = new float[300][];
            for (int model=0;model<globalPlanes.length;model++) globalPlanes[model]=plane(model==299?2:4,false,1);
            models(globalPlanes);
            links[0]=598;links[4]=599;
            GL13.glActiveTexture(GL13.GL_TEXTURE2); GL11.glBindTexture(GL11.GL_TEXTURE_2D,indices);
            GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,256,1,GL11.GL_RGBA,GL11.GL_FLOAT,links);
            GL20.glUniform2i(GL20.glGetUniformLocation(program,"span"),0,2);
            selected = draw(.2f,0,1,10,0,true);
            expect(selected,1,2,"600-triangle global texture with bounded cell selection");
            check(selected[2]==598 || selected[2]==599,"High global primitive ID retained");
            models(plane(4,false,1),plane(2,true,1));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"indexed"),0);
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"normalOutput"),0);
            GL11.glDeleteTextures(indices);
            expect(draw(.2f,0,1,10,0,true),1,2,"First opaque leaf");
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"minimumTravel"),3);
            expect(draw(.2f,0,1,10,0,true),1,4,"Per-cell interval skips earlier geometry");
            expect(draw(.2f,0,1,3.5f,0,true),0,3.5f,"No later geometry borrowed outside cell interval");
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"minimumTravel"),2);
            expect(draw(.2f,0,1,10,0,true),1,2,"Closed cell entry retains leaf boundary");
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"minimumTravel"),-1);
            expect(draw(.2f,0,1,10,0,true),2,0,"Invalid cell interval fails closed");
            GL20.glUniform1f(GL20.glGetUniformLocation(program,"minimumTravel"),0);
            expect(draw(-.2f,0,1,10,0,true),1,4,"Transparent hole continues to floor");
            expect(draw(-.2f,0,1,10,1,true),1,2,"Explicit mip changes coverage");
            GL13.glActiveTexture(GL13.GL_TEXTURE1); GL11.glBindTexture(GL11.GL_TEXTURE_2D,atlas);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_LINEAR_MIPMAP_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_LINEAR);
            expect(draw(-.2f,0,1,10,0,true),1,2,"Actual linear filtering changes alpha coverage");
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST_MIPMAP_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            expect(draw(.2f,0,1,10,0,false),2,2,"Unowned alpha stops at leaf");
            models(plane(4,false,1),plane(2,true,0));
            expect(draw(-.2f,0,1,10,0,true),2,2,"Unknown leaf cannot borrow floor");
            models(plane(2,true,1),plane(4,false,1));
            expect(draw(.2f,0,1,10,0,true),1,2,"Primitive order independence");
            expect(draw(.2f,5,-1,10,0,true),1,1,"Nearest back-facing floor");
            models(plane(2,true,1));
            expect(draw(.2f,5,-1,10,0,true),1,3,"Double-sided leaf");
            expect(draw(2,0,1,10,0,true),0,10,"Outside geometry");
            expect(draw(.2f,0,1,1,0,true),0,1,"Range stop");
            expect(draw(.2f,0,2,10,0,true),2,0,"Nonunit ray rejected");
            expect(draw(.2f,0,1,10,2,true),2,0,"Unqualified mip rejected");
            models(plane(2,true,1),plane(2,true,0));
            expect(draw(.2f,0,1,10,0,true),2,2,"Coplanar unknown wins");
            models(plane(2,true,0),plane(2,true,1));
            expect(draw(.2f,0,1,10,0,true),2,2,"Coplanar unknown wins in reverse order");
            models(plane(2,true,1),plane(2.0000005f,true,0),plane(2,true,1));
            expect(draw(.2f,0,1,10,0,true),2,2.0000005f,"Near-tie unknown cannot be overwritten");
            models(plane(2.0000005f,true,0),plane(2,true,1));
            expect(draw(.2f,0,1,10,0,true),2,2.0000005f,"Near-tie unknown reverse order");
            float[] oblique = plane(2,true,1);
            for (int offset : new int[] {0,4,8,16,20,24}) oblique[offset+2] += oblique[offset]*.5f;
            models(oblique);
            expect(draw(.2f,0,1,10,0,true),1,2.1f,"Actual diagonal plane hit");
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"normalOutput"),1);
            float[] normal = draw(.2f,0,1,10,0,true);
            check(Math.abs(normal[0]-.4472136f)<1e-5 && Math.abs(normal[1])<1e-5
                    && Math.abs(normal[2]+.8944272f)<1e-5 && normal[3]==1,"Diagonal normal not forged UP");
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"normalOutput"),0);
            float[] malformed = plane(2,true,1); malformed[3] = Float.NaN;
            models(malformed);
            expect(draw(.2f,0,1,10,0,true),2,0,"Malformed UV rejects globally");
            models(plane(2,true,1),plane(2,true,1));
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),3);
            expect(draw(.2f,0,1,10,0,true),2,0,"Texture extent mismatch rejected");
            var epoch = new ReceiverRadianceVolume.Epoch(new Object(),1,1);
            var quad = new ReceiverQuadIntersection.Quad(
                    new ReceiverQuadIntersection.Point(-1,-1,2,0,.5),new ReceiverQuadIntersection.Point(1,-1,2,1,.5),
                    new ReceiverQuadIntersection.Point(1,1,2,1,.5),new ReceiverQuadIntersection.Point(-1,1,2,0,.5),
                    (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
            var packet = ReceiverPlantPacket.capture(epoch,java.util.List.of(quad),0,0,0,true);
            var remote = new ReceiverQuadIntersection.Quad(
                    new ReceiverQuadIntersection.Point(4,-1,2,0,.5),new ReceiverQuadIntersection.Point(6,-1,2,1,.5),
                    new ReceiverQuadIntersection.Point(6,1,2,1,.5),new ReceiverQuadIntersection.Point(4,1,2,0,.5),
                    (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
            var indexedPacket = ReceiverPlantPacket.capture(epoch,java.util.List.of(quad,remote),0,0,0,true);
            var cellIndex = ReceiverPlantCellIndex.capture(indexedPacket,
                    new ReceiverPlantCellIndex.Window(-2,-2,0,9,4,4),epoch,1000);
            int[] candidates = cellIndex.candidates(0,0,1,epoch);
            check(java.util.Arrays.equals(candidates,new int[]{0,1}),"Cell index excludes remote model primitives");
            var cellPacket = indexedPacket.select(candidates);
            float[] copy = packet.triangles(); copy[0] = Float.NaN;
            check(Float.isFinite(packet.triangles()[0]),"Packet storage immutable");
            check(!packet.current(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1))
                    && !packet.current(new ReceiverRadianceVolume.Epoch(epoch.world(),1,2))
                    && !packet.current(new ReceiverRadianceVolume.Epoch(new Object(),1,1)),"Packet epoch identity guards");
            int guardPack = GL15.glGenBuffers(); GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,guardPack);
            GL15.glBufferData(GL21.GL_PIXEL_PACK_BUFFER,1,GL15.GL_STREAM_READ);
            GL11.glPixelStorei(GL11.GL_PACK_ROW_LENGTH,7); GL11.glPixelStorei(GL11.GL_PACK_SKIP_PIXELS,2);
            check(GL11.glGetError() == GL11.GL_NO_ERROR,"Guard pack setup");
            GL11.glEnable(GL30.GL_RASTERIZER_DISCARD); GL11.glEnable(GL11.GL_SCISSOR_TEST);
            check(GL11.glGetError() == GL11.GL_NO_ERROR,"Guard enables setup");
            boolean core = (GL11.glGetInteger(GL32.GL_CONTEXT_PROFILE_MASK)&GL32.GL_CONTEXT_CORE_PROFILE_BIT) != 0;
            if (core) GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,GL11.GL_LINE);
            else { GL11.glPolygonMode(GL11.GL_FRONT,GL11.GL_LINE); GL11.glPolygonMode(GL11.GL_BACK,GL11.GL_POINT); }
            check(GL11.glGetError() == GL11.GL_NO_ERROR,"Guard polygon setup profile="+GL11.glGetInteger(GL32.GL_CONTEXT_PROFILE_MASK));
            GL30.glEnablei(GL11.GL_BLEND,0); GL30.glColorMaski(0,false,true,false,false);
            int active = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
            int[] bindings = new int[4], samplers = new int[4];
            for (int unit = 0; unit < 4; unit++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+unit); bindings[unit] = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                samplers[unit] = GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit);
            }
            GL13.glActiveTexture(active);
            Thread owner = Thread.currentThread();
            Runnable guard = () -> check(Thread.currentThread() == owner && GLFW.glfwGetCurrentContext() == window,"GPU probe owner");
            var rays = java.util.List.of(new ReceiverQuadIntersection.Ray(-.2,0,0,0,0,1,10),
                    new ReceiverQuadIntersection.Ray(.2,0,0,0,0,1,10));
            for (int attempt = 0; attempt < 2; attempt++) {
                check(GL11.glGetError() == GL11.GL_NO_ERROR,"Guard setup GL error");
                if (attempt == 0) {
                    float[] probe = ReceiverPlantGpuProbe.draw(cellPacket,rays,atlas,0,epoch,guard,shared);
                    check(probe[0] == 0 && probe[4] == 1 && Math.abs(probe[5]-2)<1e-5,"Owned packet GPU draw/readback");
                } else {
                    try {
                        ReceiverPlantGpuProbe.draw(packet,rays,atlas,0,epoch,guard,"invalid shader source");
                        throw new AssertionError("Malformed shader accepted");
                    } catch (IllegalStateException expected) {}
                }
                check(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM) == program && GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING) == vao,"Program/VAO restoration");
                check(GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING) == framebuffer
                        && GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING) == framebuffer,"Framebuffer restoration");
                check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE) == active && GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING) == guardPack,"Texture/PBO restoration");
                check(GL11.glGetInteger(GL11.GL_PACK_ROW_LENGTH) == 7 && GL11.glGetInteger(GL11.GL_PACK_SKIP_PIXELS) == 2,"Pixel pack restoration");
                check(GL11.glIsEnabled(GL30.GL_RASTERIZER_DISCARD) && GL11.glIsEnabled(GL11.GL_SCISSOR_TEST)
                        && GL30.glIsEnabledi(GL11.GL_BLEND,0),"Enable restoration");
                int[] polygon = new int[2]; GL11.glGetIntegerv(GL11.GL_POLYGON_MODE,polygon);
                check(polygon[0] == GL11.GL_LINE && (core || polygon[1] == GL11.GL_POINT),"Polygon mode restoration");
                var mask = java.nio.ByteBuffer.allocateDirect(4); GL30.glGetBooleani_v(GL11.GL_COLOR_WRITEMASK,0,mask);
                check(mask.get(0)==0 && mask.get(1)!=0 && mask.get(2)==0 && mask.get(3)==0,"Indexed color mask restoration");
                for (int unit = 0; unit < 4; unit++) {
                    GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                    check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D) == bindings[unit]
                            && GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit) == samplers[unit],"Sampler binding restoration");
                }
                GL13.glActiveTexture(active);
            }
            GL15.glDeleteBuffers(guardPack);
            GL20.glDeleteProgram(program); GL30.glDeleteVertexArrays(vao); GL30.glDeleteFramebuffers(framebuffer);
            GL11.glDeleteTextures(output); GL11.glDeleteTextures(atlas); GL11.glDeleteTextures(primitives);
            System.out.println("PASS shared GLSL GPU draw/readback: indexed cell subset, segment bounds, leaf, hole, unknown barrier, mip, order, backface and ownership; controlled fixtures, not live reflection acceptance");
        } finally { GLFW.glfwDestroyWindow(window); GLFW.glfwTerminate(); }
    }
}
