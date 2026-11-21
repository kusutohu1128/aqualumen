package dev.aqualumen.physics;

import java.lang.reflect.Field;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.shaderpack.materialmap.WorldRenderingSettings;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;
import net.caffeinemc.mods.sodium.client.render.chunk.vertex.format.ChunkVertexEncoder.Vertex;
import org.lwjgl.system.MemoryUtil;

/** Opt-in exact-world TEST observer. No producer-array, native-buffer or world writes. */
public final class ReceiverMesherProbe {
    private static final String WORLD = "b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static final ReceiverMesherScope SCOPE = new ReceiverMesherScope();
    private record Arm(Set<String> requested, String request, int frame, long nano) {}
    private record Write(Arm arm, ReceiverMesherScope.Capture capture, long pointer,
                         int stride, int material, int section) {}
    private static final ThreadLocal<Write> WRITES = new ThreadLocal<>();
    private static final ConcurrentHashMap<String, Map<String, Object>> EVENTS = new ConcurrentHashMap<>();
    private static final AtomicLong SEQUENCE = new AtomicLong();
    private static volatile Arm active;
    private static volatile String failure;
    private static Path game, requestPath;
    private static Properties properties;
    private static String requestHash;
    private static boolean done;
    private static int lastFrame = -1;

    private static Object call(Object object, String name) throws ReflectiveOperationException {
        return object.getClass().getMethod(name).invoke(object);
    }
    private static Object field(Object object, String name) throws ReflectiveOperationException {
        for (Class<?> type = object.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Field value = type.getDeclaredField(name);
                value.setAccessible(true);
                return value.get(object);
            } catch (NoSuchFieldException ignored) { }
        }
        throw new NoSuchFieldException(name);
    }
    private static String sha(Path path) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
    }
    private static Properties load(Path path) throws Exception {
        if (Files.isSymbolicLink(path) || Files.size(path) > 8192) throw new IllegalStateException("Request size/symlink rejected");
        var value = new Properties();
        try (var reader = Files.newBufferedReader(path)) { value.load(reader); }
        return value;
    }
    private static String key(int x, int y, int z, String face) { return x + "," + y + "," + z + ":" + face; }
    private static String face(int x, int y, int z) {
        if (Math.abs(x) + Math.abs(y) + Math.abs(z) != 1) throw new IllegalArgumentException("Aligned face required");
        return x != 0 ? (x > 0 ? "POS_X" : "NEG_X") : y != 0 ? (y > 0 ? "POS_Y" : "NEG_Y") : (z > 0 ? "POS_Z" : "NEG_Z");
    }
    private static Set<String> requested() {
        var values = new HashSet<String>();
        for (int i = 0; i < 16; i++) {
            int[] p = Arrays.stream(properties.getProperty("point." + i).split(",")).mapToInt(Integer::parseInt).toArray();
            if (p.length != 6 || p[0] < -202 || p[0] >= -183 || p[1] < 54 || p[1] >= 67 || p[2] < 319 || p[2] >= 334)
                throw new IllegalArgumentException("Bounded saved-point scope rejected");
            values.add(key(p[0], p[1], p[2], face(p[3], p[4], p[5])));
        }
        return Set.copyOf(values);
    }
    private static void guard(Object client, Object world) throws Exception {
        if (!(boolean)call(client, "method_1542")) throw new IllegalStateException("Singleplayer required");
        Object server = call(client, "method_1576");
        if (!Class.forName("net.minecraft.class_1132").isInstance(server) || (boolean)call(server, "method_3860"))
            throw new IllegalStateException("Integrated non-LAN server required");
        Object root = Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual = ((Path)server.getClass().getMethod("method_27050", root.getClass()).invoke(server, root)).toRealPath();
        Path expected = game.resolve("saves/AqualumenNaturalV2").toRealPath();
        if (!actual.equals(expected) || Files.isSymbolicLink(game.resolve("saves/AqualumenNaturalV2")))
            throw new IllegalStateException("Wrong TEST world");
        var marker = load(actual.resolve("aqualumen-world.properties"));
        if (!WORLD.equals(marker.getProperty("world_id")) || !"308060".equals(marker.getProperty("seed"))
                || !"minecraft:noise/overworld".equals(marker.getProperty("generator"))
                || (long)call(call(server, "method_30002"), "method_8412") != 308060)
            throw new IllegalStateException("Actual TEST world identity mismatch");
        if (!call(world, "method_27983").toString().equals("ResourceKey[minecraft:dimension / minecraft:overworld]"))
            throw new IllegalStateException("Overworld required");
        if (!Iris.isPackInUseQuick() || !Iris.getCurrentPackName().equals("Aqualumen-0.6.0.zip")
                || !sha(game.resolve("shaderpacks/Aqualumen-0.6.0.zip")).equals(properties.getProperty("pack_sha256"))
                || !WorldRenderingSettings.INSTANCE.shouldUseSeparateAo())
            throw new IllegalStateException("Pinned actual pack/separate-AO mismatch");
    }
    public static void clearQuad() { SCOPE.clear(); }
    public static void beforePush(Object renderer, Object quad) {
        SCOPE.clear();
        Arm arm = active;
        if (arm == null || failure != null) return;
        try {
            Object pos = field(renderer, "pos");
            int x = (int)call(pos, "method_10263"), y = (int)call(pos, "method_10264"), z = (int)call(pos, "method_10260");
            if (x < -202 || x >= -183 || y < 54 || y >= 67 || z < 319 || z >= 334) return;
            String normal = ((Enum<?>)call(quad, "normalFace")).name();
            String key = key(x, y, z, normal);
            if (!arm.requested().contains(key) || EVENTS.containsKey(key)) return;
            String state = field(renderer, "state").toString();
            if (!state.equals("Block{minecraft:sand}")) throw new IllegalStateException("Requested mesher owner is not actual sand");
            Object offset = field(renderer, "posOffset");
            var owner = new ReceiverMesherScope.Owner(x, y, z, state, normal,
                (float)offset.getClass().getField("x").get(offset),
                (float)offset.getClass().getField("y").get(offset),
                (float)offset.getClass().getField("z").get(offset));
            Vertex[] vertices = (Vertex[])field(renderer, "vertices");
            if (vertices.length != 4) throw new IllegalStateException("Pinned quad size mismatch");
            var inputs = new ReceiverVertex.Input[4];
            for (int i = 0; i < 4; i++) {
                Vertex v = vertices[i];
                inputs[i] = new ReceiverVertex.Input(v.x, v.y, v.z, v.u, v.v, v.color, v.ao, v.light);
            }
            SCOPE.begin(owner, vertices, inputs, WorldRenderingSettings.INSTANCE.shouldUseSeparateAo());
        } catch (Exception error) { fail(error); }
    }
    public static void beginWrite(long pointer, int stride, int material, Vertex[] array, int section) {
        if (WRITES.get() != null) {
            WRITES.remove(); SCOPE.clear(); fail(new IllegalStateException("Nested encoder write unsupported")); return;
        }
        var capture = SCOPE.take(array);
        Arm arm = active;
        if (capture == null || arm == null || failure != null) return;
        if (pointer == 0 || stride < 20 || stride > 128 || stride % 4 != 0) {
            fail(new IllegalStateException("Actual encoder bounds invalid")); return;
        }
        WRITES.set(new Write(arm, capture, pointer, stride, material, section));
    }
    public static void endWrite(long returned) {
        Write write = WRITES.get(); WRITES.remove();
        if (write == null || active != write.arm() || failure != null) return;
        try {
            if (returned != write.pointer() + 4L * write.stride()) throw new IllegalStateException("Actual encoder extent mismatch");
            var c = write.capture(); var o = c.owner();
            var raw = new ArrayList<Map<String, Object>>(); var encoded = new ArrayList<List<Long>>();
            for (int i = 0; i < 4; i++) {
                var v = c.raw().get(i); var expected = c.vertices().vertex(i);
                var words = new ArrayList<Long>();
                // Only the five words actually written by this invocation, not padding/uninitialized memory.
                for (int j = 0; j < 5; j++) words.add(Integer.toUnsignedLong(MemoryUtil.memGetInt(write.pointer() + (long)i * write.stride() + 4L * j)));
                if (words.get(2) != Integer.toUnsignedLong(expected.colorABGR())
                        || (words.get(4) & 65535L) != (expected.blockByte() | expected.skyByte() << 8))
                    throw new IllegalStateException("Observed encoder output disagrees with owned AO/light inputs");
                raw.add(Map.of("xyz", List.of(v.x(), v.y(), v.z()), "uv", List.of(v.u(), v.v()),
                    "colorABGR", Integer.toUnsignedLong(v.colorABGR()), "ao", v.ao(), "packedLight", Integer.toUnsignedLong(v.light())));
                encoded.add(List.copyOf(words));
            }
            var event = new LinkedHashMap<String, Object>();
            event.put("cell", List.of(o.x(), o.y(), o.z())); event.put("face", o.face()); event.put("blockState", o.state());
            event.put("chunkRelativeOffset", List.of(o.offsetX(), o.offsetY(), o.offsetZ()));
            event.put("rawVertices", raw); event.put("encodedFirst20ByteWords", encoded);
            event.put("stride", write.stride()); event.put("material", write.material()); event.put("section", write.section());
            event.put("threadId", c.threadId()); event.put("threadName", Thread.currentThread().getName());
            event.put("sequence", SEQUENCE.incrementAndGet()); event.put("elapsedNanoseconds", System.nanoTime() - write.arm().nano());
            event.put("armedRenderFrame", write.arm().frame()); event.put("requestId", write.arm().request());
            event.put("matchingSynchronousVertexArray", true); event.put("readOnlyNativeBuffer", true);
            EVENTS.putIfAbsent(key(o.x(), o.y(), o.z(), o.face()), Collections.unmodifiableMap(event));
        } catch (Exception error) { fail(error); }
    }
    private static void fail(Exception error) {
        failure = error.toString(); active = null;
        System.err.println("[Aqualumen Receiver Mesher] TEST safely stopped: " + failure);
    }
    private static String json(Object object) {
        if (object == null) return "null";
        if (object instanceof String s) return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
        if (object instanceof Map<?, ?> map) {
            var values = new StringJoiner(",", "{", "}"); map.forEach((k, v) -> values.add(json(k.toString()) + ":" + json(v))); return values.toString();
        }
        if (object instanceof Iterable<?> list) {
            var values = new StringJoiner(",", "[", "]"); list.forEach(v -> values.add(json(v))); return values.toString();
        }
        return object.toString();
    }
    private static void write(Map<String, Object> result) throws Exception {
        Path out = game.resolve("aqualumen-receiver-mesher-probe");
        if (Files.isSymbolicLink(out)) throw new IllegalStateException("Output symlink rejected");
        Files.createDirectories(out);
        Files.writeString(out.resolve(properties.getProperty("request_id") + ".json"), json(result) + "\n", StandardOpenOption.CREATE_NEW);
        done = true; active = null;
    }
    public static void frame() {
        if (done) return;
        int frame = SystemTimeUniforms.COUNTER.getAsInt(); if (frame == lastFrame) return; lastFrame = frame;
        try {
            if (game == null) game = FabricLoader.getInstance().getGameDir().toRealPath();
            if (!game.getParent().getFileName().toString().equals("Aqualumen Lab")) { done = true; return; }
            requestPath = game.resolve("config/aqualumen-receiver-mesher-probe.properties");
            if (!Files.exists(requestPath)) { active = null; return; }
            if (properties == null) {
                properties = load(requestPath);
                if (!"1".equals(properties.getProperty("schema")) || !WORLD.equals(properties.getProperty("world_id")))
                    throw new IllegalStateException("Opt-in request scope rejected");
                UUID.fromString(properties.getProperty("request_id")); requestHash = sha(requestPath);
            }
            Class<?> type = Class.forName("net.minecraft.class_310");
            Object client = type.getMethod("method_1551").invoke(null), world = type.getField("field_1687").get(client);
            if (world == null || call(client, "method_1576") == null) { active = null; return; }
            guard(client, world);
            if (!sha(requestPath).equals(requestHash)) throw new IllegalStateException("Request changed during capture");
            if (failure != null) throw new IllegalStateException(failure);
            if (active == null) {
                active = new Arm(requested(), properties.getProperty("request_id"), frame, System.nanoTime());
                System.out.println("[Aqualumen Receiver Mesher] ARMED exact V2; awaiting requested actual mesh encodes (TEST chunk reload allowed)");
                return;
            }
            if (!EVENTS.keySet().containsAll(active.requested())) return;
            var result = new LinkedHashMap<String, Object>();
            result.put("schema", "aqualumen-actual-receiver-mesher-v1"); result.put("world_id", WORLD); result.put("seed", 308060);
            result.put("request_id", active.request()); result.put("requestSHA256", requestHash);
            result.put("armedRenderFrame", active.frame()); result.put("collectionRenderFrame", frame);
            var entries = new ArrayList<>(EVENTS.entrySet()); entries.sort(Map.Entry.comparingByKey());
            result.put("actualMesherEncodes", entries.stream().map(Map.Entry::getValue).toList());
            result.put("requestedUniqueOwners", active.requested().size()); result.put("actualSeparateAo", true);
            result.put("nativeBufferModified", false); result.put("worldMutated", false); result.put("sourceUploaded", false);
            result.put("drawMatrixOrFilteredSamplingCaptured", false); result.put("liveResourceGeometryEpochProven", false);
            result.put("shadedSourceRadiance", false); result.put("fullGoalAchieved", false); write(result);
            System.out.println("[Aqualumen Receiver Mesher] PASS requested actual immutable mesher -> Iris encoder readbacks; not source radiance or draw proof");
        } catch (Exception error) {
            fail(error); done = true;
            if (properties != null) try { write(Map.of("error", error.toString(), "world_id", WORLD, "fullGoalAchieved", false)); } catch (Exception ignored) { }
        }
    }
}
