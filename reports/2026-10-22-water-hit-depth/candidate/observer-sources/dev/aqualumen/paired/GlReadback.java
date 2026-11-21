package dev.aqualumen.paired;

import java.lang.reflect.*;
import java.nio.*;
import java.util.*;

/** Reads existing resources without creating GL objects or consuming error flags. */
public final class GlReadback {
    private static final int[] PACK_KEYS={3333,3330,32876,3332,3331,32875,3328,3329};
    public record State(int active,int binding,int readFbo,int readBuffer,int packBuffer,List<Integer> pack) {}
    public interface Boundary {
        State state()throws Exception;
        void restore(State state)throws Exception;
    }
    public interface Read<T> { T run()throws Exception; }
    public static <T> T preserving(Boundary b,Read<T> read)throws Exception {
        State saved=b.state();
        try{return read.run();}
        finally {
            b.restore(saved);
            if(!saved.equals(b.state()))throw new IllegalStateException("GL read state restoration failed");
        }
    }
    public static final Boundary REAL=new Boundary() {
        public State state()throws Exception {
            List<Integer> pack=new ArrayList<>();for(int k:PACK_KEYS)pack.add(integer(k));
            return new State(integer(34016),integer(32873),integer(36010),integer(3074),integer(35053),List.copyOf(pack));
        }
        public void restore(State s)throws Exception {
            active(s.active());bindTexture(s.binding());
            gl("GL30C","glBindFramebuffer",new Class<?>[]{int.class,int.class},36008,s.readFbo());
            gl("GL11C","glReadBuffer",new Class<?>[]{int.class},s.readBuffer());
            gl("GL15C","glBindBuffer",new Class<?>[]{int.class,int.class},35051,s.packBuffer());
            for(int i=0;i<PACK_KEYS.length;i++)store(PACK_KEYS[i],s.pack().get(i));
        }
    };
    public static Map<String,Object> sampler(int program,String name,int w,int h)throws Exception {
        int unit=uniform(program,name,35678);
        if(unit<0||unit>=integer(35661))throw new IllegalStateException("sampler unit");
        return preserving(REAL,()->{
            active(33984+unit);int texture=integer(32873);
            if(texture<=0||!(boolean)gl("GL11C","glIsTexture",new Class<?>[]{int.class},texture))
                throw new IllegalStateException("missing bound texture");
            int width=level(4096),height=level(4097),format=level(4099);
            if(width!=w||height!=h||format!=34836||parameter(33084)!=0)
                throw new IllegalStateException("unsupported bound sampler storage/base "+name+" "+width+"x"+height+" format="+format+" base="+parameter(33084));
            Map<String,Object> out=new LinkedHashMap<>();out.put("name",name);out.put("unit",unit);out.put("texture",texture);
            out.put("width",width);out.put("height",height);out.put("format",format);out.put("baseLevel",parameter(33084));
            out.put("maxLevel",parameter(33085));out.put("minFilter",parameter(10241));out.put("magFilter",parameter(10240));
            out.put("wrapS",parameter(10242));out.put("wrapT",parameter(10243));
            int sampler=(int)gl("GL30C","glGetIntegeri",new Class<?>[]{int.class,int.class},35097,unit);
            out.put("samplerObject",sampler);
            for(var e:Map.of("effectiveMinFilter",10241,"effectiveMagFilter",10240,"effectiveWrapS",10242,"effectiveWrapT",10243).entrySet())
                out.put(e.getKey(),sampler==0?parameter(e.getValue()):gl("GL33C","glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,e.getValue()));
            return out;
        });
    }
    public static Map<String,Object> depthSampler(int program,String name,int w,int h)throws Exception {
        int unit=uniform(program,name,35678);
        if(unit<0||unit>=integer(35661))throw new IllegalStateException("depth sampler unit");
        return preserving(REAL,()->{
            active(33984+unit);int texture=integer(32873);
            if(texture<=0||!(boolean)gl("GL11C","glIsTexture",new Class<?>[]{int.class},texture))
                throw new IllegalStateException("missing bound depth texture");
            int width=level(4096),height=level(4097),format=level(4099);
            if(width!=w||height!=h||!Set.of(33190,36012,35056,36013).contains(format)||parameter(33084)!=0)
                throw new IllegalStateException("unsupported depth sampler storage/base "+name+" "+width+"x"+height+" format="+format+" base="+parameter(33084));
            int sampler=(int)gl("GL30C","glGetIntegeri",new Class<?>[]{int.class,int.class},35097,unit);
            int compare=parameter(34892);
            int effectiveCompare=sampler==0?compare:(int)gl("GL33C","glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,34892);
            if(compare!=0||effectiveCompare!=0)throw new IllegalStateException("depth comparison mode must be NONE");
            Map<String,Object> out=new LinkedHashMap<>();out.put("name",name);out.put("unit",unit);out.put("texture",texture);
            out.put("width",width);out.put("height",height);out.put("format",format);out.put("baseLevel",parameter(33084));
            out.put("maxLevel",parameter(33085));out.put("minFilter",parameter(10241));out.put("magFilter",parameter(10240));
            out.put("wrapS",parameter(10242));out.put("wrapT",parameter(10243));out.put("samplerObject",sampler);
            out.put("compareMode",compare);out.put("effectiveCompareMode",effectiveCompare);
            for(var e:Map.of("effectiveMinFilter",10241,"effectiveMagFilter",10240,"effectiveWrapS",10242,"effectiveWrapT",10243).entrySet())
                out.put(e.getKey(),sampler==0?parameter(e.getValue()):gl("GL33C","glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,e.getValue()));
            return out;
        });
    }
    public static FloatBuffer rawDepth(Map<String,Object> sampler,int w,int h)throws Exception {
        return preserving(REAL,()->{
            active(33984+(int)sampler.get("unit"));
            if(integer(32873)!=(int)sampler.get("texture"))throw new IllegalStateException("depth binding changed");
            cleanPack();FloatBuffer data=poison(Math.multiplyExact(w,h));
            gl("GL11C","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},3553,0,6402,5126,data);
            for(int i=0;i<data.capacity();i++) {
                float value=data.get(i);
                if(!Float.isFinite(value)||value<0.0f||value>1.0f)throw new IllegalStateException("nonfinite, unwritten or out-of-range depth component");
            }
            return data;
        });
    }
    public static int uniform(int program,String name,int requiredType)throws Exception {
        int location=(int)gl("GL20C","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
        if(location<0)throw new IllegalStateException("inactive required uniform "+name);
        int count=(int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},program,35718);
        if(count<1||count>4096)throw new IllegalStateException("uniform count");
        IntBuffer size=ints(1),type=ints(1);
        for(int i=0;i<count;i++) {
            String found=(String)gl("GL20C","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
            if(name.equals(found)) {
                if(size.get(0)!=1||type.get(0)!=requiredType)throw new IllegalStateException("required uniform type "+name);
                return (int)gl("GL20C","glGetUniformi",new Class<?>[]{int.class,int.class},program,location);
            }
        }
        throw new IllegalStateException("required active uniform absent "+name);
    }
    public static FloatBuffer diagnostic(Map<String,Object> sampler,int w,int h)throws Exception {
        return preserving(REAL,()->{
            active(33984+(int)sampler.get("unit"));
            if(integer(32873)!=(int)sampler.get("texture"))throw new IllegalStateException("diagnostic binding changed");
            cleanPack();FloatBuffer data=poison(w*h*4);
            gl("GL11C","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},3553,0,6408,5126,data);
            CaptureRules.diagnostics(data,w,h);return data;
        });
    }
    public static FloatBuffer rawFloats(Map<String,Object> sampler,int w,int h)throws Exception {
        return preserving(REAL,()->{
            active(33984+(int)sampler.get("unit"));
            if(integer(32873)!=(int)sampler.get("texture"))throw new IllegalStateException("optical binding changed");
            cleanPack();FloatBuffer data=poison(Math.multiplyExact(Math.multiplyExact(w,h),4));
            gl("GL11C","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},3553,0,6408,5126,data);
            for(int i=0;i<data.capacity();i++)if(!Float.isFinite(data.get(i)))throw new IllegalStateException("nonfinite or unwritten optical component");
            return data;
        });
    }
    public static FloatBuffer beauty(int fbo,int texture,int w,int h)throws Exception {
        return preserving(REAL,()->{
            if(integer(36006)!=fbo||attachment(36049)!=texture||attachment(36048)!=5890
                ||attachment(36050)!=0||attachment(33296)!=9729
                ||(boolean)gl("GL11C","glIsEnabled",new Class<?>[]{int.class},36281))
                throw new IllegalStateException("unsupported final output identity/conversion");
            bindTexture(texture);
            if(level(4096)!=w||level(4097)!=h||level(4099)!=32856)throw new IllegalStateException("final output must be RGBA8");
            gl("GL30C","glBindFramebuffer",new Class<?>[]{int.class,int.class},36008,fbo);
            int targetReadBuffer=integer(3074);
            try {
                gl("GL11C","glReadBuffer",new Class<?>[]{int.class},36064);
                if((int)gl("GL30C","glCheckFramebufferStatus",new Class<?>[]{int.class},36008)!=36053)
                    throw new IllegalStateException("incomplete final read FBO");
                cleanPack();FloatBuffer data=poison(w*h*4);
                gl("GL11C","glReadPixels",new Class<?>[]{int.class,int.class,int.class,int.class,int.class,int.class,FloatBuffer.class},0,0,w,h,6408,5126,data);
                CaptureRules.rgba8(data,w,h);return data;
            }finally {
                // GL_READ_BUFFER belongs to its framebuffer, not to the binding point.
                gl("GL11C","glReadBuffer",new Class<?>[]{int.class},targetReadBuffer);
                if(integer(3074)!=targetReadBuffer)throw new IllegalStateException("target read-buffer restoration");
            }
        });
    }
    private static FloatBuffer poison(int n) {
        FloatBuffer data=ByteBuffer.allocateDirect(n*4).order(ByteOrder.nativeOrder()).asFloatBuffer();
        for(int i=0;i<n;i++)data.put(i,Float.NaN);return data;
    }
    private static void cleanPack()throws Exception {
        gl("GL15C","glBindBuffer",new Class<?>[]{int.class,int.class},35051,0);
        for(int k:PACK_KEYS)store(k,k==3333?4:0);
    }
    public static int[] viewport()throws Exception {
        IntBuffer b=ints(4);gl("GL11C","glGetIntegerv",new Class<?>[]{int.class,IntBuffer.class},2978,b);
        return new int[]{b.get(0),b.get(1),b.get(2),b.get(3)};
    }
    public static int attachment(int key)throws Exception {
        return (int)gl("GL30C","glGetFramebufferAttachmentParameteri",new Class<?>[]{int.class,int.class,int.class},36009,36064,key);
    }
    private static void store(int key,int value)throws Exception {gl("GL11C","glPixelStorei",new Class<?>[]{int.class,int.class},key,value);}
    private static int parameter(int key)throws Exception {return (int)gl("GL11C","glGetTexParameteri",new Class<?>[]{int.class,int.class},3553,key);}
    private static int level(int key)throws Exception {return (int)gl("GL11C","glGetTexLevelParameteri",new Class<?>[]{int.class,int.class,int.class},3553,0,key);}
    private static void active(int unit)throws Exception {gl("GL13C","glActiveTexture",new Class<?>[]{int.class},unit);}
    private static void bindTexture(int texture)throws Exception {gl("GL11C","glBindTexture",new Class<?>[]{int.class,int.class},3553,texture);}
    private static IntBuffer ints(int n){return ByteBuffer.allocateDirect(n*4).order(ByteOrder.nativeOrder()).asIntBuffer();}
    public static int integer(int key)throws Exception {return (int)gl("GL11C","glGetInteger",new Class<?>[]{int.class},key);}
    public static Object gl(String cls,String name,Class<?>[] types,Object... values)throws Exception {
        try{return Class.forName("org.lwjgl.opengl."+cls).getMethod(name,types).invoke(null,values);}
        catch(InvocationTargetException e){if(e.getCause() instanceof Exception cause)throw cause;throw e;}
    }
}
