package dev.aqualumen.idle;
import dev.aqualumen.animalqa.FrameSample;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.gl.shader.GlShader;
import java.nio.file.*;
import java.util.*;
import static org.lwjgl.opengl.GL11.*;
import static org.lwjgl.opengl.GL13.*;
import static org.lwjgl.opengl.GL20.*;
import static org.lwjgl.opengl.GL30.*;

public final class Capture {
    record Program(String name, Map<String,String> stages) {}
    private static final Map<Integer,Program> programs=new HashMap<>();
    private static final Path game=FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize();
    private static final boolean enabled=game.toString().matches("/tmp/aql-v190-run-[^/]+/minecraft")
            && Files.isRegularFile(game.resolve("config/idle-source.enabled"),LinkOption.NOFOLLOW_LINKS);

    public static void link(String name, GlShader[] shaders, int handle) {
        if(!enabled || !(name.equals("composite") || name.equals("deferred"))) return;
        Map<String,String> sources=new TreeMap<>();
        for(GlShader shader:shaders) {
            int id=shader.getHandle();
            String stage=glGetShaderi(id,GL_SHADER_TYPE)==GL_VERTEX_SHADER?"vsh":"fsh";
            sources.put(stage,glGetShaderSource(id));
        }
        programs.put(handle,new Program(name,sources));
    }
    public static void draw() {
        if(!enabled || programs.isEmpty()) return;
        int handle=glGetInteger(GL_CURRENT_PROGRAM);
        Program info=programs.get(handle);
        if(info==null) return;
        try {
            Object client=Class.forName("net.minecraft.class_310").getMethod("method_1551").invoke(null);
            if(!FrameSample.authorized(client)) return;
            Path out=game.resolve("idle-capture");
            Files.createDirectories(out);
            for(var stage:info.stages.entrySet())
                Files.writeString(out.resolve(info.name+"."+stage.getKey()),stage.getValue());
            int[] viewport=new int[4]; glGetIntegerv(GL_VIEWPORT,viewport);
            StringBuilder state=new StringBuilder("viewport="+Arrays.toString(viewport)+" drawFbo="+glGetInteger(GL_DRAW_FRAMEBUFFER_BINDING)+"\n");
            int active=glGetInteger(GL_ACTIVE_TEXTURE);
            try {
                for(int i=0;i<glGetInteger(GL_MAX_DRAW_BUFFERS);i++){
                    int attachment=glGetInteger(GL_DRAW_BUFFER0+i);
                    if(attachment==GL_NONE) continue;
                    int texture=glGetFramebufferAttachmentParameteri(GL_DRAW_FRAMEBUFFER,attachment,GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME);
                    int binding=glGetInteger(GL_TEXTURE_BINDING_2D);
                    try {
                        glBindTexture(GL_TEXTURE_2D,texture);
                        state.append("out ").append(i).append(" texture ").append(texture).append(" format ").append(glGetTexLevelParameteri(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT)).append(" size ").append(glGetTexLevelParameteri(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH)).append('x').append(glGetTexLevelParameteri(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT)).append('\n');
                    } finally { glBindTexture(GL_TEXTURE_2D,binding); }
                }
                for(int i=0;i<glGetProgrami(handle,GL_ACTIVE_UNIFORMS);i++){
                    var size=org.lwjgl.BufferUtils.createIntBuffer(1); var type=org.lwjgl.BufferUtils.createIntBuffer(1);
                    String name=glGetActiveUniform(handle,i,size,type);
                    if(type.get(0)!=GL_SAMPLER_2D && type.get(0)!=GL_UNSIGNED_INT_SAMPLER_2D && type.get(0)!=GL_SAMPLER_2D_SHADOW) continue;
                    int unit=glGetUniformi(handle,glGetUniformLocation(handle,name));
                    glActiveTexture(GL_TEXTURE0+unit);
                    state.append("in ").append(name).append(" unit ").append(unit).append(" texture ").append(glGetInteger(GL_TEXTURE_BINDING_2D)).append('\n');
                }
            } finally {glActiveTexture(active);}
            Files.writeString(out.resolve(info.name+".state"),state);
            programs.remove(handle);
        } catch(Exception e){throw new IllegalStateException("private source capture",e);}
    }
}
