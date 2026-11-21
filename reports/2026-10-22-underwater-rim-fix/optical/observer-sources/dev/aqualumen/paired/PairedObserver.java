package dev.aqualumen.paired;

import dev.aqualumen.bench.BathymetrySnapshot;
import dev.aqualumen.bench.ShoreRuntimeObserver;
import net.fabricmc.loader.api.FabricLoader;
import java.awt.image.BufferedImage;
import java.io.*;
import java.lang.reflect.*;
import java.nio.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.function.IntSupplier;
import javax.imageio.ImageIO;

/** Opt-in capture around one actual pinned Iris FINAL quad. */
public final class PairedObserver {
    private static final Path LAB=Path.of("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft");
    private static final Map<String,String> PINNED_MODS=Map.of(
        "iris","b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5",
        "sodium","411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2",
        "aqualumen_benchmark","ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29",
        "aqualumen_physics","d3b07b3f5e28f0c7bc5346f44391166051143662e087313d24e49008854cd16c");
    private static final Set<String> consumed=new HashSet<>();
    private static long lastPoll;
    private static Pending pending;
    private record Pending(Path game,Path out,Properties config,CaptureRules.Request request,
        CaptureRules.Identity identity,Map<String,Object> c0,Map<String,Object> c12,
        FloatBuffer diagnostic,FloatBuffer sourceC0,Map<String,Map<String,Object>> opticalSamplers,Map<String,FloatBuffer> opticalData,Map<String,Object> manifest) {}
    private PairedObserver() {}
    public static void before(Object renderer) {
        pending=null;
        long now=System.nanoTime();
        if(consumed.size()>=4||now-lastPoll<1_000_000_000L)return;
        lastPoll=now;Path out=null;Map<String,Object> manifest=null;
        try {
            Path game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(!game.equals(LAB.toRealPath())||Files.isSymbolicLink(game.resolve("config")))return;
            Properties config=properties(game.resolve("config/aqualumen-benchmark.properties"));
            Path requestPath=game.resolve("config/aqualumen-paired-water-observe.properties");
            if(!regular(requestPath))return;
            CaptureRules.Request request=CaptureRules.request(properties(requestPath));
            if(consumed.contains(request.id())||!scope(game,config)||!recorderReady(request))return;
            Map<String,Object> mods=mods(game);
            List<Double> pose=camera(request.scene());
            Path parent=game.resolve("aqualumen-benchmark"),destination=parent.resolve("paired-water-observations");
            if(Files.isSymbolicLink(parent)||Files.isSymbolicLink(destination))return;
            Files.createDirectories(destination);
            out=destination.resolve(request.id());
            if(Files.exists(out,LinkOption.NOFOLLOW_LINKS))return;
            Files.createDirectory(out);consumed.add(request.id());
            manifest=manifest(config,request);manifest.put("utcBefore",Instant.now().toString());manifest.put("modOrigins",mods);
            String rendererName=(String)GlReadback.gl("GL11C","glGetString",new Class<?>[]{int.class},7937);
            manifest.put("glRenderer",rendererName);
            if(rendererName==null||!rendererName.contains("NVIDIA"))throw new IllegalStateException("NVIDIA hardware renderer required");
            CaptureRules.Identity identity=identity(renderer,request,pose);
            Map<String,Object> c0=GlReadback.sampler(identity.program(),"colortex0",request.width(),request.height());
            Map<String,Object> c12=GlReadback.sampler(identity.program(),"colortex12",request.width(),request.height());
            manifest.put("c0Sampler",c0);manifest.put("c12Sampler",c12);
            FloatBuffer diagnostic=GlReadback.diagnostic(c12,request.width(),request.height());
            Map<String,Map<String,Object>> opticalSamplers=opticalSamplers(identity.program(),request.width(),request.height());
            FloatBuffer sourceC0=GlReadback.rawFloats(c0,request.width(),request.height());
            Map<String,FloatBuffer> opticalData=new LinkedHashMap<>();
            for(var entry:opticalSamplers.entrySet())opticalData.put(entry.getKey(),GlReadback.rawFloats(entry.getValue(),request.width(),request.height()));
            if(!opticalSamplers.equals(opticalSamplers(identity.program(),request.width(),request.height())))throw new IllegalStateException("optical samplers changed during input read");
            manifest.put("opticalSamplers",opticalSamplers);
            CaptureRules.same(identity,identity(renderer,request,camera(request.scene())));
            manifest.put("beforeReadStateRestored",true);
            pending=new Pending(game,out,config,request,identity,c0,c12,diagnostic,sourceC0,opticalSamplers,opticalData,manifest);
        }catch(Exception|LinkageError e) {
            if(out!=null&&manifest!=null)failure(out,manifest,e);
            else System.err.println("[DEBUG-paired-water] request unavailable: "+e.getClass().getSimpleName());
        }
    }
    public static void after(Object renderer) {
        Pending p=pending;pending=null;if(p==null)return;
        try {
            Properties current=properties(p.game().resolve("config/aqualumen-benchmark.properties"));
            if(!p.config().equals(current)||!scope(p.game(),current)||!recorderReady(p.request()))
                throw new IllegalStateException("scope/config/recorder changed after FINAL quad");
            if(!p.manifest().get("modOrigins").equals(mods(p.game())))throw new IllegalStateException("Mod origin identity changed");
            CaptureRules.Identity after=identity(renderer,p.request(),camera(p.request().scene()));
            CaptureRules.same(p.identity(),after);
            if(!p.c0().equals(GlReadback.sampler(after.program(),"colortex0",after.width(),after.height()))
                ||!p.c12().equals(GlReadback.sampler(after.program(),"colortex12",after.width(),after.height())))
                throw new IllegalStateException("FINAL sampler state changed");
            if(!p.opticalSamplers().equals(opticalSamplers(after.program(),after.width(),after.height())))throw new IllegalStateException("optical samplers changed after FINAL");
            FloatBuffer beauty=GlReadback.beauty(after.fbo(),after.output(),after.width(),after.height());
            if(!p.opticalSamplers().equals(opticalSamplers(after.program(),after.width(),after.height())))throw new IllegalStateException("optical samplers changed after FINAL");
            CaptureRules.same(after,identity(renderer,p.request(),camera(p.request().scene())));
            if(!scope(p.game(),current))throw new IllegalStateException("scope changed during output read");
            Map<String,Object> m=p.manifest();
            m.put("utcAfter",Instant.now().toString());m.put("afterReadStateRestored",true);
            m.put("program",after.program());m.put("frame",after.frame());m.put("drawFbo",after.fbo());
            m.put("outputTexture",after.output());m.put("outputVersion",after.outputVersion());m.put("camera",after.camera());
            m.put("rendererIdentity",System.identityHashCode(after.renderer()));m.put("pipelineIdentity",System.identityHashCode(after.pipeline()));
            m.put("targetsIdentity",System.identityHashCode(after.targets()));m.put("previewUniform",0);
            m.put("outputFormat","RGBA8, GL_LINEAR attachment, FRAMEBUFFER_SRGB disabled");
            long[] counts=CaptureRules.diagnostics(p.diagnostic(),after.width(),after.height());
            List<Long> countList=new ArrayList<>();for(long count:counts)countList.add(count);m.put("routeCounts",countList);
            Map<String,Object> files=new LinkedHashMap<>();
            files.put("classification",write(p.out(),"classification.rgba32f",CaptureRules.littleEndian(p.diagnostic())));
            files.put("sourceC0",write(p.out(),"source-C0.rgba32f",CaptureRules.littleEndian(p.sourceC0())));
            for(var entry:p.opticalData().entrySet())files.put("optics-"+entry.getKey(),write(p.out(),"optics-"+entry.getKey()+".rgba32f",CaptureRules.littleEndian(entry.getValue())));
            m.put("opticalSamplerMapsMatchedAfterQuad",true);
            byte[] rgba=CaptureRules.rgba8(beauty,after.width(),after.height());
            files.put("beauty",write(p.out(),"beauty.rgba8",rgba));
            files.put("beautyNormalizedRead",write(p.out(),"beauty-normalized.rgba32f",CaptureRules.littleEndian(beauty)));
            files.put("png",write(p.out(),"beauty.png",png(rgba,after.width(),after.height())));
            m.put("files",files);m.put("quadInvocationReturnedObserved",true);m.put("available",true);
            immutableManifest(p.out(),m);
        }catch(Exception|LinkageError e){failure(p.out(),p.manifest(),e);}
    }
    private static Map<String,Map<String,Object>> opticalSamplers(int program,int w,int h)throws Exception {
        Map<String,Map<String,Object>> samplers=new LinkedHashMap<>();
        for(String name:List.of("colortex1","colortex2","colortex3","colortex13","colortex14","colortex15"))samplers.put(name,GlReadback.sampler(program,name,w,h));
        Set<Integer> textures=new HashSet<>();
        for(var sampler:samplers.values())if(!textures.add((int)sampler.get("texture")))throw new IllegalStateException("optical textures alias");
        int c0=(int)GlReadback.sampler(program,"colortex0",w,h).get("texture"),c12=(int)GlReadback.sampler(program,"colortex12",w,h).get("texture");
        if(textures.contains(c0)||textures.contains(c12)||textures.contains(GlReadback.attachment(36049)))throw new IllegalStateException("optical input/output textures alias");
        return samplers;
    }
    private static boolean scope(Path game,Properties config)throws Exception {
        return regular(game.resolve("config/aqualumen-benchmark.enabled"))&&CaptureRules.configuration(config)
            &&ShoreRuntimeObserver.acceptsScope(BathymetrySnapshot.inspectScope(game,config));
    }
    private static Map<String,Object> mods(Path game)throws Exception {
        Path directory=game.resolve("mods");
        if(Files.isSymbolicLink(directory))throw new IllegalStateException("redirected Mods directory");
        Map<String,Object> receipts=new LinkedHashMap<>();Set<Path> expected=new HashSet<>();
        for(String id:List.of("iris","sodium","aqualumen_benchmark","aqualumen_physics","aqualumen_paired_water_probe")) {
            var mod=FabricLoader.getInstance().getModContainer(id).orElseThrow();
            List<Path> paths=mod.getOrigin().getPaths();
            if(paths.size()!=1)throw new IllegalStateException("non-jar Mod origin "+id);
            Path path=paths.getFirst();
            if(!regular(path)||!path.toRealPath().getParent().equals(directory.toRealPath())||!path.getFileName().toString().endsWith(".jar"))
                throw new IllegalStateException("Mod outside exact Lab directory "+id);
            String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
            if(PINNED_MODS.containsKey(id)&&!PINNED_MODS.get(id).equals(sha))throw new IllegalStateException("pinned Mod hash differs "+id);
            receipts.put(id,Map.of("file",path.getFileName().toString(),"sha256",sha,"version",mod.getMetadata().getVersion().getFriendlyString()));
            expected.add(path.toRealPath());
        }
        Set<Path> actual=new HashSet<>();
        try(var files=Files.newDirectoryStream(directory,"*.jar")){for(Path path:files){if(!regular(path))throw new IllegalStateException("redirected active Mod");actual.add(path.toRealPath());}}
        if(!expected.equals(actual))throw new IllegalStateException("unexpected active Mod jars");
        return receipts;
    }
    private static boolean recorderReady(CaptureRules.Request request)throws Exception {
        Class<?> recorder=Class.forName("dev.aqualumen.bench.Recorder");
        if(!"complete".equals(staticField(recorder,"state"))||!request.runId().equals(staticField(recorder,"runId")))return false;
        String[] scenes=(String[])staticField(recorder,"scenarios");int stage=(int)staticField(recorder,"stage");
        // Recorder advances beyond its final scene when it marks a run complete.
        return scenes!=null&&scenes.length==1&&stage==1&&request.scene().equals(scenes[0]);
    }
    private static CaptureRules.Identity identity(Object renderer,CaptureRules.Request request,List<Double> camera)throws Exception {
        Class<?> type=Class.forName("net.irisshaders.iris.pipeline.FinalPassRenderer");
        if(!type.isInstance(renderer))throw new IllegalStateException("not the pinned FINAL renderer");
        Object pass=field(renderer,"finalPass"),shader=field(pass,"program");
        int program=(int)shader.getClass().getMethod("getProgramId").invoke(shader);
        if(program<=0||GlReadback.integer(35725)!=program||GlReadback.uniform(program,"aqualumenPairedView",5124)!=0)
            throw new IllegalStateException("actual FINAL program or preview changed");
        int[] viewport=GlReadback.viewport();
        if(!Arrays.equals(viewport,new int[]{0,0,request.width(),request.height()}))throw new IllegalStateException("viewport changed");
        Object client=client(),target=call(client,"method_1522");
        if((int)field(target,"field_1482")!=request.width()||(int)field(target,"field_1481")!=request.height())
            throw new IllegalStateException("client framebuffer size changed");
        int texture=(int)call(target,"method_30277");
        int version=(int)Class.forName("net.irisshaders.iris.targets.Blaze3dRenderTargetExt")
            .getMethod("iris$getColorBufferVersion").invoke(target);
        if(GlReadback.attachment(36048)!=5890||GlReadback.attachment(36049)!=texture)
            throw new IllegalStateException("FINAL not drawing to client texture");
        Map<String,Object> c0=GlReadback.sampler(program,"colortex0",request.width(),request.height());
        Map<String,Object> c12=GlReadback.sampler(program,"colortex12",request.width(),request.height());
        CaptureRules.Identity identity=new CaptureRules.Identity(renderer,field(renderer,"pipeline"),field(renderer,"renderTargets"),
            program,frame(),GlReadback.integer(36006),texture,version,request.width(),request.height(),
            (int)c0.get("texture"),(int)c12.get("texture"),camera);
        CaptureRules.same(identity,identity);return identity;
    }
    private static List<Double> camera(String scene)throws Exception {
        Object mc=client(),player=field(mc,"field_1724"),world=field(mc,"field_1687"),server=call(mc,"method_1576");
        Object camera=call(field(mc,"field_1773"),"method_19418"),position=call(camera,"method_19326"),eye=call(player,"method_33571");
        Object options=field(mc,"field_1690");
        boolean first=(boolean)call(call(options,"method_31044"),"method_31034");
        if(!first||call(camera,"method_19331")!=player||!(boolean)call(player,"method_5869")
            ||!"WATER".equals(((Enum<?>)call(camera,"method_19334")).name()))throw new IllegalStateException("actual camera not first-person WATER");
        double depth=scene.equals("underwater-up-near")?.5:3.25;
        double[] expected={448.5,62.8889-depth,-383.5};List<Double> result=new ArrayList<>();
        String[] fields={"field_1352","field_1351","field_1350"};
        for(int i=0;i<3;i++) {
            double value=(double)field(position,fields[i]),e=(double)field(eye,fields[i]);
            if(!Double.isFinite(value)||!Double.isFinite(e)||Math.abs(value-expected[i])>.05||Math.abs(value-e)>.05)
                throw new IllegalStateException("fixed underwater eye pose changed");
            result.add(value);result.add(e);
        }
        float yaw=(float)call(camera,"method_19330"),pitch=(float)call(camera,"method_19329");
        if(!Float.isFinite(yaw)||!Float.isFinite(pitch)||Math.abs(yaw+45)>.05||Math.abs(pitch+90)>.05)
            throw new IllegalStateException("fixed underwater rotation changed");
        result.add((double)yaw);result.add((double)pitch);
        if((long)call(world,"method_8532")!=6000||(long)call(call(server,"method_30002"),"method_8532")!=6000)
            throw new IllegalStateException("daylight changed");
        return List.copyOf(result);
    }
    private static Map<String,Object> manifest(Properties config,CaptureRules.Request request) {
        Map<String,Object> m=new LinkedHashMap<>();m.put("schema","aqualumen-paired-water-capture-v1");m.put("observerVersion","0.1.0-optics1");m.put("opticalSchema","aqualumen-water-interface-optics-v1");
        m.put("available",false);m.put("requestId",request.id());m.put("recorderRunId",request.runId());m.put("scene",request.scene());
        m.put("worldId",CaptureRules.WORLD_ID);m.put("world","AqualumenNaturalV2");m.put("seed",308060);m.put("dimension","minecraft:overworld");
        m.put("packName",CaptureRules.PACK);m.put("packSha256",config.getProperty("expected_pack_sha256"));m.put("scopeAuthorized",true);
        m.put("width",request.width());m.put("height",request.height());m.put("viewport",List.of(0,0,request.width(),request.height()));
        m.put("seam","Iris 1.8.8 FINAL renderQuad ordinal0 immediately before and after; after Program.use and CustomUniforms.push");
        m.put("maximumRequestsPerJvm",4);m.put("timingAcceptanceExcluded",true);m.put("physicalAccepted",false);m.put("visualAccepted",false);
        m.put("errorFlagConsumed",false);m.put("glObjectsCreated",false);m.put("producerSourceIdentityDirectlyObserved",false);
        m.put("plantSourceReady",false);m.put("resolvedWavePhaseSeconds",17.0);m.put("interactionRipplesSampled",false);
        m.put("cloudAndNonWaveTimeLive",true);m.put("fluidSimulationFrozenOrValidated",false);
        m.put("rowOrder","raw files bottom-up, pixel x+y*width, RGBA interleaved; PNG top-down vertically flipped once");
        m.put("floatEncoding","IEEE754 binary32 little-endian");m.put("diagnosticChannels",List.of("route","fresnel","travel","waterMask"));
        m.put("opticalChannels",Map.of("colortex1",List.of("worldPosition.x","worldPosition.y","worldPosition.z","waterMeanSurfaceY"),"colortex2",List.of("geometricNormal.x","geometricNormal.y","geometricNormal.z","upperSurface + 2*localColumnKnown"),"colortex3",List.of("orientedNormal.x","orientedNormal.y","orientedNormal.z","grazingBlend"),"colortex13",List.of("n.x","n.y","n.z","refractionDiscriminant"),"colortex14",List.of("v.x","v.y","v.z","skyAccess"),"colortex15",List.of("transmitted.x","transmitted.y","transmitted.z","receiverKind")));
        m.put("routeNames",List.of("NOT_WATER","SSR","WORLD_SOURCE","KNOWN_UNREADY","UNKNOWN","PRODUCER_UNAVAILABLE"));
        m.put("beautyReadPolicy","Actual GL_RGBA8 output read as GL_FLOAT into NaN initialized storage, finite/UNORM8 checked; rgba8 bytes recovered with round(value*255)");
        m.put("attributionLimitations",List.of("C12 labels full-resolution water source pixels, not complete final beauty provenance",
            "FINAL mixes center and four neighbor samples plus actual texture-filter footprints",
            "Discard leaves earlier contributors; nonwater translucent draws can mix C0 while clearing surviving C12",
            "Route UNKNOWN does not identify every rejection reason or prove missing world data is the visible cause",
            "World-source producer is top-face bounded and plant transport is unavailable; no full-scene reflection claim"));
        return m;
    }
    private static Map<String,Object> write(Path directory,String name,byte[] bytes)throws Exception {
        Files.write(directory.resolve(name),bytes,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        return Map.of("name",name,"bytes",bytes.length,"sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
    }
    static byte[] png(byte[] rgba,int width,int height)throws IOException {
        BufferedImage image=new BufferedImage(width,height,BufferedImage.TYPE_INT_ARGB);
        for(int y=0;y<height;y++)for(int x=0;x<width;x++) {
            int i=(y*width+x)*4;
            image.setRGB(x,height-1-y,((rgba[i+3]&255)<<24)|((rgba[i]&255)<<16)|((rgba[i+1]&255)<<8)|(rgba[i+2]&255));
        }
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        if(!ImageIO.write(image,"png",bytes))throw new IOException("PNG writer unavailable");return bytes.toByteArray();
    }
    private static void failure(Path out,Map<String,Object> m,Throwable error) {
        m.put("available",false);m.put("errorClass",error.getClass().getSimpleName());m.put("reason",String.valueOf(error.getMessage()));
        try{immutableManifest(out,m);}catch(Exception e){System.err.println("[DEBUG-paired-water] immutable manifest unavailable: "+e.getClass().getSimpleName());}
    }
    private static void immutableManifest(Path out,Map<String,Object> m)throws IOException {
        Files.writeString(out.resolve("manifest.json"),json(m)+"\n",StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
    }
    private static boolean regular(Path p){return Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS);}
    private static Properties properties(Path p)throws Exception {
        if(!regular(p)||Files.size(p)>16384)throw new IllegalArgumentException("missing/bounded properties required");
        Properties result=new Properties();try(var in=Files.newInputStream(p,LinkOption.NOFOLLOW_LINKS)){result.load(in);}return result;
    }
    private static int frame()throws Exception{return ((IntSupplier)Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null)).getAsInt();}
    private static Object client()throws Exception{return Class.forName("net.minecraft.class_310").getMethod("method_1551").invoke(null);}
    private static Object call(Object value,String name)throws Exception{return value.getClass().getMethod(name).invoke(value);}
    private static Object staticField(Class<?> type,String name)throws Exception{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(null);}
    private static Object field(Object value,String name)throws Exception {
        for(Class<?> type=value.getClass();type!=null;type=type.getSuperclass())try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(NoSuchFieldException ignored){}
        throw new NoSuchFieldException(name);
    }
    private static String json(Object value) {
        if(value==null)return "null";if(value instanceof Number||value instanceof Boolean)return value.toString();
        if(value instanceof Map<?,?> m){StringJoiner j=new StringJoiner(",","{","}");for(var e:m.entrySet())j.add(json(e.getKey())+":"+json(e.getValue()));return j.toString();}
        if(value instanceof Iterable<?> list){StringJoiner j=new StringJoiner(",","[","]");for(Object v:list)j.add(json(v));return j.toString();}
        StringBuilder out=new StringBuilder("\"");
        for(char c:value.toString().toCharArray())switch(c){case '"'->out.append("\\\"");case '\\'->out.append("\\\\");case '\n'->out.append("\\n");case '\r'->out.append("\\r");case '\t'->out.append("\\t");default->{if(c<32)out.append(String.format("\\u%04x",(int)c));else out.append(c);}}
        return out.append('"').toString();
    }
}
