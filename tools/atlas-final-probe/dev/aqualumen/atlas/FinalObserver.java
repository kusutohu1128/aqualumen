package dev.aqualumen.atlas;

import dev.aqualumen.bench.BathymetrySnapshot;
import dev.aqualumen.bench.ShoreRuntimeObserver;
import net.fabricmc.loader.api.FabricLoader;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.lang.reflect.*;
import java.util.function.IntSupplier;

/** New isolated TEST observer; queries only after all CPU/world/file gates. */
public final class FinalObserver {
    private static final String UUID_V2="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final Set<String> consumed=new HashSet<>();
    private static final Map<Integer,Map<Integer,String>> linkedSources=new HashMap<>();
    private static final Map<Integer,Map<String,Object>> linkScopes=new HashMap<>();
    private static long lastPoll;
    public static void linked(String name,Object[] shaders,int program) {
        // ProgramCreator RETURN: linked program, shaders detached but not yet
        // destroyed by ProgramBuilder. CPU/world gates precede every GL query.
        try {
            if(!"final".equals(name)||program<=0||shaders==null||shaders.length!=2||linkedSources.size()>=8)return;
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(game.getParent()==null||!"Aqualumen Lab".equals(game.getParent().getFileName().toString())
                    ||!regular(game.resolve("config/aqualumen-benchmark.enabled")))return;
            Properties config=properties(game.resolve("config/aqualumen-benchmark.properties"));
            if(!ShoreRuntimeObserver.acceptsConfiguration(config)
                    ||!config.getProperty("expected_pack","").matches("Aqualumen-ShoreProbe-world-gh-phase-(0|45)-diagnostic-aligned-v2\\.zip"))return;
            BathymetrySnapshot.Scope scope=BathymetrySnapshot.inspectScope(game,config);
            if(linkScopes.size()<8)linkScopes.put(program,Map.of("enabled",scope.enabled(),"integrated",scope.integrated(),
                "lan",scope.lan(),"players",scope.players(),"localCamera",scope.localCamera(),"expectedPack",scope.expectedPack(),
                "candidateMod",scope.candidateMod(),"worldId",scope.worldId(),"seed",scope.seed(),"accepted",ShoreRuntimeObserver.acceptsScope(scope)));
            if(!ShoreRuntimeObserver.acceptsScope(scope)&&!constructionScope(game,config,scope))return;
            if((int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},program,35714)!=1)return;
            Map<Integer,String> sources=new LinkedHashMap<>();
            for(Object shader:shaders) {
                int id=(int)shader.getClass().getMethod("getHandle").invoke(shader);
                int type=(int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},id,35663);
                int length=(int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},id,35720);
                if(length<=1||length>262145)return;
                String source=(String)gl("GL20C","glGetShaderSource",new Class<?>[]{int.class,int.class},id,length);
                if(sources.put(type,source)!=null)return;
            }
            if(sources.keySet().equals(Set.of(35633,35632)))linkedSources.put(program,Map.copyOf(sources));
        }catch(Exception|LinkageError e){System.err.println("[DEBUG-atlas-final-link] unavailable: "+e.getClass().getSimpleName());}
    }
    private static boolean constructionScope(Path game,Properties config,BathymetrySnapshot.Scope s)throws Exception {
        // Iris 1.8.8 isPackInUseQuick requires a published pipeline. During
        // ProgramCreator.create no pipeline has yet been published. Substitute
        // only that lifecycle fact; all actual world/player/Mod guards remain.
        BathymetrySnapshot.Scope identity=new BathymetrySnapshot.Scope(s.enabled(),s.integrated(),s.lan(),s.players(),
            s.localCamera(),s.world(),s.worldId(),s.seed(),s.dimension(),true,s.candidateMod());
        if(s.expectedPack()||!ShoreRuntimeObserver.acceptsScope(identity))return false;
        Properties world=properties(game.resolve("saves/AqualumenNaturalV2/aqualumen-world.properties"));
        if(!"2".equals(world.getProperty("schema"))||!UUID_V2.equals(world.getProperty("world_id"))
            ||!"minecraft:noise/overworld".equals(world.getProperty("generator"))||!"1.21.1".equals(world.getProperty("minecraft")))return false;
        Class<?> iris=Class.forName("net.irisshaders.iris.Iris");
        String name=config.getProperty("expected_pack");
        if(!name.equals(iris.getMethod("getCurrentPackName").invoke(null))
            ||(boolean)iris.getMethod("isFallback").invoke(null)
            ||!((Optional<?>)iris.getMethod("getStoredError").invoke(null)).isEmpty())return false;
        Object manager=iris.getMethod("getPipelineManager").invoke(null);
        if(manager.getClass().getMethod("getPipelineNullable").invoke(manager)!=null)return false;
        Properties selected=properties(game.resolve("config/iris.properties"));
        Path pack=game.resolve("shaderpacks").resolve(name);
        return name.equals(selected.getProperty("shaderPack"))&&"true".equals(selected.getProperty("enableShaders"))
            &&regular(pack)&&Files.size(pack)<=16_777_216
            &&HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(pack)))
                .equals(config.getProperty("expected_pack_sha256"));
    }
    public static boolean accepts(Properties config,Properties request,String state) {
        try {
            String id=request.getProperty("request_id","");
            return ShoreRuntimeObserver.acceptsConfiguration(config)
                &&config.getProperty("expected_pack","").matches("Aqualumen-ShoreProbe-world-gh-phase-(0|45)-diagnostic-aligned-v2\\.zip")
                &&UUID_V2.equals(request.getProperty("world_id"))&&UUID.fromString(id).toString().equals(id)
                &&List.of("idle","complete","aborted").contains(state);
        }catch(Exception e){return false;}
    }
    public static void beforeQuad(Object renderer) {
        long now=System.nanoTime();if(consumed.size()>=8||now-lastPoll<1_000_000_000L)return;lastPoll=now;
        try {
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(game.getParent()==null||!"Aqualumen Lab".equals(game.getParent().getFileName().toString()))return;
            Path configDir=game.resolve("config"),requestFile=configDir.resolve("aqualumen-atlas-final-observe.properties");
            if(!regular(configDir.resolve("aqualumen-benchmark.enabled"))||!regular(requestFile))return;
            Properties config=properties(configDir.resolve("aqualumen-benchmark.properties")),request=properties(requestFile);
            Field field=Class.forName("dev.aqualumen.bench.Recorder").getDeclaredField("state");field.setAccessible(true);
            String state=(String)field.get(null);String id=request.getProperty("request_id","");
            if(!accepts(config,request,state)||consumed.contains(id)
                    ||!ShoreRuntimeObserver.acceptsScope(BathymetrySnapshot.inspectScope(game,config)))return;
            Path parent=game.resolve("aqualumen-benchmark"),out=parent.resolve("atlas-final-observations");
            if(Files.isSymbolicLink(parent)||Files.isSymbolicLink(out))return;
            Files.createDirectories(out);Path target=out.resolve(id+".json");if(Files.exists(target,LinkOption.NOFOLLOW_LINKS))return;
            consumed.add(id);
            Class<?> finalType=Class.forName("net.irisshaders.iris.pipeline.FinalPassRenderer");
            Field finalPass=finalType.getDeclaredField("finalPass");finalPass.setAccessible(true);Object pass=finalPass.get(renderer);
            Field programField=pass.getClass().getDeclaredField("program");programField.setAccessible(true);Object program=programField.get(pass);
            int expected=(int)program.getClass().getMethod("getProgramId").invoke(program);
            Map<String,Object> result=new LinkedHashMap<>(FinalSnapshot.capture(expected,new RealBoundary()));
            result.put("schema","aqualumen-atlas-final-source-observation-v1");result.put("observerVersion","0.1.3");
            result.put("linkCpuScope",linkScopes.get(expected));
            result.put("linkScopePolicy","Full live V2 guards; unpublished pipeline requires fresh CPU selected/current pack SHA and no fallback/error. Draw requires original full active-pack scope.");
            result.put("sourceObservationSeam","ProgramCreator.create RETURN after link/detach, before ProgramBuilder destroys actual GlShader arguments; exact active program cache lookup");
            result.put("requestId",id);result.put("worldId",UUID_V2);result.put("world","AqualumenNaturalV2");
            result.put("seed",308060);result.put("dimension","minecraft:overworld");result.put("benchmarkState",state);
            result.put("scopeAuthorized",true);result.put("packName",config.getProperty("expected_pack"));
            result.put("packSha256",config.getProperty("expected_pack_sha256"));result.put("utc",java.time.Instant.now().toString());
            result.put("seam","FINAL before renderQuad after Program.use and custom uniforms");
            Files.writeString(target,json(result)+"\n",StandardOpenOption.CREATE_NEW);
        }catch(Exception|LinkageError e){System.err.println("[DEBUG-atlas-final] unavailable: "+e.getClass().getSimpleName());}
    }
    private static boolean regular(Path p){return Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS);}
    private static Properties properties(Path p)throws Exception {
        if(!regular(p)||Files.size(p)>16384)throw new IllegalArgumentException();Properties out=new Properties();
        try(var input=Files.newInputStream(p,LinkOption.NOFOLLOW_LINKS)){out.load(input);}return out;
    }
    private static Object gl(String cls,String method,Class<?>[] types,Object... args)throws Exception {
        return Class.forName("org.lwjgl.opengl."+cls).getMethod(method,types).invoke(null,args);
    }
    private static int integer(int key)throws Exception{return (int)gl("GL11C","glGetInteger",new Class<?>[]{int.class},key);}
    private static class RealBoundary implements FinalSnapshot.Boundary {
        public int program()throws Exception{return integer(35725);}
        public int frame()throws Exception{return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();}
        public int[] viewport()throws Exception {
            IntBuffer v=ByteBuffer.allocateDirect(16).order(ByteOrder.nativeOrder()).asIntBuffer();
            gl("GL11C","glGetIntegerv",new Class<?>[]{int.class,IntBuffer.class},2978,v);return new int[]{v.get(0),v.get(1),v.get(2),v.get(3)};
        }
        public String renderer()throws Exception{return (String)gl("GL11C","glGetString",new Class<?>[]{int.class},7937);}
        public String version()throws Exception{return (String)gl("GL11C","glGetString",new Class<?>[]{int.class},7938);}
        public FinalSnapshot.Scalar scalar(int program,String name)throws Exception {
            int location=(int)gl("GL20C","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
            int count=(int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},program,35718);
            if(location<0||count<0||count>2048)return null;
            for(int i=0;i<count;i++) {
                IntBuffer size=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer(),type=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
                String found=(String)gl("GL20C","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
                if(name.equals(found)){float value=(float)gl("GL20C","glGetUniformf",new Class<?>[]{int.class,int.class},program,location);return new FinalSnapshot.Scalar(location,type.get(0),size.get(0),value);}
            }return null;
        }
        public Map<Integer,String> sources(int p)throws Exception {
            int link=(int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},p,35714);
            int n=(int)gl("GL20C","glGetProgrami",new Class<?>[]{int.class,int.class},p,35717);
            if(link!=1)throw new IllegalStateException();
            if(n==0){Map<Integer,String> observed=linkedSources.get(p);if(observed==null)throw new IllegalStateException();return observed;}
            if(n!=2)throw new IllegalStateException();int[] count=new int[1],ids=new int[8];
            gl("GL20C","glGetAttachedShaders",new Class<?>[]{int.class,int[].class,int[].class},p,count,ids);
            if(count[0]!=2)throw new IllegalStateException();Map<Integer,String> out=new LinkedHashMap<>();
            for(int i=0;i<2;i++) {
                int type=(int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},ids[i],35663);
                int length=(int)gl("GL20C","glGetShaderi",new Class<?>[]{int.class,int.class},ids[i],35720);
                if(length<=1||length>262145)throw new IllegalStateException();
                String source=(String)gl("GL20C","glGetShaderSource",new Class<?>[]{int.class,int.class},ids[i],length);
                if(out.put(type,source)!=null)throw new IllegalStateException();
            }return out;
        }
    }
    private static String json(Object v) {
        if(v==null)return "null";if(v instanceof Number||v instanceof Boolean)return v.toString();
        if(v instanceof Map<?,?> m){StringJoiner s=new StringJoiner(",","{","}");for(var e:m.entrySet())s.add(json(e.getKey())+":"+json(e.getValue()));return s.toString();}
        if(v instanceof Iterable<?> a){StringJoiner s=new StringJoiner(",","[","]");for(Object item:a)s.add(json(item));return s.toString();}
        StringBuilder s=new StringBuilder("\"");for(char c:v.toString().toCharArray())switch(c){case '"'->s.append("\\\"");case '\\'->s.append("\\\\");case '\n'->s.append("\\n");case '\r'->s.append("\\r");case '\t'->s.append("\\t");default->{if(c<32)s.append(String.format("\\u%04x",(int)c));else s.append(c);}}return s.append('"').toString();
    }
}
