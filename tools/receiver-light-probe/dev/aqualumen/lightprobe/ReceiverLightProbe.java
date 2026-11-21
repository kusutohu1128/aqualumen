package dev.aqualumen.lightprobe;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;
import org.lwjgl.opengl.*;

/** Strict V2-only actual pre-draw resource snapshot and owned material fetch. */
public final class ReceiverLightProbe {
    static final String WORLD="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Path game,request,directory;
    private static Properties properties;
    private static String requestHash;
    private static long warmStart;
    private static int firstFrame;
    private static boolean armed,done;
    private static Map<String,Object> pending;
    static Object call(Object object,String method) throws ReflectiveOperationException {return object.getClass().getMethod(method).invoke(object);}
    static String sha(byte[] bytes) throws Exception {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    static Properties load(Path path) throws Exception {
        if(Files.isSymbolicLink(path) || Files.size(path)>8192) throw new IllegalStateException("Opt-in path rejected");
        var result=new Properties();try(var r=Files.newBufferedReader(path)){result.load(r);}return result;
    }
    static void guard() throws Exception {
        Class<?> type=Class.forName("net.minecraft.class_310");Object client=type.getMethod("method_1551").invoke(null);
        Object world=type.getField("field_1687").get(client),server=call(client,"method_1576");
        if(world==null || !(boolean)call(client,"method_1542") || !Class.forName("net.minecraft.class_1132").isInstance(server)
                || (boolean)call(server,"method_3860")) throw new IllegalStateException("Integrated non-LAN TEST required");
        Object root=Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual=((Path)server.getClass().getMethod("method_27050",root.getClass()).invoke(server,root)).toRealPath();
        Path expected=game.resolve("saves/AqualumenNaturalV2").toRealPath();
        if(!actual.equals(expected) || Files.isSymbolicLink(game.resolve("saves/AqualumenNaturalV2"))) throw new IllegalStateException("Wrong TEST world");
        var marker=load(actual.resolve("aqualumen-world.properties"));
        if(!WORLD.equals(marker.getProperty("world_id")) || !"308060".equals(marker.getProperty("seed"))
                || !"minecraft:noise/overworld".equals(marker.getProperty("generator"))
                || (long)call(call(server,"method_30002"),"method_8412")!=308060
                || !call(world,"method_27983").toString().equals("ResourceKey[minecraft:dimension / minecraft:overworld]"))
            throw new IllegalStateException("Actual TEST identity rejected");
        if(!Iris.isPackInUseQuick() || !Iris.getCurrentPackName().equals("Aqualumen-0.6.0.zip")
                || !sha(Files.readAllBytes(game.resolve("shaderpacks/Aqualumen-0.6.0.zip"))).equals(properties.getProperty("pack_sha256"))
                || !sha(Files.readAllBytes(request)).equals(requestHash)) throw new IllegalStateException("Actual pack/request changed");
        if(!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Actual render thread required");
    }
    public static void frame() {
        if(done || armed) return;
        try {
            if(game==null) game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(!game.getParent().getFileName().toString().equals("Aqualumen Lab")){done=true;return;}
            request=game.resolve("config/aqualumen-receiver-light-probe.properties");if(!Files.exists(request))return;
            if(properties==null) {
                properties=load(request);UUID.fromString(properties.getProperty("request_id"));
                if(!WORLD.equals(properties.getProperty("world_id")) || !"1".equals(properties.getProperty("schema")))throw new IllegalStateException("Request scope rejected");
                requestHash=sha(Files.readAllBytes(request));
            }
            Class<?> type=Class.forName("net.minecraft.class_310");Object client=type.getMethod("method_1551").invoke(null);
            if(type.getField("field_1687").get(client)==null || call(client,"method_1576")==null)return;
            int frame=SystemTimeUniforms.COUNTER.getAsInt();long now=System.nanoTime();
            if(warmStart==0){guard();warmStart=now;firstFrame=frame;return;}
            if(now-warmStart<5_000_000_000L || frame-firstFrame<120)return;
            guard();armed=true;System.out.println("[Aqualumen Receiver Light] ARMED V2 actual draw resources");
        }catch(Exception e){fail(e);}
    }
    public static void beforeDraw() {
        if(!armed || done || pending!=null)return;
        try {
            guard();int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
            if(program<=0 || GL20.glGetProgrami(program,GL20.GL_LINK_STATUS)==0)return;
            int count=GL20.glGetProgrami(program,GL20.GL_ATTACHED_SHADERS);if(count<1 || count>8)return;
            int[] size=new int[1],ids=new int[count];GL20.glGetAttachedShaders(program,size,ids);
            String vs=null,fs=null;
            for(int id:ids){int t=GL20.glGetShaderi(id,GL20.GL_SHADER_TYPE);String s=GL20.glGetShaderSource(id);if(s.length()>262144)throw new IllegalStateException("Stage source bounds");if(t==GL20.GL_VERTEX_SHADER)vs=s;else if(t==GL20.GL_FRAGMENT_SHADER)fs=s;}
            if(vs==null || fs==null || !fs.contains("terrainLight") || fs.contains("refractionTrace"))return;
            directory=game.resolve("aqualumen-receiver-light-probe").resolve(properties.getProperty("request_id"));
            if(Files.isSymbolicLink(directory.getParent()) || Files.exists(directory))throw new IllegalStateException("Exclusive output required");
            Files.createDirectories(directory);
            var result=new LinkedHashMap<String,Object>();
            result.put("schema","aqualumen-actual-receiver-light-v1");result.put("world_id",WORLD);result.put("seed",308060);
            result.put("request_id",properties.getProperty("request_id"));result.put("requestSHA256",requestHash);
            result.put("program",program);result.put("vao",GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING));result.put("frame",SystemTimeUniforms.COUNTER.getAsInt());
            result.put("renderer",GL11.glGetString(GL11.GL_RENDERER));result.put("glVersion",GL11.glGetString(GL11.GL_VERSION));
            result.put("linkedVertexSource",vs);result.put("linkedFragmentSource",fs);
            result.put("linkedVertexSourceSHA256",sha(vs.getBytes(StandardCharsets.UTF_8)));result.put("linkedFragmentSourceSHA256",sha(fs.getBytes(StandardCharsets.UTF_8)));
            var inputs=ResourceSnapshot.capture(program,directory);result.put("resources",inputs);
            byte[] query;
            try(var stream=ReceiverLightProbe.class.getResourceAsStream("/material-queries.bin")){if(stream==null)throw new IllegalStateException("Actual query fixture missing");query=stream.readAllBytes();}
            if(!sha(query).equals(properties.getProperty("query_fixture_sha256")))throw new IllegalStateException("Query fixture changed");
            result.put("queryFixtureSHA256",sha(query));result.put("materialFetch",GpuMaterialFetch.run(program,query));
            result.put("archivedGeometry",true);result.put("liveMeshResourceEpochProven",false);result.put("originalTerrainFragmentInvocation",false);
            result.put("shadedWorldSourceUploaded",false);result.put("fullGoalAchieved",false);pending=result;
        }catch(Exception e){fail(e);}
    }
    public static void afterDraw() {
        if(pending==null || done)return;
        try {
            if(!pending.get("program").equals(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)) || !pending.get("vao").equals(GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING))
                    || !pending.get("frame").equals(SystemTimeUniforms.COUNTER.getAsInt()))throw new IllegalStateException("Original draw scope changed");
            pending.put("originalMultiDrawReturned",true);write(pending);
            System.out.println("[Aqualumen Receiver Light] PASS actual resources and controlled material fetch; not source radiance");
        }catch(Exception e){fail(e);}
    }
    private static String json(Object value) {
        if(value==null)return "null";
        if(value instanceof String s)return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";
        if(value instanceof Map<?,?> m){var j=new StringJoiner(",","{","}");m.forEach((k,v)->j.add(json(k.toString())+":"+json(v)));return j.toString();}
        if(value instanceof Iterable<?> l){var j=new StringJoiner(",","[","]");for(var v:l)j.add(json(v));return j.toString();}return value.toString();
    }
    static void write(Map<String,Object> result) throws Exception {
        if(directory==null){directory=game.resolve("aqualumen-receiver-light-probe").resolve(properties.getProperty("request_id"));Files.createDirectories(directory);}
        Files.writeString(directory.resolve("readback.json"),json(result)+"\n",StandardOpenOption.CREATE_NEW);done=true;armed=false;
    }
    static void fail(Exception e) {
        done=true;armed=false;pending=null;System.err.println("[Aqualumen Receiver Light] TEST safely stopped: "+e);
        if(properties!=null)try{write(Map.of("error",e.toString(),"fullGoalAchieved",false));}catch(Exception ignored){}
    }
}
