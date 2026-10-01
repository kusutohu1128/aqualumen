package dev.aqualumen.bench;
import net.fabricmc.loader.api.FabricLoader;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;
import java.util.concurrent.Executor;

// Development-only instrument. It never connects to a server or sends chat messages.
public final class Recorder {
    private static final long WARMUP=15_000_000_000L, SAMPLE=30_000_000_000L;
    private static final String[] NAMES={"noon-water","coast-shadows","sunset-water","underwater","moving-view"};
    private static final String[] TELEPORTS={"tp @s 0 65 12 0 8","tp @s 0 65 24 180 6","tp @s 0 65 12 90 6","tp @s 0 59 12 0 8","tp @s 0 65 12 0 8"};
    private static boolean disabled=false,done=false,initialized=false;
    private static int stage=-1;
    private static long start=0,previous=0;
    private static final ArrayList<Double> timings=new ArrayList<>();
    private static Path dir;
    private static Field playerField,worldField,screenField;
    private static Method command,yaw,getFramebuffer,getWindow,getWidth,getHeight,screenshot;
    private static Object server,commandManager,commandSource;
    private static void init(Object mc) throws Exception {
        Path game=FabricLoader.getInstance().getGameDir();
        if (!game.getParent().getFileName().toString().equals("Aqualumen Lab") || !Files.exists(game.resolve("config/aqualumen-benchmark.enabled"))) { disabled=true;return; }
        Class<?> c=mc.getClass();
        playerField=c.getField("field_1724");worldField=c.getField("field_1687");screenField=c.getField("field_1755");
        server=c.getMethod("method_1576").invoke(mc);
        if (server==null || playerField.get(mc)==null || screenField.get(mc)!=null) return;
        Object player=playerField.get(mc);
        commandManager=server.getClass().getMethod("method_3734").invoke(server);
        commandSource=server.getClass().getMethod("method_3739").invoke(server);
        command=commandManager.getClass().getMethod("method_44252",Class.forName("net.minecraft.class_2168"),String.class);
        yaw=player.getClass().getMethod("method_36456",float.class);
        getFramebuffer=c.getMethod("method_1522");getWindow=c.getMethod("method_22683");
        Object window=getWindow.invoke(mc);
        getWidth=window.getClass().getMethod("method_4489");getHeight=window.getClass().getMethod("method_4506");
        screenshot=Class.forName("net.minecraft.class_318").getMethod("method_22690",java.io.File.class,String.class,Class.forName("net.minecraft.class_276"),Consumer.class);
        dir=game.resolve("aqualumen-benchmark");Files.createDirectories(dir);
        if (!Class.forName("net.irisshaders.iris.Iris").getMethod("isPackInUseQuick").invoke(null).equals(Boolean.TRUE)) throw new IllegalStateException("Shader pack not active");
        for (String line:new String[]{
            "gamemode spectator @a", "gamerule doDaylightCycle false", "gamerule doWeatherCycle false", "weather clear",
            "fill -48 59 -24 48 66 -8 sandstone", "fill -32 57 0 32 58 64 sand",
            "fill 8 63 -2 10 76 0 stone_bricks", "fill 7 76 -3 11 77 1 stone_bricks",
            "fill -12 67 -16 -12 73 -16 oak_log", "fill -15 71 -19 -9 75 -13 oak_leaves[persistent=true]"}) send(mc,line);
        initialized=true;
        next(mc);
    }
    private static void send(Object mc,String text) {
        String localCommand=text.replace("@s","@a");
        ((Executor)server).execute(()-> {
            try { command.invoke(commandManager,commandSource,localCommand); }
            catch(Exception error) { throw new RuntimeException("Local benchmark setup failed",error); }
        });
    }
    private static void next(Object mc) throws Exception {
        ++stage;
        if(stage>=NAMES.length) { done=true;Files.writeString(dir.resolve("complete.txt"),"All five local scenarios recorded.\n");System.out.println("[Aqualumen] Benchmark complete");return; }
        send(mc,"time set "+(stage==2?12700:6000));
        send(mc,TELEPORTS[stage]);
        timings.clear();start=System.nanoTime();previous=0;
        System.out.println("[Aqualumen] Warmup: "+NAMES[stage]);
    }
    public static void frame(Object mc) {
        if(disabled||done) return;
        try {
            if(!initialized) { init(mc);return; }
            if(worldField.get(mc)==null || playerField.get(mc)==null || screenField.get(mc)!=null) { previous=0;return; }
            long now=System.nanoTime(),elapsed=now-start;
            if(stage==4) yaw.invoke(playerField.get(mc),(float)((elapsed-WARMUP)*1e-9*12.0));
            if(elapsed>=WARMUP && previous!=0) timings.add((now-previous)*1e-6);
            previous=now;
            if(elapsed>=WARMUP+SAMPLE && timings.size()>10) {
                ArrayList<Double> sorted=new ArrayList<>(timings);Collections.sort(sorted);
                double mean=timings.stream().mapToDouble(Double::doubleValue).average().orElseThrow();
                int onePercentCount=Math.max(1,(int)Math.ceil(sorted.size()*0.01));
                double slowMean=sorted.subList(sorted.size()-onePercentCount,sorted.size()).stream().mapToDouble(Double::doubleValue).average().orElseThrow();
                double p99=sorted.get(Math.min(sorted.size()-1,(int)Math.ceil(sorted.size()*0.99)-1));
                double max=sorted.get(sorted.size()-1);
                Object window=getWindow.invoke(mc);
                int width=(int)getWidth.invoke(window),height=(int)getHeight.invoke(window);
                String report=String.format(Locale.ROOT,"{\n  \"scenario\":\"%s\",\n  \"resolution\":[%d,%d],\n  \"frames\":%d,\n  \"mean_fps\":%.2f,\n  \"one_percent_low_fps\":%.2f,\n  \"p99_ms\":%.4f,\n  \"max_ms\":%.4f,\n  \"min_instantaneous_fps\":%.2f,\n  \"frames_over_16_667_ms\":%d,\n  \"warmup_seconds\":15,\n  \"sample_seconds\":30\n}\n",NAMES[stage],width,height,timings.size(),1000.0/mean,1000.0/slowMean,p99,max,1000.0/max,timings.stream().filter(t->t>1000.0/60.0).count());
                Files.writeString(dir.resolve(NAMES[stage]+".json"),report);
                StringBuilder csv=new StringBuilder("frame,ms\n");for(int i=0;i<timings.size();++i) csv.append(i).append(',').append(timings.get(i)).append('\n');
                Files.writeString(dir.resolve(NAMES[stage]+".csv"),csv);
                System.out.printf(Locale.ROOT,"[Aqualumen] %s: %.1f FPS, 1%% low %.1f, p99 %.2f ms, worst %.2f ms%n",NAMES[stage],1000.0/mean,1000.0/slowMean,p99,max);
                screenshot.invoke(null,FabricLoader.getInstance().getGameDir().toFile(),"aqualumen-"+NAMES[stage]+".png",getFramebuffer.invoke(mc),(Consumer<Object>)ignored->{});
                next(mc);
            }
        } catch(Exception error) { disabled=true;System.err.println("[Aqualumen] Benchmark disabled: "+error);error.printStackTrace(); }
    }
}
