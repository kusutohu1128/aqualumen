package dev.aqualumen.bench;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.*;
import java.util.Properties;
import net.fabricmc.loader.api.FabricLoader;

/** Render-tail timestamps in the single opted-in private world, for the door campaign. */
public final class Recorder {
    private static final String ID = "b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Object server;
    private static BufferedWriter output;
    private static boolean disabled;
    private static int count;

    public static void frame(Object client) {
        if (disabled) return;
        final long tick = System.nanoTime();
        try {
            Object current = client.getClass().getMethod("method_1576").invoke(client);
            if (current == null) return;
            if (server != current) {
                if (server != null) throw new IllegalStateException("world changed");
                Path game = FabricLoader.getInstance().getGameDir().toRealPath();
                String optIn = System.getProperty("aqualumen.house.frameclock");
                if (optIn == null || !game.equals(Path.of(optIn).toRealPath())
                    || !game.getParent().getFileName().toString().startsWith("house-clock-")
                    || !Files.readString(game.resolve("config/house-frameclock.enabled")).trim().equals(ID))
                    throw new IllegalStateException("private opt-in");
                if (!(boolean)client.getClass().getMethod("method_1542").invoke(client)
                    || (boolean)current.getClass().getMethod("method_3860").invoke(current))
                    throw new IllegalStateException("server type");
                Object root = Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
                Path actual = ((Path)current.getClass().getMethod("method_27050", root.getClass()).invoke(current, root)).toRealPath();
                if (!actual.equals(game.resolve("saves/AqualumenNaturalV2").toRealPath())) throw new IllegalStateException("world path");
                Properties marker = new Properties();
                try (var stream = Files.newInputStream(actual.resolve("aqualumen-world.properties"))) { marker.load(stream); }
                if (!ID.equals(marker.getProperty("world_id")) || !"308060".equals(marker.getProperty("seed")))
                    throw new IllegalStateException("world id");
                output = Files.newBufferedWriter(game.resolve("client-frames.csv"), StandardOpenOption.CREATE_NEW);
                server = current;
                Object fb = client.getClass().getMethod("method_1522").invoke(client);
                System.out.println("[HouseClock] private frame clock ready; framebuffer "
                    +fb.getClass().getField("field_1482").getInt(fb)+"x"
                    +fb.getClass().getField("field_1481").getInt(fb));
            }
            output.write(Long.toString(tick));
            output.newLine();
            if (++count % 64 == 0) output.flush();
        } catch (Exception e) {
            disabled = true;
            System.err.println("[HouseClock] disabled " + e);
            if (output != null) try { output.close(); } catch (IOException ignored) {}
        }
    }
}
