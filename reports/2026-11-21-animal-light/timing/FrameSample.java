package dev.aqualumen.animalqa;

import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import net.fabricmc.loader.api.FabricLoader;

// Private measurement only. The rendered client and its integrated-server
// save must both match the single disposable clone before emitting intervals.
public final class FrameSample {
    private static final String ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Path game;
    private static Method serverMethod;
    private static Object acceptedServer;
    private static boolean disabled;
    private static long previous, batchStart;
    private static final StringBuilder deltas=new StringBuilder(4096);

    private static boolean accepts(Object server) throws Exception {
        if(!Class.forName("net.minecraft.class_1132").isInstance(server) ||
           (boolean) server.getClass().getMethod("method_3860").invoke(server)) return false;
        Object root=Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual=((Path)server.getClass().getMethod("method_27050",root.getClass()).invoke(server,root)).toRealPath();
        Path wanted=game.resolve("saves/AqualumenNaturalV2");
        if(!wanted.equals(actual)) return false;
        Properties properties=new Properties();
        try(var reader=Files.newBufferedReader(actual.resolve("aqualumen-world.properties"))) {
            properties.load(reader);
        }
        return ID.equals(properties.getProperty("world_id"));
    }

    public static void record(Object client) {
        if(disabled) return;
        try {
            if(game==null) {
                game=FabricLoader.getInstance().getGameDir().toRealPath();
                Path opt=game.resolve("config/animal-frame-probe.enabled");
                if(!game.getParent().getFileName().toString().startsWith("aql-v190-run-") ||
                   !Files.isRegularFile(opt) || !game.toString().equals(Files.readString(opt).strip())) {
                    disabled=true;
                    return;
                }
                serverMethod=client.getClass().getMethod("method_1576");
            }
            Object server=serverMethod.invoke(client);
            if(server!=acceptedServer || server==null) {
                previous=0;
                deltas.setLength(0);
                acceptedServer=null;
                if(server==null) return;
                if(!accepts(server)) { disabled=true; return; }
                acceptedServer=server;
            }
            long now=System.nanoTime();
            if(previous==0) batchStart=now;
            else deltas.append(' ').append((now-previous+500)/1000);
            previous=now;
            if(now-batchStart>=1_000_000_000L) {
                System.out.println("AQ_RENDER_INTERVALS_US "+System.currentTimeMillis()+deltas);
                deltas.setLength(0);
                batchStart=now;
            }
        } catch(Exception error) {
            disabled=true;
            System.err.println("AQ_RENDER_PROBE_FAILED "+error);
        }
    }
    private FrameSample() {}
}
