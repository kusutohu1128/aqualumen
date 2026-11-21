package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import org.lwjgl.opengl.*;

public final class ReceiverSourceDraw {
    private static int sourceProgram;
    private static String sourceFragment;
    public record Result(List<Float> total, List<Float> sun) {
        public Result { total=List.copyOf(total); sun=List.copyOf(sun); }
    }
    public record Point(ReceiverSodiumScope.Snapshot face,ReceiverTriangle.Sample sample) { }
    private ReceiverSourceDraw() { }

    public static final class Session implements AutoCloseable {
        private final ReceiverRadianceVolume.Epoch epoch;
        private final Thread owner=Thread.currentThread();
        private int program;
        private int original;
        private String originalFragment;
        private boolean closed;
        public Session(ReceiverRadianceVolume.Epoch epoch) { this.epoch=epoch; }
        private int program(ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch now) {
            if(closed || Thread.currentThread()!=owner || epoch==null || now==null
                    || epoch.world()!=now.world() || epoch.frame()!=now.frame() || epoch.resources()!=now.resources()
                    || !lighting.current(now) || lighting.program()!=sourceProgram || sourceFragment==null)
                throw new IllegalStateException("Owned source session expired");
            if(program!=0) {
                if(original!=lighting.program() || originalFragment!=sourceFragment
                        || !GL20.glIsProgram(original) || !GL20.glIsProgram(program))
                    throw new IllegalStateException("Owned source session program expired");
                return program;
            }
            int vertex=0,fragment=0,candidate=0;
            try {
                fragment=fragment(lighting.program());
                vertex=GL20.glCreateShader(GL20.GL_VERTEX_SHADER);
                GL20.glShaderSource(vertex,"#version 330 core\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}");
                GL20.glCompileShader(vertex);
                if(GL20.glGetShaderi(vertex,GL20.GL_COMPILE_STATUS)==0)
                    throw new IllegalStateException("Owned source vertex compile failed: "+GL20.glGetShaderInfoLog(vertex));
                candidate=GL20.glCreateProgram(); GL20.glAttachShader(candidate,vertex); GL20.glAttachShader(candidate,fragment);
                var outputs=Pattern.compile("out\\s+vec4\\s+(\\w+)\\s*;").matcher(GL20.glGetShaderSource(fragment));
                while(outputs.find()) {
                    String name=outputs.group(1);
                    int location=GL30.glGetFragDataLocation(lighting.program(),name);
                    if(location>=0) GL30.glBindFragDataLocation(candidate,location,name);
                }
                GL20.glLinkProgram(candidate);
                if(GL20.glGetProgrami(candidate,GL20.GL_LINK_STATUS)==0)
                    throw new IllegalStateException("Owned actual source fragment link failed: "+GL20.glGetProgramInfoLog(candidate));
                program=candidate; candidate=0; original=lighting.program(); originalFragment=sourceFragment;
                return program;
            } finally {
                if(candidate!=0) GL20.glDeleteProgram(candidate);
                if(vertex!=0) GL20.glDeleteShader(vertex);
                if(fragment!=0) GL20.glDeleteShader(fragment);
            }
        }
        public void close() {
            if(Thread.currentThread()!=owner) throw new IllegalStateException("Owned source session close outside owner");
            if(program!=0) GL20.glDeleteProgram(program);
            program=0; closed=true;
        }
    }

    public static void compiled(int program, net.irisshaders.iris.gl.shader.GlShader[] shaders) {
        if(program==sourceProgram) { sourceProgram=0; sourceFragment=null; }
        for(var shader:shaders) {
            int handle=shader.getHandle();
            if(GL20.glGetShaderi(handle,GL20.GL_SHADER_TYPE)!=GL20.GL_FRAGMENT_SHADER) continue;
            String source=GL20.glGetShaderSource(handle);
            if(source.length()>262144 || !source.contains("receiverInputSize") || !source.contains("shadeOpaqueReceiver")) continue;
            sourceProgram=program; sourceFragment=source;
        }
    }

    public static Result point(Session session, ReceiverSodiumScope.Snapshot face, ReceiverTriangle.Sample sample,
                               ReceiverTerrainState terrain, ReceiverLightingState lighting,
                               ReceiverRadianceVolume.Epoch now) {
        return points(session,List.of(new Point(face,sample)),terrain,lighting,now).get(0);
    }
    public static List<Result> points(Session session,List<Point> inputs,ReceiverTerrainState terrain,
                                      ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch now) {
        var materials=new ArrayList<ReceiverMaterialPoint>();
        for(var input:List.copyOf(inputs)) {
            var face=input.face();
            materials.add(new ReceiverMaterialPoint(face.epoch(),face.x()+.5,face.y()+1.0,face.z()+.5,
                    0,1,0,input.sample().value()));
        }
        return materialPoints(session,materials,terrain,lighting,now,false);
    }
    public static List<Result> materialPoints(Session session,List<ReceiverMaterialPoint> inputs,ReceiverTerrainState terrain,
                                      ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch now) {
        return materialPoints(session,inputs,terrain,lighting,now,false);
    }
    public static List<Result> cutoutMaterialPoints(Session session,List<ReceiverMaterialPoint> inputs,ReceiverTerrainState terrain,
                                      ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch now) {
        return materialPoints(session,inputs,terrain,lighting,now,true);
    }
    private static List<Result> materialPoints(Session session,List<ReceiverMaterialPoint> inputs,ReceiverTerrainState terrain,
                                      ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch now,boolean cutout) {
        inputs=List.copyOf(inputs);
        if(inputs.isEmpty()) return List.of();
        int width=inputs.size();
        if(width>4096 || width>GL11.glGetInteger(GL11.GL_MAX_TEXTURE_SIZE))
            throw new IllegalStateException("Receiver source batch too wide");
        if(now==null || !lighting.current(now))
            throw new IllegalStateException("Receiver source draw has no current owner");
        for(var input:inputs) {
            if(!input.epoch().matches(now.world(),now.frame(),now.resources()))
                throw new IllegalStateException("Receiver source batch has stale face");
        }
        if(!GL.getCapabilities().OpenGL33 && !GL.getCapabilities().GL_ARB_sampler_objects)
            throw new IllegalStateException("Receiver source sampler objects unavailable");
        int previousProgram=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        int previousVao=GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING);
        int previousDraw=GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING);
        int previousRead=GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING);
        int previousActive=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        int previousPack=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
        int[] viewport=new int[4]; GL11.glGetIntegerv(GL11.GL_VIEWPORT,viewport);
        int[] packNames={GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_ROWS,
                         GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SWAP_BYTES};
        int[] packValues=new int[packNames.length];
        for(int index=0;index<packNames.length;index++) packValues[index]=GL11.glGetInteger(packNames[index]);
        int[] flags={GL11.GL_BLEND,GL11.GL_DEPTH_TEST,GL11.GL_STENCIL_TEST,GL11.GL_SCISSOR_TEST,
                     GL11.GL_CULL_FACE,GL30.GL_RASTERIZER_DISCARD,GL11.GL_COLOR_LOGIC_OP,GL30.GL_FRAMEBUFFER_SRGB};
        boolean[] enabled=new boolean[flags.length];
        for(int index=0;index<flags.length;index++) enabled[index]=GL11.glIsEnabled(flags[index]);
        int[] polygon=new int[2]; GL11.glGetIntegerv(GL11.GL_POLYGON_MODE,polygon);
        boolean core=(GL11.glGetInteger(GL32.GL_CONTEXT_PROFILE_MASK)&GL32.GL_CONTEXT_CORE_PROFILE_BIT)!=0;
        if(polygon[0]!=GL11.GL_FILL && polygon[0]!=GL11.GL_LINE && polygon[0]!=GL11.GL_POINT)
            throw new IllegalStateException("Polygon mode unavailable");
        if(!core && polygon[1]!=GL11.GL_FILL && polygon[1]!=GL11.GL_LINE && polygon[1]!=GL11.GL_POINT)
            throw new IllegalStateException("Compatibility back polygon mode unavailable");
        int drawBuffers=GL11.glGetInteger(GL20.GL_MAX_DRAW_BUFFERS);
        boolean[] blends=new boolean[drawBuffers];
        var masks=new ArrayList<ByteBuffer>();
        for(int index=0;index<drawBuffers;index++) {
            blends[index]=GL30.glIsEnabledi(GL11.GL_BLEND,index);
            var mask=ByteBuffer.allocateDirect(4); GL30.glGetBooleani_v(GL11.GL_COLOR_WRITEMASK,index,mask); masks.add(mask);
        }
        int[] textures=new int[11], samplers=new int[11];
        for(int unit=0;unit<11;unit++) {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
            textures[unit]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
            samplers[unit]=GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit);
        }
        var allocated=new ArrayList<Integer>();
        int program=0, framebuffer=0, vao=0;
        var upload=new ReceiverRadianceTextureUpload();
        try {
            program=session.program(lighting,now);
            GL20.glUseProgram(program);
            for(String name:new String[]{"gbufferModelViewInverse","shadowModelView","shadowProjection"})
                GL20.glUniformMatrix4fv(location(program,name),false,lighting.value(name));
            for(String name:new String[]{"cameraPosition","sunPosition","shadowLightPosition"})
                GL20.glUniform3fv(location(program,name),lighting.value(name));
            for(String name:new String[]{"frameTimeCounter","rainStrength"})
                GL20.glUniform1f(location(program,name),lighting.value(name)[0]);
            GL20.glUniform1i(location(program,"aqualumenDimension"),0);
            GL20.glUniform1i(location(program,"receiverTexelMode"),1);
            GL20.glUniform1i(location(program,"receiverAlphaMode"),cutout?1:0);
            GL20.glUniform2i(location(program,"receiverInputSize"),width,1);
            float[][] data=new float[7][width*4];
            float[] camera=lighting.value("cameraPosition");
            for(int index=0;index<width;index++) {
                var input=inputs.get(index); var value=input.attributes();
                float[][] channels={{1,1,1,1},{value.red(),value.green(),value.blue(),1},
                        {input.normalX(),input.normalY(),input.normalZ(),1},
                        {(float)(input.x()-camera[0]),(float)(input.y()-camera[1]),(float)(input.z()-camera[2]),1},
                        {value.block(),value.sky(),value.ao(),1},{value.u(),value.v(),0,1},{0,0,0,0}};
                for(int channel=0;channel<7;channel++) System.arraycopy(channels[channel],0,data[channel],index*4,4);
            }
            String[] names={"receiverInputTexel","receiverInputTint","receiverInputNormal","receiverInputPosition",
                            "receiverInputLightmap","receiverInputUv","receiverInputGradients","receiverAtlas",
                            "colortex6","colortex7","shadowtex0"};
            for(int unit=0;unit<11;unit++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                int texture, sampler=0;
                if(unit<7) { texture=upload.create(width,1,data[unit]); allocated.add(texture); }
                else if(unit==7) { texture=terrain.atlas(); sampler=terrain.sampler(); }
                else { var captured=lighting.texture(names[unit]); texture=captured.texture(); sampler=captured.sampler(); }
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture); GL33.glBindSampler(unit,sampler);
                GL20.glUniform1i(location(program,names[unit]),unit);
            }
            framebuffer=GL30.glGenFramebuffers(); GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,framebuffer);
            for(int index=0;index<2;index++) {
                int texture=upload.create(width,1,new float[width*4]); allocated.add(texture);
                GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0+index,GL11.GL_TEXTURE_2D,texture,0);
            }
            GL20.glDrawBuffers(new int[]{GL30.GL_COLOR_ATTACHMENT0,GL30.GL_COLOR_ATTACHMENT1});
            if(GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER)!=GL30.GL_FRAMEBUFFER_COMPLETE)
                throw new IllegalStateException("Owned source framebuffer incomplete");
            vao=GL30.glGenVertexArrays(); GL30.glBindVertexArray(vao);
            GL11.glViewport(0,0,width,1); GL11.glColorMask(true,true,true,true); GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,GL11.GL_FILL);
            for(int flag:flags) GL11.glDisable(flag);
            GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);
            for(int name:packNames) GL11.glPixelStorei(name,name==GL11.GL_PACK_ALIGNMENT?4:0);
            float[][] result=new float[2][width*4];
            for(int index=0;index<2;index++) {
                GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0+index);
                GL11.glReadPixels(0,0,width,1,GL11.GL_RGBA,GL11.GL_FLOAT,result[index]);
                for(float channel:result[index]) if(!Float.isFinite(channel) || channel<0)
                    throw new IllegalStateException("Owned source RGB/readiness invalid");
            }
            var results=new ArrayList<Result>();
            for(int index=0;index<width;index++) {
                int offset=index*4; float ready=result[0][offset+3];
                if((ready!=0 && ready!=1) || result[1][offset+3]!=ready)
                    throw new IllegalStateException("Owned source batch readiness unpaired");
                for(int channel=0;channel<3;channel++) {
                    if(result[1][offset+channel]>result[0][offset+channel]
                            || ready==0 && (result[0][offset+channel]!=0 || result[1][offset+channel]!=0))
                        throw new IllegalStateException("Owned source batch radiance unpaired");
                }
                results.add(new Result(List.of(result[0][offset],result[0][offset+1],result[0][offset+2],ready),
                        List.of(result[1][offset],result[1][offset+1],result[1][offset+2],ready)));
            }
            return List.copyOf(results);
        } finally {
            GL20.glUseProgram(previousProgram); GL30.glBindVertexArray(previousVao);
            GL30.glBindFramebuffer(GL30.GL_DRAW_FRAMEBUFFER,previousDraw); GL30.glBindFramebuffer(GL30.GL_READ_FRAMEBUFFER,previousRead);
            GL11.glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
            if(core) GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,polygon[0]);
            else { GL11.glPolygonMode(GL11.GL_FRONT,polygon[0]); GL11.glPolygonMode(GL11.GL_BACK,polygon[1]); }
            for(int index=0;index<flags.length;index++) { if(enabled[index]) GL11.glEnable(flags[index]); else GL11.glDisable(flags[index]); }
            for(int index=0;index<drawBuffers;index++) { var mask=masks.get(index); GL30.glColorMaski(index,mask.get(0)!=0,mask.get(1)!=0,mask.get(2)!=0,mask.get(3)!=0); }
            for(int index=0;index<drawBuffers;index++) { if(blends[index]) GL30.glEnablei(GL11.GL_BLEND,index); else GL30.glDisablei(GL11.GL_BLEND,index); }
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,previousPack);
            for(int index=0;index<packNames.length;index++) GL11.glPixelStorei(packNames[index],packValues[index]);
            for(int unit=0;unit<11;unit++) { GL13.glActiveTexture(GL13.GL_TEXTURE0+unit); GL11.glBindTexture(GL11.GL_TEXTURE_2D,textures[unit]); GL33.glBindSampler(unit,samplers[unit]); }
            GL13.glActiveTexture(previousActive);
            if(vao!=0) GL30.glDeleteVertexArrays(vao); if(framebuffer!=0) GL30.glDeleteFramebuffers(framebuffer);
            for(int texture:allocated) upload.delete(texture);
            if(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=previousProgram
                    || GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING)!=previousVao
                    || GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING)!=previousDraw
                    || GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING)!=previousRead
                    || GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING)!=previousPack)
                throw new IllegalStateException("Owned source draw did not restore draw bindings");
            int[] restoredViewport=new int[4]; GL11.glGetIntegerv(GL11.GL_VIEWPORT,restoredViewport);
            if(!java.util.Arrays.equals(viewport,restoredViewport)) throw new IllegalStateException("Owned source viewport restoration failed");
            for(int index=0;index<flags.length;index++) if(GL11.glIsEnabled(flags[index])!=enabled[index])
                throw new IllegalStateException("Owned source render enable restoration failed");
            for(int index=0;index<packNames.length;index++) if(GL11.glGetInteger(packNames[index])!=packValues[index])
                throw new IllegalStateException("Owned source pixel-pack restoration failed");
            for(int index=0;index<drawBuffers;index++) {
                var mask=ByteBuffer.allocateDirect(4); GL30.glGetBooleani_v(GL11.GL_COLOR_WRITEMASK,index,mask);
                for(int channel=0;channel<4;channel++) if(mask.get(channel)!=masks.get(index).get(channel))
                    throw new IllegalStateException("Owned source indexed color mask restoration failed");
                if(GL30.glIsEnabledi(GL11.GL_BLEND,index)!=blends[index])
                    throw new IllegalStateException("Owned source indexed blend restoration failed");
            }
            try {
                for(int unit=0;unit<11;unit++) {
                    GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                    if(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)!=textures[unit]
                            || GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit)!=samplers[unit])
                        throw new IllegalStateException("Owned source texture/sampler restoration failed");
                }
            } finally { GL13.glActiveTexture(previousActive); }
        }
    }

    private static int location(int program,String name) {
        int location=GL20.glGetUniformLocation(program,name);
        if(location<0) throw new IllegalStateException("Owned source active uniform missing: "+name);
        return location;
    }

    private static int fragment(int program) {
        if(program!=sourceProgram || sourceFragment==null || !GL20.glIsProgram(program)
                || GL20.glGetUniformLocation(program,"receiverInputSize")<0)
            throw new IllegalStateException("Actual compiled receiver source owner unavailable");
        int shader=GL20.glCreateShader(GL20.GL_FRAGMENT_SHADER);
        GL20.glShaderSource(shader,sourceFragment); GL20.glCompileShader(shader);
        if(GL20.glGetShaderi(shader,GL20.GL_COMPILE_STATUS)==0) {
            String log=GL20.glGetShaderInfoLog(shader); GL20.glDeleteShader(shader);
            throw new IllegalStateException("Owned actual source fragment compile failed: "+log);
        }
        return shader;
    }
}
