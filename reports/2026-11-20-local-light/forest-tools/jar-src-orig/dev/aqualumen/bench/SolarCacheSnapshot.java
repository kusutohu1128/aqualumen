package dev.aqualumen.bench;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Field;
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
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Properties;
import java.util.UUID;
import java.util.function.IntSupplier;
import net.fabricmc.loader.api.FabricLoader;

/** One requested observation of an existing terrain/water solar-cache input. */
public final class SolarCacheSnapshot {
    private static final String WORLD="AqualumenNaturalV2",WORLD_ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final Set<String> completedRequests=new HashSet<>();
    private static final Map<String,Long> pollAt=new HashMap<>();
    private static FloatBuffer scratch;
    private SolarCacheSnapshot() {}
    public record Context(BathymetrySnapshot.Scope scope, String benchmarkState, boolean currentPipeline) {}
    public record Sampler(int location, int type, int size, int unit) {}
    public record Target(int main, int alt, String format, int width, int height) {}
    public record Texture(int id, boolean exists, int format, int width, int height, int baseLevel) {}
    public record State(int active, int binding, int packBuffer, int alignment, int rowLength,
            int imageHeight, int skipPixels, int skipRows, int skipImages, int swap, int lsb) {}
    /** Only the real Fabric/Iris/GL boundary is injectable. No internal mocks. */
    public interface SystemBoundary {
        Context context() throws Exception;
        int currentProgram() throws Exception;
        int frame() throws Exception;
        int maximumTextureUnits() throws Exception;
        Sampler sampler(int program, String name) throws Exception;
        Target target(int index) throws Exception;
        State save() throws Exception;
        void selectUnit(int unit) throws Exception;
        Texture texture() throws Exception;
        float[] readCacheTexels(Texture texture) throws Exception;
        void restore(State state) throws Exception;
        default ShoreSamplerSnapshot.Uniform uniform(int program,String name)throws Exception {return null;}
        default int[] viewport()throws Exception {return null;}
    }
    public static Map<String,Object> capture(int expectedProgram, String pass, SystemBoundary boundary) {
        return capture(expectedProgram,pass,false,boundary);
    }
    public static Map<String,Object> capture(int expectedProgram,String pass,boolean includeProjection,SystemBoundary boundary) {
        Map<String,Object> result=new LinkedHashMap<>();
        Map<String,Object> projection=new LinkedHashMap<>();
        projection.put("requested",includeProjection);projection.put("available",false);
        projection.put("preparedUniformsOnly",true);projection.put("shaderFetchExecutedProven",false);
        projection.put("sameFrameScreenshotProven",false);
        projection.put("stateUnchanged",false);projection.put("reason",includeProjection?"cache_capture_not_successful":"not_requested");
        result.put("projection",projection);
        result.put("available",false);result.put("stateRestored",false);result.put("scopeAuthorized",false);
        result.put("timingAcceptanceExcluded",true);result.put("visualQualityAccepted",false);
        result.put("shaderFetchExecutedProven",false);result.put("cacheWrittenThisFrameProven",false);
        result.put("reason","invalid_request");
        if(boundary==null||expectedProgram<=0||!Set.of("TERRAIN","TERRAIN_CUTOUT","TRANSLUCENT").contains(pass==null?"":pass))return result;
        State saved=null;
        try {
            result.put("reason","unauthorized_scope");
            Context context=boundary.context();
            if(context==null||!ShoreRuntimeObserver.acceptsScope(context.scope()))return result;
            result.put("scopeAuthorized",true);result.put("benchmarkState",context.benchmarkState());
            result.put("reason","measurement_or_lifecycle_active");
            if(!Set.of("idle","complete","aborted").contains(context.benchmarkState()==null?"":context.benchmarkState()))return result;
            result.put("reason","unknown_pipeline");
            if(!context.currentPipeline())return result;
            result.put("reason","unknown_or_non_current_program");
            int program=boundary.currentProgram();
            result.put("program",program);result.put("expectedProgram",expectedProgram);result.put("pass",pass);
            if(program!=expectedProgram)throw new IllegalStateException("Current program mismatch");
            saved=boundary.save();
            if(saved==null)throw new IllegalStateException("Missing caller state");
            result.put("stateBefore",stateValues(saved));
            int frame=boundary.frame();result.put("snapshotFrame",frame);
            if(frame<0)throw new IllegalStateException("Invalid frame identity");
            int units=boundary.maximumTextureUnits();
            if(units<=0)throw new IllegalStateException("No fragment texture units");
            Map<String,Object> clear=new LinkedHashMap<>(),cloudy=new LinkedHashMap<>();
            result.put("C7",clear);result.put("C6",cloudy);
            result.put("reason","named_sampler_binding_or_target_mismatch");
            Texture clearTexture=observeSource(boundary,program,"colortex7",7,units,clear);
            Texture cloudyTexture=observeSource(boundary,program,"colortex6",6,units,cloudy);
            if(clearTexture.id()==cloudyTexture.id()||clear.get("unit").equals(cloudy.get("unit")))
                throw new IllegalStateException("Clear and cloudy inputs alias");
            boundary.selectUnit((Integer)clear.get("unit"));
            result.put("reason","cache_readback_unavailable_or_invalid");
            float[] pixels=boundary.readCacheTexels(clearTexture);
            if(pixels==null||pixels.length!=8)throw new IllegalStateException("Incomplete cache readback");
            for(float value:pixels)if(!Float.isFinite(value))throw new IllegalStateException("Nonfinite cache value");
            for(int c=0;c<3;c++)if(!(pixels[c]>0&&pixels[c]<=1)||pixels[4+c]!=0)
                throw new IllegalStateException("Invalid clear solar cache or reserved-row neighbour");
            if(pixels[3]!=1||pixels[7]!=1)throw new IllegalStateException("Invalid reserved-row alpha");
            List<Map<String,Object>> samples=new ArrayList<>();
            for(int x=0;x<2;x++)samples.add(Map.of("x",x,"y",511,"rgba",numbers(pixels,x*4)));
            clear.put("cacheTexels",samples);clear.put("wholeTargetReadbackBytes",1024L*512*16);
            clear.put("exportedTexelCount",2);
            result.put("reason","inputs_changed_during_capture");
            if(!clearTexture.equals(boundary.texture()))throw new IllegalStateException("C7 binding changed");
            boundary.selectUnit((Integer)cloudy.get("unit"));
            if(!cloudyTexture.equals(boundary.texture()))throw new IllegalStateException("C6 binding changed");
            for(Map<String,Object> input:List.of(clear,cloudy)) {
                Sampler prior=new Sampler((Integer)input.get("location"),(Integer)input.get("type"),
                        (Integer)input.get("size"),(Integer)input.get("unit"));
                if(!prior.equals(boundary.sampler(program,(String)input.get("name"))))
                    throw new IllegalStateException("Named sampler assignment changed");
            }
            if(includeProjection) {
                result.put("reason","projection_uniforms_unavailable_or_inconsistent");
                observeProjection(boundary,program,frame,pass,projection);
            }
            if(boundary.currentProgram()!=program||boundary.frame()!=frame)
                throw new IllegalStateException("Program or frame changed");
            result.put("readbackPolicy","GL3.2 glGetTexImage level0 once; bounded 8MiB scratch, only two integer texels exported");
            result.put("errorFlagPolicy","untouched; no glGetError, no texture/program/FBO/sampler binding changes");
            result.remove("reason");result.put("available",true);
        } catch(Exception|LinkageError error) {
            result.put("available",false);result.put("errorClass",errorClass(error));
        } finally {
            if(saved!=null) {
                Throwable failure=null;
                try {boundary.restore(saved);}catch(Exception|LinkageError error){failure=error;}
                try {
                    State after=boundary.save();
                    if(after==null)throw new IllegalStateException("Missing restored state");
                    result.put("stateAfter",stateValues(after));
                    if(!saved.equals(after))throw new IllegalStateException("Incomplete state restoration");
                }catch(Exception|LinkageError error){if(failure==null)failure=error;else result.put("stateQueryErrorClass",errorClass(error));}
                if(failure==null)result.put("stateRestored",true);
                else {result.put("available",false);result.put("stateRestored",false);result.put("reason","state_restoration_failed");result.put("restoreErrorClass",errorClass(failure));}
            }
            if(includeProjection&&!Boolean.TRUE.equals(result.get("available"))) {
                projection.put("available",false);
                projection.putIfAbsent("reason","outer_capture_failed");
            }
        }
        return result;
    }
    private static void observeProjection(SystemBoundary boundary,int program,int frame,String pass,Map<String,Object> result)throws Exception {
        result.put("reason","projection_requires_translucent_water_program");
        if(!"TRANSLUCENT".equals(pass))throw new IllegalStateException("Not the identified water program");
        State before=null;
        try {
            result.put("reason","projection_current_program_or_frame_mismatch");
            int current=boundary.currentProgram(),currentFrame=boundary.frame();
            result.put("program",current);result.put("frameBefore",currentFrame);
            if(current!=program||currentFrame!=frame)throw new IllegalStateException("Projection observation changed program or frame");
            before=boundary.save();if(before==null)throw new IllegalStateException("Missing projection caller state");
            result.put("stateBefore",stateValues(before));
            result.put("matrixOrder","column-major; index=column*4+row; GLSL column vectors");
            result.put("matrixValueEncoding","actual GPU float32 widened losslessly to JSON float64; inverses queried, never recomputed");
            Map<String,Object> matrices=new LinkedHashMap<>(),scalars=new LinkedHashMap<>();
            result.put("matrices",matrices);result.put("scalars",scalars);
            result.put("reason","typed_projection_uniform_unavailable_or_incompatible");
            for(String name:new String[]{"gbufferProjection","gbufferProjectionInverse","gbufferModelView","gbufferModelViewInverse"}) {
                ShoreSamplerSnapshot.Uniform value=requiredUniform(boundary,program,name,0x8B5C,16);
                matrices.put(name,Map.of("location",value.location(),"type",value.type(),"size",value.size(),"values",allNumbers(value.values())));
            }
            for(String name:new String[]{"isEyeInWater","viewWidth","viewHeight"}) {
                boolean integer=name.equals("isEyeInWater");
                ShoreSamplerSnapshot.Uniform value=requiredUniform(boundary,program,name,integer?0x1404:0x1406,1);
                float scalar=value.values()[0];
                if(integer&&(scalar!=Math.rint(scalar)||scalar<0||scalar>2))throw new IllegalStateException("Invalid actual eye medium");
                Map<String,Object> observed=new LinkedHashMap<>();
                observed.put("location",value.location());observed.put("type",value.type());observed.put("size",value.size());
                if(integer)observed.put("value",(int)scalar);else observed.put("value",(double)scalar);
                scalars.put(name,observed);
            }
            result.put("reason","actual_projection_viewport_or_dimensions_mismatch");
            int[] viewport=boundary.viewport();
            if(viewport==null||viewport.length!=4||viewport[0]!=0||viewport[1]!=0
                    ||viewport[2]<=0||viewport[2]>2560||viewport[3]<=0||viewport[3]>1440
                    ||!Double.valueOf(viewport[2]).equals(((Map<?,?>)scalars.get("viewWidth")).get("value"))
                    ||!Double.valueOf(viewport[3]).equals(((Map<?,?>)scalars.get("viewHeight")).get("value")))
                throw new IllegalStateException("Actual viewport differs from shader source dimensions");
            result.put("viewport",List.of(viewport[0],viewport[1],viewport[2],viewport[3]));
            int afterProgram=boundary.currentProgram(),afterFrame=boundary.frame();
            result.put("programAfter",afterProgram);result.put("frameAfter",afterFrame);
            result.put("reason","projection_program_or_frame_changed");
            if(afterProgram!=program||afterFrame!=frame)throw new IllegalStateException("Projection program or frame changed");
            result.put("nativeReplayScope","resampled-NDC flat-interface fixture, not the actual scene or a same-frame PNG");
            result.remove("reason");result.put("available",true);
        } catch(Exception|LinkageError error) {
            result.put("available",false);result.put("errorClass",errorClass(error));throw error;
        } finally {
            if(before!=null) {
                try {
                    State after=boundary.save();
                    if(after!=null)result.put("stateAfter",stateValues(after));
                    if(!before.equals(after)) {
                        result.put("reason","projection_query_changed_caller_state");
                        throw new IllegalStateException("Projection query changed caller state");
                    }
                    result.put("stateUnchanged",true);
                }catch(Exception|LinkageError error) {
                    result.put("available",false);result.putIfAbsent("reason","projection_caller_state_unverified");
                    result.put("stateQueryErrorClass",errorClass(error));throw error;
                }
            }
        }
    }
    private static ShoreSamplerSnapshot.Uniform requiredUniform(SystemBoundary boundary,int program,String name,int type,int count)throws Exception {
        ShoreSamplerSnapshot.Uniform value=boundary.uniform(program,name);
        if(value==null||value.location()<0||value.type()!=type||value.size()!=1||value.values()==null||value.values().length!=count)
            throw new IllegalStateException("Actual typed uniform unavailable");
        for(float component:value.values())if(!Float.isFinite(component))throw new IllegalStateException("Nonfinite actual uniform");
        return value;
    }
    private static List<Double> allNumbers(float[] values) {
        List<Double> result=new ArrayList<>();for(float value:values)result.add((double)value);return result;
    }
    private static Texture observeSource(SystemBoundary boundary,int program,String name,int index,int units,Map<String,Object> source)throws Exception {
        source.put("name",name);source.put("active",false);
        Sampler sampler=boundary.sampler(program,name);
        if(sampler==null||sampler.location()<0)throw new IllegalStateException("Inactive named sampler");
        source.put("active",true);source.put("location",sampler.location());source.put("type",sampler.type());
        source.put("size",sampler.size());source.put("unit",sampler.unit());
        if(sampler.type()!=0x8B5E||sampler.size()!=1||sampler.unit()<0||sampler.unit()>=units
                ||sampler.unit()==0||sampler.unit()==2)throw new IllegalStateException("Invalid assigned Sodium scalar sampler");
        Target target=boundary.target(index);
        if(target==null||target.main()<=0||target.alt()<=0||target.main()==target.alt()
                ||!"RGBA16F".equals(target.format())||target.width()!=1024||target.height()!=512)
            throw new IllegalStateException("Missing declared existing LUT target");
        source.put("pipelineIndex",index);source.put("mainTextureId",target.main());source.put("altTextureId",target.alt());
        source.put("declaredFormat",target.format());
        boundary.selectUnit(sampler.unit());Texture texture=boundary.texture();
        if(texture!=null) {
            source.put("textureId",texture.id());source.put("textureExists",texture.exists());source.put("actualFormat",texture.format());
            source.put("width",texture.width());source.put("height",texture.height());source.put("baseLevel",texture.baseLevel());
        }
        if(texture==null||!texture.exists()||(texture.id()!=target.main()&&texture.id()!=target.alt())
                ||texture.format()!=34842||texture.width()!=1024||texture.height()!=512||texture.baseLevel()!=0)
            throw new IllegalStateException("Actual named input differs from the pipeline target");
        source.put("pipelineSide",texture.id()==target.main()?"main":"alt");
        return texture;
    }
    private static List<Double> numbers(float[] values,int offset) {
        List<Double> result=new ArrayList<>();for(int c=0;c<4;c++)result.add((double)values[offset+c]);return result;
    }
    private static Map<String,Object> stateValues(State state) {
        return Map.ofEntries(Map.entry("active",state.active()),Map.entry("binding",state.binding()),Map.entry("packBuffer",state.packBuffer()),
                Map.entry("alignment",state.alignment()),Map.entry("rowLength",state.rowLength()),Map.entry("imageHeight",state.imageHeight()),
                Map.entry("skipPixels",state.skipPixels()),Map.entry("skipRows",state.skipRows()),Map.entry("skipImages",state.skipImages()),
                Map.entry("swap",state.swap()),Map.entry("lsb",state.lsb()));
    }
    private static String errorClass(Throwable error) {
        while(error instanceof InvocationTargetException reflected&&reflected.getCause()!=null)error=reflected.getCause();
        return error.getClass().getSimpleName();
    }

    /** TEST-only one-shot. Never changes or removes the request/Recorder/world.
     * Request: config/aqualumen-solar-cache-observe.properties, schema=1,
     * world_id=b22dbccb-2970-41e6-847f-f183b1ec923d, request_id=canonical UUID,
     * pass=TRANSLUCENT|TERRAIN|TERRAIN_CUTOUT. One pass per request UUID.
     * Optional projection=true additionally requires current TRANSLUCENT's four
     * scalar mat4 uniforms, actual eye/source dimensions and GL viewport. Missing
     * or incompatible values fail the whole requested observation; default false
     * preserves the C7-only contract. Matrices are read, not reconstructed.
     * Output: aqualumen-benchmark/solar-cache-observations/{UUID}.json, CREATE_NEW.
     * Only idle/complete/aborted instrumentation permits GL; authorized requests
     * during active measurement/lifecycle phases export failure, not a later retry.
     * Queries prove prepared input connection/cache, not a per-fragment fetch or
     * producer freshness. No raw full-image artifact or framebuffer is created.
     */
    public static void afterSodiumSetup(int program,String pass,Object pipeline) {
        if(!Set.of("TERRAIN","TERRAIN_CUTOUT","TRANSLUCENT").contains(pass==null?"":pass)||completedRequests.size()>=8)return;
        long now=System.nanoTime();
        if(now-pollAt.getOrDefault(pass,0L)<1_000_000_000L)return;
        pollAt.put(pass,now); // Independent pass clocks cannot starve TRANSLUCENT.
        try {
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(game.getParent()==null||!"Aqualumen Lab".equals(game.getParent().getFileName().toString())
                    ||Files.isSymbolicLink(game.resolve("config")))return;
            Path marker=game.resolve("config/aqualumen-benchmark.enabled");
            Path configPath=game.resolve("config/aqualumen-benchmark.properties");
            Path requestPath=game.resolve("config/aqualumen-solar-cache-observe.properties");
            if(!regular(marker)||!regular(configPath)||!regular(requestPath))return;
            Properties config=properties(configPath),request=properties(requestPath);
            if(!"2".equals(config.getProperty("schema"))||!WORLD.equals(config.getProperty("world"))
                    ||!WORLD_ID.equals(config.getProperty("world_id"))
                    ||!config.getProperty("expected_pack","").matches("Aqualumen-[A-Za-z0-9][A-Za-z0-9._-]*\\.zip")
                    ||!config.getProperty("expected_pack_sha256","").matches("[0-9a-f]{64}")
                    ||!"1".equals(request.getProperty("schema"))||!WORLD_ID.equals(request.getProperty("world_id"))
                    ||!pass.equals(request.getProperty("pass")))return;
            String id=request.getProperty("request_id","");
            String projection=request.getProperty("projection","false");
            if(!Set.of("true","false").contains(projection))return;
            if(!UUID.fromString(id).toString().equals(id)||completedRequests.contains(id))return;
            Path parent=game.resolve("aqualumen-benchmark"),output=parent.resolve("solar-cache-observations");
            if(Files.isSymbolicLink(parent)||Files.isSymbolicLink(output)
                    ||Files.exists(output.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS))return;
            Map<String,Object> result=capture(program,pass,projection.equals("true"),new ReflectedBoundary(game,config,pipeline));
            if(!Boolean.TRUE.equals(result.get("scopeAuthorized")))return;
            completedRequests.add(id); // Consume authorized successes/failures internally, never edit the request.
            result.put("requestId",id);result.put("world",WORLD);result.put("worldId",WORLD_ID);result.put("seed",308060);
            result.put("dimension","minecraft:overworld");result.put("packName",config.getProperty("expected_pack"));
            result.put("packSha256",config.getProperty("expected_pack_sha256"));result.put("utc",Instant.now().toString());
            result.put("observerVersion",FabricLoader.getInstance().getModContainer("aqualumen_benchmark")
                    .map(mod->mod.getMetadata().getVersion().getFriendlyString()).orElse("unavailable"));
            result.put("seam","SodiumShader.setupState TAIL; after sampler/uniform/custom-uniform/image/atlas binding updates");
            result.put("maximumRequestsPerJvm",8);result.put("minimumPollIntervalSecondsPerPass",1);
            Files.createDirectories(output);
            Files.writeString(output.resolve(id+".json"),json(result)+"\n",StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        }catch(Exception|LinkageError error) {
            // No paths, account information, request contents or exception messages.
            System.err.println("[Aqualumen] Requested solar cache observation unavailable: "+errorClass(error));
        }
    }
    private static boolean regular(Path path){return Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS);}
    private static Properties properties(Path path)throws Exception {
        if(Files.size(path)>16384)throw new IllegalArgumentException("Oversized properties");
        Properties result=new Properties();try(var input=Files.newInputStream(path)){result.load(input);}return result;
    }
    /** Real pinned APIs, no target creation, texture binding, uploads or error-flag consumption. */
    private static final class ReflectedBoundary implements SystemBoundary {
        private final Path game;private final Properties config;private final Object pipeline;
        ReflectedBoundary(Path game,Properties config,Object pipeline){this.game=game;this.config=config;this.pipeline=pipeline;}
        public Context context()throws Exception {
            BathymetrySnapshot.Scope scope=BathymetrySnapshot.inspectScope(game,config);
            if(!ShoreRuntimeObserver.acceptsScope(scope))return new Context(scope,"unavailable",false);
            Field state=Recorder.class.getDeclaredField("state");state.setAccessible(true);
            String phase=(String)state.get(null);
            Object manager=Class.forName("net.irisshaders.iris.Iris").getMethod("getPipelineManager").invoke(null);
            Object current=manager==null?null:manager.getClass().getMethod("getPipelineNullable").invoke(manager);
            boolean active=current==pipeline&&Class.forName("net.irisshaders.iris.pipeline.IrisRenderingPipeline").isInstance(current);
            return new Context(scope,phase,active);
        }
        public int currentProgram()throws Exception{return integer(0x8B8D);}
        public int frame()throws Exception {
            return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();
        }
        public int maximumTextureUnits()throws Exception{return integer(0x8872);}
        public Sampler sampler(int program,String name)throws Exception {
            int location=(int)gl("GL20","glGetUniformLocation",new Class<?>[]{int.class,CharSequence.class},program,name);
            if(location<0)return null;
            int count=(int)gl("GL20","glGetProgrami",new Class<?>[]{int.class,int.class},program,0x8B86);
            if(count<0||count>2048)throw new IllegalStateException("Invalid active uniform count");
            IntBuffer size=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            IntBuffer type=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
            for(int i=0;i<count;i++) {
                String found=(String)gl("GL20","glGetActiveUniform",new Class<?>[]{int.class,int.class,int.class,IntBuffer.class,IntBuffer.class},program,i,256,size,type);
                if(!name.equals(found))continue;
                int unit=(type.get(0)==0x8B5E&&size.get(0)==1)?(int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,location):-1;
                return new Sampler(location,type.get(0),size.get(0),unit);
            }
            throw new IllegalStateException("Named uniform not active");
        }
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
                int kind=type.get(0),length=size.get(0);float[] values=null;
                if(length==1&&kind==0x1404)values=new float[]{(int)gl("GL20","glGetUniformi",new Class<?>[]{int.class,int.class},program,location)};
                else if(length==1&&(kind==0x8B5C||kind==0x1406)) {
                    int components=kind==0x8B5C?16:1;
                    FloatBuffer data=ByteBuffer.allocateDirect(components*4).order(ByteOrder.nativeOrder()).asFloatBuffer();
                    for(int c=0;c<components;c++)data.put(c,Float.NaN);
                    gl("GL20","glGetUniformfv",new Class<?>[]{int.class,int.class,FloatBuffer.class},program,location,data);
                    values=new float[components];for(int c=0;c<components;c++)values[c]=data.get(c);
                }
                return new ShoreSamplerSnapshot.Uniform(location,kind,length,-1,values);
            }
            throw new IllegalStateException("Named projection uniform not active");
        }
        public int[] viewport()throws Exception {
            IntBuffer value=ByteBuffer.allocateDirect(16).order(ByteOrder.nativeOrder()).asIntBuffer();
            gl("GL11","glGetIntegerv",new Class<?>[]{int.class,IntBuffer.class},0x0BA2,value);
            return new int[]{value.get(0),value.get(1),value.get(2),value.get(3)};
        }
        public Target target(int index)throws Exception {
            Class<?> type=Class.forName("net.irisshaders.iris.pipeline.IrisRenderingPipeline");
            Field field=type.getDeclaredField("renderTargets");field.setAccessible(true);
            Object targets=field.get(pipeline);Class<?> collection=Class.forName("net.irisshaders.iris.targets.RenderTargets");
            int count=(int)collection.getMethod("getRenderTargetCount").invoke(targets);
            if(index<0||index>=count)return null;
            Object target=collection.getMethod("get",int.class).invoke(targets,index); // Never getOrCreate.
            if(target==null)return null;
            Class<?> targetType=Class.forName("net.irisshaders.iris.targets.RenderTarget");
            Object format=targetType.getMethod("getInternalFormat").invoke(target);
            if(!(format instanceof Enum<?> declared))throw new IllegalStateException("Missing target format");
            return new Target((int)targetType.getMethod("getMainTexture").invoke(target),(int)targetType.getMethod("getAltTexture").invoke(target),
                    declared.name(),(int)targetType.getMethod("getWidth").invoke(target),(int)targetType.getMethod("getHeight").invoke(target));
        }
        public State save()throws Exception {
            return new State(integer(0x84E0),integer(0x8069),integer(0x88ED),integer(0x0D05),integer(0x0D02),integer(0x806C),
                    integer(0x0D04),integer(0x0D03),integer(0x806B),integer(0x0D00),integer(0x0D01));
        }
        public void selectUnit(int unit)throws Exception{gl("GL13","glActiveTexture",new Class<?>[]{int.class},0x84C0+unit);}
        public Texture texture()throws Exception {
            int id=integer(0x8069);
            boolean exists=id>0&&(boolean)gl("GL11","glIsTexture",new Class<?>[]{int.class},id);
            if(!exists)return new Texture(id,false,0,0,0,-1);
            return new Texture(id,true,level(0x1003),level(0x1000),level(0x1001),
                    (int)gl("GL11","glGetTexParameteri",new Class<?>[]{int.class,int.class},0x0DE1,0x813C));
        }
        public float[] readCacheTexels(Texture texture)throws Exception {
            if(texture.width()!=1024||texture.height()!=512)throw new IllegalStateException("Unbounded cache readback");
            int count=1024*512*4;
            if(scratch==null)try {scratch=ByteBuffer.allocateDirect(count*4).order(ByteOrder.nativeOrder()).asFloatBuffer();}
                catch(OutOfMemoryError error){throw new IllegalStateException("Bounded scratch unavailable");}
            scratch.clear();for(int i=0;i<count;i++)scratch.put(i,Float.NaN);
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,0);
            for(int name:new int[]{0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01})store(name,0);
            store(0x0D05,4);
            gl("GL11","glGetTexImage",new Class<?>[]{int.class,int.class,int.class,int.class,FloatBuffer.class},0x0DE1,0,0x1908,0x1406,scratch);
            float[] pixels=new float[8];int offset=511*1024*4;for(int c=0;c<8;c++)pixels[c]=scratch.get(offset+c);return pixels;
        }
        public void restore(State state)throws Exception {
            gl("GL13","glActiveTexture",new Class<?>[]{int.class},state.active());
            gl("GL15","glBindBuffer",new Class<?>[]{int.class,int.class},0x88EB,state.packBuffer());
            int[] names={0x0D05,0x0D02,0x806C,0x0D04,0x0D03,0x806B,0x0D00,0x0D01};
            int[] values={state.alignment(),state.rowLength(),state.imageHeight(),state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb()};
            for(int i=0;i<names.length;i++)store(names[i],values[i]);
        }
    }
    private static int integer(int name)throws Exception{return (int)gl("GL11","glGetInteger",new Class<?>[]{int.class},name);}
    private static int level(int name)throws Exception{return (int)gl("GL11","glGetTexLevelParameteri",new Class<?>[]{int.class,int.class,int.class},0x0DE1,0,name);}
    private static void store(int name,int value)throws Exception{gl("GL11","glPixelStorei",new Class<?>[]{int.class,int.class},name,value);}
    private static Object gl(String type,String method,Class<?>[] parameters,Object... values)throws Exception {
        return Class.forName("org.lwjgl.opengl."+type).getMethod(method,parameters).invoke(null,values);
    }
    private static String json(Object value) {
        if(value instanceof Map<?,?> map) {
            List<String> items=new ArrayList<>();for(var entry:map.entrySet())items.add(quote(entry.getKey().toString())+":"+json(entry.getValue()));
            return "{"+String.join(",",items)+"}";
        }
        if(value instanceof Iterable<?> list){List<String> items=new ArrayList<>();for(Object item:list)items.add(json(item));return "["+String.join(",",items)+"]";}
        if(value instanceof Number number){if(!Double.isFinite(number.doubleValue()))throw new IllegalArgumentException("Nonfinite export");return number.toString();}
        if(value instanceof Boolean)return value.toString();if(value==null)return "null";return quote(value.toString());
    }
    private static String quote(String value) {
        return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";
    }
}
