package dev.aqualumen.suntest;

import dev.aqualumen.bench.Recorder;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.IntBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.function.IntSupplier;
import net.fabricmc.loader.api.FabricLoader;

/** One-shot prepared uniform observation. No GL writes/binds/textures/error consumption. */
public final class SunGuardObserver {
    private static final SunRequestGate REQUESTS=new SunRequestGate();
    private static long lastPoll;private static boolean polled;
    private SunGuardObserver() {}
    public static void afterUniforms(int program,String pass,boolean tessellation,Object pipeline) {
        if(!"TRANSLUCENT".equals(pass)||!tessellation||program<=0)return;
        long now=System.nanoTime();if(polled&&now-lastPoll<1_000_000_000L)return;polled=true;lastPoll=now;
        try {
            Path game=FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize();
            Path requestFile=game.resolve("config/aqualumen-sun-guard-observe.properties");
            if(!Files.isRegularFile(requestFile,LinkOption.NOFOLLOW_LINKS)||Files.size(requestFile)>16384)return;
            SunAuthorization.SystemBoundary authorization=SunAuthorization.runtime(game);
            SunAuthorization.Input input=authorization.input();
            if(input==null||!input.filesystemAuthorized()||SunAuthorization.value(authorization)!=1)return;
            Properties request=properties(requestFile);
            if(!"1".equals(request.getProperty("schema"))
                    ||!"b22dbccb-2970-41e6-847f-f183b1ec923d".equals(request.getProperty("world_id")))return;
            String id=request.getProperty("request_id","");
            if(!java.util.UUID.fromString(id).toString().equals(id))return;
            Field state=Recorder.class.getDeclaredField("state");state.setAccessible(true);
            Object value=state.get(null);String phase=value instanceof String s?s:"unavailable";
            if(!List.of("idle","complete","aborted").contains(phase)||!currentPipeline(pipeline))return;
            Map<String,String> versions=versions();if(!expectedVersions(versions))return;
            Path benchmark=game.resolve("aqualumen-benchmark"),output=benchmark.resolve("sun-guard-observations");
            if(!safeDirectory(benchmark)||!safeDirectory(output))return;
            Path destination=output.resolve(id+".json");
            if(Files.exists(destination,LinkOption.NOFOLLOW_LINKS)||!REQUESTS.claim(id,now))return;
            SunGuardSnapshot.Context context=new SunGuardSnapshot.Context(authorization,phase,pass,tessellation,true,program);
            Map<String,Object> result=new LinkedHashMap<>(SunGuardSnapshot.capture(context,new ReflectedBoundary()));
            result.put("schema","aqualumen-sun-guard-observation-v1");result.put("requestId",id);
            result.put("capturedUtc",java.time.Instant.now().toString());result.put("observerVersion","0.1.0");
            result.put("world","AqualumenNaturalV2");result.put("worldId",request.getProperty("world_id"));
            result.put("seed",308060);result.put("dimension","minecraft:overworld");result.put("scopeAuthorized",true);
            result.put("localIntegratedSinglePlayer",true);result.put("currentPipelineMatches",true);
            result.put("containsTessellation",true);result.put("pass",pass);result.put("benchmarkState",phase);
            result.put("packName",input.configuration().getProperty("expected_pack"));
            result.put("packSha256",input.configuration().getProperty("expected_pack_sha256"));result.put("versions",versions);
            result.put("seam","SodiumShader.updateUniforms TAIL");
            result.put("supplierPath","SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch");
            result.put("registrationPath","CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME");
            result.put("allGLStateUnchangedProven",false);
            Files.writeString(destination,json(result)+"\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        } catch(Exception|LinkageError failure) {
            System.err.println("[Aqualumen Sun TEST] observation unavailable: "+errorClass(failure));
        }
    }
    private static boolean currentPipeline(Object pipeline)throws Exception {
        Object manager=Class.forName("net.irisshaders.iris.Iris").getMethod("getPipelineManager").invoke(null);
        Object current=manager==null?null:manager.getClass().getMethod("getPipelineNullable").invoke(manager);
        return pipeline!=null&&current==pipeline&&Class.forName("net.irisshaders.iris.pipeline.IrisRenderingPipeline").isInstance(current);
    }
    private static Properties properties(Path file)throws Exception {
        byte[] bytes;try(var in=Files.newInputStream(file,LinkOption.NOFOLLOW_LINKS)){bytes=in.readNBytes(16385);}
        if(bytes.length>16384)throw new IllegalArgumentException();Properties p=new Properties();
        p.load(new java.io.ByteArrayInputStream(bytes));return p;
    }
    private static boolean safeDirectory(Path directory)throws Exception {
        if(!Files.exists(directory,LinkOption.NOFOLLOW_LINKS))Files.createDirectory(directory);
        return Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS)&&directory.equals(directory.toRealPath());
    }
    private static Map<String,String> versions() {
        Map<String,String> result=new LinkedHashMap<>();
        for(String id:List.of("aqualumen_water_sun_test","aqualumen_benchmark","aqualumen_physics","iris","sodium","minecraft"))
            result.put(id,FabricLoader.getInstance().getModContainer(id).map(m->m.getMetadata().getVersion().getFriendlyString()).orElse("absent"));
        return result;
    }
    private static boolean expectedVersions(Map<String,String> versions) {
        String[] ids={"aqualumen_water_sun_test","aqualumen_benchmark","aqualumen_physics","iris","sodium","minecraft"};
        String[] pinned={"0.1.0","0.3.9","0.3.0","1.8.8","0.6.9","1.21.1"};
        for(int i=0;i<ids.length;i++){String actual=versions.get(ids[i]);if(actual==null||!(actual.equals(pinned[i])||actual.startsWith(pinned[i]+"+")))return false;}
        return true;
    }
    private static String errorClass(Throwable error) {
        while(error instanceof java.lang.reflect.InvocationTargetException e&&e.getCause()!=null)error=e.getCause();return error.getClass().getSimpleName();
    }
    private static Object gl(String owner,String method,Class<?>[] arguments,Object...values)throws Exception {
        return Class.forName("org.lwjgl.opengl."+owner).getMethod(method,arguments).invoke(null,values);
    }
    private static final class ReflectedBoundary implements SunGuardSnapshot.SystemBoundary {
        public int frame()throws Exception {
            return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();
        }
        public int currentProgram()throws Exception {return (int)gl("GL11","glGetInteger",new Class<?>[]{int.class},35725);}
        public SunGuardSnapshot.Uniform uniform(int program,String name)throws Exception {
            int location=(int)gl("GL20","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
            if(location<0)return null;
            int count=(int)gl("GL20","glGetProgrami",new Class<?>[]{int.class,int.class},program,35718);
            if(count<0||count>2048)throw new IllegalStateException();
            IntBuffer size=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            IntBuffer type=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            for(int i=0;i<count;i++) {
                String found=(String)gl("GL20","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
                if(name.equals(found))return new SunGuardSnapshot.Uniform(found,location,type.get(0),size.get(0));
            }
            return null;
        }
        public int integerUniform(int program,int location)throws Exception {
            return (int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,location);
        }
    }
    private static String json(Object value) {
        if(value==null)return "null";if(value instanceof Boolean||value instanceof Number)return value.toString();
        if(value instanceof Map<?,?> m)return m.entrySet().stream().map(e->json(e.getKey().toString())+":"+json(e.getValue())).collect(java.util.stream.Collectors.joining(",","{","}"));
        if(value instanceof Iterable<?> values){var items=new java.util.ArrayList<String>();for(Object item:values)items.add(json(item));return String.join(",",items).transform(s->"["+s+"]");}
        String s=value.toString();StringBuilder result=new StringBuilder("\"");
        for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '\\'->result.append("\\\\");case '"'->result.append("\\\"");case '\n'->result.append("\\n");case '\r'->result.append("\\r");case '\t'->result.append("\\t");default->{if(c<32)result.append(String.format("\\u%04x",(int)c));else result.append(c);}}}
        return result.append('"').toString();
    }
}
