package dev.aqualumen.stageprobe;

import dev.aqualumen.bench.BathymetrySnapshot;
import dev.aqualumen.bench.Recorder;
import dev.aqualumen.bench.ShoreRuntimeObserver;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.function.IntSupplier;
import net.fabricmc.loader.api.FabricLoader;

/** Explicit one-shot TEST request only. No renderer state writes, resource creation or texture reads. */
public final class WaterStageObserver {
    public static final String VERSION="0.1.0";
    private static final String WORLD_ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final RequestGate REQUESTS=new RequestGate();
    private static long lastPoll;
    private static boolean polled;
    private WaterStageObserver() {}

    public static void afterSetup(int constructorProgram,String pass,boolean containsTessellation,Object pipeline) {
        // A non-tessellated terrain/solid setup must not consume the requested capture.
        if(!containsTessellation||constructorProgram<=0)return;
        long now=System.nanoTime();
        if(polled&&now-lastPoll<1_000_000_000L)return;
        lastPoll=now;polled=true;
        try {
            Path game=FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize();
            if(!labPath(game))return;
            Path configDir=game.resolve("config");
            if(!directory(configDir))return;
            Path marker=configDir.resolve("aqualumen-benchmark.enabled");
            Path benchmark=configDir.resolve("aqualumen-benchmark.properties");
            Path requestFile=configDir.resolve("aqualumen-water-stage-observe.properties");
            if(!regular(marker)||Files.size(marker)>16384||!regular(benchmark)||!regular(requestFile))return;
            Properties config=properties(benchmark),request=properties(requestFile);
            if(!ShoreRuntimeObserver.acceptsConfiguration(config)||!WORLD_ID.equals(request.getProperty("world_id")))return;
            String requestId=request.getProperty("request_id","");
            if(!canonicalUuid(requestId))return;
            String includeSources=request.getProperty("include_sources","false");
            if(!includeSources.equals("true")&&!includeSources.equals("false"))return;
            Map<String,String> versions=versions();
            if(!expectedVersions(versions))return;
            BathymetrySnapshot.Scope scope=BathymetrySnapshot.inspectScope(game,config);
            if(!ShoreRuntimeObserver.acceptsScope(scope)||!currentPipeline(pipeline))return;
            // Actual Iris CPU flag, after setupState, before claim and before all GL reads.
            if(!usingTessellation())return;
            String benchmarkState=benchmarkState();
            boolean idle=List.of("idle","complete","aborted").contains(benchmarkState);
            Path benchmarkRoot=game.resolve("aqualumen-benchmark");
            Path output=benchmarkRoot.resolve("water-stage-observations");
            if(!safeOutputDirectory(benchmarkRoot)||!safeOutputDirectory(output))return;
            Path destination=output.resolve(requestId+".json");
            if(Files.exists(destination,LinkOption.NOFOLLOW_LINKS))return;
            if(!REQUESTS.claim(requestId,now))return;
            StageSnapshot.Context context=new StageSnapshot.Context(config,scope,idle,constructorProgram,Boolean.parseBoolean(includeSources));
            Map<String,Object> result=new LinkedHashMap<>(StageSnapshot.capture(context,new ReflectedBoundary()));
            result.put("schema","aqualumen-water-stage-observation-v1");
            result.put("requestId",requestId);result.put("capturedUtc",java.time.Instant.now().toString());
            result.put("observerVersion",VERSION);result.put("versions",versions);
            result.put("world",scope.world());result.put("worldId",scope.worldId());result.put("seed",scope.seed());
            result.put("dimension",scope.dimension());result.put("localIntegratedSinglePlayer",true);
            result.put("scopeAccepted",true);result.put("currentPipelineMatches",true);
            result.put("benchmarkState",benchmarkState);result.put("afterSetupStateTail",true);
            result.put("pass",safePass(pass));result.put("constructorContainsTessellation",true);
            result.put("expectedPack",config.getProperty("expected_pack"));
            result.put("expectedPackSha256",config.getProperty("expected_pack_sha256"));
            result.put("usingTessellationAtAdmission",true);
            result.put("sourceHashesRequested",Boolean.parseBoolean(includeSources));
            result.put("drawIssuedProven",false);result.put("tessInvocationCountProven",false);
            result.put("fragmentValueFetchProven",false);result.put("nativeOrNaturalAppearanceAccepted",false);
            Files.writeString(destination,json(result)+"\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        } catch(Exception|LinkageError failure) {
            // No paths, shader source, request contents or exception messages in logs.
            System.err.println("[Aqualumen Water Stage TEST] unavailable: "+errorClass(failure));
        }
    }
    private static boolean labPath(Path game)throws Exception {
        return game.getFileName()!=null&&"minecraft".equals(game.getFileName().toString())
                &&game.getParent()!=null&&"Aqualumen Lab".equals(game.getParent().getFileName().toString())
                &&game.getParent().getParent()!=null&&"instances".equals(game.getParent().getParent().getFileName().toString())
                &&game.equals(game.toRealPath());
    }
    private static boolean regular(Path path){return Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS);}
    private static boolean directory(Path path){return Files.isDirectory(path,LinkOption.NOFOLLOW_LINKS);}
    private static boolean safeOutputDirectory(Path path)throws Exception {
        if(Files.exists(path,LinkOption.NOFOLLOW_LINKS))return directory(path)&&path.equals(path.toRealPath());
        if(!directory(path.getParent())||!path.getParent().equals(path.getParent().toRealPath()))return false;
        Files.createDirectory(path);return true;
    }
    private static Properties properties(Path path)throws Exception {
        if(!regular(path)||Files.size(path)>16384)throw new IllegalArgumentException();
        byte[] bytes;
        try(var input=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)){bytes=input.readNBytes(16385);}
        if(bytes.length>16384)throw new IllegalArgumentException();
        Properties result=new Properties();
        try(var input=new java.io.ByteArrayInputStream(bytes)){result.load(input);}
        return result;
    }
    private static boolean canonicalUuid(String value) {
        try{return java.util.UUID.fromString(value).toString().equals(value);}
        catch(IllegalArgumentException failure){return false;}
    }
    private static Map<String,String> versions() {
        Map<String,String> result=new LinkedHashMap<>();
        for(String id:List.of("aqualumen_water_stage_probe","aqualumen_benchmark","iris","sodium","minecraft","aqualumen_physics"))
            result.put(id,FabricLoader.getInstance().getModContainer(id).map(mod->mod.getMetadata().getVersion().getFriendlyString()).orElse("absent"));
        return result;
    }
    private static boolean expectedVersions(Map<String,String> versions) {
        return version(versions,"aqualumen_water_stage_probe",VERSION)&&version(versions,"aqualumen_benchmark","0.3.9")
                &&version(versions,"iris","1.8.8")&&version(versions,"sodium","0.6.9")
                &&version(versions,"minecraft","1.21.1")&&version(versions,"aqualumen_physics","0.3.0");
    }
    private static boolean version(Map<String,String> versions,String id,String expected) {
        String actual=versions.get(id);return actual!=null&&(actual.equals(expected)||actual.startsWith(expected+"+"));
    }
    private static boolean currentPipeline(Object pipeline)throws Exception {
        Object manager=Class.forName("net.irisshaders.iris.Iris").getMethod("getPipelineManager").invoke(null);
        Object actual=manager==null?null:manager.getClass().getMethod("getPipelineNullable").invoke(manager);
        return actual==pipeline&&Class.forName("net.irisshaders.iris.pipeline.IrisRenderingPipeline").isInstance(actual);
    }
    private static boolean usingTessellation()throws Exception {
        return Class.forName("net.irisshaders.iris.vertices.ImmediateState").getField("usingTessellation").getBoolean(null);
    }
    private static String benchmarkState()throws Exception {
        Field state=Recorder.class.getDeclaredField("state");state.setAccessible(true);
        Object phase=state.get(null);return phase instanceof String value?value:"unavailable";
    }
    private static String safePass(String pass){return pass!=null&&pass.matches("[A-Z_]{1,32}")?pass:"unavailable";}
    private static String errorClass(Throwable failure) {
        while(failure instanceof InvocationTargetException invocation&&invocation.getCause()!=null)failure=invocation.getCause();
        return failure.getClass().getSimpleName();
    }
    private static Object gl(String owner,String name,Class<?>[] arguments,Object... values)throws Exception {
        return Class.forName("org.lwjgl.opengl."+owner).getMethod(name,arguments).invoke(null,values);
    }
    private static final class ReflectedBoundary implements StageSnapshot.Boundary {
        public boolean usingTessellation()throws Exception{return WaterStageObserver.usingTessellation();}
        public int frame()throws Exception {
            return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();
        }
        public int currentProgram()throws Exception{return integer(35725);}
        public int programParameter(int program,int parameter)throws Exception {
            return (int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},program,parameter);
        }
        public int[] attachedShaders(int program,int maximum)throws Exception {
            if(maximum!=8)throw new IllegalArgumentException();
            int[] count=new int[1],shaders=new int[maximum];
            gl("GL20C","glGetAttachedShaders",new Class<?>[]{int.class,int[].class,int[].class},program,count,shaders);
            if(count[0]<0||count[0]>maximum)throw new IllegalStateException();
            return Arrays.copyOf(shaders,count[0]);
        }
        public int shaderType(int shader)throws Exception {
            return (int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},shader,35663);
        }
        public String shaderSource(int shader,int maximumBytes)throws Exception {
            int length=(int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},shader,35720);
            if(length<=1||length>maximumBytes+1)throw new IllegalStateException();
            return (String)gl("GL20C","glGetShaderSource",new Class<?>[]{int.class,int.class},shader,length);
        }
        public int patchVertices()throws Exception{return integer(36466);}
        public StageSnapshot.Capabilities capabilities()throws Exception {
            String version=(String)gl("GL11C","glGetString",new Class<?>[]{int.class},7938);
            String renderer=(String)gl("GL11C","glGetString",new Class<?>[]{int.class},7937);
            Object capabilities=gl("GL","getCapabilities",new Class<?>[]{});
            return new StageSnapshot.Capabilities(version,renderer,
                    capabilities.getClass().getField("GL_ARB_tessellation_shader").getBoolean(capabilities),
                    capabilities.getClass().getField("OpenGL40").getBoolean(capabilities));
        }
        private static int integer(int parameter)throws Exception {
            return (int)gl("GL11C","glGetInteger",new Class<?>[]{int.class},parameter);
        }
    }
    /** Only safe observed metadata reaches this serializer; never raw shader source or exception messages. */
    private static String json(Object value) {
        if(value==null)return "null";
        if(value instanceof Map<?,?> map) {
            StringBuilder result=new StringBuilder("{");boolean first=true;
            for(var entry:map.entrySet()){if(!first)result.append(',');first=false;result.append(json(String.valueOf(entry.getKey()))).append(':').append(json(entry.getValue()));}
            return result.append('}').toString();
        }
        if(value instanceof Iterable<?> list) {
            StringBuilder result=new StringBuilder("[");boolean first=true;
            for(Object item:list){if(!first)result.append(',');first=false;result.append(json(item));}
            return result.append(']').toString();
        }
        if(value instanceof Boolean||value instanceof Number)return value.toString();
        StringBuilder result=new StringBuilder("\"");
        for(char c:value.toString().toCharArray())switch(c){
            case '"'->result.append("\\\"");case '\\'->result.append("\\\\");
            case '\n'->result.append("\\n");case '\r'->result.append("\\r");case '\t'->result.append("\\t");
            default->{if(c<32)result.append(String.format("\\u%04x",(int)c));else result.append(c);}
        }
        return result.append('"').toString();
    }
}
