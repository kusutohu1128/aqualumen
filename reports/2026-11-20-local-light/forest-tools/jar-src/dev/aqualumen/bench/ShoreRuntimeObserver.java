package dev.aqualumen.bench;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.UUID;
import java.util.function.IntSupplier;
import net.fabricmc.loader.api.FabricLoader;

/** TEST-only, one-shot observation of the actual FINAL program's bound inputs.
 * No GL call is allowed until the existing exact-world/pack/Mod scope accepts.
 * The GL 3.2 adapter only selects already assigned units and normalizes PACK
 * state; it never binds textures, samplers, programs or framebuffers, creates
 * GL objects, uploads data, or consumes the caller's GL error flags.
 */
public final class ShoreRuntimeObserver {
    private static final String WORLD="AqualumenNaturalV2";
    private static final String WORLD_ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final int MAX_WIDTH=2560,MAX_HEIGHT=1440,MAX_REQUESTS=8;
    private static final Set<String> completedRequests=new HashSet<>();
    private static long lastPoll;
    // Only the render thread uses this bounded buffer. Reuse across all source
    // targets and requests instead of retaining one full image per sampler.
    private static FloatBuffer scratch;
    private ShoreRuntimeObserver() {}

    /** Pure guards are public for CPU tests; their success is not GL evidence. */
    public static boolean acceptsScope(BathymetrySnapshot.Scope scope) {
        return scope!=null&&scope.enabled()&&scope.integrated()&&!scope.lan()
                &&scope.players()==1&&scope.localCamera()&&WORLD.equals(scope.world())
                &&WORLD_ID.equals(scope.worldId())&&scope.seed()==308060
                &&"minecraft:overworld".equals(scope.dimension())
                &&scope.expectedPack()&&scope.candidateMod();
    }
    public static boolean acceptsConfiguration(Properties config) {
        return config!=null&&"2".equals(config.getProperty("schema"))
                &&WORLD.equals(config.getProperty("world"))&&WORLD_ID.equals(config.getProperty("world_id"))
                &&config.getProperty("expected_pack","").matches("Aqualumen-ShoreProbe-world-[A-Za-z0-9][A-Za-z0-9._-]*\\.zip")
                &&config.getProperty("expected_pack_sha256","").matches("[0-9a-f]{64}");
    }
    public static List<ShoreSamplerSnapshot.Texel> parseTexels(String pixels,int width,int height) {
        if(width<=0||height<=0||width>MAX_WIDTH||height>MAX_HEIGHT||pixels==null||pixels.isBlank())
            throw new IllegalArgumentException("Invalid bounded texel request");
        String[] tokens=pixels.split(",",-1);
        if(tokens.length>16)throw new IllegalArgumentException("Too many selected texels");
        List<ShoreSamplerSnapshot.Texel> result=new ArrayList<>();
        Set<ShoreSamplerSnapshot.Texel> unique=new HashSet<>();
        for(String token:tokens) {
            String text=token.trim();
            if(!text.matches("[0-9]{1,5}:[0-9]{1,5}"))throw new IllegalArgumentException("Invalid texel coordinate");
            String[] coordinate=text.split(":");
            ShoreSamplerSnapshot.Texel point=new ShoreSamplerSnapshot.Texel(
                    Integer.parseInt(coordinate[0]),Integer.parseInt(coordinate[1]));
            if(point.x()>=width||point.y()>=height||!unique.add(point))
                throw new IllegalArgumentException("Out-of-range or repeated texel");
            result.add(point);
        }
        return List.copyOf(result);
    }

    /** Called only before the pinned FINAL renderQuad invocation, never HEAD. */
    public static void beforeFinalQuad(Object renderer) {
        if(completedRequests.size()>=MAX_REQUESTS)return;
        long now=System.nanoTime();
        if(lastPoll!=0&&now-lastPoll<1_000_000_000L)return;
        lastPoll=now;
        boolean scoped=false;
        Path output=null;
        String id=null;
        Map<String,Object> result=new LinkedHashMap<>();
        try {
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(game.getParent()==null||!"Aqualumen Lab".equals(game.getParent().getFileName().toString()))return;
            Path marker=game.resolve("config/aqualumen-benchmark.enabled");
            Path configPath=game.resolve("config/aqualumen-benchmark.properties");
            Path requestPath=game.resolve("config/aqualumen-shore-observe.properties");
            if(!regular(marker)||!regular(configPath)||!regular(requestPath))return;
            Properties config=properties(configPath),request=properties(requestPath);
            if(!acceptsConfiguration(config)||!WORLD_ID.equals(request.getProperty("world_id")))return;
            id=request.getProperty("request_id","");
            if(!UUID.fromString(id).toString().equals(id)||completedRequests.contains(id))return;
            if(!acceptsScope(BathymetrySnapshot.inspectScope(game,config)))return;
            // Everything above, including the reused real scope boundary, is
            // CPU/filesystem-only. Ordinary worlds never reach OpenGL queries.
            scoped=true;
            Path parent=game.resolve("aqualumen-benchmark");
            Path destination=parent.resolve("shore-observations");
            if(Files.isSymbolicLink(parent)||Files.isSymbolicLink(destination))return;
            output=destination;
            completedRequests.add(id); // Consume authorized attempts, including failures.
            if(Files.exists(output.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS))return;
            result.put("available",false);result.put("stateRestored",false);
            result.put("scopeAuthorized",true);result.put("requestId",id);result.put("worldId",WORLD_ID);
            result.put("world",WORLD);result.put("seed",308060);result.put("dimension","minecraft:overworld");
            result.put("packName",config.getProperty("expected_pack"));
            result.put("packSha256",config.getProperty("expected_pack_sha256"));
            result.put("observerVersion",FabricLoader.getInstance().getModContainer("aqualumen_benchmark")
                    .map(mod->mod.getMetadata().getVersion().getFriendlyString()).orElse("unavailable"));
            result.put("utc",Instant.now().toString());result.put("tag","DEBUG-shore-runtime");
            result.put("seam","FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push");
            result.put("maximumRequestsPerJvm",MAX_REQUESTS);result.put("minimumRequestIntervalSeconds",1);
            result.put("timingAcceptanceExcluded",true);result.put("visualQualityAccepted",false);
            result.put("reason","final_identity_or_capture_request_unavailable");
            int expected=expectedProgram(renderer);
            int[] extent=framebufferExtent();
            int width=extent[0],height=extent[1];
            if(width<=0||height<=0||width>MAX_WIDTH||height>MAX_HEIGHT)
                throw new IllegalStateException("Framebuffer exceeds bounded observation extent");
            for(String axis:new String[]{"width","height"}) {
                String requested=request.getProperty(axis);
                if(requested!=null&&Integer.parseInt(requested)!=(axis.equals("width")?width:height))
                    throw new IllegalArgumentException("Requested framebuffer extent does not match");
            }
            List<ShoreSamplerSnapshot.Texel> texels=parseTexels(request.getProperty("pixels"),width,height);
            int frame=frame();
            result.put("snapshotFrame",frame);result.put("frameTimeCounter",frameTime());
            result.put("unshiftedCameraPosition",camera());
            result.put("cameraCoordinateConvention","actual GameRenderer camera, absolute/unshifted; not the shader's shifted cameraPosition");
            RealGlBoundary boundary=new RealGlBoundary();
            result.remove("reason");
            result.putAll(ShoreSamplerSnapshot.capture(expected,width,height,texels,boundary));
            Object sources=result.get("samplers");
            if(sources instanceof List<?> list)for(Object source:list)
                if(source instanceof Map<?,?> map)map.remove("rawRgba32f");
            result.put("samplerMetadata",boundary.metadata);
            result.put("rawReadPolicy","GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported");
            result.put("samplingInterpretation","unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values");
            result.put("selectedTexelsFiniteOnly",true);
            if(frame()!=frame) {
                result.put("available",false);result.put("reason","frame_changed_during_observation");
            }
        } catch(Exception|LinkageError error) {
            if(!scoped)return;
            result.put("available",false);result.put("errorClass",errorClass(error));
        }
        if(scoped&&output!=null&&id!=null)try {
            Files.createDirectories(output);
            Files.writeString(output.resolve(id+".json"),json(result)+"\n",StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        } catch(Exception|LinkageError error) {
            System.err.println("[DEBUG-shore-runtime] Immutable observation export unavailable: "+errorClass(error));
        }
    }

    private static int expectedProgram(Object renderer)throws ReflectiveOperationException {
        Class<?> type=Class.forName("net.irisshaders.iris.pipeline.FinalPassRenderer");
        if(!type.isInstance(renderer))throw new IllegalStateException("Unknown final renderer");
        Field finalPass=type.getDeclaredField("finalPass");finalPass.setAccessible(true);
        Object pass=finalPass.get(renderer);
        if(pass==null)throw new IllegalStateException("No actual final pass");
        Class<?> passType=Class.forName("net.irisshaders.iris.pipeline.FinalPassRenderer$Pass");
        Field programField=passType.getDeclaredField("program");programField.setAccessible(true);
        Object program=programField.get(pass);
        Class<?> programType=Class.forName("net.irisshaders.iris.gl.program.Program");
        if(!programType.isInstance(program))throw new IllegalStateException("No final Program identity");
        int id=(int)programType.getMethod("getProgramId").invoke(program);
        if(id<=0)throw new IllegalStateException("Invalid final Program identity");
        return id;
    }
    private static int[] framebufferExtent()throws ReflectiveOperationException {
        Class<?> client=Class.forName("net.minecraft.class_310");
        Object mc=client.getMethod("method_1551").invoke(null);
        Object target=client.getMethod("method_1522").invoke(mc);
        Class<?> type=Class.forName("net.minecraft.class_276");
        return new int[]{(int)type.getField("field_1482").get(target),(int)type.getField("field_1481").get(target)};
    }
    private static int frame()throws ReflectiveOperationException {
        return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();
    }
    private static float frameTime()throws ReflectiveOperationException {
        Object timer=Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("TIMER").get(null);
        float value=(float)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms$Timer")
                .getMethod("getFrameTimeCounter").invoke(timer);
        if(!Float.isFinite(value))throw new IllegalStateException("Nonfinite frame time");
        return value;
    }
    private static List<Double> camera()throws ReflectiveOperationException {
        Object position=Class.forName("net.irisshaders.iris.uniforms.CameraUniforms")
                .getMethod("getUnshiftedCameraPosition").invoke(null);
        Class<?> vector=Class.forName("org.joml.Vector3d");
        List<Double> result=new ArrayList<>();
        for(String axis:new String[]{"x","y","z"}) {
            double value=(double)vector.getField(axis).get(position);
            if(!Double.isFinite(value))throw new IllegalStateException("Nonfinite actual camera");
            result.add(value);
        }
        return result;
    }
    private static boolean regular(Path path) {return Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS);}
    private static Properties properties(Path path)throws Exception {
        if(Files.size(path)>16384)throw new IllegalArgumentException("Oversized observation properties");
        Properties result=new Properties();try(var input=Files.newInputStream(path)){result.load(input);}return result;
    }

    /** The actual GL boundary. No fabricated storage/binding or shader values. */
    private static final class RealGlBoundary implements ShoreSamplerSnapshot.SystemBoundary {
        private final List<Map<String,Object>> metadata=new ArrayList<>();
        public int currentProgram()throws Exception {return integer(0x8B8D);}
        public ShoreSamplerSnapshot.Viewport viewport()throws Exception {
            IntBuffer value=ByteBuffer.allocateDirect(16).order(ByteOrder.nativeOrder()).asIntBuffer();
            gl("GL11","glGetIntegerv",new Class<?>[]{int.class,IntBuffer.class},0x0BA2,value);
            return new ShoreSamplerSnapshot.Viewport(value.get(0),value.get(1),value.get(2),value.get(3));
        }
        public String renderer()throws Exception {
            return (String)gl("GL11","glGetString",new Class<?>[]{int.class},0x1F01);
        }
        public int maximumTextureUnits()throws Exception {return integer(0x8B4D);}
        public ShoreSamplerSnapshot.Uniform uniform(int program,String name)throws Exception {
            int location=(int)gl("GL20","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
            if(location<0)return null;
            int count=(int)gl("GL20","glGetProgrami",new Class<?>[]{int.class,int.class},program,0x8B86);
            if(count<0||count>2048)throw new IllegalStateException("Invalid active uniform count");
            IntBuffer size=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            IntBuffer type=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            for(int i=0;i<count;i++) {
                String found=(String)gl("GL20","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
                if(!name.equals(found))continue;
                int kind=type.get(0),length=size.get(0),unit=-1;
                float[] values=null;
                if(kind==0x8B5E&&length==1)
                    unit=(int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,location);
                else if(length==1&&(kind==0x8B5C||kind==0x8B51)) {
                    FloatBuffer data=floats(kind==0x8B5C?16:3);
                    gl("GL20","glGetUniformfv",new Class<?>[]{int.class,int.class,FloatBuffer.class},program,location,data);
                    values=new float[data.capacity()];data.get(values);
                }
                return new ShoreSamplerSnapshot.Uniform(location,kind,length,unit,values);
            }
            throw new IllegalStateException("Named input is not an active uniform");
        }
        public ShoreSamplerSnapshot.State save()throws Exception {
            return new ShoreSamplerSnapshot.State(integer(0x84E0),integer(0x8069),integer(0x88ED),
                    integer(0x0D05),integer(0x0D02),integer(0x806C),integer(0x0D04),integer(0x0D03),
                    integer(0x806B),integer(0x0D00),integer(0x0D01));
        }
        public void selectUnit(int unit)throws Exception {
            gl("GL13","glActiveTexture",new Class<?>[]{int.class},0x84C0+unit);
        }
        public ShoreSamplerSnapshot.Texture texture()throws Exception {
            int id=integer(0x8069);
            boolean exists=id>0&&(boolean)gl("GL11","glIsTexture",new Class<?>[]{int.class},id);
            if(!exists)return new ShoreSamplerSnapshot.Texture(id,false,0,0,0);
            Map<String,Object> data=new LinkedHashMap<>();
            data.put("unit",integer(0x84E0)-0x84C0);data.put("textureId",id);
            data.put("textureMinFilter",parameter(0x2801));data.put("textureMagFilter",parameter(0x2800));
            data.put("textureWrapS",parameter(0x2802));data.put("textureWrapT",parameter(0x2803));
            int base=parameter(0x813C);
            data.put("textureBaseLevel",base);data.put("textureMaxLevel",parameter(0x813D));
            samplerMetadata(data);metadata.add(data);
            if(base!=0)throw new IllegalStateException("Texture base level is not the observed level zero");
            return new ShoreSamplerSnapshot.Texture(id,true,level(0x1003),level(0x1000),level(0x1001));
        }
        private static void samplerMetadata(Map<String,Object> data) {
            data.put("samplerObjectObserved",false);data.put("effectiveFilteringObserved",false);
            data.put("samplerObjectReason","GL33_or_ARB_sampler_objects_not_available");
            try {
                Object caps=Class.forName("org.lwjgl.opengl.GL").getMethod("getCapabilities").invoke(null);
                Class<?> type=Class.forName("org.lwjgl.opengl.GLCapabilities");
                boolean core=(boolean)type.getField("OpenGL33").get(caps);
                boolean arb=(boolean)type.getField("GL_ARB_sampler_objects").get(caps);
                if(!core&&!arb)return;
                int sampler=(int)gl("GL30","glGetIntegeri",new Class<?>[]{int.class,int.class},0x8919,(int)data.get("unit"));
                data.put("samplerObjectId",sampler);data.put("samplerObjectObserved",true);
                if(sampler==0) {
                    data.put("effectiveMinFilter",data.get("textureMinFilter"));
                    data.put("effectiveMagFilter",data.get("textureMagFilter"));
                    data.put("effectiveWrapS",data.get("textureWrapS"));data.put("effectiveWrapT",data.get("textureWrapT"));
                } else {
                    String api=core?"GL33":"ARBSamplerObjects";
                    String[] names={"effectiveMinFilter","effectiveMagFilter","effectiveWrapS","effectiveWrapT"};
                    int[] parameters={0x2801,0x2800,0x2802,0x2803};
                    for(int i=0;i<names.length;i++)data.put(names[i],gl(api,"glGetSamplerParameteri",new Class<?>[]{int.class,int.class},sampler,parameters[i]));
                }
                data.put("effectiveFilteringObserved",true);data.remove("samplerObjectReason");
            } catch(Exception|LinkageError error) {data.put("samplerObjectReason","optional_query_unavailable");data.put("samplerObjectErrorClass",errorClass(error));}
        }
        public float[] readTexels(ShoreSamplerSnapshot.Texture texture,List<ShoreSamplerSnapshot.Texel> points)throws Exception {
            int width=texture.width(),height=texture.height();
            long count=Math.multiplyExact(Math.multiplyExact((long)width,height),4L);
            long bytes=Math.multiplyExact(count,Float.BYTES);
            if(width<=0||height<=0||width>MAX_WIDTH||height>MAX_HEIGHT||bytes>2560L*1440*16)
                throw new IllegalStateException("Unbounded target readback");
            int elements=Math.toIntExact(count);
            if(scratch==null||scratch.capacity()<elements)scratch=floats(elements);
            scratch.clear();scratch.limit(elements);
            for(int i=0;i<elements;i++)scratch.put(i,Float.NaN);
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,0);
            for(int name:new int[]{0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01})pixelStore(name,0);
            pixelStore(0x0D05,4);
            gl("GL11","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},
                    0x0DE1,0,0x1908,0x1406,scratch);
            float[] selected=new float[points.size()*4];
            for(int i=0;i<points.size();i++) {
                ShoreSamplerSnapshot.Texel point=points.get(i);
                int offset=(point.y()*width+point.x())*4;
                for(int c=0;c<4;c++)selected[i*4+c]=scratch.get(offset+c);
            }
            metadata.getLast().put("wholeTargetReadbackBytes",bytes);
            metadata.getLast().put("exportedTexelCount",points.size());
            return selected;
        }
        public void restore(ShoreSamplerSnapshot.State state)throws Exception {
            // Raw GL selection is restored before Iris resumes, so its cached
            // active unit still agrees. No texture binding was ever changed.
            gl("GL13","glActiveTexture",new Class<?>[]{int.class},state.active());
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,state.packBuffer());
            int[] names={0x0D05,0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01};
            int[] values={state.alignment(),state.rowLength(),state.imageHeight(),state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb()};
            for(int i=0;i<names.length;i++)pixelStore(names[i],values[i]);
        }
    }
    private static FloatBuffer floats(int count) {
        try {
            return ByteBuffer.allocateDirect(Math.multiplyExact(count,Float.BYTES)).order(ByteOrder.nativeOrder()).asFloatBuffer();
        } catch(OutOfMemoryError error) {
            // Convert this bounded diagnostic allocation failure into the
            // snapshot's ordinary failure path, including its finally restore.
            throw new IllegalStateException("Diagnostic scratch allocation unavailable");
        }
    }
    private static int integer(int name)throws Exception {return (int)gl("GL11","glGetInteger",new Class<?>[]{int.class},name);}
    private static int level(int name)throws Exception {return (int)gl("GL11","glGetTexLevelParameteri",new Class<?>[]{int.class,int.class,int.class},0x0DE1,0,name);}
    private static int parameter(int name)throws Exception {return (int)gl("GL11","glGetTexParameteri",new Class<?>[]{int.class,int.class},0x0DE1,name);}
    private static void pixelStore(int name,int value)throws Exception {gl("GL11","glPixelStorei",new Class<?>[]{int.class,int.class},name,value);}
    private static Object gl(String type,String name,Class<?>[] parameters,Object... values)throws Exception {
        Method method=Class.forName("org.lwjgl.opengl."+type).getMethod(name,parameters);return method.invoke(null,values);
    }
    private static String errorClass(Throwable error) {
        while(error instanceof InvocationTargetException reflected&&reflected.getCause()!=null)error=reflected.getCause();
        return error.getClass().getSimpleName();
    }
    private static String json(Object value) {
        if(value instanceof Map<?,?> map) {
            List<String> entries=new ArrayList<>();
            for(var entry:map.entrySet())entries.add(quote(entry.getKey().toString())+":"+json(entry.getValue()));
            return "{"+String.join(",",entries)+"}";
        }
        if(value instanceof Iterable<?> list) {
            List<String> entries=new ArrayList<>();for(Object item:list)entries.add(json(item));return "["+String.join(",",entries)+"]";
        }
        if(value instanceof Number number) {
            if(!Double.isFinite(number.doubleValue()))throw new IllegalArgumentException("Nonfinite JSON number");
            return number.toString();
        }
        if(value instanceof Boolean)return value.toString();
        if(value==null)return "null";
        if(value.getClass().isArray())throw new IllegalArgumentException("Raw arrays are not an observation export");
        return quote(value.toString());
    }
    private static String quote(String value) {
        StringBuilder result=new StringBuilder("\"");
        for(int i=0;i<value.length();i++) {
            char c=value.charAt(i);
            if(c=='"'||c=='\\')result.append('\\').append(c);
            else if(c<32)result.append(String.format("\\u%04x",(int)c));
            else result.append(c);
        }
        return result.append('"').toString();
    }
}
