package dev.aqualumen.bench;

import java.io.OutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.CompletableFuture;

/** Replays client respawn identity lag without Minecraft, a GPU or user saves. */
public final class FinisherWaitTest {
    public static final class Key {
        private final String dimension;
        Key(String dimension) { this.dimension = dimension; }
        public String method_29177() { return dimension; }
    }
    public static final class World {
        private final String dimension;
        World(String dimension) { this.dimension = dimension; }
        public Key method_27983() { return new Key(dimension); }
    }
    public static final class Client {
        public Object field_1724 = new Object();
        public World field_1687;
        private Object camera;
        Client(String dimension, boolean followsPlayer) {
            field_1687 = dimension == null ? null : new World(dimension);
            camera = followsPlayer ? field_1724 : new Object();
        }
        public Object method_1560() { return camera; }
        public Object method_1576() { return null; } // A ready client must still fail the strict server guard.
    }
    private static void set(String name, Object value) throws Exception {
        Field field = Recorder.class.getDeclaredField(name); field.setAccessible(true); field.set(null, value);
    }
    private static String state() throws Exception {
        Field field = Recorder.class.getDeclaredField("state"); field.setAccessible(true); return (String)field.get(null);
    }
    private static Path replay(Client client, long elapsed) throws Exception {
        Path fixture = Files.createTempDirectory(Path.of("build"), "finisher-test.");
        set("initialized", true); set("disabled", false); set("state", "finishing");
        set("control", fixture); set("runDir", fixture); set("runId", "finisher-regression");
        set("scenarios", new String[]{"end-view"}); set("stage", 1); set("hudChanged", false);
        set("asyncError", null); set("pending", CompletableFuture.completedFuture(null));
        long now = System.nanoTime(); set("pollAt", now); set("start", now - elapsed);
        PrintStream stdout = System.out, stderr = System.err;
        try (PrintStream discard = new PrintStream(OutputStream.nullOutputStream())) {
            System.setOut(discard); System.setErr(discard); Recorder.frame(client);
        } finally { System.setOut(stdout); System.setErr(stderr); }
        return fixture;
    }
    private static void waiting(Client client) throws Exception {
        Path fixture = replay(client, 1_000_000L);
        if (!state().equals("finishing") || Files.exists(fixture.resolve("aborted.json")) || Files.exists(fixture.resolve("complete.json")))
            throw new AssertionError("Transient dimension/camera state must wait without aborting or accepting");
    }
    public static void main(String[] args) throws Exception {
        waiting(new Client("minecraft:the_end", true));
        waiting(new Client("minecraft:overworld", false));
        waiting(new Client(null, false));
        Client absent = new Client("minecraft:overworld", false); absent.field_1724 = null; absent.camera = null; waiting(absent);
        Path timedOut = replay(new Client("minecraft:the_end", true), 60_000_000_001L);
        if (!state().equals("aborted") || !Files.readString(timedOut.resolve("aborted.json")).contains("Client did not finish returning to the local Overworld camera"))
            throw new AssertionError("Unresolved client transition must fail after sixty seconds");
        Path ready = replay(new Client("minecraft:overworld", true), 1_000_000L);
        if (!state().equals("aborted") || !Files.readString(ready.resolve("aborted.json")).contains("An integrated singleplayer server is required"))
            throw new AssertionError("Ready state must still execute the unchanged strict world/server guard");
        System.out.println("Finisher readiness regressions passed (dimension, camera, absent player, timeout, strict guard)");
    }
}
