package dev.aqualumen.lightprobe;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import org.lwjgl.opengl.*;
import org.lwjgl.system.MemoryUtil;
import org.lwjgl.system.MemoryStack;

/** Actual active uniforms and all defined sampled2D levels, read only. */
final class ResourceSnapshot {
    record Uniform(String name,int size,int type) {}
    static Uniform activeUniform(int program,int index) {
        try(var stack=MemoryStack.stackPush()) {
            var size=stack.mallocInt(1);var type=stack.mallocInt(1);
            return new Uniform(GL20.glGetActiveUniform(program,index,size,type),size.get(0),type.get(0));
        }
    }
    private static final int[] PACK={GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SKIP_ROWS,
        GL12.GL_PACK_IMAGE_HEIGHT,GL12.GL_PACK_SKIP_IMAGES,GL11.GL_PACK_SWAP_BYTES,GL11.GL_PACK_LSB_FIRST};
    private static int slots(int type) {
        return switch(type){case GL11.GL_FLOAT,GL11.GL_INT,GL20.GL_BOOL,GL20.GL_SAMPLER_2D,GL20.GL_SAMPLER_2D_SHADOW ->1;
            case GL20.GL_FLOAT_VEC2,GL20.GL_INT_VEC2,GL20.GL_BOOL_VEC2->2;case GL20.GL_FLOAT_VEC3,GL20.GL_INT_VEC3,GL20.GL_BOOL_VEC3->3;
            case GL20.GL_FLOAT_VEC4,GL20.GL_INT_VEC4,GL20.GL_BOOL_VEC4,GL20.GL_FLOAT_MAT2->4;case GL20.GL_FLOAT_MAT3->9;case GL20.GL_FLOAT_MAT4->16;
            default->throw new IllegalStateException("Unsupported active uniform type "+type);};
    }
    private static boolean floating(int t){return t==GL11.GL_FLOAT || t==GL20.GL_FLOAT_VEC2 || t==GL20.GL_FLOAT_VEC3 || t==GL20.GL_FLOAT_VEC4 || t==GL20.GL_FLOAT_MAT2 || t==GL20.GL_FLOAT_MAT3 || t==GL20.GL_FLOAT_MAT4;}
    static Map<String,Object> capture(int program,Path directory) throws Exception {
        if(ByteOrder.nativeOrder()!=ByteOrder.LITTLE_ENDIAN)throw new IllegalStateException("Little endian required");
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE),pbo=GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
        int[] pack=new int[PACK.length];for(int i=0;i<PACK.length;i++)pack[i]=GL11.glGetInteger(PACK[i]);
        var uniforms=new LinkedHashMap<String,Object>();var textures=new LinkedHashMap<String,Object>();var raw=new HashMap<Integer,Object>();
        long total=0;
        try {
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);for(int i=0;i<PACK.length;i++)GL11.glPixelStorei(PACK[i],i==0?1:0);
            int count=GL20.glGetProgrami(program,GL20.GL_ACTIVE_UNIFORMS);if(count<1 || count>512)throw new IllegalStateException("Active uniform count bounds");
            for(int i=0;i<count;i++) {
                var uniform=activeUniform(program,i);String name=uniform.name();int type=uniform.type();
                if(uniform.size()!=1)throw new IllegalStateException("Unsupported uniform array "+name);
                int loc=GL20.glGetUniformLocation(program,name),n=slots(type);var values=new ArrayList<Number>();
                if(floating(type)){float[] v=new float[n];GL20.glGetUniformfv(program,loc,v);for(float x:v){if(!Float.isFinite(x))throw new IllegalStateException("Nonfinite uniform");values.add(x);}}
                else {int[] v=new int[n];GL20.glGetUniformiv(program,loc,v);for(int x:v)values.add(x);}
                uniforms.put(name,Map.of("type",type,"values",List.copyOf(values)));
                if(type!=GL20.GL_SAMPLER_2D && type!=GL20.GL_SAMPLER_2D_SHADOW)continue;
                int unit=values.get(0).intValue();if(unit<0 || unit>=GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS))throw new IllegalStateException("Sampler unit bounds");
                GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);int id=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D),sampler=GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit);
                if(id<=0 || !GL11.glIsTexture(id))throw new IllegalStateException("Actual texture absent: "+name);
                var meta=new LinkedHashMap<String,Object>();meta.put("unit",unit);meta.put("textureID",id);meta.put("samplerObject",sampler);
                int base=GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_BASE_LEVEL),max=GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_MAX_LEVEL);
                if(base<0 || base>12 || max<base)throw new IllegalStateException("Texture level range unsupported");meta.put("baseLevel",base);meta.put("maxLevel",max);
                for(var e:Map.of("minFilter",GL11.GL_TEXTURE_MIN_FILTER,"magFilter",GL11.GL_TEXTURE_MAG_FILTER,"wrapS",GL11.GL_TEXTURE_WRAP_S,
                    "wrapT",GL11.GL_TEXTURE_WRAP_T,"compareMode",GL14.GL_TEXTURE_COMPARE_MODE,"compareFunc",GL14.GL_TEXTURE_COMPARE_FUNC).entrySet())
                    meta.put(e.getKey(),sampler==0?GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,e.getValue()):GL33.glGetSamplerParameteri(sampler,e.getValue()));
                for(var e:Map.of("minLOD",GL12.GL_TEXTURE_MIN_LOD,"maxLOD",GL12.GL_TEXTURE_MAX_LOD,"lodBias",GL14.GL_TEXTURE_LOD_BIAS).entrySet())
                    meta.put(e.getKey(),sampler==0?GL11.glGetTexParameterf(GL11.GL_TEXTURE_2D,e.getValue()):GL33.glGetSamplerParameterf(sampler,e.getValue()));
                meta.put("maxAnisotropy",GL.getCapabilities().GL_EXT_texture_filter_anisotropic ?
                    (sampler==0?GL11.glGetTexParameterf(GL11.GL_TEXTURE_2D,EXTTextureFilterAnisotropic.GL_TEXTURE_MAX_ANISOTROPY_EXT):GL33.glGetSamplerParameterf(sampler,EXTTextureFilterAnisotropic.GL_TEXTURE_MAX_ANISOTROPY_EXT)):1);
                if(!raw.containsKey(id)) {
                    var levels=new ArrayList<Object>();
                    for(int level=base;level<=Math.min(max,12);level++) {
                        int w=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,level,GL11.GL_TEXTURE_WIDTH),h=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,level,GL11.GL_TEXTURE_HEIGHT);
                        if(w==0 || h==0)break;if(w>4096 || h>4096 || w<0 || h<0)throw new IllegalStateException("Readback texture extent bounds");
                        int format=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,level,GL11.GL_TEXTURE_INTERNAL_FORMAT);
                        boolean depth=type==GL20.GL_SAMPLER_2D_SHADOW || format==GL11.GL_DEPTH_COMPONENT || format==GL14.GL_DEPTH_COMPONENT16
                            || format==GL14.GL_DEPTH_COMPONENT24 || format==GL14.GL_DEPTH_COMPONENT32 || format==GL30.GL_DEPTH_COMPONENT32F;
                        int channels=depth?1:4;
                        int bytes=Math.multiplyExact(Math.multiplyExact(w,h),channels*4);total+=bytes;if(total>256L*1024*1024)throw new IllegalStateException("Readback memory budget");
                        ByteBuffer data=MemoryUtil.memAlloc(bytes);
                        try {
                            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,level,depth?GL11.GL_DEPTH_COMPONENT:GL11.GL_RGBA,GL11.GL_FLOAT,data);
                            if(GL11.glGetError()!=GL11.GL_NO_ERROR)throw new IllegalStateException("Actual texture readback GL error");
                            var floats=data.order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();for(int p=0;p<floats.capacity();p++)if(!Float.isFinite(floats.get(p)))throw new IllegalStateException("Nonfinite actual sampled texture");
                            byte[] body=new byte[bytes];data.get(body);String file="texture-"+id+"-level-"+level+".f32";
                            Files.write(directory.resolve(file),body,StandardOpenOption.CREATE_NEW);
                            levels.add(Map.of("level",level,"width",w,"height",h,"channels",channels,"file",file,"SHA256",ReceiverLightProbe.sha(body),
                                "internalFormat",GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,level,GL11.GL_TEXTURE_INTERNAL_FORMAT)));
                        }finally{MemoryUtil.memFree(data);}
                    }
                    if(levels.isEmpty())throw new IllegalStateException("No defined sampled texture levels");raw.put(id,List.copyOf(levels));
                }
                meta.put("levels",raw.get(id));textures.put(name,meta);
            }
        }finally {
            GL13.glActiveTexture(active);GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,pbo);for(int i=0;i<PACK.length;i++)GL11.glPixelStorei(PACK[i],pack[i]);
        }
        if(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)!=active || GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING)!=pbo)throw new IllegalStateException("Readback state not restored");
        for(int i=0;i<PACK.length;i++)if(GL11.glGetInteger(PACK[i])!=pack[i])throw new IllegalStateException("Pixel pack state not restored");
        return Map.of("uniforms",uniforms,"textures",textures,"rawTextureBytes",total,"listedPackStateRestored",true,"textureDataModified",false);
    }
}
