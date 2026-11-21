package dev.aqualumen.atlasjoint;
import dev.aqualumen.atlas.FinalSnapshot;
import dev.aqualumen.bench.*;
import net.fabricmc.loader.api.FabricLoader;
import java.lang.reflect.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.IntSupplier;

/** Isolated TEST before/after the very same FINAL quad invocation. */
public final class JointObserver {
    private static final String WORLD_ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final Set<String> consumed=new HashSet<>();
    private static long lastPoll;
    private static Pending pending;
    private record Pending(Path game,Properties config,String id,Map<String,Object> result,
        int program,int frame,int fbo,int texture,List<OutputSnapshot.Pixel> outputPixels) {}
    private static boolean scope(Path game,Properties config)throws Exception {
        return game.getParent()!=null&&"Aqualumen Lab".equals(game.getParent().getFileName().toString())
            &&regular(game.resolve("config/aqualumen-benchmark.enabled"))&&ShoreRuntimeObserver.acceptsConfiguration(config)
            &&config.getProperty("expected_pack","").matches("Aqualumen-ShoreProbe-world-gh-phase-(0|45)-diagnostic-aligned-v2\\.zip")
            &&ShoreRuntimeObserver.acceptsScope(BathymetrySnapshot.inspectScope(game,config));
    }
    public static void before(Object renderer) {
        pending=null;long now=System.nanoTime();if(consumed.size()>=8||now-lastPoll<1_000_000_000L)return;lastPoll=now;
        try {
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            Properties config=properties(game.resolve("config/aqualumen-benchmark.properties"));
            Path requestPath=game.resolve("config/aqualumen-atlas-joint-observe.properties");if(!regular(requestPath)||!scope(game,config))return;
            Properties request=properties(requestPath);String id=request.getProperty("request_id","");
            if(!UUID.fromString(id).toString().equals(id)||!WORLD_ID.equals(request.getProperty("world_id"))||consumed.contains(id))return;
            Field state=Class.forName("dev.aqualumen.bench.Recorder").getDeclaredField("state");state.setAccessible(true);
            if(!List.of("idle","complete","aborted").contains(state.get(null)))return;
            List<ShoreSamplerSnapshot.Texel> local=ShoreRuntimeObserver.parseTexels(request.getProperty("local_pixels"),400,450);
            Path out=game.resolve("aqualumen-benchmark/atlas-joint-observations");
            if(Files.isSymbolicLink(out)||Files.isSymbolicLink(out.getParent())||Files.exists(out.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS))return;
            consumed.add(id);int program=expectedProgram(renderer),frame=frame(),fbo=integer(36006),texture=clientColorTexture();
            Map<String,Object> r=new LinkedHashMap<>();r.put("schema","aqualumen-atlas-joint-output-v1");
            r.put("observerVersion","0.1.3");r.put("requestId",id);r.put("kind",request.getProperty("kind","alignment"));
            r.put("world", "AqualumenNaturalV2");r.put("worldId",WORLD_ID);r.put("seed",308060);r.put("dimension","minecraft:overworld");
            r.put("scopeAuthorized",true);r.put("packName",config.getProperty("expected_pack"));r.put("packSha256",config.getProperty("expected_pack_sha256"));
            r.put("beforeFrame",frame);r.put("program",program);r.put("utc",java.time.Instant.now().toString());
            r.put("seam","before and after ordinal0 actual FINAL renderQuad, after Program.use/custom uniforms, before UI");
            r.put("physicalAccepted",false);r.put("visualAccepted",false);r.put("timingAcceptanceExcluded",true);
            r.put("producerSameInvocationDeclaredNotDirectlyObserved",true);
            r.put("directShaderLocalAddressReadbackObserved",false);
            FinalSnapshot.Boundary fb=(FinalSnapshot.Boundary)construct("dev.aqualumen.atlas.FinalObserver$RealBoundary");
            Map<String,Object> finalSource=FinalSnapshot.capture(program,fb);r.put("final",finalSource);
            List<ShoreSamplerSnapshot.Texel> source=new ArrayList<>(),neighbors=new ArrayList<>();
            List<Map<String,Object>> addresses=new ArrayList<>();List<OutputSnapshot.Pixel> output=new ArrayList<>();
            for(ShoreSamplerSnapshot.Texel p:local) {
                int x=4*p.x()+2,y=2*p.y()+1;source.add(new ShoreSamplerSnapshot.Texel(x,y));
                addresses.add(Map.of("localX",p.x(),"localY",p.y(),"sourceX",x,"sourceY",y));
                neighbors.add(new ShoreSamplerSnapshot.Texel(x,y));neighbors.add(new ShoreSamplerSnapshot.Texel(x,Math.min(899,y+1)));
                neighbors.add(new ShoreSamplerSnapshot.Texel(x,Math.max(0,y-1)));neighbors.add(new ShoreSamplerSnapshot.Texel(Math.min(1599,x+1),y));
                neighbors.add(new ShoreSamplerSnapshot.Texel(Math.max(0,x-1),y));
                for(int tile=0;tile<8;tile++)output.add(new OutputSnapshot.Pixel(p.x()+400*(tile%4),p.y()+450*(tile/4)));
            }
            r.put("addressDerivation","canonical aligned integer main; these are calculated addresses, not shader-local readback");r.put("addresses",addresses);
            ShoreSamplerSnapshot.SystemBoundary sb=(ShoreSamplerSnapshot.SystemBoundary)construct("dev.aqualumen.bench.ShoreRuntimeObserver$RealGlBoundary");
            Map<String,Object> raw=ShoreSamplerSnapshot.capture(program,1600,900,source,sb);
            if(raw.get("samplers") instanceof List<?> list)for(Object item:list)if(item instanceof Map<?,?> m)m.remove("rawRgba32f");
            r.put("raw",raw);r.put("c0",captureC0(sb,program,neighbors));
            r.put("transportUniforms",transport(sb,program));
            Field metadata=sb.getClass().getDeclaredField("metadata");metadata.setAccessible(true);r.put("samplerMetadata",metadata.get(sb));
            if(frame()!=frame||integer(35725)!=program||integer(36006)!=fbo)throw new IllegalStateException("before changed");
            pending=new Pending(game,config,id,r,program,frame,fbo,texture,output);
        }catch(Exception|LinkageError e){System.err.println("[DEBUG-atlas-joint] before unavailable: "+rootClass(e));}
    }
    public static void after(Object renderer) {
        Pending p=pending;pending=null;if(p==null)return;
        try {
            if(!scope(p.game(),p.config())){p.result().put("available",false);p.result().put("reason","scope_changed_after_quad");}
            else {
                Map<String,Object> output=OutputSnapshot.capture(p.program(),p.frame(),p.fbo(),p.texture(),p.outputPixels(),new RealOutput());
                p.result().put("output",output);p.result().put("afterFrame",frame());
                boolean ready=Boolean.TRUE.equals(output.get("available"))
                    &&Boolean.TRUE.equals(((Map<?,?>)p.result().get("final")).get("available"))
                    &&Boolean.TRUE.equals(((Map<?,?>)p.result().get("raw")).get("available"))
                    &&Boolean.TRUE.equals(((Map<?,?>)p.result().get("c0")).get("available"));
                p.result().put("available",ready);p.result().put("quadInvocationReturnedObserved",true);
            }
            Path out=p.game().resolve("aqualumen-benchmark/atlas-joint-observations");Files.createDirectories(out);
            Files.writeString(out.resolve(p.id()+".json"),json(p.result())+"\n",StandardOpenOption.CREATE_NEW);
        }catch(Exception|LinkageError e){System.err.println("[DEBUG-atlas-joint] after unavailable: "+rootClass(e));}
    }
    private static Map<String,Object> captureC0(ShoreSamplerSnapshot.SystemBoundary b,int program,List<ShoreSamplerSnapshot.Texel> pixels)throws Exception {
        ShoreSamplerSnapshot.State saved=b.save();Map<String,Object> r=new LinkedHashMap<>();r.put("available",false);
        try {
            ShoreSamplerSnapshot.Uniform u=b.uniform(program,"colortex0");
            if(u==null||u.type()!=35678||u.size()!=1||u.unit()<0||u.unit()>=b.maximumTextureUnits())throw new IllegalStateException("C0 uniform");
            b.selectUnit(u.unit());ShoreSamplerSnapshot.Texture t=b.texture();
            if(t==null||!t.exists()||t.format()!=34836||t.width()!=1600||t.height()!=900)throw new IllegalStateException("C0 storage");
            float[] raw=b.readTexels(t,pixels);List<Map<String,Object>> samples=new ArrayList<>();
            if(raw.length!=pixels.size()*4)throw new IllegalStateException();
            for(int i=0;i<pixels.size();i++)samples.add(Map.of("x",pixels.get(i).x(),"y",pixels.get(i).y(),"rgba",numbers(raw,i*4,4)));
            r.put("unit",u.unit());r.put("textureId",t.id());r.put("actualFormat",t.format());r.put("width",t.width());r.put("height",t.height());
            r.put("samples",samples);r.put("available",true);
        }finally{b.restore(saved);boolean restored=saved.equals(b.save());r.put("stateRestored",restored);if(!restored)r.put("available",false);}
        return r;
    }
    private static Map<String,Object> transport(ShoreSamplerSnapshot.SystemBoundary b,int program)throws Exception {
        Map<String,Object> r=new LinkedHashMap<>();
        for(String name:List.of("gbufferModelViewInverse","sunPosition")) {
            ShoreSamplerSnapshot.Uniform u=b.uniform(program,name);int type=name.equals("sunPosition")?35665:35676;
            int size=name.equals("sunPosition")?3:16;
            if(u==null||u.type()!=type||u.size()!=1||u.values()==null||u.values().length!=size)throw new IllegalStateException("transport uniform");
            r.put(name,Map.of("type",type,"size",1,"values",numbers(u.values(),0,size)));
        }
        int loc=(int)gl("GL20C","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,"aqualumenDimension");
        if(loc<0)throw new IllegalStateException();r.put("aqualumenDimension",gl("GL20C","glGetUniformi",new Class<?>[]{int.class,int.class},program,loc));
        return r;
    }
    private static final class RealOutput implements OutputSnapshot.Boundary {
        private final Map<String,Object> metadata=new LinkedHashMap<>();
        public Map<String,Object> readMetadata(){return metadata;}
        public OutputSnapshot.State state()throws Exception{return new OutputSnapshot.State(integer(36010),integer(3074),integer(35053),
            integer(3333),integer(3330),integer(32876),integer(3332),integer(3331),integer(32875),integer(3328),integer(3329));}
        public int program()throws Exception{return integer(35725);}
        public int frame()throws Exception{return JointObserver.frame();}
        public int[] viewport()throws Exception{IntBuffer b=ints(4);gl("GL11C","glGetIntegerv",new Class<?>[]{int.class,IntBuffer.class},2978,b);return new int[]{b.get(0),b.get(1),b.get(2),b.get(3)};}
        public int drawFbo()throws Exception{return integer(36006);}
        public int outputTexture()throws Exception {
            if(attachment(36048)!=5890)throw new IllegalStateException("not a texture attachment");return attachment(36049);
        }
        public int colorEncoding()throws Exception{return attachment(33296);}
        public boolean srgbEnabled()throws Exception{return (boolean)gl("GL11C","glIsEnabled",new Class<?>[]{int.class},36281);}
        public float[] read(int fbo,List<OutputSnapshot.Pixel> points)throws Exception {
            int binding=integer(32873),active=integer(34016),texture=outputTexture();
            try {
                gl("GL11C","glBindTexture",new Class<?>[]{int.class,int.class},3553,texture);
                for(var entry:Map.of("width",4096,"height",4097,"internalFormat",4099).entrySet())
                    metadata.put(entry.getKey(),gl("GL11C","glGetTexLevelParameteri",new Class<?>[]{int.class,int.class,int.class},3553,0,entry.getValue()));
            }finally {
                gl("GL11C","glBindTexture",new Class<?>[]{int.class,int.class},3553,binding);
                boolean unchanged=integer(32873)==binding&&integer(34016)==active;
                metadata.put("textureQueryBindingAndActiveRestored",unchanged);
                if(!unchanged)throw new IllegalStateException("output storage query restore");
            }
            if(!metadata.get("width").equals(1600)||!metadata.get("height").equals(900)
                ||!metadata.get("internalFormat").equals(32856))throw new IllegalStateException("unsupported output storage");
            gl("GL30C","glBindFramebuffer",new Class<?>[]{int.class,int.class},36008,fbo);
            int targetReadBuffer=integer(3074);metadata.put("targetReadBufferBefore",targetReadBuffer);
            try {
            gl("GL11C","glReadBuffer",new Class<?>[]{int.class},36064);
            if((int)gl("GL30C","glCheckFramebufferStatus",new Class<?>[]{int.class},36008)!=36053)throw new IllegalStateException("incomplete read framebuffer");
            gl("GL15C","glBindBuffer",new Class<?>[]{int.class,int.class},35051,0);
            for(int key:new int[]{3330,32876,3332,3331,32875,3328,3329})pixelStore(key,0);pixelStore(3333,4);
            float[] out=new float[points.size()*4];FloatBuffer values=floats(4);
            for(int i=0;i<points.size();i++) {
                values.clear();for(int c=0;c<4;c++)values.put(c,Float.NaN);OutputSnapshot.Pixel p=points.get(i);
                gl("GL11C","glReadPixels",new Class<?>[]{int.class,int.class,int.class,int.class,int.class,int.class,FloatBuffer.class},p.x(),p.y(),1,1,6408,5126,values);
                for(int c=0;c<4;c++)out[i*4+c]=values.get(c);
            }return out;
            } finally {
                // Read-buffer selection belongs to its FBO, not global state.
                // Restore the target selection before restoring the caller's FBO.
                gl("GL11C","glReadBuffer",new Class<?>[]{int.class},targetReadBuffer);
                metadata.put("targetReadBufferAfter",integer(3074));
                if(integer(3074)!=targetReadBuffer)throw new IllegalStateException("target read-buffer restoration");
            }
        }
        public void restore(OutputSnapshot.State s)throws Exception {
            gl("GL30C","glBindFramebuffer",new Class<?>[]{int.class,int.class},36008,s.readFbo());gl("GL11C","glReadBuffer",new Class<?>[]{int.class},s.readBuffer());
            gl("GL15C","glBindBuffer",new Class<?>[]{int.class,int.class},35051,s.packBuffer());
            int[] keys={3333,3330,32876,3332,3331,32875,3328,3329};int[] values={s.alignment(),s.rowLength(),s.imageHeight(),s.skipPixels(),s.skipRows(),s.skipImages(),s.swap(),s.lsb()};
            for(int i=0;i<keys.length;i++)pixelStore(keys[i],values[i]);
        }
    }
    private static int attachment(int key)throws Exception{return (int)gl("GL30C","glGetFramebufferAttachmentParameteri",new Class<?>[]{int.class,int.class,int.class},36009,36064,key);}
    private static int clientColorTexture()throws Exception {
        Class<?> mc=Class.forName("net.minecraft.class_310");Object client=mc.getMethod("method_1551").invoke(null);
        Object target=mc.getMethod("method_1522").invoke(client);return (int)Class.forName("net.minecraft.class_276").getMethod("method_30277").invoke(target);
    }
    private static int expectedProgram(Object renderer)throws Exception {
        Field pass=renderer.getClass().getDeclaredField("finalPass");pass.setAccessible(true);Object p=pass.get(renderer);
        Field program=p.getClass().getDeclaredField("program");program.setAccessible(true);Object shader=program.get(p);
        return (int)shader.getClass().getMethod("getProgramId").invoke(shader);
    }
    private static Object construct(String name)throws Exception{Constructor<?> c=Class.forName(name).getDeclaredConstructor();c.setAccessible(true);return c.newInstance();}
    private static int frame()throws Exception{return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();}
    private static int integer(int key)throws Exception{return (int)gl("GL11C","glGetInteger",new Class<?>[]{int.class},key);}
    private static Object gl(String cls,String name,Class<?>[] types,Object... values)throws Exception{return Class.forName("org.lwjgl.opengl."+cls).getMethod(name,types).invoke(null,values);}
    private static void pixelStore(int key,int value)throws Exception{gl("GL11C","glPixelStorei",new Class<?>[]{int.class,int.class},key,value);}
    private static IntBuffer ints(int n){return ByteBuffer.allocateDirect(n*4).order(ByteOrder.nativeOrder()).asIntBuffer();}
    private static FloatBuffer floats(int n){return ByteBuffer.allocateDirect(n*4).order(ByteOrder.nativeOrder()).asFloatBuffer();}
    private static boolean regular(Path p){return Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS);}
    private static Properties properties(Path p)throws Exception{if(!regular(p)||Files.size(p)>16384)throw new IllegalArgumentException();Properties r=new Properties();try(var in=Files.newInputStream(p,LinkOption.NOFOLLOW_LINKS)){r.load(in);}return r;}
    private static List<Double> numbers(float[] data,int offset,int size){List<Double> r=new ArrayList<>();for(int i=offset;i<offset+size;i++){if(!Float.isFinite(data[i]))throw new IllegalArgumentException();r.add((double)data[i]);}return r;}
    private static String rootClass(Throwable e){while(e instanceof InvocationTargetException t&&t.getCause()!=null)e=t.getCause();return e.getClass().getSimpleName();}
    private static String json(Object v){if(v==null)return "null";if(v instanceof Number||v instanceof Boolean)return v.toString();if(v instanceof Map<?,?> m){StringJoiner j=new StringJoiner(",","{","}");for(var e:m.entrySet())j.add(json(e.getKey())+":"+json(e.getValue()));return j.toString();}if(v instanceof Iterable<?> a){StringJoiner j=new StringJoiner(",","[","]");for(Object e:a)j.add(json(e));return j.toString();}StringBuilder s=new StringBuilder("\"");for(char c:v.toString().toCharArray())switch(c){case '"'->s.append("\\\"");case '\\'->s.append("\\\\");case '\n'->s.append("\\n");case '\r'->s.append("\\r");case '\t'->s.append("\\t");default->{if(c<32)s.append(String.format("\\u%04x",(int)c));else s.append(c);}}return s.append('"').toString();}
}
