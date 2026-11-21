package dev.aqualumen.physics;

import java.nio.file.*;
import java.util.*;
import java.security.MessageDigest;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;

/** Exact-world-guarded TEST-only CPU/GPU atlas readback. No uniforms or world mutations. */
public final class ReceiverMaterialProbe {
    private static final String WORLD="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Path game,request;
    private static Properties properties;
    private static boolean done;
    private static int lastFrame=-1,attempts;
    private static int firstFrame=-1;
    private static long warmStart,lastCapture;
    private static String requestHash;
    private static final List<Map<String,Object>> observations=new ArrayList<>();
    private static Object call(Object object,String method) throws ReflectiveOperationException {
        return object.getClass().getMethod(method).invoke(object);
    }
    private static Properties properties(Path path) throws Exception {
        if(Files.isSymbolicLink(path)||Files.size(path)>8192)throw new IllegalStateException("TEST property path/size rejected");
        Properties result=new Properties();try(var reader=Files.newBufferedReader(path)){result.load(reader);}return result;
    }
    private static String sha(Path path) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
    }
    private static void guard(Object client) throws Exception {
        if(!(boolean)call(client,"method_1542"))throw new IllegalStateException("Integrated singleplayer required");
        Object server=call(client,"method_1576");
        if(!Class.forName("net.minecraft.class_1132").isInstance(server)||(boolean)call(server,"method_3860"))throw new IllegalStateException("Integrated non-LAN server required");
        Object root=Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual=((Path)server.getClass().getMethod("method_27050",root.getClass()).invoke(server,root)).toRealPath();
        Path expected=game.resolve("saves/AqualumenNaturalV2").toRealPath();
        if(!actual.equals(expected)||Files.isSymbolicLink(game.resolve("saves/AqualumenNaturalV2")))throw new IllegalStateException("Wrong TEST world");
        Properties marker=properties(actual.resolve("aqualumen-world.properties"));
        if(!WORLD.equals(marker.getProperty("world_id"))||!"308060".equals(marker.getProperty("seed"))
                ||!"minecraft:noise/overworld".equals(marker.getProperty("generator")))throw new IllegalStateException("TEST UUID/seed/generator marker mismatch");
        if((long)call(call(server,"method_30002"),"method_8412")!=308060)throw new IllegalStateException("Actual TEST seed mismatch");
        if(!Iris.isPackInUseQuick()||!Iris.getCurrentPackName().equals("Aqualumen-0.6.0.zip")
                ||!sha(game.resolve("shaderpacks/Aqualumen-0.6.0.zip")).equals(properties.getProperty("pack_sha256")))
            throw new IllegalStateException("Controlled pack identity mismatch");
    }
    private static String json(Object object) {
        if(object==null)return "null";
        if(object instanceof String s)return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\"";
        if(object instanceof Map<?,?> map){var values=new StringJoiner(",","{","}");map.forEach((k,v)->values.add(json(k.toString())+":"+json(v)));return values.toString();}
        if(object instanceof Iterable<?> list){var values=new StringJoiner(",","[","]");list.forEach(v->values.add(json(v)));return values.toString();}
        return object.toString();
    }
    private static List<Double> uv(ReceiverFace.UV uv){return List.of(uv.u(),uv.v());}
    private static List<Float> color(ReceiverFace.Color c){return List.of(c.r(),c.g(),c.b());}
    private static List<Integer> rgba(ReceiverTexture.Sample s){return List.of(s.red(),s.green(),s.blue(),s.alpha());}
    private static Map<String,Object> calibration() throws Exception {
        Class<?> imageType=Class.forName("net.minecraft.class_1011");
        Object image=imageType.getConstructor(int.class,int.class,boolean.class).newInstance(2,2,true);
        try {
            var set=imageType.getMethod("method_4305",int.class,int.class,int.class);
            var get=imageType.getMethod("method_4315",int.class,int.class);
            int[] pattern={0xff030201,0xff060504,0xff090807,0xff0c0b0a},actual=new int[4];
            for(int y=0;y<2;y++)for(int x=0;x<2;x++)set.invoke(image,x,y,pattern[y*2+x]);
            for(int y=0;y<2;y++)for(int x=0;x<2;x++)actual[y*2+x]=(int)get.invoke(image,x,y);
            var sprite=new ReceiverFace.Sprite("fixture","known_rgba",0,1,0,1);
            var face=new ReceiverFace.Face(1,1,sprite,new ReceiverFace.UV(0,0),new ReceiverFace.UV(0,1),new ReceiverFace.UV(1,0),
                    new ReceiverFace.Color(1,1,1),new ReceiverFace.Color(1,1,1),true,15,0,1);
            var snapshot=ReceiverTexture.capture(sprite,2,2,actual,false);
            if(snapshot==null)throw new IllegalStateException("Known native image unexpectedly unsupported");
            var bytes=new ArrayList<Integer>();
            for(String method:List.of("method_35623","method_35625","method_35626","method_4311"))
                bytes.add(((byte)imageType.getMethod(method,int.class,int.class).invoke(image,0,1))&255);
            var sample=snapshot.sample(face,.75,.25);
            set.invoke(image,0,1,0xffffffff);
            if(!bytes.equals(List.of(7,8,9,255)) || !rgba(sample).equals(bytes)
                    || !snapshot.sample(face,.75,.25).equals(sample))throw new IllegalStateException("Native known-channel/immutable fixture failed");
            return Map.of("expectedRGBA",List.of(7,8,9,255),"sampleRGBA",rgba(sample),"nativeByteRGBA",bytes,
                    "immutableAfterOwnNativeImageMutation",true,"rgbaSHA256",snapshot.rgbaSHA256(),"actualAssetMutated",false);
        } finally {((AutoCloseable)image).close();}
    }
    private static void write(Map<String,Object> result) throws Exception {
        Path output=game.resolve("aqualumen-receiver-material-probe");
        if(Files.isSymbolicLink(output))throw new IllegalStateException("Output symlink rejected");
        Files.createDirectories(output);
        Files.writeString(output.resolve(properties.getProperty("request_id")+".json"),json(result)+"\n",StandardOpenOption.CREATE_NEW);
        done=true;
    }
    public static void capture() {
        if(done)return;
        int frame=SystemTimeUniforms.COUNTER.getAsInt();if(frame==lastFrame)return;lastFrame=frame;
        try {
            if(game==null)game=FabricLoader.getInstance().getGameDir().toRealPath();
            if(!game.getParent().getFileName().toString().equals("Aqualumen Lab")){done=true;return;}
            request=game.resolve("config/aqualumen-receiver-material-probe.properties");
            if(!Files.exists(request))return;
            if(properties==null){properties=properties(request);
                if(!"3".equals(properties.getProperty("schema"))||!WORLD.equals(properties.getProperty("world_id")))throw new IllegalStateException("Request scope rejected");
                UUID.fromString(properties.getProperty("request_id"));requestHash=sha(request);}
            Class<?> type=Class.forName("net.minecraft.class_310");Object client=type.getMethod("method_1551").invoke(null),world=type.getField("field_1687").get(client);
            if(world==null||call(client,"method_1576")==null)return;
            if(!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))return;
            long now=System.nanoTime();
            if(warmStart==0){guard(client);warmStart=now;firstFrame=frame;return;}
            if(now-warmStart<5_000_000_000L || frame-firstFrame<120 || (lastCapture!=0 && now-lastCapture<1_000_000_000L))return;
            guard(client);
            if(!sha(request).equals(requestHash))throw new IllegalStateException("Request changed during observations");
            var gpu=GpuReceiverAtlas.capture(client);
            var adapter=new LoadedReceiverFaces(client,world);var values=new ArrayList<Map<String,Object>>();
            for(int i=0;i<16;i++) {
                int[] p=Arrays.stream(properties.getProperty("point."+i).split(",")).mapToInt(Integer::parseInt).toArray();
                if(p.length!=6||p[0]<-202||p[0]>=-183||p[1]<54||p[1]>=67||p[2]<319||p[2]>=334)throw new IllegalStateException("Bounded point scope rejected");
                var material=adapter.materialAt(p[0],p[1],p[2],p[3],p[4],p[5]);
                if(material==null || material.texture()==null){if(++attempts>600)throw new IllegalStateException("Actual face/texture remains unloaded or unsupported");return;}
                var source=material.source();var texture=material.texture();
                var f=source.face();var s=f.sprite();var item=new LinkedHashMap<String,Object>();
                item.put("cell",List.of(p[0],p[1],p[2]));item.put("normal",List.of(p[3],p[4],p[5]));item.put("blockState",source.blockState());
                item.put("renderingSeed",source.renderingSeed());item.put("atlas",s.atlas());item.put("sprite",s.id());
                item.put("spriteBounds",List.of(s.minU(),s.maxU(),s.minV(),s.maxV()));item.put("uvOrigin",uv(f.origin()));item.put("uvS",uv(f.alongS()));item.put("uvT",uv(f.alongT()));
                item.put("vertexColor",color(f.vertexColor()));item.put("tint",color(f.tint()));item.put("shade",f.shade());item.put("vanillaBrightness",f.vanillaBrightness());
                item.put("skyLight",f.skyLight());item.put("blockLight",f.blockLight());values.add(item);
                double[] local=Arrays.stream(properties.getProperty("local."+i).split(",")).mapToDouble(Double::parseDouble).toArray();
                if(local.length!=2)throw new IllegalStateException("Local point coordinates rejected");
                var sample=texture.sample(f,local[0],local[1]);
                if(sample==null)throw new IllegalStateException("Saved first point UV remains unready");
                item.put("savedPointLocalST",List.of(local[0],local[1]));item.put("savedPointPixel",List.of(sample.x(),sample.y()));
                item.put("savedPointRGBA",rgba(sample));item.put("textureSize",List.of(texture.width(),texture.height()));
                item.put("mipLevel",0);item.put("sampling","nearest/clamped unit-face endpoints; not GPU terrain filtering");
                item.put("staticOpaqueTexture",true);item.put("textureRGBA_SHA256",texture.rgbaSHA256());
                var gpuTexture=gpu.pixels().sprite(s,texture.width(),texture.height());
                if(gpuTexture==null || !gpuTexture.rgbaSHA256().equals(texture.rgbaSHA256()))
                    throw new IllegalStateException("Actual GPU atlas region differs from native sprite bytes");
                var gpuSample=gpuTexture.sample(f,local[0],local[1]);
                if(gpuSample==null || !gpuSample.equals(sample))throw new IllegalStateException("GPU/native actual first point differs");
                item.put("gpuTextureRGBA_SHA256",gpuTexture.rgbaSHA256());item.put("gpuSavedPointRGBA",rgba(gpuSample));
                var grid=new ArrayList<Map<String,Object>>();
                for(double a:List.of(.25,.75))for(double b:List.of(.25,.75)){
                    var pixel=texture.sample(f,a,b);if(pixel==null)throw new IllegalStateException("Grid UV unready");
                    grid.add(Map.of("localST",List.of(a,b),"pixel",List.of(pixel.x(),pixel.y()),"rgba",rgba(pixel)));
                }
                item.put("grid",grid);
            }
            observations.add(Map.of("frame",frame,"elapsedNanoseconds",now-warmStart,"actualClientFaces",values,"gpuAtlas",gpu.metadata()));lastCapture=now;
            if(observations.size()<3)return;
            Map<String,Object> result=new LinkedHashMap<>();result.put("schema","aqualumen-actual-receiver-atlas-v1");result.put("world_id",WORLD);
            result.put("seed",308060);result.put("request_id",properties.getProperty("request_id"));result.put("requestSHA256",requestHash);result.put("firstWorldFrame",firstFrame);
            result.put("observations",observations);result.put("knownNativeImageControl",calibration());result.put("actualNativeImagePixelReadback",true);
            result.put("GPUAtlasPixelReadback",true);result.put("knownGPUTextureControl",GpuReceiverAtlas.calibration());result.put("atlasReloadCoherenceProven",false);
            result.put("rawLightNotSmoothed",true);result.put("radianceComputed",false);result.put("sourceUploaded",false);
            result.put("fullGoalAchieved",false);write(result);
            System.out.println("[Aqualumen Receiver Material] 3 warmed observations of 16 actual CPU/GPU atlas regions captured; no source radiance upload");
        } catch(Exception error) {
            done=true;System.err.println("[Aqualumen Receiver Material] TEST safely stopped: "+error);
            if(properties!=null)try{write(Map.of("error",error.toString(),"world_id",WORLD,"fullGoalAchieved",false));}catch(Exception ignored){}
        }
    }
}
