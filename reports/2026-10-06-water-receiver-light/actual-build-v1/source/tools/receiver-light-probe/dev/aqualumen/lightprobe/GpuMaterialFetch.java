package dev.aqualumen.lightprobe;

import java.io.*;
import java.nio.*;
import java.util.*;
import dev.aqualumen.physics.ReceiverTriangle;
import dev.aqualumen.physics.ReceiverVertexShader;
import org.lwjgl.opengl.*;
import org.lwjgl.system.MemoryUtil;

/** Controlled textureGrad queries of the actually bound atlas. Not natural derivatives. */
final class GpuMaterialFetch {
    private static final int[] PACK={GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SKIP_ROWS,
        GL12.GL_PACK_IMAGE_HEIGHT,GL12.GL_PACK_SKIP_IMAGES,GL11.GL_PACK_SWAP_BYTES,GL11.GL_PACK_LSB_FIRST};
    private static final int[] FLAGS={GL11.GL_DEPTH_TEST,GL11.GL_CULL_FACE,GL11.GL_SCISSOR_TEST,GL11.GL_STENCIL_TEST,GL11.GL_DITHER,GL30.GL_FRAMEBUFFER_SRGB};
    private static final String VS="""
        #version 150
        void main() { vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2); gl_Position=vec4(p*2.0-1.0,0.0,1.0); }
        """;
    private static final String FS="""
        #version 150
        uniform sampler2D atlas;
        uniform vec2 queryUv, queryDx, queryDy;
        out vec4 material;
        void main() { material=textureGrad(atlas,queryUv,queryDx,queryDy); }
        """;
    private record Query(int face,double s,double t,ReceiverVertexShader.Output value) {}
    private static float[] uniform(int program,String name,int count) {
        int loc=GL20.glGetUniformLocation(program,name);if(loc<0)throw new IllegalStateException("Actual uniform absent: "+name);
        float[] result=new float[count];GL20.glGetUniformfv(program,loc,result);return result;
    }
    private static List<Query> queries(int program,byte[] fixture) throws IOException {
        var uniforms=ReceiverVertexShader.Uniforms.capture(uniform(program,"iris_LightmapTextureMatrix",16),uniform(program,"u_TexCoordShrink",2));
        if(uniforms==null)throw new IllegalStateException("Actual decode uniforms rejected");
        try(var in=new DataInputStream(new ByteArrayInputStream(fixture))) {
            if(in.readInt()!=0x41514d31 || in.readInt()!=14)throw new IllegalStateException("Bounded archived face fixture required");
            var quads=new ReceiverTriangle.Quad[14];
            for(int f=0;f<14;f++) {
                var vertices=new ReceiverTriangle.Vertex[4];
                for(int v=0;v<4;v++) {
                    double s=in.readDouble(),t=in.readDouble();
                    var encoded=new ReceiverVertexShader.Encoded(in.readInt(),in.readInt(),in.readInt());
                    vertices[v]=new ReceiverTriangle.Vertex(s,t,ReceiverVertexShader.decode(encoded,uniforms));
                }
                quads[f]=ReceiverTriangle.capture(vertices,new int[]{0,1,2,2,3,0});
                if(quads[f]==null)throw new IllegalStateException("Archived face attributes rejected");
            }
            if(in.readInt()!=16)throw new IllegalStateException("Exact first receiver point count required");
            var result=new ArrayList<Query>();
            for(int i=0;i<16;i++) {
                int f=in.readInt();double s=in.readDouble(),t=in.readDouble();
                if(f<0 || f>=14)throw new IllegalStateException("Face index rejected");
                var sample=quads[f].sample(s,t);if(sample==null)throw new IllegalStateException("Point outside face");
                result.add(new Query(f,s,t,sample.value()));
            }
            if(in.read()!=-1)throw new IllegalStateException("Trailing fixture data rejected");return result;
        }
    }
    private static int shader(int type,String source) {
        int id=GL20.glCreateShader(type);GL20.glShaderSource(id,source);GL20.glCompileShader(id);
        if(GL20.glGetShaderi(id,GL20.GL_COMPILE_STATUS)==0) {
            String log=GL20.glGetShaderInfoLog(id);GL20.glDeleteShader(id);throw new IllegalStateException("Owned material shader failed: "+log);
        }
        return id;
    }
    static Map<String,Object> run(int original,byte[] fixture) throws Exception {
        var queries=queries(original,fixture);
        int loc=GL20.glGetUniformLocation(original,"gtexture");if(loc<0)throw new IllegalStateException("Actual atlas uniform missing");
        int[] atlasUnit=new int[1];GL20.glGetUniformiv(original,loc,atlasUnit);
        int free=GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS)-1;
        for(int i=0;i<GL20.glGetProgrami(original,GL20.GL_ACTIVE_UNIFORMS);i++) {
            int[] size=new int[1],type=new int[1];String name=GL20.glGetActiveUniform(original,i,size,type);
            if(type[0]==GL20.GL_SAMPLER_2D || type[0]==GL20.GL_SAMPLER_2D_SHADOW) {
                int[] unit=new int[1];GL20.glGetUniformiv(original,GL20.glGetUniformLocation(original,name),unit);
                if(unit[0]==free)throw new IllegalStateException("Unused allocation texture unit required");
            }
        }
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        GL13.glActiveTexture(GL13.GL_TEXTURE0+atlasUnit[0]);
        int atlas=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D),base=GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_BASE_LEVEL);
        int width=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,base,GL11.GL_TEXTURE_WIDTH),height=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,base,GL11.GL_TEXTURE_HEIGHT);
        GL13.glActiveTexture(active);
        if(atlas<=0 || width<=0 || height<=0 || base!=0)throw new IllegalStateException("Actual base-zero atlas required");
        if(GL30.glIsEnabledi(GL11.GL_BLEND,0) || GL11.glIsEnabled(GL30.GL_RASTERIZER_DISCARD))throw new IllegalStateException("Opaque non-discard state required");
        int[] polygon=new int[2];GL11.glGetIntegerv(GL11.GL_POLYGON_MODE,polygon);
        if(polygon[0]!=GL11.GL_FILL || polygon[1]!=GL11.GL_FILL)throw new IllegalStateException("Filled polygon state required");
        ByteBuffer mask=MemoryUtil.memAlloc(4);
        try {GL11.glGetBooleanv(GL11.GL_COLOR_WRITEMASK,mask);for(int i=0;i<4;i++)if(mask.get(i)==0)throw new IllegalStateException("All color channels required");}
        finally {MemoryUtil.memFree(mask);}
        for(int i=0;i<GL11.glGetInteger(GL30.GL_MAX_CLIP_DISTANCES);i++)if(GL11.glIsEnabled(GL30.GL_CLIP_DISTANCE0+i))throw new IllegalStateException("Enabled clip plane unsupported");
        int vao=GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING),draw=GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING),read=GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING);
        int packPbo=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING),unpackPbo=GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING);
        int[] viewport=new int[4],pack=new int[PACK.length];boolean[] flags=new boolean[FLAGS.length];
        GL11.glGetIntegerv(GL11.GL_VIEWPORT,viewport);
        for(int i=0;i<PACK.length;i++)pack[i]=GL11.glGetInteger(PACK[i]);for(int i=0;i<FLAGS.length;i++)flags[i]=GL11.glIsEnabled(FLAGS[i]);
        GL13.glActiveTexture(GL13.GL_TEXTURE0+free);int freeBinding=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);GL13.glActiveTexture(active);
        int vs=0,fs=0,program=0,ownedVao=0,fbo=0,output=0;
        var observations=new ArrayList<Object>();
        try {
            if(GL11.glGetError()!=GL11.GL_NO_ERROR)throw new IllegalStateException("Preexisting GL error before owned material query");
            vs=shader(GL20.GL_VERTEX_SHADER,VS);fs=shader(GL20.GL_FRAGMENT_SHADER,FS);
            program=GL20.glCreateProgram();GL20.glAttachShader(program,vs);GL20.glAttachShader(program,fs);GL30.glBindFragDataLocation(program,0,"material");GL20.glLinkProgram(program);
            if(GL20.glGetProgrami(program,GL20.GL_LINK_STATUS)==0)throw new IllegalStateException("Owned material program link failed: "+GL20.glGetProgramInfoLog(program));
            GL20.glUseProgram(program);GL20.glUniform1i(GL20.glGetUniformLocation(program,"atlas"),atlasUnit[0]);
            ownedVao=GL30.glGenVertexArrays();GL30.glBindVertexArray(ownedVao);
            output=GL11.glGenTextures();GL13.glActiveTexture(GL13.GL_TEXTURE0+free);GL11.glBindTexture(GL11.GL_TEXTURE_2D,output);
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,0);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,1,1,0,GL11.GL_RGBA,GL11.GL_FLOAT,(ByteBuffer)null);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST);GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            fbo=GL30.glGenFramebuffers();GL30.glBindFramebuffer(GL30.GL_FRAMEBUFFER,fbo);
            GL30.glFramebufferTexture2D(GL30.GL_FRAMEBUFFER,GL30.GL_COLOR_ATTACHMENT0,GL11.GL_TEXTURE_2D,output,0);
            GL11.glDrawBuffer(GL30.GL_COLOR_ATTACHMENT0);GL11.glReadBuffer(GL30.GL_COLOR_ATTACHMENT0);
            if(GL30.glCheckFramebufferStatus(GL30.GL_FRAMEBUFFER)!=GL30.GL_FRAMEBUFFER_COMPLETE)throw new IllegalStateException("Owned floating target incomplete");
            GL11.glViewport(0,0,1,1);for(int flag:FLAGS)GL11.glDisable(flag);
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);for(int i=0;i<PACK.length;i++)GL11.glPixelStorei(PACK[i],i==0?1:0);
            int uv=GL20.glGetUniformLocation(program,"queryUv"),dx=GL20.glGetUniformLocation(program,"queryDx"),dy=GL20.glGetUniformLocation(program,"queryDy");
            float[] rhos={0,1,(float)Math.sqrt(2),4,16};
            for(int point=0;point<queries.size();point++) {
                var q=queries.get(point);var a=q.value();GL20.glUniform2f(uv,a.u(),a.v());
                for(float rho:rhos) {
                    float x=rho/width,y=rho/height;GL20.glUniform2f(dx,x,0);GL20.glUniform2f(dy,0,y);
                    GL30.glClearBufferfv(GL11.GL_COLOR,0,new float[]{-123,-123,-123,-123});GL11.glDrawArrays(GL11.GL_TRIANGLES,0,3);
                    float[] rgba=new float[4];GL11.glReadPixels(0,0,1,1,GL11.GL_RGBA,GL11.GL_FLOAT,rgba);
                    if(GL11.glGetError()!=GL11.GL_NO_ERROR)throw new IllegalStateException("Owned textureGrad query GL error");
                    var values=new ArrayList<Float>();for(float value:rgba){if(!Float.isFinite(value) || value==-123)throw new IllegalStateException("Missing/nonfinite material fetch");values.add(value);}
                    var result=new LinkedHashMap<String,Object>();result.put("point",point);result.put("face",q.face());result.put("local",List.of(q.s(),q.t()));
                    result.put("uv",List.of(a.u(),a.v()));result.put("decodedAttributes",List.of(a.u(),a.v(),a.block(),a.sky(),a.red(),a.green(),a.blue(),a.ao()));
                    result.put("rho",rho);result.put("dUVdx",List.of(x,0));result.put("dUVdy",List.of(0,y));result.put("rgba",values);observations.add(result);
                }
            }
        } finally {
            GL30.glBindFramebuffer(GL30.GL_DRAW_FRAMEBUFFER,draw);GL30.glBindFramebuffer(GL30.GL_READ_FRAMEBUFFER,read);
            GL30.glBindVertexArray(vao);GL20.glUseProgram(original);GL11.glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
            for(int i=0;i<FLAGS.length;i++){if(flags[i])GL11.glEnable(FLAGS[i]);else GL11.glDisable(FLAGS[i]);}
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,packPbo);GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,unpackPbo);
            for(int i=0;i<PACK.length;i++)GL11.glPixelStorei(PACK[i],pack[i]);
            GL13.glActiveTexture(GL13.GL_TEXTURE0+free);GL11.glBindTexture(GL11.GL_TEXTURE_2D,freeBinding);GL13.glActiveTexture(active);
            if(fbo!=0)GL30.glDeleteFramebuffers(fbo);if(output!=0)GL11.glDeleteTextures(output);if(ownedVao!=0)GL30.glDeleteVertexArrays(ownedVao);
            if(program!=0)GL20.glDeleteProgram(program);if(vs!=0)GL20.glDeleteShader(vs);if(fs!=0)GL20.glDeleteShader(fs);
        }
        int[] afterViewport=new int[4];GL11.glGetIntegerv(GL11.GL_VIEWPORT,afterViewport);
        if(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=original || GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING)!=vao
                || GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING)!=draw || GL11.glGetInteger(GL30.GL_READ_FRAMEBUFFER_BINDING)!=read
                || GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)!=active || !Arrays.equals(viewport,afterViewport)
                || GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING)!=packPbo || GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING)!=unpackPbo)
            throw new IllegalStateException("Owned material query state not restored");
        for(int i=0;i<PACK.length;i++)if(GL11.glGetInteger(PACK[i])!=pack[i])throw new IllegalStateException("Pack state not restored");
        for(int i=0;i<FLAGS.length;i++)if(GL11.glIsEnabled(FLAGS[i])!=flags[i])throw new IllegalStateException("Enabled state not restored");
        GL13.glActiveTexture(GL13.GL_TEXTURE0+free);int restoredFree=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        GL13.glActiveTexture(GL13.GL_TEXTURE0+atlasUnit[0]);int restoredAtlas=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);GL13.glActiveTexture(active);
        if(restoredFree!=freeBinding || restoredAtlas!=atlas || GL11.glGetError()!=GL11.GL_NO_ERROR)throw new IllegalStateException("Texture binding/error restoration failed");
        return Map.of("observations",observations,"count",observations.size(),"atlasTextureID",atlas,"atlasUnit",atlasUnit[0],
            "controlledFootprints",true,"naturalFragmentDerivatives",false,"listedGLStateRestored",true,
            "originalTextureDataModified",false,"vertexShaderSource",VS,"fragmentShaderSource",FS);
    }
}
