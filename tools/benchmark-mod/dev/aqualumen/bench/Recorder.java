package dev.aqualumen.bench;

import net.fabricmc.loader.api.FabricLoader;
import java.lang.reflect.*;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.regex.Pattern;

/** Development instrumentation, explicitly enabled and confined to one local world.
 * No network connection, chat message, CLI process, downloaded world or terrain edit.
 * Intermediary reflection keeps this small tool independent of a remapped client JAR.
 */
public final class Recorder {
    private static final Set<String> KNOWN = Set.of("ocean-day", "coast-day", "river-day", "ocean-dusk", "ocean-night", "ocean-rain", "underwater", "moving-view", "boat-contact", "chunk-traversal", "cave-water", "glass-layers", "nether-view", "end-view");
    private static final double BUDGET = 1000.0 / 60.0;
    private static Path game, control, runDir, worldPath;
    private static Properties config, worldMarker;
    private static Object minecraft, server, serverWorld, dispatcher, source;
    private static Object options, originalTutorial;
    private static boolean originalHud, hudChanged, initialized, disabled, autoQuit;
    private static String state = "idle", runId = "", requestId = "", playerUuid = "", playerTarget = "", packHash = "";
    private static String[] scenarios;
    private static int stage = -1;
    private static long pollAt, validateAt, start, sampleStart, previous, motionAt;
    private static double warmupSeconds, sampleSeconds;
    private static final ArrayList<Long> timings = new ArrayList<>();
    private static final Map<String, Site> sites = new LinkedHashMap<>();
    private static final ArrayList<int[]> glassFixtures = new ArrayList<>();
    private static CompletableFuture<Void> pending;
    private static Path screenshotPath;
    private static long screenshotStarted;
    private static long physicsAt;
    private static final ArrayList<Map<String, Object>> physicsSamples = new ArrayList<>();
    private static int maximumContacts;
    private static double maximumForce;
    private static boolean physicsActive;
    private static Method execute;
    private static volatile Throwable asyncError;

    private record Site(double x, double y, double z, float yaw, float pitch, String biome, int depth) {}

    private static Object call(Object object, String method) throws Exception {
        try { return object.getClass().getMethod(method).invoke(object); }
        catch (NoSuchMethodException publicLookupFailed) {
            for (Class<?> type = object.getClass(); type != null; type = type.getSuperclass()) {
                try { Method target = type.getDeclaredMethod(method); target.setAccessible(true); return target.invoke(object); }
                catch (NoSuchMethodException ignored) {}
            }
            throw publicLookupFailed;
        }
    }
    private static Object optionalCall(Object object, String method) {
        try { return call(object, method); }
        catch (Exception error) { return "Unavailable: " + error.getClass().getSimpleName(); }
    }
    private static String optionalCloudSetting() {
        try {
            Object manager = Class.forName("net.irisshaders.iris.Iris").getMethod("getPipelineManager").invoke(null);
            Object pipeline = call(manager, "getPipelineNullable");
            return pipeline == null ? "No current pipeline" : call(pipeline, "getCloudSetting").toString();
        } catch (Exception error) { return "Unavailable: " + error.getClass().getSimpleName(); }
    }
    private static Field field(Object object, String name) throws Exception {
        for (Class<?> type = object.getClass(); type != null; type = type.getSuperclass()) {
            try { Field value = type.getDeclaredField(name); value.setAccessible(true); return value; }
            catch (NoSuchFieldException ignored) {}
        }
        throw new NoSuchFieldException(name);
    }
    private static Object value(Object object, String name) throws Exception { return field(object, name).get(object); }
    private static Properties properties(Path path) throws Exception {
        Properties result = new Properties();
        try (var reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) { result.load(reader); }
        return result;
    }
    private static void atomic(Path path, String text) throws Exception {
        Path temporary = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(temporary, text, StandardCharsets.UTF_8);
        try { Files.move(temporary, path, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
        catch (AtomicMoveNotSupportedException error) { Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING); }
    }
    private static String hash(Path path) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
    }
    private static Map<String, Object> map(Object... pairs) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int index = 0; index < pairs.length; index += 2) result.put((String)pairs[index], pairs[index + 1]);
        return result;
    }
    private static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof String text) return "\"" + text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
        if (value instanceof Map<?, ?> object) {
            StringJoiner result = new StringJoiner(",", "{", "}");
            object.forEach((key, item) -> result.add(json(String.valueOf(key)) + ":" + json(item)));
            return result.toString();
        }
        if (value instanceof Iterable<?> items) {
            StringJoiner result = new StringJoiner(",", "[", "]");
            items.forEach(item -> result.add(json(item))); return result.toString();
        }
        if (value instanceof Object[] items) return json(Arrays.asList(items));
        return String.valueOf(value);
    }
    private static void status(String note) throws Exception {
        atomic(control.resolve("status.json"), json(map("state", state, "run_id", runId, "request_id", requestId,
            "scenario", stage >= 0 && scenarios != null && stage < scenarios.length ? scenarios[stage] : "",
            "note", note, "updated_utc", Instant.now().toString())) + "\n");
        System.out.println("[Aqualumen] Benchmark " + state + ": " + note);
    }
    private static void init(Object mc) throws Exception {
        minecraft = mc;
        game = FabricLoader.getInstance().getGameDir().toRealPath();
        if (!game.getParent().getFileName().toString().equals("Aqualumen Lab")) { disabled = true; return; }
        if (!Files.exists(game.resolve("config/aqualumen-benchmark.enabled"))) return;
        if (!Files.exists(game.resolve("config/aqualumen-benchmark.properties"))) return;
        control = game.resolve("aqualumen-benchmark"); Files.createDirectories(control);
        initialized = true; status("Waiting for a local control request");
    }
    private static String irisName() throws Exception { return (String)Class.forName("net.irisshaders.iris.Iris").getMethod("getCurrentPackName").invoke(null); }
    private static boolean iris(String method) throws Exception { return (boolean)Class.forName("net.irisshaders.iris.Iris").getMethod(method).invoke(null); }
    private static Object option(String method) throws Exception { return call(call(options, method), "method_41753"); }
    private static int[] resolution(Object mc, boolean framebuffer) throws Exception {
        Object object = call(mc, framebuffer ? "method_1522" : "method_22683");
        return framebuffer ? new int[]{(int)value(object, "field_1482"), (int)value(object, "field_1481")} : new int[]{(int)call(object, "method_4489"), (int)call(object, "method_4506")};
    }
    private static List<Integer> size(Object mc, boolean framebuffer) throws Exception {
        int[] result = resolution(mc, framebuffer); return List.of(result[0], result[1]);
    }
    private static void guard(Object mc, boolean checkHash) throws Exception {
        Object currentServer = call(mc, "method_1576");
        if (currentServer == null || !Class.forName("net.minecraft.class_1132").isInstance(currentServer) || !(boolean)call(mc, "method_1542"))
            throw new IllegalStateException("An integrated singleplayer server is required");
        if ((boolean)call(currentServer, "method_3860")) throw new IllegalStateException("LAN-published worlds are forbidden");
        Object saveRoot = Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path actual = ((Path)currentServer.getClass().getMethod("method_27050", saveRoot.getClass()).invoke(currentServer, saveRoot)).toRealPath();
        Path expected = game.resolve("saves").resolve(config.getProperty("world")).toRealPath();
        if (!actual.equals(expected) || !expected.startsWith(game.resolve("saves")) || !expected.getFileName().toString().startsWith("AqualumenNatural"))
            throw new IllegalStateException("Wrong world directory: " + actual);
        Properties marker = properties(actual.resolve("aqualumen-world.properties"));
        if (!marker.getProperty("world_id", "").equals(config.getProperty("world_id")) || !marker.getProperty("generator", "").equals("minecraft:noise/overworld"))
            throw new IllegalStateException("World UUID or vanilla noise generator marker mismatch");
        UUID.fromString(marker.getProperty("world_id"));
        Object actualWorld = call(currentServer, "method_30002");
        if ((long)call(actualWorld, "method_8412") != Long.parseLong(marker.getProperty("seed"))) throw new IllegalStateException("Actual world seed disagrees with marker");
        Object generator = call(call(actualWorld, "method_14178"), "method_12129");
        if (!Class.forName("net.minecraft.class_3754").isInstance(generator) || !biome(call(generator, "method_41541")).equals("minecraft:overworld"))
            throw new IllegalStateException("Actual overworld generator is not vanilla overworld noise");
        Object player = value(mc, "field_1724");
        if (player == null || value(mc, "field_1687") == null) throw new IllegalStateException("Player not in a loaded world");
        if (call(mc, "method_1560") != player) throw new IllegalStateException("Camera must follow the identified local player, not another entity");
        String actualUuid = call(player, "method_5667").toString();
        if (!playerUuid.isEmpty() && !actualUuid.equals(playerUuid)) throw new IllegalStateException("Player UUID changed");
        Object manager = call(currentServer, "method_3760");
        List<?> players = (List<?>)call(manager, "method_14571");
        if (players.size() != 1 || !call(players.getFirst(), "method_5667").toString().equals(actualUuid))
            throw new IllegalStateException("Exactly the local UUID player is required");
        if (!iris("isPackInUseQuick") || iris("isFallback") || !irisName().equals(config.getProperty("expected_pack")))
            throw new IllegalStateException("Expected shader pack is not active, or Iris fallback is active");
        if (((Optional<?>)Class.forName("net.irisshaders.iris.Iris").getMethod("getStoredError").invoke(null)).isPresent())
            throw new IllegalStateException("Iris reports a stored shader error");
        if (checkHash) {
            String actualHash = hash(game.resolve("shaderpacks").resolve(config.getProperty("expected_pack")));
            if (!actualHash.equals(config.getProperty("expected_pack_sha256"))) throw new IllegalStateException("Installed pack SHA-256 mismatch");
            packHash = actualHash;
        }
        options = value(mc, "field_1690");
        for (boolean framebuffer : new boolean[]{false, true}) {
            int[] dimensions = resolution(mc, framebuffer);
            if (dimensions[0] != Integer.parseInt(config.getProperty("width")) || dimensions[1] != Integer.parseInt(config.getProperty("height")))
                throw new IllegalStateException((framebuffer ? "Framebuffer" : "Window") + " resolution mismatch: " + Arrays.toString(dimensions));
        }
        if ((int)option("method_42503") != Integer.parseInt(config.getProperty("render_chunks")) || (int)option("method_42510") != Integer.parseInt(config.getProperty("simulation_chunks")))
            throw new IllegalStateException("Render or simulation distance mismatch");
        UUID targetUuid = UUID.fromString(actualUuid);
        long upper = targetUuid.getMostSignificantBits(), lower = targetUuid.getLeastSignificantBits();
        playerTarget = "@a[limit=1,nbt={UUID:[I;" + (int)(upper >>> 32) + "," + (int)upper + "," + (int)(lower >>> 32) + "," + (int)lower + "]}]";
        server = currentServer; worldPath = actual; worldMarker = marker; playerUuid = actualUuid;
    }
    private static void command(String text) throws Exception {
        try { execute.invoke(dispatcher, text, source); }
        catch (InvocationTargetException error) { throw new IllegalStateException("Integrated-server command failed: " + text, error.getCause()); }
    }
    private static CompletableFuture<Void> local(CheckedRunnable action) {
        CompletableFuture<Void> result = new CompletableFuture<>();
        ((Executor)server).execute(() -> { try { action.run(); result.complete(null); } catch (Throwable error) { result.completeExceptionally(error); } });
        return result;
    }
    @FunctionalInterface private interface CheckedRunnable { void run() throws Exception; }
    private static String biome(Object entry) throws Exception { return (String)Class.forName("net.minecraft.class_6880").getMethod("method_55840").invoke(entry); }
    private static Object pos(int x, int y, int z) throws Exception { return Class.forName("net.minecraft.class_2338").getConstructor(int.class, int.class, int.class).newInstance(x, y, z); }
    private static boolean water(int x, int y, int z) throws Exception {
        return serverWorld.getClass().getMethod("method_8320", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, pos(x, y, z)).toString().contains("minecraft:water");
    }
    private static boolean air(int x, int y, int z) throws Exception {
        Object block = serverWorld.getClass().getMethod("method_8320", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, pos(x, y, z));
        return (boolean)call(block, "method_26215");
    }
    private static Site cave() throws Exception {
        Object sky = Class.forName("net.minecraft.class_1944").getField("field_9284").get(null);
        Method skyLight = serverWorld.getClass().getMethod("method_8314", sky.getClass(), Class.forName("net.minecraft.class_2338"));
        // Bounded optional search in the spawn region, independent of default suite.
        for (int radius = 0; radius <= 128; radius += 16) {
            for (int x = -radius; x <= radius; x += 16) for (int z = -radius; z <= radius; z += 16) {
                if (radius != 0 && Math.abs(x) != radius && Math.abs(z) != radius) continue;
                for (int y = 48; y >= -40; y--) {
                    if (!water(x, y, z) || !air(x, y + 1, z) || !air(x, y + 2, z) || !air(x, y + 3, z)) continue;
                    if ((int)skyLight.invoke(serverWorld, sky, pos(x, y + 2, z)) != 0) continue;
                    int depth = 1; while (depth < 32 && water(x, y - depth, z)) depth++;
                    Object actualBiome = serverWorld.getClass().getMethod("method_23753", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, pos(x, y, z));
                    return new Site(x + .5, y + 1.1, z + .5, 0, 28, biome(actualBiome), depth);
                }
            }
        }
        throw new IllegalStateException("Optional cave-water search found no enclosed natural aquifer with an air pocket within128blocks");
    }
    private static Site discover(String kind) throws Exception {
        Predicate<Object> match = entry -> {
            try {
                String id = biome(entry);
                return switch (kind) {
                    case "ocean" -> id.contains("deep_") && id.contains("ocean") && !id.contains("frozen");
                    case "coast" -> id.equals("minecraft:beach");
                    case "river" -> id.equals("minecraft:river");
                    default -> false;
                };
            } catch (Exception error) { throw new RuntimeException(error); }
        };
        Object pair = serverWorld.getClass().getMethod("method_42108", Predicate.class, Class.forName("net.minecraft.class_2338"), int.class, int.class, int.class)
            .invoke(serverWorld, match, pos(0, 63, 0), 6400, 64, 64);
        if (pair == null) throw new IllegalStateException("No natural " + kind + " biome found within 6400 blocks");
        Object center = call(pair, "getFirst");
        int centerX = (int)call(center, "method_10263"), centerZ = (int)call(center, "method_10260");
        // Inspect only naturally generated water. A biome coordinate may be on a bank.
        for (int radius = 0; radius <= 128; radius += 8) {
            for (int dx = -radius; dx <= radius; dx += 8) for (int dz = -radius; dz <= radius; dz += 8) {
                if (radius != 0 && Math.abs(dx) != radius && Math.abs(dz) != radius) continue;
                int x = centerX + dx, z = centerZ + dz;
                for (int y = 80; y >= 48; y--) if (water(x, y, z) && !water(x, y + 1, z)) {
                    int depth = 1; while (depth < 32 && water(x, y - depth, z)) depth++;
                    if (kind.equals("ocean") && depth < 8) continue;
                    Object actualBiome = serverWorld.getClass().getMethod("method_23753", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, pos(x, y, z));
                    float yaw = kind.equals("coast") ? (float)Math.toDegrees(Math.atan2(dx, -dz)) : -45.0f;
                    return new Site(x + .5, y + 2.1, z + .5, yaw, 9.0f, biome(actualBiome), depth);
                }
            }
        }
        throw new IllegalStateException("Located " + kind + " biome has no suitable natural surface water");
    }
    private static void suppressHud(Object mc) throws Exception {
        originalHud = (boolean)value(options, "field_1842");
        originalTutorial = value(options, "field_1875");
        field(options, "field_1842").setBoolean(options, true);
        Object none = Class.forName("net.minecraft.class_1157").getField("field_5653").get(null);
        Object tutorial = call(mc, "method_1577");
        tutorial.getClass().getMethod("method_4910", none.getClass()).invoke(tutorial, none);
        call(call(mc, "method_1566"), "method_2000");
        hudChanged = true;
    }
    private static void restoreHud(Object mc) throws Exception {
        if (!hudChanged) return;
        field(options, "field_1842").setBoolean(options, originalHud);
        Object tutorial = call(mc, "method_1577");
        tutorial.getClass().getMethod("method_4910", originalTutorial.getClass()).invoke(tutorial, originalTutorial);
        hudChanged = false;
    }
    private static void startRun(Object mc, Properties request) throws Exception {
        if (Set.of("preparing", "preparing-scene", "warmup", "sampling", "screenshot", "finishing").contains(state)) throw new IllegalStateException("A run is already active");
        runDir = null; stage = -1; scenarios = null;
        config = properties(game.resolve("config/aqualumen-benchmark.properties"));
        if (!config.getProperty("schema", "").equals("2") || !request.getProperty("world_id", "").equals(config.getProperty("world_id")))
            throw new IllegalStateException("Configuration schema or request world UUID mismatch");
        playerUuid = ""; guard(mc, true);
        runId = request.getProperty("run_id", "");
        if (!runId.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")) throw new IllegalArgumentException("Invalid run identifier");
        scenarios = request.getProperty("scenarios", "").split(",");
        if (scenarios.length == 0 || new HashSet<>(Arrays.asList(scenarios)).size() != scenarios.length || !KNOWN.containsAll(Arrays.asList(scenarios)))
            throw new IllegalArgumentException("Unknown or duplicate scenarios");
        warmupSeconds = Double.parseDouble(request.getProperty("warmup_seconds", "20"));
        sampleSeconds = Double.parseDouble(request.getProperty("sample_seconds", "30"));
        if (!Double.isFinite(warmupSeconds) || !Double.isFinite(sampleSeconds) || warmupSeconds < 5 || sampleSeconds < 5 || sampleSeconds > 300)
            throw new IllegalArgumentException("Invalid warmup/sample durations");
        autoQuit = Boolean.parseBoolean(request.getProperty("auto_quit", "false"));
        Path runs = control.resolve("runs"); Files.createDirectories(runs);
        runDir = runs.resolve(runId); Files.createDirectory(runDir);
        sites.clear(); timings.clear(); stage = -1; previous = 0; asyncError = null;
        suppressHud(mc);
        Object commandManager = call(server, "method_3734");
        dispatcher = call(commandManager, "method_9235");
        source = call(call(server, "method_3739"), "method_9217");
        execute = dispatcher.getClass().getMethod("execute", String.class, Object.class);
        serverWorld = call(server, "method_30002");
        pending = local(() -> {
            command("gamemode spectator " + playerTarget);
            command("gamerule doDaylightCycle false"); command("gamerule doWeatherCycle false");
            command("gamerule doMobSpawning false"); command("gamerule sendCommandFeedback false"); command("gamerule logAdminCommands false");
            boolean ocean = Arrays.stream(scenarios).anyMatch(scene -> !scene.startsWith("coast") && !scene.startsWith("river") && !scene.equals("cave-water"));
            if (ocean) sites.put("ocean", discover("ocean"));
            if (Arrays.asList(scenarios).contains("coast-day")) sites.put("coast", discover("coast"));
            if (Arrays.asList(scenarios).contains("river-day")) sites.put("river", discover("river"));
            if (Arrays.asList(scenarios).contains("cave-water")) sites.put("cave", cave());
            if (Arrays.asList(scenarios).contains("nether-view")) sites.put("nether", new Site(.5, 70, .5, 120, 12, "fixed-nether-view", 0));
            if (Arrays.asList(scenarios).contains("end-view")) sites.put("end", new Site(.5, 80, .5, 0, 18, "fixed-end-view", 0));
        });
        state = "preparing"; status("Discovering real ocean, beach and river water on the local server");
    }
    private static Site site() {
        String scene = scenarios[stage];
        return sites.get(scene.startsWith("coast") ? "coast" : scene.startsWith("river") ? "river" : scene.equals("cave-water") ? "cave" : scene.equals("nether-view") ? "nether" : scene.equals("end-view") ? "end" : "ocean");
    }
    private static String dimension(String scene) { return scene.equals("nether-view") ? "minecraft:the_nether" : scene.equals("end-view") ? "minecraft:the_end" : "minecraft:overworld"; }
    private static String actualDimension(Object mc) throws Exception {
        Object world = value(mc, "field_1687");
        if (world == null) return "unloaded";
        return call(call(world, "method_27983"), "method_29177").toString();
    }
    private static double cameraY() { return scenarios[stage].equals("underwater") ? site().y - 6.1 : scenarios[stage].equals("chunk-traversal") ? 100 : site().y; }
    private static void cleanBoat() throws Exception {
        // Only a benchmark-created entity is eligible for removal.
        Object playerManager = call(server, "method_3760");
        Object player = playerManager.getClass().getMethod("method_14602", UUID.class).invoke(playerManager, UUID.fromString(playerUuid));
        if (player != null && (boolean)call(player, "method_5765")) command("ride " + playerTarget + " dismount");
        command("execute if entity @e[type=minecraft:boat,tag=aqualumen_bench] run kill @e[type=minecraft:boat,tag=aqualumen_bench]");
        command("gamemode spectator " + playerTarget);
    }
    private static void cleanGlass() throws Exception {
        for (int[] b : glassFixtures) command(String.format(Locale.ROOT, "fill %d %d %d %d %d %d minecraft:air replace minecraft:glass", b[0], b[1], b[2], b[3], b[4], b[5]));
        glassFixtures.clear();
    }
    private static void glass(Site site) throws Exception {
        int x = (int)Math.floor(site.x), y = (int)Math.floor(site.y), z = (int)Math.floor(site.z);
        for (int offset : new int[]{-6, -3, 0}) {
            int[] b = {x - 3, y, z + offset, x + 3, y + 6, z + offset};
            for (int xx = b[0]; xx <= b[3]; xx++) for (int yy = b[1]; yy <= b[4]; yy++) if (!air(xx, yy, b[2])) throw new IllegalStateException("Optional glass fixture would replace natural terrain");
            glassFixtures.add(b);
            command(String.format(Locale.ROOT, "fill %d %d %d %d %d %d minecraft:glass", b[0], b[1], b[2], b[3], b[4], b[5]));
        }
    }
    private static void next(Object mc) throws Exception {
        stage++;
        if (stage >= scenarios.length) {
            pending = local(() -> {
                cleanBoat(); cleanGlass();
                if (!dimension(scenarios[scenarios.length - 1]).equals("minecraft:overworld")) {
                    Site home = sites.get("ocean");
                    command(String.format(Locale.ROOT, "execute in minecraft:overworld run tp %s %.3f %.3f %.3f -45 9", playerTarget, home.x, home.y, home.z));
                }
            });
            state = "finishing"; status("All scenes recorded; completing local cleanup"); return;
        }
        Site site = site(); String name = scenarios[stage];
        pending = local(() -> {
            cleanBoat(); cleanGlass(); command("time set " + (name.equals("ocean-dusk") ? 12700 : name.equals("ocean-night") ? 18000 : 6000));
            command("weather " + (name.equals("ocean-rain") ? "rain" : "clear") + " 1000000");
            command(String.format(Locale.ROOT, "execute in %s run tp %s %.3f %.3f %.3f %.3f %.3f", dimension(name), playerTarget, site.x, cameraY(), name.equals("glass-layers") ? site.z - 12 : site.z, name.equals("glass-layers") ? 0.0 : name.equals("ocean-dusk") ? 90.0 : site.yaw, site.pitch));
            if (name.equals("glass-layers")) glass(site);
            if (name.equals("boat-contact")) {
                command("gamemode creative " + playerTarget);
                command(String.format(Locale.ROOT, "summon minecraft:boat %.3f %.3f %.3f {Tags:[\"aqualumen_bench\"],Type:\"oak\",Invulnerable:1b}", site.x, site.y - 1.5, site.z));
                command("ride " + playerTarget + " mount @e[type=minecraft:boat,tag=aqualumen_bench,limit=1]");
            }
        });
        timings.clear(); previous = 0; state = "preparing-scene"; start = System.nanoTime();
        physicsSamples.clear(); maximumContacts = 0; maximumForce = 0; physicsActive = false; physicsAt = 0;
        status("Setting local scene " + name);
    }
    private static Map<String, Object> identity(Object mc) throws Exception {
        return map("world_id", config.getProperty("world_id"), "pack_name", irisName(), "pack_sha256", packHash,
            "shader_active", iris("isPackInUseQuick"), "shader_fallback", iris("isFallback"),
            "resolution", size(mc, false), "framebuffer_resolution", size(mc, true), "player_dimension", actualDimension(mc));
    }
    private static void runMetadata(Object mc) throws Exception {
        Map<String, Object> metadata = identity(mc);
        Map<String, String> mods = new TreeMap<>();
        FabricLoader.getInstance().getAllMods().forEach(mod -> mods.put(mod.getMetadata().getId(), mod.getMetadata().getVersion().getFriendlyString()));
        Map<String, Object> coordinates = new LinkedHashMap<>();
        sites.forEach((name, site) -> coordinates.put(name, map("position", List.of(site.x, site.y, site.z), "yaw", site.yaw, "pitch", site.pitch, "biome", site.biome, "water_depth_blocks", site.depth)));
        Class<?> gl = Class.forName("org.lwjgl.opengl.GL11");
        Method glString = gl.getMethod("glGetString", int.class);
        metadata.putAll(map("schema", 2, "run_id", runId, "started_utc", Instant.now().toString(),
            "minecraft", mods.get("minecraft"), "java", System.getProperty("java.version"), "mods", mods,
            "garbage_collectors", ManagementFactory.getGarbageCollectorMXBeans().stream().map(bean -> bean.getName()).toList(),
            "jvm_heap_initial_bytes", ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getInit(), "jvm_heap_max_bytes", ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getMax(),
            "iris_pipeline_cloud_setting", optionalCloudSetting(), "minecraft_effective_cloud_mode", optionalCall(options, "method_1632").toString(),
            "world_directory", worldPath.toString(), "world_generator", worldMarker.getProperty("generator"), "seed", Long.parseLong(worldMarker.getProperty("seed")),
            "player_uuid", playerUuid, "expected_pack_sha256", config.getProperty("expected_pack_sha256"),
            "expected_resolution", List.of(Integer.parseInt(config.getProperty("width")), Integer.parseInt(config.getProperty("height"))),
            "render_chunks", option("method_42503"), "simulation_chunks", option("method_42510"), "vsync", option("method_42433"), "frame_limit", optionalCall(mc, "method_16009"),
            "gl_renderer", glString.invoke(null, 7937), "gl_version", glString.invoke(null, 7938),
            "scenarios", Arrays.asList(scenarios), "warmup_seconds", warmupSeconds, "sample_seconds", sampleSeconds, "sites", coordinates,
            "frame_method", "System.nanoTime render-tail intervals; one start boundary discarded; setup/screenshots outside sample",
            "camera_lock", "GameRenderer.renderWorld HEAD, after mouse/tick input; current and interpolated yaw/pitch; actual Camera validated at capture",
            "terrain_fixture", Arrays.asList(scenarios).contains("glass-layers") ? "Three temporary glass slabs in previously verified air; removed after scene; disposable exact UUID world only" : "No terrain placement"));
        Path irisConfig = game.resolve("config/iris.properties");
        metadata.put("iris_configuration", Files.readString(irisConfig));
        Path packOptions = game.resolve("shaderpacks").resolve(config.getProperty("expected_pack") + ".txt");
        metadata.put("pack_options", Files.exists(packOptions) ? Files.readString(packOptions) : "Defaults (no installed pack options file)");
        atomic(runDir.resolve("run.json"), json(metadata) + "\n");
    }
    private static float expectedYaw(long now) {
        String scene = scenarios[stage];
        if (scene.equals("moving-view")) return site().yaw + (state.equals("sampling") ? (float)((now - sampleStart) * 1e-9 * 12.0) : 0);
        if (scene.equals("boat-contact") || scene.equals("chunk-traversal") || scene.equals("glass-layers")) return 0;
        return scene.equals("ocean-dusk") ? 90 : site().yaw;
    }
    private static float expectedPitch() { return scenarios[stage].equals("chunk-traversal") || scenarios[stage].equals("boat-contact") ? 10 : site().pitch; }
    public static void beforeWorldRender() {
        if (!(state.equals("warmup") || state.equals("sampling")) || minecraft == null) return;
        try {
            Object player = value(minecraft, "field_1724");
            if (player == null) return;
            if (call(minecraft, "method_1576") != server || !call(player, "method_5667").toString().equals(playerUuid) || call(minecraft, "method_1560") != player)
                throw new IllegalStateException("Camera lock left the verified integrated-server/player scope");
            float yaw = expectedYaw(System.nanoTime()), pitch = expectedPitch();
            player.getClass().getMethod("method_36456", float.class).invoke(player, yaw);
            player.getClass().getMethod("method_36457", float.class).invoke(player, pitch);
            field(player, "field_5982").setFloat(player, yaw);
            field(player, "field_6004").setFloat(player, pitch);
        } catch (Throwable error) { asyncError = error; }
    }
    private static void motion(Object mc, long now) throws Exception {
        String scene = scenarios[stage];
        if (now - motionAt < 50_000_000L || !(scene.equals("chunk-traversal") || scene.equals("boat-contact"))) return;
        motionAt = now;
        double elapsed = (now - sampleStart) * 1e-9;
        double z = site().z + elapsed * (scene.equals("boat-contact") ? 6.0 : 32.0);
        String target = scene.equals("boat-contact") ? "@e[type=minecraft:boat,tag=aqualumen_bench,limit=1]" : playerTarget;
        double y = scene.equals("boat-contact") ? site().y - 1.5 : 100;
        double x = site().x;
        CompletableFuture<Void> task = local(() -> command(String.format(Locale.ROOT, "tp %s %.3f %.3f %.3f 0 10", target, x, y, z)));
        task.exceptionally(error -> { asyncError = error; return null; });
    }
    private static double diagnosticNumber(String text, String key) {
        var match = Pattern.compile("\"" + key + "\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)").matcher(text);
        return match.find() ? Double.parseDouble(match.group(1)) : 0;
    }
    private static void physics(long now, boolean force) throws Exception {
        if (!force && now - physicsAt < 1_000_000_000L) return;
        physicsAt = now;
        Path path = game.resolve("config/aqualumen-physics-status.json");
        if (!Files.exists(path)) return;
        String diagnostics = Files.readString(path);
        int contacts = (int)diagnosticNumber(diagnostics, "contacts");
        double forceValue = diagnosticNumber(diagnostics, "max_force");
        boolean active = diagnosticNumber(diagnostics, "active") > 0;
        maximumContacts = Math.max(maximumContacts, contacts); maximumForce = Math.max(maximumForce, forceValue); physicsActive |= active;
        physicsSamples.add(map("elapsed_seconds", (now - sampleStart) * 1e-9, "contacts", contacts, "max_force", forceValue, "active", active, "raw_json", diagnostics));
    }
    private static void capture(Object mc, long now) throws Exception {
        guard(mc, true);
        physics(now, true);
        if (timings.size() < 10) throw new IllegalStateException("Too few frame intervals");
        ArrayList<Long> sorted = new ArrayList<>(timings); Collections.sort(sorted);
        double total = timings.stream().mapToDouble(Long::doubleValue).sum();
        int slowCount = Math.max(1, (int)Math.ceil(sorted.size() * .01));
        double slowTotal = sorted.subList(sorted.size() - slowCount, sorted.size()).stream().mapToDouble(Long::doubleValue).sum();
        double max = sorted.getLast() * 1e-6;
        Site site = site(); String name = scenarios[stage];
        Map<String, Object> row = identity(mc);
        row.putAll(map("scenario", name, "run_id", runId, "workload", name.equals("chunk-traversal") ? "chunk-traversal" : name.equals("boat-contact") ? "scripted-boat-contact" : "warmed-view",
            "frames", timings.size(), "mean_fps", 1e9 * timings.size() / total, "one_percent_low_fps", 1e9 * slowCount / slowTotal,
            "p99_ms", sorted.get(Math.min(sorted.size() - 1, (int)Math.ceil(sorted.size() * .99) - 1)) * 1e-6, "max_ms", max,
            "min_instantaneous_fps", 1000.0 / max, "frames_over_16_667_ms", timings.stream().filter(timing -> timing * 1e-6 > BUDGET).count(),
            "warmup_seconds", warmupSeconds, "sample_seconds_requested", sampleSeconds, "sample_seconds_actual", (now - sampleStart) * 1e-9,
            "recorded_seconds", total * 1e-9, "site", map("x", site.x, "y", cameraY(), "z", site.z, "biome", site.biome, "water_depth_blocks", site.depth),
            "window_focused", optionalCall(mc, "method_1569"), "physics_active_seen", physicsActive, "maximum_contacts", maximumContacts, "maximum_force", maximumForce,
            "contact_driver", name.equals("boat-contact") ? "server-command boat translation 6m/s at20Hz; actual mounted player and entity" : "none"));
        Object cameraPlayer = value(mc, "field_1724");
        float actualYaw = (float)call(cameraPlayer, "method_36454"), actualPitch = (float)call(cameraPlayer, "method_36455");
        if (Math.abs(actualPitch - expectedPitch()) > .05 || (!name.equals("moving-view") && Math.abs(actualYaw - expectedYaw(now)) > .05))
            throw new IllegalStateException("Camera orientation does not match requested scene");
        Object camera = call(value(mc, "field_1773"), "method_19418");
        if (call(camera, "method_19331") != cameraPlayer) throw new IllegalStateException("Rendered Camera focuses another entity");
        float renderedYaw = (float)call(camera, "method_19330"), renderedPitch = (float)call(camera, "method_19329");
        if (Math.abs(renderedYaw - actualYaw) > .05 || Math.abs(renderedPitch - actualPitch) > .05)
            throw new IllegalStateException("Rendered Camera orientation disagrees with locked local player");
        row.put("actual_player_rotation", List.of(actualYaw, actualPitch));
        row.put("actual_camera_rotation", List.of(renderedYaw, renderedPitch));
        row.put("expected_camera_rotation", List.of(expectedYaw(now), expectedPitch()));
        double px = (double)call(cameraPlayer, "method_23317"), py = (double)call(cameraPlayer, "method_23318"), pz = (double)call(cameraPlayer, "method_23321");
        row.put("actual_player_position", List.of(px, py, pz));
        if (!name.equals("boat-contact") && !name.equals("chunk-traversal") && (Math.abs(px - site.x) > .5 || Math.abs(py - cameraY()) > .5 || Math.abs(pz - (name.equals("glass-layers") ? site.z - 12 : site.z)) > .5))
            throw new IllegalStateException("Player moved away from fixed scene position");
        Object cameraPosition = call(camera, "method_19326");
        row.put("actual_camera_position", List.of(value(cameraPosition, "field_1352"), value(cameraPosition, "field_1351"), value(cameraPosition, "field_1350")));
        row.put("camera_follows_local_player", true);
        row.put("camera_lock", "GameRenderer.renderWorld HEAD, after input; current and interpolated yaw/pitch");
        atomic(runDir.resolve(name + "-physics-samples.json"), json(physicsSamples) + "\n");
        if (name.equals("boat-contact") && (!physicsActive || maximumContacts < 1 || maximumForce <= 0))
            throw new IllegalStateException("Boat-contact scene did not observe an active physics bridge with a nonzero moving contact");
        Path physics = game.resolve("config/aqualumen-physics-status.json");
        if (Files.exists(physics)) {
            String diagnostics = Files.readString(physics);
            row.put("physics_status_json", diagnostics);
            Files.copy(physics, runDir.resolve(name + "-physics.json"), StandardCopyOption.REPLACE_EXISTING);
        }
        atomic(runDir.resolve(name + ".json"), json(row) + "\n");
        StringBuilder csv = new StringBuilder("frame,ns,ms\n");
        for (int index = 0; index < timings.size(); index++) csv.append(index).append(',').append(timings.get(index)).append(',').append(timings.get(index) * 1e-6).append('\n');
        atomic(runDir.resolve(name + ".csv"), csv.toString());
        String screenshotName = "aqualumen-" + runId + "-" + name + ".png";
        screenshotPath = game.resolve("screenshots").resolve(screenshotName);
        if (Files.exists(screenshotPath)) throw new IllegalStateException("Screenshot name already exists");
        Method screenshot = Class.forName("net.minecraft.class_318").getMethod("method_22690", java.io.File.class, String.class, Class.forName("net.minecraft.class_276"), Consumer.class);
        call(call(mc, "method_1566"), "method_2000");
        screenshot.invoke(null, game.toFile(), screenshotName, call(mc, "method_1522"), (Consumer<Object>)ignored -> {});
        screenshotStarted = System.nanoTime(); state = "screenshot"; previous = 0;
        status(String.format(Locale.ROOT, "%s %.1f FPS; P99 %.3f ms; worst %.3f ms; awaiting screenshot", name, row.get("mean_fps"), row.get("p99_ms"), max));
    }
    private static void abort(Object mc, String reason) throws Exception {
        state = "aborted"; previous = 0;
        if (runDir != null) atomic(runDir.resolve("aborted.json"), json(map("run_id", runId, "status", "aborted", "reason", reason, "utc", Instant.now().toString())) + "\n");
        restoreHud(mc); status(reason);
        asyncError = null;
    }
    private static void poll(Object mc) throws Exception {
        Path requestPath = control.resolve("request.properties");
        if (!Files.exists(requestPath)) return;
        Properties request = properties(requestPath);
        requestId = request.getProperty("request_id", "");
        UUID.fromString(requestId);
        // Consume exactly one immutable request before acknowledging it. Stale files
        // cannot restart a finished run, and reports can never be overwritten.
        Files.delete(requestPath);
        String action = request.getProperty("action", "");
        if (action.equals("start")) { startRun(mc, request); return; }
        config = properties(game.resolve("config/aqualumen-benchmark.properties"));
        if (!request.getProperty("world_id", "").equals(config.getProperty("world_id"))) throw new IllegalStateException("Control world UUID mismatch");
        guard(mc, false);
        if (action.equals("stop")) { if (Set.of("preparing", "preparing-scene", "warmup", "sampling", "screenshot", "finishing").contains(state)) abort(mc, "Stopped by local control request"); else status("No active run"); }
        else if (action.equals("quit")) {
            if (Set.of("preparing", "preparing-scene", "warmup", "sampling", "screenshot").contains(state)) abort(mc, "Quit by local control request");
            restoreHud(mc); state = "quitting"; status("Stopping the verified isolated Minecraft client"); call(mc, "method_1592");
        } else throw new IllegalArgumentException("Unknown control action");
    }
    public static void frame(Object mc) {
        if (disabled) return;
        try {
            if (!initialized) { init(mc); return; }
            long now = System.nanoTime();
            if (now - pollAt >= 250_000_000L) { pollAt = now; poll(mc); }
            if (asyncError != null) throw new IllegalStateException("Asynchronous movement failed", asyncError);
            if (state.equals("preparing") || state.equals("preparing-scene") || state.equals("finishing")) {
                if (!pending.isDone()) return;
                pending.join();
                if (state.equals("preparing")) { guard(mc, true); runMetadata(mc); next(mc); return; }
                if (state.equals("finishing")) {
                    guard(mc, true); restoreHud(mc);
                    atomic(runDir.resolve("complete.json"), json(map("run_id", runId, "status", "complete", "scenarios", Arrays.asList(scenarios), "utc", Instant.now().toString())) + "\n");
                    state = "complete"; status("All requested natural-world scenes, raw timings and screenshots recorded");
                    if (autoQuit) { state = "quitting"; status("Auto-quit after verified completion"); call(mc, "method_1592"); }
                    return;
                }
                if (value(mc, "field_1755") != null) return;
                if (!actualDimension(mc).equals(dimension(scenarios[stage]))) {
                    if (now - start > 60_000_000_000L) throw new IllegalStateException("Client did not arrive in requested dimension");
                    return;
                }
                guard(mc, false); start = System.nanoTime(); previous = 0; state = "warmup"; status("Warming " + scenarios[stage]); return;
            }
            if (state.equals("screenshot")) {
                if (Files.exists(screenshotPath) && Files.size(screenshotPath) > 0) {
                    Files.copy(screenshotPath, runDir.resolve(scenarios[stage] + ".png")); next(mc);
                } else if (now - screenshotStarted > 15_000_000_000L) throw new IllegalStateException("Screenshot did not complete");
                return;
            }
            if (!(state.equals("warmup") || state.equals("sampling"))) return;
            if (value(mc, "field_1755") != null) throw new IllegalStateException("A UI screen interrupted the scene");
            if (!actualDimension(mc).equals(dimension(scenarios[stage]))) throw new IllegalStateException("Player dimension changed during scene");
            if (now - validateAt > 1_000_000_000L) { validateAt = now; guard(mc, false); }
            if (state.equals("warmup")) {
                if ((now - start) * 1e-9 >= warmupSeconds) {
                    state = "sampling"; status("Measuring " + scenarios[stage]); sampleStart = System.nanoTime(); previous = 0; motionAt = 0;
                }
                return;
            }
            if (previous != 0) timings.add(now - previous);
            previous = now;
            motion(mc, now);
            physics(now, false);
            if ((now - sampleStart) * 1e-9 >= sampleSeconds) capture(mc, now);
        } catch (Throwable error) {
            Throwable reason = error instanceof CompletionException && error.getCause() != null ? error.getCause() : error;
            System.err.println("[Aqualumen] Benchmark failure: " + reason); reason.printStackTrace();
            try { if (initialized) abort(mc, reason.toString()); } catch (Throwable ignored) {}
            // A failed request remains inspectable; a later corrected request can run.
            if (!initialized) disabled = true;
        }
    }
}
