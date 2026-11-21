package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import org.lwjgl.opengl.*;

public final class ReceiverPlantGpuProbe {
    private ReceiverPlantGpuProbe() {}
    public static float[] draw(ReceiverPlantPacket packet, List<ReceiverQuadIntersection.Ray> rays,
            int atlas, int sampler, ReceiverRadianceVolume.Epoch now, Runnable guard, String kernel) {
        guard.run();
        var owned = List.copyOf(rays);
        if (!packet.current(now) || owned.isEmpty() || owned.size() > 4096
                || atlas == 0 || !GL11.glIsTexture(atlas) || sampler != 0 && !GL33.glIsSampler(sampler))
            throw new IllegalArgumentException("Plant GPU probe owner/extent unavailable");
        int previousProgram = GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM), previousVao = GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING);
        int previousDraw = GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING), previousRead = GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING);
        int previousActive = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE), previousPack = GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
        int[] viewport = new int[4], polygon = new int[2];
        GL11.glGetIntegerv(GL11.GL_VIEWPORT,viewport); GL11.glGetIntegerv(GL11.GL_POLYGON_MODE,polygon);
        boolean core = (GL11.glGetInteger(GL32.GL_CONTEXT_PROFILE_MASK)&GL32.GL_CONTEXT_CORE_PROFILE_BIT) != 0;
        int[] flags = {GL11.GL_DEPTH_TEST,GL11.GL_STENCIL_TEST,GL11.GL_SCISSOR_TEST,GL11.GL_CULL_FACE,
                GL30.GL_RASTERIZER_DISCARD,GL11.GL_COLOR_LOGIC_OP,GL30.GL_FRAMEBUFFER_SRGB};
        boolean[] enabled = new boolean[flags.length];
        for (int index = 0; index < flags.length; index++) enabled[index] = GL11.glIsEnabled(flags[index]);
        int drawBuffers = GL11.glGetInteger(GL20.GL_MAX_DRAW_BUFFERS);
        boolean[] blends = new boolean[drawBuffers];
        var masks = new ArrayList<ByteBuffer>();
        for (int index = 0; index < drawBuffers; index++) {
            blends[index] = GL30.glIsEnabledi(GL11.GL_BLEND,index);
            var mask = ByteBuffer.allocateDirect(4); GL30.glGetBooleani_v(GL11.GL_COLOR_WRITEMASK,index,mask); masks.add(mask);
        }
        int[] packNames = {GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_ROWS,GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SWAP_BYTES};
        int[] packValues = new int[packNames.length], textures = new int[4], samplers = new int[4];
        for (int index = 0; index < packNames.length; index++) packValues[index] = GL11.glGetInteger(packNames[index]);
        for (int unit = 0; unit < 4; unit++) {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
            textures[unit] = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
            samplers[unit] = GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit);
        }
        var allocated = new ArrayList<Integer>(); var shaders = new ArrayList<Integer>();
        Thread owner = Thread.currentThread(); var capabilities = GL.getCapabilities();
        var upload = new ReceiverRadianceTextureUpload(() -> {
            if (Thread.currentThread() != owner || GL.getCapabilities() != capabilities)
                throw new IllegalStateException("Plant probe cleanup context unavailable");
        });
        int program = 0, framebuffer = 0, vao = 0;
        try {
            shaders.add(compile(GL20.GL_VERTEX_SHADER,"#version 330 compatibility\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}"));
            shaders.add(compile(GL20.GL_FRAGMENT_SHADER,"#version 330 compatibility\n"+kernel+
                    "\nuniform sampler2D primitives,atlas,origins,directions;uniform int count;layout(location=0)out vec4 color;"+
                    "void main(){ivec2 p=ivec2(gl_FragCoord.xy);vec4 o=texelFetch(origins,p,0),d=texelFetch(directions,p,0);"+
                    "WaterPlantHit h=waterPlantFirst(primitives,atlas,count,o.xyz,d.xyz,o.w,0.0,0,true);color=vec4(h.status,h.travel,h.uv);}"));
            program = GL20.glCreateProgram(); for (int shader : shaders) GL20.glAttachShader(program,shader);
            GL20.glLinkProgram(program);
            if (GL20.glGetProgrami(program,GL20.GL_LINK_STATUS) == 0) throw new IllegalStateException(GL20.glGetProgramInfoLog(program));
            GL20.glUseProgram(program);
            float[] origins = new float[owned.size()*4], directions = new float[origins.length];
            for (int index = 0; index < owned.size(); index++) {
                var ray = owned.get(index); int offset = index*4;
                origins[offset] = (float)(ray.x()-packet.x()); origins[offset+1] = (float)(ray.y()-packet.y()); origins[offset+2] = (float)(ray.z()-packet.z());
                origins[offset+3] = (float)ray.limit(); directions[offset] = (float)ray.dx(); directions[offset+1] = (float)ray.dy(); directions[offset+2] = (float)ray.dz();
            }
            float[][] data = {packet.triangles(),origins,directions}; String[] names = {"primitives","origins","directions","atlas"};
            for (int unit = 0; unit < 4; unit++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                int texture = atlas;
                if (unit < 3) { texture = upload.create(unit == 0 ? 4 : owned.size(),unit == 0 ? packet.count() : 1,data[unit]); allocated.add(texture); }
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture); GL33.glBindSampler(unit,unit == 3 ? sampler : 0);
                GL20.glUniform1i(GL20.glGetUniformLocation(program,names[unit]),unit);
            }
            GL20.glUniform1i(GL20.glGetUniformLocation(program,"count"),packet.count());
            int output = upload.create(owned.size(),1,new float[owned.size()*4]); allocated.add(output);
            framebuffer = GL30.glGenFramebuffers(); GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,framebuffer);
            GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0,GL11.GL_TEXTURE_2D,output,0);
            GL11.glDrawBuffer(GL30.GL_COLOR_ATTACHMENT0); GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0);
            if (GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER) != GL30.GL_FRAMEBUFFER_COMPLETE) throw new IllegalStateException("Plant probe framebuffer incomplete");
            vao = GL30.glGenVertexArrays(); GL30.glBindVertexArray(vao); GL11.glViewport(0,0,owned.size(),1);
            GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,GL11.GL_FILL);
            for (int flag : flags) GL11.glDisable(flag);
            for (int index = 0; index < drawBuffers; index++) { GL30.glDisablei(GL11.GL_BLEND,index); GL30.glColorMaski(index,true,true,true,true); }
            guard.run(); GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);
            for (int name : packNames) GL11.glPixelStorei(name,name == GL11.GL_PACK_ALIGNMENT ? 4 : 0);
            float[] result = new float[owned.size()*4]; GL11.glReadPixels(0,0,owned.size(),1,GL11.GL_RGBA,GL11.GL_FLOAT,result);
            int error = GL11.glGetError();
            if (error != GL11.GL_NO_ERROR) throw new IllegalStateException("Plant probe GL error="+error);
            guard.run(); return result;
        } finally {
            GL20.glUseProgram(previousProgram); GL30.glBindVertexArray(previousVao);
            GL30.glBindFramebuffer(GL30.GL_DRAW_FRAMEBUFFER,previousDraw); GL30.glBindFramebuffer(GL30.GL_READ_FRAMEBUFFER,previousRead);
            GL11.glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
            if (core) GL11.glPolygonMode(GL11.GL_FRONT_AND_BACK,polygon[0]);
            else { GL11.glPolygonMode(GL11.GL_FRONT,polygon[0]); GL11.glPolygonMode(GL11.GL_BACK,polygon[1]); }
            for (int index = 0; index < flags.length; index++) { if (enabled[index]) GL11.glEnable(flags[index]); else GL11.glDisable(flags[index]); }
            for (int index = 0; index < drawBuffers; index++) {
                var mask = masks.get(index); GL30.glColorMaski(index,mask.get(0)!=0,mask.get(1)!=0,mask.get(2)!=0,mask.get(3)!=0);
                if (blends[index]) GL30.glEnablei(GL11.GL_BLEND,index); else GL30.glDisablei(GL11.GL_BLEND,index);
            }
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,previousPack);
            for (int index = 0; index < packNames.length; index++) GL11.glPixelStorei(packNames[index],packValues[index]);
            for (int unit = 0; unit < 4; unit++) { GL13.glActiveTexture(GL13.GL_TEXTURE0+unit); GL11.glBindTexture(GL11.GL_TEXTURE_2D,textures[unit]); GL33.glBindSampler(unit,samplers[unit]); }
            GL13.glActiveTexture(previousActive);
            if (vao != 0) GL30.glDeleteVertexArrays(vao); if (framebuffer != 0) GL30.glDeleteFramebuffers(framebuffer);
            for (int texture : allocated) upload.delete(texture);
            for (int shader : shaders) GL20.glDeleteShader(shader); if (program != 0) GL20.glDeleteProgram(program);
        }
    }
    private static int compile(int type, String source) {
        int shader = GL20.glCreateShader(type); GL20.glShaderSource(shader,source); GL20.glCompileShader(shader);
        if (GL20.glGetShaderi(shader,GL20.GL_COMPILE_STATUS) == 0) {
            String error = GL20.glGetShaderInfoLog(shader); GL20.glDeleteShader(shader); throw new IllegalStateException(error);
        }
        return shader;
    }
}
