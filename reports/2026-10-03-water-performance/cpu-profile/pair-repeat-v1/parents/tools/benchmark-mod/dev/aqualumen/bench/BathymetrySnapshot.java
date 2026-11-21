package dev.aqualumen.bench;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Properties;
import java.util.Set;
import java.util.UUID;

/** Passive, opt-in observation of an existing bound bathymetry texture. */
public final class BathymetrySnapshot {
    private static final Set<String> completedRequests=new HashSet<>();
    private static long lastPoll;
    private BathymetrySnapshot() {}
    /** Reuse the same live exact-world/pack/seed guards for other passive tools.
     * This performs metadata reads only, before any OpenGL observation.
     */
    public static Scope inspectScope(Path game, Properties config) throws Exception {
        return new ReflectedBoundary(game, config).scope();
    }
    public record Scope(boolean enabled, boolean integrated, boolean lan, int players,
            boolean localCamera, String world, String worldId, long seed, String dimension,
            boolean expectedPack, boolean candidateMod) {}
    public record ModState(int texture, int frame, int ready, int known, float[] grid, boolean failed, float[] pixels) {}
    public record Uniforms(int unit, int ready, float[] grid) {}
    public record Texture(int id, boolean exists, int format, int width, int height,
            int min, int mag, int wrapS, int wrapT) {}
    public record State(int active, int binding, int packBuffer, int alignment, int rowLength,
            int imageHeight, int skipPixels, int skipRows, int skipImages, int swap, int lsb) {}
    /** Only the external Minecraft/filesystem/OpenGL boundary is injectable. */
    public interface SystemBoundary {
        Scope scope() throws Exception;
        ModState modState() throws Exception;
        int frame() throws Exception;
        int currentProgram() throws Exception;
        Uniforms uniforms(int program) throws Exception;
        State save() throws Exception;
        void selectUnit(int unit) throws Exception;
        Texture texture() throws Exception;
        float[] readPixels() throws Exception;
        void restore(State state) throws Exception;
    }
    public static Map<String,Object> capture(int expectedProgram, SystemBoundary boundary) {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("available",false);result.put("stateRestored",false);
        result.put("timingAcceptanceExcluded",true);result.put("visualQualityAccepted",false);
        State saved=null;
        try {
            Scope scope=boundary.scope();
            if(scope==null||!scope.enabled()||!scope.integrated()||scope.lan()||scope.players()!=1
                    ||!scope.localCamera()||!"AqualumenNaturalV2".equals(scope.world())
                    ||!"b22dbccb-2970-41e6-847f-f183b1ec923d".equals(scope.worldId())
                    ||scope.seed()!=308060||!"minecraft:overworld".equals(scope.dimension())
                    ||!scope.expectedPack()||!scope.candidateMod()) {
                result.put("reason","outside_authorized_test_scope");return result;
            }
            result.put("scopeAuthorized",true);result.put("reason","mod_snapshot_unavailable_or_stale");
            ModState mod=boundary.modState();
            if(mod==null||mod.failed()||mod.texture()<=0||mod.frame()!=boundary.frame())
                throw new IllegalStateException("No current Mod snapshot");
            result.put("reason","unknown_or_non_current_program");
            if(expectedProgram<=0||boundary.currentProgram()!=expectedProgram)
                throw new IllegalStateException("Unknown or non-current program");
            result.put("reason","named_uniforms_unavailable_or_inconsistent");
            Uniforms uniforms=boundary.uniforms(expectedProgram);
            if(uniforms==null||uniforms.unit()<0||(uniforms.ready()!=0&&uniforms.ready()!=1)
                    ||uniforms.ready()!=mod.ready()||!finiteGrid(uniforms.grid())
                    ||!finiteGrid(mod.grid())||!Arrays.equals(uniforms.grid(),mod.grid())
                    ||uniforms.grid()[2]!=64)
                throw new IllegalStateException("Missing or inconsistent named uniforms");
            result.put("program",expectedProgram);result.put("samplerUnit",uniforms.unit());
            result.put("ready",uniforms.ready());result.put("grid",numbers(uniforms.grid()));
            result.put("snapshotFrame",mod.frame());result.put("modStoredTextureId",mod.texture());
            saved=boundary.save();boundary.selectUnit(uniforms.unit());
            result.put("reason","actual_binding_or_storage_unavailable_or_inconsistent");
            Texture texture=boundary.texture();
            if(texture==null||!texture.exists()||texture.id()!=mod.texture()||texture.format()!=34836
                    ||texture.width()!=64||texture.height()!=64||texture.min()!=9728||texture.mag()!=9728
                    ||texture.wrapS()!=33071||texture.wrapT()!=33071)
                throw new IllegalStateException("Actual binding or storage does not match the Mod contract");
            result.put("textureId",texture.id());result.put("actualFormat",texture.format());
            result.put("width",texture.width());result.put("height",texture.height());
            result.put("minFilter",texture.min());result.put("magFilter",texture.mag());
            result.put("wrapS",texture.wrapS());result.put("wrapT",texture.wrapT());
            result.put("reason","field_readback_unavailable_or_inconsistent");
            float[] pixels=boundary.readPixels();
            if(pixels==null||pixels.length!=64*64*4)throw new IllegalStateException("Incomplete field readback");
            // Do not consume/clear GL error flags. Even plausible/stale columns
            // must equal the actual current upload buffer, not merely its counts.
            if(mod.pixels()==null||!Arrays.equals(pixels,mod.pixels()))
                throw new IllegalStateException("GL readback differs from stored CPU upload");
            int known=0;
            for(int i=0;i<pixels.length;i+=4) {
                for(int c=0;c<4;c++)if(!Float.isFinite(pixels[i+c]))throw new IllegalStateException("Nonfinite uploaded field");
                if(pixels[i+2]==1) {
                    known++;
                    if(!(pixels[i]>0&&pixels[i]<=32.001f)||pixels[i+3]!=0
                            ||Math.abs(pixels[i+1]-uniforms.grid()[3])>0.12002f)
                        throw new IllegalStateException("Invalid confirmed uploaded column");
                } else if(pixels[i]!=0||pixels[i+1]!=0||pixels[i+2]!=0||pixels[i+3]!=0)
                    throw new IllegalStateException("Unknown uploaded columns must be zero");
            }
            if(known!=mod.known()||(known>0?1:0)!=uniforms.ready())
                throw new IllegalStateException("Uploaded validity disagrees with current Mod snapshot");
            List<Map<String,Object>> samples=new ArrayList<>();
            for(int[] point:new int[][]{{32,32},{31,32},{32,31},{31,31},{40,32}}) {
                int i=(point[1]*64+point[0])*4;
                samples.add(Map.of("texelX",point[0],"texelZ",point[1],"depth",(double)pixels[i],
                        "surfaceRelativeY",(double)pixels[i+1],"validity",(double)pixels[i+2],"reserved",(double)pixels[i+3]));
            }
            result.put("knownColumns",known);result.put("samples",samples);
            result.put("readbackBytes",pixels.length*Float.BYTES);
            result.put("rawRgba32f",pixels);
            result.put("errorFlagPolicy","untouched; field readback compared to current stored CPU upload buffer");
            result.remove("reason");
            result.put("available",true);
        } catch(Exception|LinkageError error) {
            result.put("available",false);result.put("errorClass",errorClass(error));
        } finally {
            if(saved!=null)try {
                boundary.restore(saved);
                if(!saved.equals(boundary.save()))throw new IllegalStateException("Incomplete caller state restoration");
                result.put("stateRestored",true);
            }
            catch(Exception|LinkageError error) {result.put("available",false);result.put("reason","state_restoration_failed");result.put("restoreErrorClass",errorClass(error));}
        }
        return result;
    }
    private static boolean finiteGrid(float[] grid) {
        if(grid==null||grid.length!=4)return false;
        for(float value:grid)if(!Float.isFinite(value))return false;
        return true;
    }
    private static List<Double> numbers(float[] values) {
        List<Double> result=new ArrayList<>();for(float value:values)result.add((double)value);return result;
    }
    private static String errorClass(Throwable error) {
        while(error instanceof java.lang.reflect.InvocationTargetException reflected&&reflected.getCause()!=null)error=reflected.getCause();
        return error.getClass().getSimpleName();
    }
    /** Candidate identity at the real external Fabric metadata boundary. */
    public static boolean acceptsPhysicsMetadata(net.fabricmc.loader.api.metadata.ModMetadata metadata)throws Exception {
        return metadata!=null&&"0.3.0".equals(metadata.getVersion().getFriendlyString());
    }

    /** Called only at the pinned SodiumShader.updateUniforms TAIL seam.
     * One immutable 64KiB readback/request, at most eight requests/JVM and 1Hz.
     * Leaving a request in place never causes continuous sampling. No Recorder changes.
     */
    public static void afterSodiumUniforms(int expectedProgram,String pass) {
        if(!"TRANSLUCENT".equals(pass)||completedRequests.size()>=8)return;
        long now=System.nanoTime();if(now-lastPoll<1_000_000_000L)return;lastPoll=now;
        boolean scoped=false;
        try {
            Object loader=Class.forName("net.fabricmc.loader.api.FabricLoader").getMethod("getInstance").invoke(null);
            Path game=((Path)call(loader,"getGameDir")).toRealPath();
            if(!"Aqualumen Lab".equals(game.getParent().getFileName().toString()))return;
            Path marker=game.resolve("config/aqualumen-benchmark.enabled");
            Path configPath=game.resolve("config/aqualumen-benchmark.properties");
            Path requestPath=game.resolve("config/aqualumen-bathymetry-observe.properties");
            if(!Files.isRegularFile(marker)||!Files.isRegularFile(configPath)||!Files.isRegularFile(requestPath))return;
            Properties config=properties(configPath),request=properties(requestPath);
            String id=request.getProperty("request_id","");
            if(!UUID.fromString(id).toString().equals(id)||completedRequests.contains(id))return;
            if(!"b22dbccb-2970-41e6-847f-f183b1ec923d".equals(request.getProperty("world_id")))return;
            Path output=game.resolve("aqualumen-benchmark/bathymetry-observations");
            if(Files.exists(output.resolve(id+".json"))) {completedRequests.add(id);return;}
            Map<String,Object> result=capture(expectedProgram,new ReflectedBoundary(game,config));
            if(!Boolean.TRUE.equals(result.get("scopeAuthorized")))return; // Including failed/unknown guards: ordinary worlds stay inert.
            scoped=true;
            completedRequests.add(id);
            result.put("observerVersion","0.3.6");result.put("requestId",id);result.put("worldId",request.getProperty("world_id"));
            result.put("utc",Instant.now().toString());result.put("pass",pass);
            result.put("seam","actual SodiumShader.updateUniforms TAIL, before draw");
            result.put("maxRequestsPerJvm",8);result.put("minimumRequestIntervalSeconds",1);
            float[] raw=(float[])result.remove("rawRgba32f");
            Files.createDirectories(output);
            if(Boolean.TRUE.equals(result.get("available"))&&raw!=null) {
                ByteBuffer bytes=ByteBuffer.allocate(raw.length*Float.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                for(float value:raw)bytes.putFloat(value);
                byte[] data=bytes.array();
                Files.write(output.resolve(id+".rgba32f"),data,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
                result.put("fieldFile",id+".rgba32f");result.put("fieldEncoding","RGBA float32 little-endian, row-major z then x");
                result.put("fieldSha256",hex(MessageDigest.getInstance("SHA-256").digest(data)));
            }
            Files.writeString(output.resolve(id+".json"),json(result)+"\n",StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        } catch(Exception|LinkageError error) {
            // No private paths/messages or account contents are printed.
            if(scoped)System.err.println("[Aqualumen] Passive bathymetry observation unavailable: "+errorClass(error));
        }
    }
    private static Properties properties(Path path)throws Exception {
        Properties result=new Properties();try(var input=Files.newInputStream(path)){result.load(input);}return result;
    }
    private static Object call(Object target,String name)throws Exception {return target.getClass().getMethod(name).invoke(target);}
    private static Object field(Object target,String name)throws Exception {return target.getClass().getField(name).get(target);}
    private static Object staticField(Class<?> type,String name)throws Exception {
        Field field=type.getDeclaredField(name);field.setAccessible(true);return field.get(null);
    }
    private static String hex(byte[] data) {return java.util.HexFormat.of().formatHex(data);}
    private static String quote(String value) {
        return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";
    }
    private static String json(Object value) {
        if(value instanceof Map<?,?> map) {
            List<String> entries=new ArrayList<>();for(var entry:map.entrySet())entries.add(quote(entry.getKey().toString())+":"+json(entry.getValue()));return "{"+String.join(",",entries)+"}";
        }
        if(value instanceof Iterable<?> list) {List<String> entries=new ArrayList<>();for(Object item:list)entries.add(json(item));return "["+String.join(",",entries)+"]";}
        if(value instanceof Number||value instanceof Boolean)return value.toString();
        if(value==null)return "null";return quote(value.toString());
    }
    /** All reflection here is the real pinned external boundary, not a shader/voxel replacement. */
    private static final class ReflectedBoundary implements SystemBoundary {
        private final Path game;private final Properties config;
        ReflectedBoundary(Path game,Properties config){this.game=game;this.config=config;}
        public Scope scope()throws Exception {
            boolean enabled="2".equals(config.getProperty("schema"))&&"AqualumenNaturalV2".equals(config.getProperty("world"))
                    &&"b22dbccb-2970-41e6-847f-f183b1ec923d".equals(config.getProperty("world_id"));
            if(!enabled)return new Scope(false,false,false,0,false,"","",0,"",false,false);
            if(!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
                throw new IllegalStateException("Observer requires the render thread");
            Object mc=Class.forName("net.minecraft.class_310").getMethod("method_1551").invoke(null);
            Object server=call(mc,"method_1576"),world=field(mc,"field_1687"),player=field(mc,"field_1724");
            if(server==null||world==null||player==null||!Class.forName("net.minecraft.class_1132").isInstance(server))
                return new Scope(true,false,false,0,false,"","",0,"",false,false);
            Object rootFolder=Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
            Path actual=((Path)server.getClass().getMethod("method_27050",rootFolder.getClass()).invoke(server,rootFolder)).toRealPath();
            Path expected=game.resolve("saves/AqualumenNaturalV2").toRealPath();
            if(!actual.equals(expected))return new Scope(true,true,false,0,false,"","",0,"",false,false);
            Properties worldMarker=properties(actual.resolve("aqualumen-world.properties"));
            String id=worldMarker.getProperty("world_id","");long seed=Long.parseLong(worldMarker.getProperty("seed","0"));
            Object serverWorld=call(server,"method_30002");
            boolean realSeed=(long)call(serverWorld,"method_8412")==seed;
            Object key=call(world,"method_27983");String dimension=call(key,"method_29177").toString();
            Object manager=call(server,"method_3760");List<?> players=(List<?>)call(manager,"method_14571");
            boolean local=call(mc,"method_1560")==player&&players.size()==1
                    &&call(player,"method_5667").equals(call(players.getFirst(),"method_5667"));
            Class<?> iris=Class.forName("net.irisshaders.iris.Iris");
            String pack=(String)iris.getMethod("getCurrentPackName").invoke(null);
            String expectedPack=config.getProperty("expected_pack","");
            boolean packMatches=expectedPack.startsWith("Aqualumen")&&!expectedPack.contains("/")&&!expectedPack.contains("\\")
                    &&pack.equals(expectedPack)&&(boolean)iris.getMethod("isPackInUseQuick").invoke(null)
                    &&!(boolean)iris.getMethod("isFallback").invoke(null)
                    &&((Optional<?>)iris.getMethod("getStoredError").invoke(null)).isEmpty();
            if(packMatches)packMatches=hex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(game.resolve("shaderpacks").resolve(expectedPack))))
                    .equals(config.getProperty("expected_pack_sha256"));
            Object loader=Class.forName("net.fabricmc.loader.api.FabricLoader").getMethod("getInstance").invoke(null);
            Optional<?> mod=(Optional<?>)loader.getClass().getMethod("getModContainer",String.class).invoke(loader,"aqualumen_physics");
            boolean candidate=mod.isPresent()&&acceptsPhysicsMetadata((net.fabricmc.loader.api.metadata.ModMetadata)call(mod.get(),"getMetadata"));
            return new Scope(true,(boolean)call(mc,"method_1542"),(boolean)call(server,"method_3860"),players.size(),local,
                    actual.getFileName().toString(),id,realSeed?seed:0,dimension,
                    packMatches&&"minecraft:noise/overworld".equals(worldMarker.getProperty("generator")),candidate);
        }
        public ModState modState()throws Exception {
            Class<?> type=Class.forName("dev.aqualumen.physics.Bathymetry");Object grid=staticField(type,"grid");
            float[] values=new float[4];int i=0;for(String component:new String[]{"x","y","z","w"})values[i++]=(float)field(grid,component);
            FloatBuffer stored=((FloatBuffer)staticField(type,"pixels")).asReadOnlyBuffer();stored.rewind();
            float[] pixels=new float[stored.remaining()];stored.get(pixels);
            return new ModState((int)staticField(type,"texture"),(int)staticField(type,"lastFrame"),(int)staticField(type,"ready"),
                    (int)staticField(type,"known"),values,(boolean)staticField(type,"failed"),pixels);
        }
        public int frame()throws Exception {
            Object counter=Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null);
            return ((java.util.function.IntSupplier)counter).getAsInt();
        }
        public int currentProgram()throws Exception {return integer(0x8B8D);}
        public Uniforms uniforms(int program)throws Exception {
            int sampler=location(program,"aqualumenBathymetry"),ready=location(program,"aqualumenBathymetryReady"),grid=location(program,"aqualumenBathymetryGrid");
            requireType(program,"aqualumenBathymetry",0x8B5E);requireType(program,"aqualumenBathymetryReady",0x1404);requireType(program,"aqualumenBathymetryGrid",0x8B52);
            int unit=(int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,sampler);
            if(unit<0||unit>=integer(0x8B4D))throw new IllegalStateException("Invalid actual sampler unit");
            int r=(int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,ready);
            FloatBuffer data=buffer(4);gl("GL20","glGetUniformfv",new Class<?>[]{int.class,int.class,FloatBuffer.class},program,grid,data);
            float[] values=new float[4];data.get(values);return new Uniforms(unit,r,values);
        }
        private static int location(int program,String name)throws Exception {
            int location=(int)gl("GL20","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
            if(location<0)throw new IllegalStateException("Named program input unavailable");return location;
        }
        private static void requireType(int program,String name,int expected)throws Exception {
            int count=(int)gl("GL20","glGetProgrami",new Class<?>[]{int.class,int.class},program,0x8B86);
            IntBuffer size=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer(),type=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            for(int i=0;i<count;i++) {
                String found=(String)gl("GL20","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
                if(name.equals(found)) {if(type.get(0)!=expected||size.get(0)!=1)throw new IllegalStateException("Named uniform has incompatible type");return;}
            }
            throw new IllegalStateException("Named uniform is not active");
        }
        public State save()throws Exception {return new State(integer(0x84E0),integer(0x8069),integer(0x88ED),integer(0x0D05),integer(0x0D02),integer(0x806C),integer(0x0D04),integer(0x0D03),integer(0x806B),integer(0x0D00),integer(0x0D01));}
        public void selectUnit(int unit)throws Exception {gl("GL13","glActiveTexture",new Class<?>[]{int.class},0x84C0+unit);}
        public Texture texture()throws Exception {
            int id=integer(0x8069);boolean exists=id>0&&(boolean)gl("GL11","glIsTexture",new Class<?>[]{int.class},id);
            if(!exists)return new Texture(id,false,0,0,0,0,0,0,0);
            return new Texture(id,true,level(0x1003),level(0x1000),level(0x1001),parameter(0x2801),parameter(0x2800),parameter(0x2802),parameter(0x2803));
        }
        public float[] readPixels()throws Exception {
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,0);
            for(int name:new int[]{0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01})pixelStore(name,0);
            pixelStore(0x0D05,4);
            FloatBuffer pixels=buffer(64*64*4);
            gl("GL11","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},0x0DE1,0,0x1908,0x1406,pixels);
            float[] values=new float[pixels.capacity()];pixels.get(values);return values;
        }
        public void restore(State state)throws Exception {
            // We never change texture bindings: only select the already assigned unit.
            gl("GL13","glActiveTexture",new Class<?>[]{int.class},state.active());
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,state.packBuffer());
            int[] names={0x0D05,0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01};
            int[] values={state.alignment(),state.rowLength(),state.imageHeight(),state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb()};
            for(int i=0;i<names.length;i++)pixelStore(names[i],values[i]);
        }
        private static FloatBuffer buffer(int floats) {return ByteBuffer.allocateDirect(floats*Float.BYTES).order(ByteOrder.nativeOrder()).asFloatBuffer();}
        private static int integer(int name)throws Exception {return (int)gl("GL11","glGetInteger",new Class<?>[]{int.class},name);}
        private static int level(int name)throws Exception {return (int)gl("GL11","glGetTexLevelParameteri",new Class<?>[]{int.class,int.class,int.class},0x0DE1,0,name);}
        private static int parameter(int name)throws Exception {return (int)gl("GL11","glGetTexParameteri",new Class<?>[]{int.class,int.class},0x0DE1,name);}
        private static void pixelStore(int name,int value)throws Exception {gl("GL11","glPixelStorei",new Class<?>[]{int.class,int.class},name,value);}
        private static Object gl(String type,String name,Class<?>[] parameters,Object... values)throws Exception {
            Method method=Class.forName("org.lwjgl.opengl."+type).getMethod(name,parameters);return method.invoke(null,values);
        }
    }
}
