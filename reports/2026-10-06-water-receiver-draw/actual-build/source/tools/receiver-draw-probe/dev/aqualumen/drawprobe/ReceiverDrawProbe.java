package dev.aqualumen.drawprobe;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;
import org.lwjgl.opengl.*;

/** Strict V2-only actual pre-draw snapshot and bounded owned GPU vertex decoder. */
public final class ReceiverDrawProbe {
    private static final String WORLD = "b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Path game, request;
    private static Properties properties;
    private static String requestHash;
    private static boolean armed, done;
    private static int firstFrame = -1;
    private static long warmStart;
    private static Map<String, Object> pending;
    private static Object call(Object object, String method) throws ReflectiveOperationException { return object.getClass().getMethod(method).invoke(object); }
    private static Properties load(Path path) throws Exception {
        if (Files.isSymbolicLink(path) || Files.size(path) > 8192) throw new IllegalStateException("Opt-in request path rejected");
        var value = new Properties(); try (var reader = Files.newBufferedReader(path)) { value.load(reader); } return value;
    }
    private static String sha(byte[] bytes) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    private static void guard() throws Exception {
        Class<?> type = Class.forName("net.minecraft.class_310"); Object client = type.getMethod("method_1551").invoke(null);
        Object world = type.getField("field_1687").get(client), server = call(client, "method_1576");
        if (world == null || !(boolean)call(client, "method_1542") || !Class.forName("net.minecraft.class_1132").isInstance(server)
                || (boolean)call(server, "method_3860")) throw new IllegalStateException("Integrated non-LAN TEST required");
        Object root = Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual = ((Path)server.getClass().getMethod("method_27050", root.getClass()).invoke(server, root)).toRealPath();
        Path expected = game.resolve("saves/AqualumenNaturalV2").toRealPath();
        if (!actual.equals(expected) || Files.isSymbolicLink(game.resolve("saves/AqualumenNaturalV2"))) throw new IllegalStateException("Wrong TEST world");
        var marker = load(actual.resolve("aqualumen-world.properties"));
        if (!WORLD.equals(marker.getProperty("world_id")) || !"308060".equals(marker.getProperty("seed"))
                || !"minecraft:noise/overworld".equals(marker.getProperty("generator"))
                || (long)call(call(server, "method_30002"), "method_8412") != 308060
                || !call(world, "method_27983").toString().equals("ResourceKey[minecraft:dimension / minecraft:overworld]"))
            throw new IllegalStateException("Actual TEST identity/dimension rejected");
        if (!Iris.isPackInUseQuick() || !Iris.getCurrentPackName().equals("Aqualumen-0.6.0.zip")
                || !sha(Files.readAllBytes(game.resolve("shaderpacks/Aqualumen-0.6.0.zip"))).equals(properties.getProperty("pack_sha256"))
                || !sha(Files.readAllBytes(request)).equals(requestHash)) throw new IllegalStateException("Actual pack/request changed");
        if (!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Render thread required");
    }
    public static void frame() {
        if (done || armed) return;
        try {
            if (game == null) game = FabricLoader.getInstance().getGameDir().toRealPath();
            if (!game.getParent().getFileName().toString().equals("Aqualumen Lab")) { done = true; return; }
            request = game.resolve("config/aqualumen-receiver-draw-probe.properties"); if (!Files.exists(request)) return;
            if (properties == null) {
                properties = load(request); UUID.fromString(properties.getProperty("request_id"));
                if (!"1".equals(properties.getProperty("schema")) || !WORLD.equals(properties.getProperty("world_id"))) throw new IllegalStateException("Request scope rejected");
                requestHash = sha(Files.readAllBytes(request));
            }
            Class<?> type = Class.forName("net.minecraft.class_310"); Object client = type.getMethod("method_1551").invoke(null);
            if (type.getField("field_1687").get(client) == null || call(client, "method_1576") == null) return;
            int frame = SystemTimeUniforms.COUNTER.getAsInt(); long now = System.nanoTime();
            if (warmStart == 0) { guard(); warmStart = now; firstFrame = frame; return; }
            if (now-warmStart < 5_000_000_000L || frame-firstFrame < 120) return;
            guard(); armed = true;
            System.out.println("[Aqualumen Receiver Draw] ARMED exact V2 after warmup; awaiting actual terrain draw");
        } catch (Exception error) { fail(error); }
    }
    private static float[] uniform(int program, String name, int count) {
        int location = GL20.glGetUniformLocation(program, name); if (location < 0) throw new IllegalStateException("Actual terrain uniform absent: " + name);
        float[] values = new float[count]; GL20.glGetUniformfv(program, location, values);
        for (float value : values) if (!Float.isFinite(value)) throw new IllegalStateException("Actual uniform nonfinite"); return values;
    }
    private static List<Float> floats(float[] values) { var list = new ArrayList<Float>(); for (float value : values) list.add(value); return list; }
    private static Map<String, Object> texture(int program) throws Exception {
        int location = GL20.glGetUniformLocation(program, "gtexture"); if (location < 0) throw new IllegalStateException("Actual gtexture absent");
        int unit = GL20.glGetUniformi(program, location), active = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        if (unit < 0 || unit >= GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS)) throw new IllegalStateException("Actual sampler unit invalid");
        var result = new LinkedHashMap<String, Object>();
        try {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+unit); int id = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
            if (id <= 0 || !GL11.glIsTexture(id)) throw new IllegalStateException("Actual draw atlas binding missing");
            result.put("unit", unit); result.put("textureID", id);
            result.put("size", List.of(GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_WIDTH), GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_HEIGHT)));
            int sampler = GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING, unit); result.put("samplerObject", sampler);
            for (var entry : Map.of("minFilter", GL11.GL_TEXTURE_MIN_FILTER, "magFilter", GL11.GL_TEXTURE_MAG_FILTER,
                    "wrapS", GL11.GL_TEXTURE_WRAP_S, "wrapT", GL11.GL_TEXTURE_WRAP_T).entrySet()) {
                result.put("texture_"+entry.getKey(), GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D, entry.getValue()));
                result.put("effective_"+entry.getKey(), sampler == 0 ? result.get("texture_"+entry.getKey()) : GL33.glGetSamplerParameteri(sampler, entry.getValue()));
            }
            result.put("baseLevel", GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D, GL12.GL_TEXTURE_BASE_LEVEL));
            result.put("maxLevel", GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D, GL12.GL_TEXTURE_MAX_LEVEL));
            result.put("effectiveMinLOD", sampler == 0 ? GL11.glGetTexParameterf(GL11.GL_TEXTURE_2D, GL12.GL_TEXTURE_MIN_LOD) : GL33.glGetSamplerParameterf(sampler, GL12.GL_TEXTURE_MIN_LOD));
            result.put("effectiveMaxLOD", sampler == 0 ? GL11.glGetTexParameterf(GL11.GL_TEXTURE_2D, GL12.GL_TEXTURE_MAX_LOD) : GL33.glGetSamplerParameterf(sampler, GL12.GL_TEXTURE_MAX_LOD));
        } finally { GL13.glActiveTexture(active); }
        if (GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE) != active) throw new IllegalStateException("Texture query did not restore active unit");
        result.put("activeTextureBeforeAfter", active); result.put("textureDataModified", false);
        return result;
    }
    public static void beforeDraw(Object batch) {
        if (!armed || done || pending != null) return;
        try {
            guard(); int program = GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
            if (program <= 0 || GL20.glGetProgrami(program, GL20.GL_LINK_STATUS) == 0) return;
            int count = GL20.glGetProgrami(program, GL20.GL_ATTACHED_SHADERS);
            if (count < 1 || count > 8) return;
            int[] length = new int[1], ids = new int[count]; GL20.glGetAttachedShaders(program, length, ids);
            String vertex = null, fragment = null;
            for (int id : ids) {
                int type = GL20.glGetShaderi(id, GL20.GL_SHADER_TYPE), size = GL20.glGetShaderi(id, GL20.GL_SHADER_SOURCE_LENGTH);
                if (size < 1 || size > 262144) throw new IllegalStateException("Actual linked stage source bounds rejected");
                String source = GL20.glGetShaderSource(id);
                if (type == GL20.GL_VERTEX_SHADER) vertex = source;
                if (type == GL20.GL_FRAGMENT_SHADER) fragment = source;
            }
            if (vertex == null || fragment == null || !fragment.contains("terrainLight") || !fragment.contains("vertexColor.a") || fragment.contains("refractionTrace")) return;
            float[] matrix = uniform(program, "iris_LightmapTextureMatrix", 16), shrink = uniform(program, "u_TexCoordShrink", 2);
            var attrs = new LinkedHashMap<String, Object>(); var locations = new LinkedHashMap<String, Integer>();
            int stride = 0; long origin = 0;
            String[] names = {"a_Position", "a_Color", "a_TexCoord", "a_LightAndData"};
            int[] sizes = {2, 4, 2, 4}, types = {GL11.GL_UNSIGNED_INT, GL11.GL_UNSIGNED_BYTE, GL11.GL_UNSIGNED_SHORT, GL11.GL_UNSIGNED_BYTE}, offsets = {0, 8, 12, 16};
            for (int i = 0; i < names.length; i++) {
                int location = GL20.glGetAttribLocation(program, names[i]); if (location < 0) throw new IllegalStateException("Actual terrain attribute absent");
                int size = GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_SIZE), type = GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_TYPE);
                int actualStride = GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_STRIDE), normalized = GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_NORMALIZED);
                int integer = GL20.glGetVertexAttribi(location, GL30.GL_VERTEX_ATTRIB_ARRAY_INTEGER), buffer = GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_BUFFER_BINDING);
                long offset = GL20.glGetVertexAttribPointer(location, GL20.GL_VERTEX_ATTRIB_ARRAY_POINTER);
                if (i == 0) { stride = actualStride; origin = offset; }
                if (GL20.glGetVertexAttribi(location, GL20.GL_VERTEX_ATTRIB_ARRAY_ENABLED) == 0 || buffer <= 0
                        || size != sizes[i] || type != types[i] || actualStride != stride || offset-origin != offsets[i]
                        || normalized != (i == 1 ? 1 : 0) || integer != (i == 1 ? 0 : 1))
                    throw new IllegalStateException("Actual VAO vertex format not qualified: " + names[i]);
                locations.put(names[i], location);
                attrs.put(names[i], Map.of("location", location, "size", size, "type", type, "stride", actualStride,
                    "normalized", normalized, "integer", integer, "buffer", buffer, "offset", offset));
            }
            byte[] words;
            try (var stream = ReceiverDrawProbe.class.getResourceAsStream("/receiver-vertices.words")) {
                if (stream == null) throw new IllegalStateException("Archived actual vertex fixture missing"); words = stream.readAllBytes();
            }
            if (!sha(words).equals(properties.getProperty("vertex_fixture_sha256"))) throw new IllegalStateException("Actual input fixture identity changed");
            var result = new LinkedHashMap<String, Object>();
            result.put("schema", "aqualumen-actual-receiver-draw-v1"); result.put("world_id", WORLD); result.put("seed", 308060);
            result.put("request_id", properties.getProperty("request_id")); result.put("requestSHA256", requestHash);
            result.put("drawProgram", program); result.put("vao", GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING));
            result.put("frame", SystemTimeUniforms.COUNTER.getAsInt()); result.put("batchSize", call(batch, "size"));
            result.put("threadId", Thread.currentThread().threadId()); result.put("renderer", GL11.glGetString(GL11.GL_RENDERER)); result.put("glVersion", GL11.glGetString(GL11.GL_VERSION));
            result.put("linkedVertexSource", vertex); result.put("linkedFragmentSource", fragment);
            result.put("linkedVertexSourceSHA256", sha(vertex.getBytes(StandardCharsets.UTF_8))); result.put("linkedFragmentSourceSHA256", sha(fragment.getBytes(StandardCharsets.UTF_8)));
            result.put("lightmapMatrixColumnMajor", floats(matrix)); result.put("texCoordShrink", floats(shrink)); result.put("attributes", attrs);
            result.put("gtexture", texture(program)); result.put("vertexFixtureSHA256", sha(words));
            result.put("gpuDecode", GpuVertexDecode.run(vertex, words, matrix, shrink, locations, stride));
            result.put("archivedActualVertexInputs", true); result.put("liveMeshResourceEpochProven", false);
            result.put("filteredFragmentFetchProven", false); result.put("shadedWorldSourceUploaded", false); result.put("fullGoalAchieved", false);
            if (GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM) != program) throw new IllegalStateException("Original draw program not restored");
            pending = result;
        } catch (Exception error) { fail(error); }
    }
    public static void afterDraw() {
        if (pending == null || done) return;
        try {
            if (!pending.get("drawProgram").equals(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM))
                    || !pending.get("vao").equals(GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING))
                    || !pending.get("frame").equals(SystemTimeUniforms.COUNTER.getAsInt())) throw new IllegalStateException("Original draw scope changed");
            pending.put("originalMultiDrawReturned", true); write(pending);
            System.out.println("[Aqualumen Receiver Draw] PASS actual draw inputs and owned actual-source GPU vertex decoding captured; not source radiance");
        } catch (Exception error) { fail(error); }
    }
    private static String json(Object object) {
        if (object == null) return "null";
        if (object instanceof String s) return "\""+s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")+"\"";
        if (object instanceof Map<?, ?> m) { var values = new StringJoiner(",", "{", "}"); m.forEach((k,v)->values.add(json(k.toString())+":"+json(v))); return values.toString(); }
        if (object instanceof Iterable<?> l) { var values = new StringJoiner(",", "[", "]"); l.forEach(v->values.add(json(v))); return values.toString(); }
        return object.toString();
    }
    private static void write(Map<String, Object> result) throws Exception {
        Path directory = game.resolve("aqualumen-receiver-draw-probe"); if (Files.isSymbolicLink(directory)) throw new IllegalStateException("Output symlink rejected");
        Files.createDirectories(directory); Files.writeString(directory.resolve(properties.getProperty("request_id")+".json"), json(result)+"\n", StandardOpenOption.CREATE_NEW);
        done = true; armed = false;
    }
    private static void fail(Exception error) {
        done = true; armed = false; pending = null; System.err.println("[Aqualumen Receiver Draw] TEST safely stopped: "+error);
        if (properties != null) try { write(Map.of("error", error.toString(), "world_id", WORLD, "fullGoalAchieved", false)); } catch (Exception ignored) { }
    }
}
