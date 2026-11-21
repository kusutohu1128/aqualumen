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
import java.util.concurrent.atomic.AtomicLongArray;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.regex.Pattern;

/** Development instrumentation, explicitly enabled and confined to one local world.
 * No network connection, chat message, CLI process or downloaded world.
 * Optional temporary fixtures are exact-UUID guarded and journaled for cleanup.
 * Intermediary reflection keeps this small tool independent of a remapped client JAR.
 */
public final class Recorder {
    private static final Set<String> KNOWN = Set.of("ocean-day", "coast-day", "coast-rain-close", "river-day", "ocean-dusk", "ocean-night", "ocean-rain", "underwater", "moving-view", "boat-contact", "chunk-traversal", "cave-water", "glass-layers", "nether-view", "end-view", "ocean-sun-day", "ocean-sun-dusk");
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
    private static volatile OcclusionFixture.Plan ownedOpaque;
    private static volatile LocalLightFixture.Plan ownedLocal;
    private static volatile Map<String, Object> localValidation;
    private static CompletableFuture<Void> localValidationTask;
    private static volatile long localCleanedAt;
    private static volatile int localSettle; // 0 none/done, 1 settle recheck due, 2 scheduled
    private static final String LOCAL_JOURNAL = "local-light-fixture-journal.json";
    // Walk route evidence: 25 Hz actual pose rows joined to any clip by elapsed_ns since sample start.
    private static final StringBuilder walkRoute = new StringBuilder();
    private static long walkLogAt;
    private static Object walkFov;
    private static boolean fixtureRun, quitAfterCleanup;
    private static String abortReason = "";
    private static CompletableFuture<Void> pending;
    private static Path screenshotPath;
    private static long screenshotStarted;
    private static ScreenshotCompletion screenshotCompletion;
    private static NativeMotionCapture nativeMotion;
    private static GroundShadowClip groundClip;
    private static boolean fullFrameClip;
    private static boolean recordGroundClip;
    private static boolean captureMotion;
    private static long physicsAt;
    private static final ArrayList<Map<String, Object>> physicsSamples = new ArrayList<>();
    private static int maximumContacts;
    private static double maximumForce;
    private static double underwaterSurfaceY;
    private static boolean physicsActive;
    private static Method execute;
    private static volatile Throwable asyncError;
    // Carried-light (lamp-hand-*) driver state: real item stacks in the identified player's two hand slots.
    private record HandOwnership(LocalLightFixture.Plan plan, String gameMode, int selectedSlot, HandLightFixture.Progress progress) {}
    private static final String HAND_JOURNAL = "hand-light-fixture-journal.json";
    private static volatile HandOwnership ownedHand;
    private static HandLightFixture.Progress handRunBaseline;
    private static String handRestoredGameMode = "";
    private static volatile String handPreRunGameMode = "";
    private static final StringBuilder handTrace = new StringBuilder();
    private static long handTraceAt, handSettleStart;
    private static int handStepIssued, handSettle; // handSettle: 0 none/done, 1 client restoration check due
    private static long[] handSwapScheduled = new long[0], handSwapIssued = new long[0], handSwapClient = new long[0],
        handSwapRenderer = new long[0], handSwapSettled = new long[0];
    private static AtomicLongArray handSwapServer = new AtomicLongArray(0);
    private static boolean handWorldPass;
    private static Field hudField;

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
        if (scenarios != null && Arrays.stream(scenarios).anyMatch(scene -> UnderwaterScene.parse(scene) != null || LocalLightFixture.parse(scene) != null) &&
            !UnderwaterScene.authorized(expected.getFileName().toString(), marker.getProperty("world_id"), Long.parseLong(marker.getProperty("seed"))))
            throw new IllegalStateException("Water fixture views require the exact dedicated V2 UUID and seed308060");
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
    private static String blockId(OcclusionFixture.Cell cell) throws Exception {
        Object blockState = serverWorld.getClass().getMethod("method_8320", Class.forName("net.minecraft.class_2338"))
            .invoke(serverWorld, pos(cell.x(), cell.y(), cell.z()));
        Object registry = Class.forName("net.minecraft.class_7923").getField("field_41175").get(null);
        return registry.getClass().getMethod("method_10221", Object.class).invoke(registry, call(blockState, "method_26204")).toString();
    }
    private static void fixtureScope() throws Exception {
        if (!OcclusionFixture.authorized(config.getProperty("world"), config.getProperty("world_id")) ||
            !OcclusionFixture.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id")))
            throw new IllegalStateException("Opaque fixtures require the exact dedicated AqualumenNaturalV2 UUID");
        // Recheck the latched server/save/marker at the server-thread mutation seam.
        if (call(minecraft, "method_1576") != server || serverWorld != call(server, "method_30002") || (boolean)call(server, "method_3860"))
            throw new IllegalStateException("Opaque fixture cleanup/placement left its isolated server");
        Object saveRoot = Class.forName("net.minecraft.class_5218").getField("field_24188").get(null);
        Path current = ((Path)server.getClass().getMethod("method_27050", saveRoot.getClass()).invoke(server, saveRoot)).toRealPath();
        Properties marker = properties(current.resolve("aqualumen-world.properties"));
        if (!current.equals(worldPath) || !OcclusionFixture.authorized(current.getFileName().toString(), marker.getProperty("world_id")) ||
            !marker.getProperty("generator", "").equals("minecraft:noise/overworld") ||
            (long)call(serverWorld, "method_8412") != Long.parseLong(marker.getProperty("seed")))
            throw new IllegalStateException("Opaque fixture save/UUID/seed changed");
        List<?> players = (List<?>)call(call(server, "method_3760"), "method_14571");
        if (players.size() != 1 || !call(players.getFirst(), "method_5667").toString().equals(playerUuid))
            throw new IllegalStateException("Opaque fixture identified player changed");
    }
    private static Map<String, Object> fixtureMetadata(OcclusionFixture.Plan plan) {
        if (plan.range().equals("natural-shore")) return map("range", plan.range(),
            "materials", List.of("minecraft:stone", "minecraft:oak_fence"), "requested_start_time", plan.timeOfDay(),
            "requested_player_position", List.of(plan.scene().equals("ground-camera-motion") ? 133.6 : 134,66,335), "requested_camera_rotation", List.of(plan.yaw(),plan.pitch()),
            "moving_sun", plan.scene().equals("ground-sun-motion"), "placed_cells", plan.placements().size());
        return map("range", plan.range(), "background_color", plan.color(), "wall_present", plan.wallPresent(),
            "wall_plane_axis", plan.wallAxis(), "wall_bounds", plan.wallBounds(), "target_bounds", plan.targetBounds(),
            "wall_material", "minecraft:white_concrete", "target_material", "minecraft:" + plan.color() + "_concrete",
            "fixed_lights", plan.lights(), "requested_world_time", plan.timeOfDay(),
            "requested_player_position", List.of(448.5,160,-383.5), "requested_camera_rotation", List.of(plan.yaw(),plan.pitch()),
            "placed_cells", plan.placements().size(), "reserved_air_cells", plan.reserved().size(),
            "eye_tolerance_m", OcclusionFixture.EYE_TOLERANCE);
    }
    private static Map<String, Object> fixtureJournal(OcclusionFixture.Plan plan, String phase) {
        return map("world_directory", worldPath.toString(), "world_id", OcclusionFixture.WORLD_ID,
            "run_id", runId, "scene", plan.scene(), "phase", phase, "utc", Instant.now().toString(),
            "fixture", fixtureMetadata(plan), "expected_cells", plan.placements().stream()
                .map(cell -> map("x", cell.x(), "y", cell.y(), "z", cell.z(), "expected_block", cell.block())).toList());
    }
    private static void placeOpaque(OcclusionFixture.Plan plan) throws Exception {
        fixtureScope();
        if (ownedOpaque != null || Files.exists(control.resolve("opaque-fixture-journal.json")))
            throw new IllegalStateException("An unresolved opaque fixture journal must be reviewed before placement");
        // Check the complete approved plot before changing even one cell, including
        // the absent wall in positive-control variants. Never replace terrain.
        for (OcclusionFixture.Cell cell : plan.reserved())
            if (!blockId(cell).equals("minecraft:air")) throw new IllegalStateException("Opaque fixture requires exact AIR at " + cell);
        if (plan.range().equals("natural-shore")) for (OcclusionFixture.Cell cell : plan.placements()) {
            if (cell.y() == 63 && !Set.of("minecraft:grass_block", "minecraft:gravel", "minecraft:sand")
                .contains(blockId(new OcclusionFixture.Cell(cell.x(), 62, cell.z(), ""))))
                throw new IllegalStateException("Natural support changed under " + cell);
        }
        ownedOpaque = plan;
        String journal = json(fixtureJournal(plan, "before-placement")) + "\n";
        atomic(control.resolve("opaque-fixture-journal.json"), journal);
        atomic(runDir.resolve(plan.scene() + "-fixture-prepared.json"), journal);
        for (OcclusionFixture.Cell cell : plan.placements()) {
            command(String.format(Locale.ROOT, "execute in minecraft:overworld if block %d %d %d minecraft:air run setblock %d %d %d %s",
                cell.x(), cell.y(), cell.z(), cell.x(), cell.y(), cell.z(), cell.block()));
            if (!blockId(cell).equals(cell.block())) throw new IllegalStateException("Opaque fixture placement did not produce the journaled exact state: " + cell);
        }
        atomic(runDir.resolve(plan.scene() + "-fixture-placed.json"), json(fixtureJournal(plan, "placed")) + "\n");
    }
    private static void cleanOpaque() throws Exception {
        OcclusionFixture.Plan plan = ownedOpaque;
        if (plan == null) return;
        fixtureScope();
        ArrayList<Map<String, Object>> conflicts = new ArrayList<>();
        for (OcclusionFixture.Cell cell : plan.placements()) {
            String actual = blockId(cell);
            switch (OcclusionFixture.cleanupDecision(cell, actual)) {
                case REMOVE -> command(String.format(Locale.ROOT,
                    "execute in minecraft:overworld if block %d %d %d %s run setblock %d %d %d minecraft:air",
                    cell.x(), cell.y(), cell.z(), cell.block(), cell.x(), cell.y(), cell.z()));
                case ALREADY_AIR -> { }
                case CONFLICT -> conflicts.add(map("x", cell.x(), "y", cell.y(), "z", cell.z(), "actual_block", actual));
            }
        }
        for (OcclusionFixture.Cell cell : plan.placements())
            if (!blockId(cell).equals("minecraft:air") && conflicts.stream().noneMatch(conflict -> conflict.get("x").equals(cell.x()) && conflict.get("y").equals(cell.y()) && conflict.get("z").equals(cell.z())))
                conflicts.add(map("x", cell.x(), "y", cell.y(), "z", cell.z(), "actual_block", blockId(cell)));
        Map<String, Object> evidence = fixtureJournal(plan, conflicts.isEmpty() ? "cleaned-to-air" : "cleanup-conflict");
        evidence.put("cleanup_complete", conflicts.isEmpty()); evidence.put("conflicts_preserved", conflicts);
        atomic(runDir.resolve(plan.scene() + "-fixture-cleanup.json"), json(evidence) + "\n");
        if (!conflicts.isEmpty()) {
            atomic(control.resolve("opaque-fixture-journal.json"), json(evidence) + "\n");
            throw new IllegalStateException("Opaque fixture replacement states preserved; cleanup incomplete: " + conflicts.size());
        }
        Files.deleteIfExists(control.resolve("opaque-fixture-journal.json")); ownedOpaque = null;
    }
    private static boolean fixturesPending() {
        return ownedOpaque != null || ownedLocal != null || ownedHand != null || Files.exists(control.resolve("opaque-fixture-journal.json")) ||
            Files.exists(control.resolve(LOCAL_JOURNAL)) || Files.exists(control.resolve(HAND_JOURNAL));
    }
    private static void localScope() throws Exception {
        fixtureScope();
        long actualSeed = (long)call(serverWorld, "method_8412");
        if (!LocalLightFixture.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), actualSeed) ||
            !LocalLightFixture.authorized(config.getProperty("world"), config.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))))
            throw new IllegalStateException("Local-light fixture requires the exact dedicated AqualumenNaturalV2 UUID and seed308060");
    }
    private static String stateText(int x, int y, int z) throws Exception {
        return serverWorld.getClass().getMethod("method_8320", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, pos(x, y, z)).toString();
    }
    private static String blockAt(int x, int y, int z) throws Exception { return blockId(new OcclusionFixture.Cell(x, y, z, "")); }
    private interface BoxVisitor { void visit(int x, int y, int z) throws Exception; }
    private static int eachBoxCell(BoxVisitor visitor) throws Exception {
        List<Integer> b = LocalLightFixture.BOX; int count = 0;
        for (int x = b.get(0); x <= b.get(3); x++) for (int y = b.get(1); y <= b.get(4); y++) for (int z = b.get(2); z <= b.get(5); z++) { visitor.visit(x, y, z); count++; }
        return count;
    }
    private static Map<String, Object> localJournal(LocalLightFixture.Plan plan, String phase) {
        return map("world_directory", worldPath.toString(), "world_id", OcclusionFixture.WORLD_ID, "seed", LocalLightFixture.SEED,
            "run_id", runId, "scene", plan.scene(), "phase", phase, "utc", Instant.now().toString(),
            "reserved_air_box_inclusive", LocalLightFixture.BOX, "restore_state", "minecraft:air",
            "expected_cells", plan.placements().stream().map(cell -> map("x", cell.x(), "y", cell.y(), "z", cell.z(),
                "expected_state", cell.state(), "role", cell.role())).toList());
    }
    private static void placeLocal(LocalLightFixture.Plan plan) throws Exception {
        localScope();
        if (plan.hand() != null) requireCarriedTestGame();
        if (fixturesPending()) throw new IllegalStateException("An unresolved fixture journal must be reviewed before local-light placement");
        // The whole reservation (scene, camera body and view path) must be exact AIR before even one change.
        int checked = eachBoxCell((x, y, z) -> {
            String id = blockAt(x, y, z);
            if (!id.equals("minecraft:air")) throw new IllegalStateException("Local-light fixture requires exact AIR at " + x + "," + y + "," + z + " (found " + id + ")");
        });
        ArrayList<Map<String, Object>> previous = new ArrayList<>();
        for (LocalLightFixture.Cell cell : plan.placements())
            previous.add(map("x", cell.x(), "y", cell.y(), "z", cell.z(), "previous_state", stateText(cell.x(), cell.y(), cell.z()),
                "expected_state", cell.state(), "role", cell.role()));
        ownedLocal = plan;
        Map<String, Object> journal = localJournal(plan, "before-placement");
        journal.put("reserved_air_cells_verified", checked); journal.put("previous_states", previous);
        String text = json(journal) + "\n";
        atomic(control.resolve(LOCAL_JOURNAL), text);
        atomic(runDir.resolve(plan.scene() + "-fixture-prepared.json"), text);
        // Supports and the sealed basin precede attachments and water (reviewed order in LocalLightFixture).
        for (LocalLightFixture.Cell cell : plan.placements()) {
            command(String.format(Locale.ROOT, "execute in minecraft:overworld if block %d %d %d minecraft:air run setblock %d %d %d %s",
                cell.x(), cell.y(), cell.z(), cell.x(), cell.y(), cell.z(), cell.state()));
            if (!LocalLightFixture.stateMatches(cell, blockAt(cell.x(), cell.y(), cell.z()), stateText(cell.x(), cell.y(), cell.z())))
                throw new IllegalStateException("Local-light placement did not produce the journaled exact state: " + cell);
        }
        atomic(runDir.resolve(plan.scene() + "-fixture-placed.json"), json(localJournal(plan, "placed")) + "\n");
    }
    /** Server thread, before sampling: every placed state exact and every other reserved cell still AIR. */
    private static Map<String, Object> validateLocal(LocalLightFixture.Plan plan) throws Exception {
        localScope();
        if (ownedLocal == null || !ownedLocal.scene().equals(plan.scene())) throw new IllegalStateException("Local-light fixture ownership changed before sampling");
        Map<List<Integer>, LocalLightFixture.Cell> expected = LocalLightFixture.grid(plan);
        int[] counts = new int[2];
        ArrayList<String> mismatches = new ArrayList<>();
        eachBoxCell((x, y, z) -> {
            LocalLightFixture.Cell cell = expected.get(List.of(x, y, z));
            String id = blockAt(x, y, z);
            if (cell != null ? LocalLightFixture.stateMatches(cell, id, stateText(x, y, z)) : id.equals("minecraft:air")) counts[cell != null ? 0 : 1]++;
            else mismatches.add(x + "," + y + "," + z + "=" + stateText(x, y, z));
        });
        if (!mismatches.isEmpty())
            throw new IllegalStateException("Local-light block validation failed (" + mismatches.size() + "): " + mismatches.subList(0, Math.min(5, mismatches.size())));
        return map("passed", true, "placed_cells_exact_state", counts[0], "other_reserved_cells_exact_air", counts[1],
            "server_world_time", (long)call(serverWorld, "method_8532"), "utc", Instant.now().toString());
    }
    private static void cleanLocal() throws Exception {
        LocalLightFixture.Plan plan = ownedLocal;
        if (plan == null) return;
        localScope();
        ArrayList<Map<String, Object>> conflicts = new ArrayList<>();
        int removed = 0;
        // Reverse order: lamps before their supports, water before its basin, so nothing drops or flows.
        for (LocalLightFixture.Cell cell : LocalLightFixture.cleanupOrder(plan)) {
            String actual = blockAt(cell.x(), cell.y(), cell.z());
            switch (LocalLightFixture.cleanupDecision(cell, actual)) {
                case REMOVE -> { command(String.format(Locale.ROOT,
                    "execute in minecraft:overworld if block %d %d %d %s run setblock %d %d %d minecraft:air",
                    cell.x(), cell.y(), cell.z(), cell.id(), cell.x(), cell.y(), cell.z())); removed++; }
                case ALREADY_AIR -> { }
                case CONFLICT -> conflicts.add(map("x", cell.x(), "y", cell.y(), "z", cell.z(), "actual_state", stateText(cell.x(), cell.y(), cell.z())));
            }
        }
        int checked = eachBoxCell((x, y, z) -> {
            if (!blockAt(x, y, z).equals("minecraft:air") && conflicts.stream().noneMatch(c -> c.get("x").equals(x) && c.get("y").equals(y) && c.get("z").equals(z)))
                conflicts.add(map("x", x, "y", y, "z", z, "actual_state", stateText(x, y, z)));
        });
        Map<String, Object> evidence = localJournal(plan, conflicts.isEmpty() ? "restored-to-air" : "cleanup-conflict");
        evidence.put("cleanup_complete", conflicts.isEmpty()); evidence.put("removed_cells", removed);
        evidence.put("reserved_cells_rechecked", checked); evidence.put("conflicts_preserved", conflicts);
        atomic(runDir.resolve(plan.scene() + "-fixture-cleanup.json"), json(evidence) + "\n");
        if (!conflicts.isEmpty()) {
            atomic(control.resolve(LOCAL_JOURNAL), json(evidence) + "\n");
            throw new IllegalStateException("Local-light fixture foreign/replacement states preserved; cleanup incomplete: " + conflicts.size());
        }
        Files.deleteIfExists(control.resolve(LOCAL_JOURNAL)); ownedLocal = null; localCleanedAt = System.nanoTime();
    }
    /** Delayed final recheck (>=1.5 s, i.e. several fluid ticks after the last cleanup). */
    private static void settleLocal() throws Exception {
        localScope();
        ArrayList<String> nonAir = new ArrayList<>();
        int checked = eachBoxCell((x, y, z) -> { if (!blockAt(x, y, z).equals("minecraft:air")) nonAir.add(x + "," + y + "," + z + "=" + stateText(x, y, z)); });
        atomic(runDir.resolve("local-light-settled-cleanup.json"), json(map("reserved_air_box_inclusive", LocalLightFixture.BOX,
            "cells_checked", checked, "all_exact_air", nonAir.isEmpty(), "non_air", nonAir,
            "seconds_after_last_cleanup", (System.nanoTime() - localCleanedAt) * 1e-9, "utc", Instant.now().toString())) + "\n");
        if (!nonAir.isEmpty()) throw new IllegalStateException("Local-light reservation not AIR after settling: " + nonAir.size());
        localSettle = 0;
    }
    // ---- Carried-light driver (lamp-hand-*): real item stacks, exact inventory/recipe/game-mode journal and restoration.
    private static String itemId(Object stack) throws Exception {
        if (stack == null || (boolean)call(stack, "method_7960")) return HandLightFixture.EMPTY;
        Object registry = Class.forName("net.minecraft.class_7923").getField("field_41178").get(null);
        return registry.getClass().getMethod("method_10221", Object.class).invoke(registry, call(stack, "method_7909")).toString();
    }
    private static int itemCount(Object stack) throws Exception {
        return stack == null || (boolean)call(stack, "method_7960") ? 0 : (int)call(stack, "method_7947");
    }
    /** Carried-light opt-in copied from the consumed start request; never read from any other source. */
    private static Map<String, String> handOptIn = Map.of();
    private static HandLightFixture.TestGame handTestGame;
    /** Re-proves, at every carried-light mutation seam, that this process runs the private duplicated TEST game. */
    private static HandLightFixture.TestGame requireCarriedTestGame() throws Exception {
        String session = (String)call(call(minecraft, "method_1548"), "method_1676");
        String profile = playerUuid.isEmpty() || server == null ? null : (String)call(call(serverPlayer(), "method_7334"), "getName");
        HandLightFixture.TestGame identified = HandLightFixture.privateTestGame(FabricLoader.getInstance().getGameDir(), session, profile,
            handOptIn, config.getProperty("world"));
        if (!identified.game().equals(game) || !worldPath.equals(identified.game().resolve("saves").resolve(config.getProperty("world"))))
            throw new IllegalStateException("Carried-light TEST game guard: running game/world differ from the identified TEST game");
        if (handTestGame != null && !handTestGame.equals(identified)) throw new IllegalStateException("Carried-light TEST game identity changed during the run");
        Object arm = option("method_42552"), right = Class.forName("net.minecraft.class_1306").getField("field_6183").get(null);
        if (arm != right) throw new IllegalStateException("Carried-light ROIs assume a right-handed player (main arm " + arm + ")");
        handTestGame = identified;
        return identified;
    }
    private static Object serverPlayer() throws Exception {
        Object manager = call(server, "method_3760");
        Object player = manager.getClass().getMethod("method_14602", UUID.class).invoke(manager, UUID.fromString(playerUuid));
        if (player == null) throw new IllegalStateException("Identified carried-light driver is not on the integrated server");
        return player;
    }
    private static List<String> inventoryIds(Object player) throws Exception {
        Object inventory = call(player, "method_31548");
        int size = (int)call(inventory, "method_5439");
        Method stack = inventory.getClass().getMethod("method_5438", int.class);
        List<String> ids = new ArrayList<>(size);
        for (int index = 0; index < size; index++) ids.add(itemId(stack.invoke(inventory, index)));
        return ids;
    }
    private static String gameModeName(Object mode) throws Exception { return mode == null ? "none" : (String)call(mode, "method_8381"); }
    private static String serverGameMode(Object player) throws Exception { return gameModeName(call(value(player, "field_13974"), "method_14257")); }
    private static int selectedSlot(Object player) throws Exception { return (int)value(call(player, "method_31548"), "field_7545"); }
    private static Object handStack(Object player, String slot) throws Exception {
        return call(player, slot.equals(HandLightFixture.MAIN_SLOT) ? "method_6047" : "method_6079");
    }
    /** Unlocked recipe ids and every obtained advancement criterion; read-only (getProgress would insert entries). */
    private static HandLightFixture.Progress progress(Object player) throws Exception {
        Set<String> recipes = new HashSet<>(), criteria = new HashSet<>();
        for (Object id : new ArrayList<>((Set<?>)value(call(player, "method_14253"), "field_15300"))) recipes.add(id.toString());
        Map<?, ?> tracked = (Map<?, ?>)value(call(player, "method_14236"), "field_41735");
        for (Map.Entry<?, ?> entry : new ArrayList<>(tracked.entrySet())) {
            String advancement = call(entry.getKey(), "comp_1919").toString();
            for (Object criterion : (Iterable<?>)call(entry.getValue(), "method_734"))
                criteria.add(HandLightFixture.criterionKey(advancement, criterion.toString()));
        }
        return new HandLightFixture.Progress(recipes, criteria);
    }
    private static Map<String, Object> serverHands(Object player) throws Exception {
        Object main = handStack(player, HandLightFixture.MAIN_SLOT), off = handStack(player, HandLightFixture.OFF_SLOT);
        return map("main", itemId(main), "main_count", itemCount(main), "off", itemId(off), "off_count", itemCount(off),
            "selected_hotbar_slot", selectedSlot(player), "game_mode", serverGameMode(player));
    }
    private static void setHandSlot(Object player, String slot, String want) throws Exception {
        Object stack = handStack(player, slot);
        String actual = itemId(stack); int count = itemCount(stack);
        if (HandLightFixture.slotMatches(want, actual, count)) return;
        if (!HandLightFixture.slotWritable(actual, count))
            throw new IllegalStateException("Carried-light " + slot + " holds a foreign stack " + actual + " x" + count + "; preserved, nothing written");
        command(HandLightFixture.equipCommand(playerTarget, slot, want));
        Object after = handStack(player, slot);
        if (!HandLightFixture.slotMatches(want, itemId(after), itemCount(after)))
            throw new IllegalStateException("Carried-light " + slot + " did not become " + want + " (actual " + itemId(after) + " x" + itemCount(after) + ")");
    }
    /** Server thread: write both hand slots, then prove the whole 41-slot inventory is exactly the expected equipment. */
    private static void applyEquip(Object player, HandOwnership owned, HandLightFixture.Equip equip) throws Exception {
        if (selectedSlot(player) != owned.selectedSlot()) throw new IllegalStateException("Driver selected hotbar slot changed");
        setHandSlot(player, HandLightFixture.MAIN_SLOT, equip.main());
        setHandSlot(player, HandLightFixture.OFF_SLOT, equip.off());
        List<String> violations = HandLightFixture.inventoryViolations(inventoryIds(player), owned.selectedSlot(), equip);
        if (!violations.isEmpty()) throw new IllegalStateException("Carried-light inventory differs from " + equip.describe() + ": " + violations);
    }
    private static Map<String, Object> handJournal(HandOwnership owned, String phase, boolean baselineLists) {
        LocalLightFixture.Plan plan = owned.plan();
        Map<String, Object> journal = map("world_directory", worldPath.toString(), "world_id", OcclusionFixture.WORLD_ID, "seed", LocalLightFixture.SEED,
            "run_id", runId, "scene", plan.scene(), "phase", phase, "utc", Instant.now().toString(), "player_uuid", playerUuid,
            "driver", "identified sole local player of the exact dedicated V2 world (disposable driver)",
            "restore_game_mode", owned.gameMode(), "selected_hotbar_slot", owned.selectedSlot(),
            "initial_inventory", "all " + HandLightFixture.INVENTORY_SLOTS + " slots verified empty before any change",
            "fixture_items", new TreeSet<>(HandLightFixture.FIXTURE_ITEMS), "slots_written", List.of(HandLightFixture.MAIN_SLOT, HandLightFixture.OFF_SLOT),
            "equip_schedule", plan.hand().steps().stream().map(step -> map("at_seconds", step.atSeconds(), "main", step.equip().main(), "off", step.equip().off())).toList(),
            "baseline_recipe_count", owned.progress().recipes().size(), "baseline_criteria_count", owned.progress().criteria().size(),
            "restore_method", "clear only single fixture lamp stacks (conditional `execute if items`), take newly unlocked recipes, revoke newly obtained advancement criteria, restore game mode; foreign stacks are preserved and reported");
        if (baselineLists) { journal.put("baseline_recipes", owned.progress().recipes()); journal.put("baseline_criteria", owned.progress().criteria()); }
        return journal;
    }
    private static void equipHand(LocalLightFixture.Plan plan) throws Exception {
        localScope();
        requireCarriedTestGame();
        if (ownedHand != null || Files.exists(control.resolve(HAND_JOURNAL)))
            throw new IllegalStateException("An unresolved carried-light journal must be reviewed before equipping");
        if (ownedLocal != plan) throw new IllegalStateException("Carried-light equipment requires its own placed room");
        Object player = serverPlayer();
        List<String> initial = inventoryIds(player);
        List<String> violations = HandLightFixture.inventoryViolations(initial);
        if (!violations.isEmpty())
            throw new IllegalStateException("Disposable driver inventory must be completely empty before equipping (nothing changed): " + violations);
        int selected = selectedSlot(player);
        if (selected < 0 || selected > 8) throw new IllegalStateException("Unexpected selected hotbar slot " + selected);
        HandOwnership owned = new HandOwnership(plan, serverGameMode(player), selected, progress(player));
        if (handRunBaseline == null) handRunBaseline = owned.progress();
        else if (!handRunBaseline.equals(owned.progress()))
            throw new IllegalStateException("Recipe/advancement state drifted from the run baseline between carried-light scenes");
        ownedHand = owned;
        String text = json(handJournal(owned, "before-equip", true)) + "\n";
        atomic(control.resolve(HAND_JOURNAL), text);
        atomic(runDir.resolve(plan.scene() + "-hand-prepared.json"), text);
        // Creative first person: spectators have no rendered hand and no Iris HandRenderer pass.
        command("gamemode creative " + playerTarget);
        if (!serverGameMode(player).equals("creative")) throw new IllegalStateException("Carried-light driver did not enter creative mode");
        applyEquip(player, owned, plan.hand().initial());
        Map<String, Object> equipped = handJournal(owned, "equipped", false);
        equipped.put("server_hands", serverHands(player));
        atomic(runDir.resolve(plan.scene() + "-hand-equipped.json"), json(equipped) + "\n");
    }
    /** Server thread, during sampling: one scheduled instantaneous swap of real stacks. */
    private static void swapHand(LocalLightFixture.Plan plan, int step, long base) throws Exception {
        localScope();
        requireCarriedTestGame();
        HandOwnership owned = ownedHand;
        if (owned == null || owned.plan() != plan) throw new IllegalStateException("Carried-light ownership changed before a scheduled swap");
        Object player = serverPlayer();
        if (!serverGameMode(player).equals("creative")) throw new IllegalStateException("Carried-light driver left creative mode");
        applyEquip(player, owned, plan.hand().steps().get(step).equip());
        handSwapServer.set(step, System.nanoTime() - base);
    }
    private static void cleanHand() throws Exception {
        HandOwnership owned = ownedHand;
        if (owned == null) return;
        localScope();
        Object player = serverPlayer();
        ArrayList<Map<String, Object>> conflicts = new ArrayList<>();
        ArrayList<String> cleared = new ArrayList<>();
        for (String slot : List.of(HandLightFixture.MAIN_SLOT, HandLightFixture.OFF_SLOT)) {
            Object stack = handStack(player, slot);
            String actual = itemId(stack); int count = itemCount(stack);
            switch (HandLightFixture.slotCleanup(actual, count)) {
                case CLEAR -> { command(HandLightFixture.clearCommand(playerTarget, slot, actual)); cleared.add(slot + ":" + actual); }
                case ALREADY_EMPTY -> { }
                case CONFLICT -> conflicts.add(map("slot", slot, "actual_item", actual, "count", count));
            }
        }
        List<String> nonEmpty = HandLightFixture.inventoryViolations(inventoryIds(player));
        HandLightFixture.Restore restore = HandLightFixture.restore(owned.progress(), progress(player));
        for (String restoreCommand : HandLightFixture.restoreCommands(restore, playerTarget)) command(restoreCommand);
        boolean progressExact = progress(player).equals(owned.progress());
        command("gamemode " + owned.gameMode() + " " + playerTarget);
        String mode = serverGameMode(player);
        boolean complete = conflicts.isEmpty() && nonEmpty.isEmpty() && progressExact && mode.equals(owned.gameMode());
        Map<String, Object> evidence = handJournal(owned, complete ? "restored" : "cleanup-conflict", !complete);
        evidence.putAll(map("cleanup_complete", complete, "cleared_slots", cleared, "conflicts_preserved", conflicts,
            "inventory_non_empty_after_clear", nonEmpty, "recipes_taken", restore.takeRecipes(), "criteria_revoked", restore.revokeCriteria(),
            "baseline_recipes_missing", restore.lostRecipes(), "baseline_criteria_missing", restore.lostCriteria(),
            "recipe_and_criteria_state_exact", progressExact, "actual_game_mode", mode, "server_hands", serverHands(player)));
        atomic(runDir.resolve(owned.plan().scene() + "-hand-cleanup.json"), json(evidence) + "\n");
        if (!complete) {
            atomic(control.resolve(HAND_JOURNAL), json(evidence) + "\n");
            throw new IllegalStateException("Carried-light restoration incomplete; journal retained (conflicts " + conflicts.size() +
                ", non-empty " + nonEmpty.size() + ", progress exact " + progressExact + ", game mode " + mode + ")");
        }
        Files.deleteIfExists(control.resolve(HAND_JOURNAL));
        ownedHand = null; handRestoredGameMode = owned.gameMode(); handSettle = 1;
    }
    /** Delayed server recheck at finish: still empty, run-baseline recipes/criteria (late grants revoked) and game mode. */
    private static void settleHandServer() throws Exception {
        if (handRunBaseline == null || handSettle != 1) return;
        localScope();
        Object player = serverPlayer();
        List<String> nonEmpty = HandLightFixture.inventoryViolations(inventoryIds(player));
        HandLightFixture.Restore late = HandLightFixture.restore(handRunBaseline, progress(player));
        for (String restoreCommand : HandLightFixture.restoreCommands(late, playerTarget)) command(restoreCommand);
        boolean exact = progress(player).equals(handRunBaseline);
        String mode = serverGameMode(player);
        atomic(runDir.resolve("hand-light-settled-server.json"), json(map("inventory_all_empty", nonEmpty.isEmpty(), "non_empty", nonEmpty,
            "late_recipes_taken", late.takeRecipes(), "late_criteria_revoked", late.revokeCriteria(), "recipe_and_criteria_state_exact", exact,
            "baseline_recipe_count", handRunBaseline.recipes().size(), "baseline_criteria_count", handRunBaseline.criteria().size(),
            "game_mode", mode, "expected_game_mode", handRestoredGameMode, "utc", Instant.now().toString())) + "\n");
        if (!nonEmpty.isEmpty() || !exact || !mode.equals(handRestoredGameMode))
            throw new IllegalStateException("Carried-light driver not restored after settling");
    }
    private record HeldState(String main, int mainCount, String off, int offCount, int selected, String rendererMain, String rendererOff,
                             float equipMain, float equipOff, String gameMode, boolean firstPerson, boolean flying) {
        boolean items(HandLightFixture.Equip equip) { return HandLightFixture.equipMatches(equip, main, mainCount, off, offCount); }
        boolean settled(HandLightFixture.Equip equip, int selectedSlot) {
            return items(equip) && rendererMain.equals(equip.main()) && rendererOff.equals(equip.off()) &&
                equipMain >= HandLightFixture.SETTLED_EQUIP && equipOff >= HandLightFixture.SETTLED_EQUIP &&
                gameMode.equals("creative") && firstPerson && selected == selectedSlot;
        }
        Map<String, Object> evidence() {
            return map("client_main", main, "client_main_count", mainCount, "client_off", off, "client_off_count", offCount,
                "selected_hotbar_slot", selected, "held_item_renderer_main", rendererMain, "held_item_renderer_off", rendererOff,
                "equip_progress_main", equipMain, "equip_progress_off", equipOff, "client_game_mode", gameMode,
                "first_person", firstPerson, "flying", flying);
        }
    }
    /** Client thread: the actual client player stacks (Iris heldItemId/heldItemId2 inputs) and what HeldItemRenderer draws. */
    private static HeldState held(Object mc) throws Exception {
        Object player = value(mc, "field_1724");
        Object main = call(player, "method_6047"), off = call(player, "method_6079");
        Object renderer = value(value(mc, "field_1773"), "field_4012");
        return new HeldState(itemId(main), itemCount(main), itemId(off), itemCount(off), (int)value(call(player, "method_31548"), "field_7545"),
            itemId(value(renderer, "field_4047")), itemId(value(renderer, "field_4048")),
            (float)value(renderer, "field_4043"), (float)value(renderer, "field_4052"),
            gameModeName(call(value(mc, "field_1761"), "method_2920")), (boolean)call(call(options, "method_31044"), "method_31034"),
            (boolean)value(call(player, "method_31549"), "field_7479"));
    }
    /** Iris' own item light API on the actual client stack (the source of heldBlockLightValue/heldBlockLightValue2). */
    private static Object irisItemLight(Object mc, String slot) {
        try {
            Object player = value(mc, "field_1724"), stack = handStack(player, slot);
            Class<?> provider = Class.forName("net.irisshaders.iris.api.v0.item.IrisItemLightProvider");
            Object item = call(stack, "method_7909");
            if (!provider.isInstance(item)) return "Item is not an IrisItemLightProvider";
            Class<?> playerType = Class.forName("net.minecraft.class_1657"), stackType = Class.forName("net.minecraft.class_1799");
            Object emission = provider.getMethod("getLightEmission", playerType, stackType).invoke(item, player, stack);
            Object color = provider.getMethod("getLightColor", playerType, stackType).invoke(item, player, stack);
            return map("item", itemId(stack), "emission", emission, "color", List.of(color.getClass().getField("x").getFloat(color),
                color.getClass().getField("y").getFloat(color), color.getClass().getField("z").getFloat(color)));
        } catch (Exception error) { return "Unavailable: " + error.getClass().getSimpleName(); }
    }
    private static double[] playerFeet(Object player) throws Exception {
        return new double[]{(double)call(player, "method_23317"), (double)call(player, "method_23318"), (double)call(player, "method_23321")};
    }
    private static double[] vector(Object vec) throws Exception {
        return new double[]{(double)value(vec, "field_1352"), (double)value(vec, "field_1351"), (double)value(vec, "field_1350")};
    }
    private static void startHandSampling(LocalLightFixture.Plan plan) {
        int steps = plan.hand().steps().size();
        handSwapScheduled = new long[steps]; handSwapIssued = new long[steps]; handSwapClient = new long[steps];
        handSwapRenderer = new long[steps]; handSwapSettled = new long[steps]; handSwapServer = new AtomicLongArray(steps);
        for (int step = 0; step < steps; step++) {
            handSwapScheduled[step] = Math.round(plan.hand().steps().get(step).atSeconds() * 1e9);
            handSwapIssued[step] = handSwapClient[step] = handSwapRenderer[step] = handSwapSettled[step] = -1; handSwapServer.set(step, -1);
        }
        // Step 0 was equipped while preparing the scene and proven settled before sampling.
        handSwapIssued[0] = handSwapClient[0] = handSwapRenderer[0] = handSwapSettled[0] = 0; handSwapServer.set(0, 0);
        handStepIssued = 0; handTrace.setLength(0); handTrace.append(HandLightFixture.TRACE_HEADER); handTraceAt = 0;
    }
    /** Every sampled frame of a lamp-hand scene: issue due swaps, observe them frame-exactly and log a 25 Hz trace. */
    private static void handFrame(Object mc, long now, LocalLightFixture.Plan plan) throws Exception {
        HandLightFixture.Spec spec = plan.hand();
        HandOwnership owned = ownedHand;
        if (owned == null || owned.plan() != plan) throw new IllegalStateException("Carried-light ownership missing during sampling");
        long elapsed = now - sampleStart;
        double seconds = elapsed * 1e-9;
        int step = spec.stepAt(seconds);
        while (handStepIssued < step) {
            int due = ++handStepIssued; long base = sampleStart;
            handSwapIssued[due] = elapsed;
            local(() -> swapHand(plan, due, base)).exceptionally(error -> { asyncError = error; return null; });
        }
        HeldState state = held(mc);
        for (int index = 1; index <= handStepIssued; index++) {
            HandLightFixture.Equip equip = spec.steps().get(index).equip();
            if (handSwapClient[index] < 0 && index == step && state.items(equip)) handSwapClient[index] = elapsed;
            if (handSwapRenderer[index] < 0 && handSwapClient[index] >= 0 && state.rendererMain().equals(equip.main()) && state.rendererOff().equals(equip.off()))
                handSwapRenderer[index] = elapsed;
            if (handSwapSettled[index] < 0 && handSwapRenderer[index] >= 0 && state.settled(equip, owned.selectedSlot())) handSwapSettled[index] = elapsed;
        }
        HandLightFixture.Equip expected = spec.equipAt(seconds);
        boolean itemsOk = state.items(expected);
        boolean inGrace = step > 0 && seconds - spec.steps().get(step).atSeconds() <= HandLightFixture.SWAP_GRACE_SECONDS &&
            state.items(spec.steps().get(step - 1).equip());
        if (!itemsOk && !inGrace)
            throw new IllegalStateException(String.format(Locale.ROOT, "Carried-light client stacks at %.3f s are main=%s x%d off=%s x%d, expected %s",
                seconds, state.main(), state.mainCount(), state.off(), state.offCount(), expected.describe()));
        if (!state.gameMode().equals("creative") || !state.firstPerson() || state.selected() != owned.selectedSlot())
            throw new IllegalStateException("Carried-light driver left creative first person or changed hotbar slot during sampling");
        if (now - handTraceAt < 40_000_000L) return;
        handTraceAt = now;
        Object player = value(mc, "field_1724");
        double[] feet = playerFeet(player), eye = vector(call(player, "method_33571"));
        Object camera = call(value(mc, "field_1773"), "method_19418");
        double[] rendered = vector(call(camera, "method_19326"));
        double expectedX = HandLightFixture.routeEyeX(spec, seconds);
        boolean poseOk = HandLightFixture.poseMatches(expectedX, HandLightFixture.trackTolerance(spec), state.firstPerson(), feet, eye, rendered);
        if (!poseOk)
            throw new IllegalStateException(String.format(Locale.ROOT, "Carried-light pose left its law at %.3f s: expected eye x %.4f, player %s, eye %s, camera %s",
                seconds, expectedX, Arrays.toString(feet), Arrays.toString(eye), Arrays.toString(rendered)));
        handTrace.append(HandLightFixture.traceRow(elapsed, (long)call(value(mc, "field_1687"), "method_8532"), step, expectedX, feet, rendered,
            (float)call(camera, "method_19330"), (float)call(camera, "method_19329"), expected, state.main(), state.mainCount(), state.off(), state.offCount(),
            state.selected(), state.rendererMain(), state.rendererOff(), state.equipMain(), state.equipOff(), state.gameMode(), state.firstPerson(),
            state.flying(), poseOk, itemsOk));
    }
    private static List<Map<String, Object>> handSwapEvidence(LocalLightFixture.Plan plan) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (int step = 0; step < plan.hand().steps().size(); step++) {
            HandLightFixture.Equip equip = plan.hand().steps().get(step).equip();
            long client = handSwapClient[step], scheduled = handSwapScheduled[step];
            rows.add(map("step", step, "scheduled_ns", scheduled, "expected_main", equip.main(), "expected_off", equip.off(),
                "issued_ns", handSwapIssued[step], "server_applied_ns", handSwapServer.get(step), "client_observed_ns", client,
                "renderer_observed_ns", handSwapRenderer[step], "renderer_settled_ns", handSwapSettled[step],
                "client_latency_ms", step == 0 || client < 0 ? null : (client - scheduled) * 1e-6));
        }
        return rows;
    }
    private static Map<String, Object> handFixtureMetadata(LocalLightFixture.Plan plan) {
        HandLightFixture.Spec spec = plan.hand();
        List<Double> main = HandLightFixture.handOrigin(true), off = HandLightFixture.handOrigin(false);
        Map<String, Object> visible = new LinkedHashMap<>(), fromMain = new LinkedHashMap<>(), fromOff = new LinkedHashMap<>(), distance = new LinkedHashMap<>();
        var grid = LocalLightFixture.grid(plan);
        HandLightFixture.samples().forEach((name, point) -> {
            visible.put(name, LocalLightFixture.clear(plan, plan.eye(), point, true));
            boolean[] m = HandLightFixture.tapsOpen(grid, HandLightFixture.vec(point), HandLightFixture.vec(main));
            boolean[] o = HandLightFixture.tapsOpen(grid, HandLightFixture.vec(point), HandLightFixture.vec(off));
            fromMain.put(name, List.of(m[0], m[1], m[2]));
            fromOff.put(name, List.of(o[0], o[1], o[2]));
            distance.put(name, Math.sqrt(Math.pow(point.get(0) - plan.eyeX(), 2) + Math.pow(point.get(1) - plan.eyeY(), 2) + Math.pow(point.get(2) - plan.eyeZ(), 2)));
        });
        Map<String, Integer> roles = new TreeMap<>();
        plan.placements().forEach(cell -> roles.merge(cell.role(), 1, Integer::sum));
        Map<String, Object> result = map("scene", plan.scene(), "seed", LocalLightFixture.SEED, "kind", "carried-light (hand-held) TEST fixture",
            "reserved_air_box_inclusive", LocalLightFixture.BOX, "reserved_air_cells", LocalLightFixture.boxCells(),
            "room_shell_inclusive", List.of(HandLightFixture.SHELL_X0, HandLightFixture.SHELL_Y0, HandLightFixture.SHELL_Z0, HandLightFixture.SHELL_X1, HandLightFixture.SHELL_Y1, HandLightFixture.SHELL_Z1),
            "room_interior_air_inclusive", List.of(HandLightFixture.SHELL_X0 + 1, HandLightFixture.SHELL_Y0 + 1, HandLightFixture.SHELL_Z0 + 1, HandLightFixture.SHELL_X1 - 1, HandLightFixture.SHELL_Y1 - 1, HandLightFixture.SHELL_Z1 - 1),
            "materials", map("floor_y150", HandLightFixture.FLOOR, "ceiling_y154", HandLightFixture.CEILING, "receiver_back_wall_z-412", HandLightFixture.RECEIVER,
                "side_and_south_walls", HandLightFixture.WALL, "pillars", HandLightFixture.PILLAR),
            "pillar", spec.pillar().name().toLowerCase(Locale.ROOT),
            "pillar_cells", spec.pillar() == HandLightFixture.Pillar.NONE ? List.of() : plan.placements().stream().filter(cell -> cell.role().endsWith("-pillar")).map(LocalLightFixture.Cell::position).toList(),
            "requested_player_position", List.of(plan.eyeX(), plan.playerY(), plan.eyeZ()), "requested_eye_position", plan.eye(),
            "requested_camera_rotation", List.of(plan.yaw(), plan.pitch()), "requested_world_time", plan.timeOfDay(),
            "eye_to_surface_m", map("back_wall", plan.eyeZ() - (HandLightFixture.SHELL_Z0 + 1), "south_wall", HandLightFixture.SHELL_Z1 - plan.eyeZ(),
                "ceiling", HandLightFixture.SHELL_Y1 - plan.eyeY(), "floor", plan.eyeY() - (HandLightFixture.SHELL_Y0 + 1),
                "west_wall", plan.eyeX() - (HandLightFixture.SHELL_X0 + 1), "east_wall", HandLightFixture.SHELL_X1 - plan.eyeX()),
            "equip_schedule", spec.steps().stream().map(step -> map("at_seconds", step.atSeconds(), "main", step.equip().main(), "off", step.equip().off(),
                "vanilla_luminance_main", HandLightFixture.VANILLA_LUMINANCE.get(step.equip().main()), "vanilla_luminance_off", HandLightFixture.VANILLA_LUMINANCE.get(step.equip().off()))).toList(),
            "final_expected_equipment", map("main", spec.last().main(), "off", spec.last().off()),
            "route", spec.walking() ? map("law", "eye x = 406.65 + 1.75*sin(2*pi*t/8s) for 0<=t<=8 s from sample start, then held at 406.65 (fixed pose); y 152.62, z -407.0, yaw 180, pitch 0 fixed",
                "driver", "integrated-server tp of the identified creative player at 20 Hz (tick-stepped)", "tracking_tolerance_m", HandLightFixture.TRACK_TOLERANCE,
                "front_pillar_crossings_seconds", HandLightFixture.routePillarCrossings()) : false,
            "release_light_anchors", map("method", "Geometric model of the release shader (not a rendered-light measurement): " + HandLightFixture.ANCHOR_SOURCE +
                    "; evaluated at the requested eye, yaw 180, pitch 0, right-handed", "view_offset_right_down_forward_m", List.of(HandLightFixture.HAND_RIGHT, HandLightFixture.HAND_DOWN, HandLightFixture.HAND_FORWARD),
                "main", main, "off", off,
                "emitter", map("radius_m", HandLightFixture.EMITTER_RADIUS, "tap_radius_m", HandLightFixture.EMITTER_RADIUS * HandLightFixture.TAP_SCALE,
                    "taps", "centre+u, centre-0.5u+0.866v, centre-0.5u-0.866v; u = normalize(cross(l, up))*radius*0.66, v = cross(l, u), l receiver->anchor",
                    "receiver_start_offset_m", HandLightFixture.RECEIVER_NORMAL_OFFSET, "traversal", "lampTransmission carried=true: every visited cell incl. the tap's, >0.00005 m inside a full block blocks, <=32 cells")),
            "receiver_rois", HandLightFixture.roiReports(),
            "private_test_game", handTestGame == null ? "unverified" : map("game", handTestGame.game().toString(), "untouched_original_game", handTestGame.original().toString(),
                "matrix", handTestGame.matrix(), "player", HandLightFixture.TEST_USERNAME,
                "checks", "explicit request opt-in naming this game and the independently derived original; symlink-free path; distinct inode from the original; non-hard-linked TEST world files"),
            "camera_to_sample_voxel_clear", visible, "main_taps_to_sample_open", fromMain, "off_taps_to_sample_open", fromOff,
            "eye_to_sample_distance_m", distance, "surface_samples", HandLightFixture.samples(),
            "vanilla_light", "No emitting block placed and the shell is sealed: vanilla block and sky light are 0 in the room; all carried light is shader-side",
            "placed_cells", plan.placements().size(), "placed_cells_by_role", roles, "eye_tolerance_m", HandLightFixture.EYE_TOLERANCE);
        return result;
    }
    private static Map<String, Object> walkMetadata() {
        return map("law", "eye x = 410.5 + (405.5-410.5)*clamp(t/8s,0,1), t from sample start; then held at 405.5",
            "start_eye", List.of(LocalLightFixture.WALK_START_X, LocalLightFixture.EYE_Y, LocalLightFixture.EYE_Z),
            "end_eye", List.of(LocalLightFixture.WALK_END_X, LocalLightFixture.EYE_Y, LocalLightFixture.EYE_Z),
            "route_seconds", LocalLightFixture.WALK_SECONDS, "speed_m_per_s", (LocalLightFixture.WALK_START_X - LocalLightFixture.WALK_END_X) / LocalLightFixture.WALK_SECONDS,
            "fixed", "eye y 157.0, z -402.0, yaw 180, pitch 22",
            "cluster_boundary", map("axis", "x", "world_x", LocalLightFixture.WALK_BOUNDARY_X, "cluster_size_blocks", LocalLightFixture.CLUSTER_SIZE,
                "convention", "world-aligned floor(x/8); x=408 is not a 16-block chunk-section boundary",
                "clusters", List.of(LocalLightFixture.clusterX(LocalLightFixture.WALK_START_X), LocalLightFixture.clusterX(LocalLightFixture.WALK_END_X)),
                "analytical_crossing_seconds", LocalLightFixture.walkBoundarySeconds()),
            "driver", "integrated-server tp of the identified spectator at 20 Hz (tick-stepped translation, not per-frame interpolated)",
            "tracking_tolerance_m", LocalLightFixture.WALK_TRACK_TOLERANCE,
            "collision", "spectator body box cells along the whole route are reserved AIR and never placed (CPU-tested)",
            "route_log", "<scene>-walk-route.csv at 25 Hz: actual player and rendered Camera position per elapsed_ns; join to native-motion frames.csv or full-frame ticks.csv by elapsed_ns",
            "fixed_view_variants", map("lamp-night-walk-east", LocalLightFixture.EYE_X, "lamp-night-walk-west", LocalLightFixture.WALK_WEST_X));
    }
    private static List<Float> irisCameraMatrix(Object state, String getter) throws Exception {
        Object matrix = call(state, getter);
        float[] data = new float[16];
        Class.forName("org.joml.Matrix4fc").getMethod("get", float[].class).invoke(matrix, (Object)data);
        List<Float> result = new ArrayList<>(16);
        for (float value : data) {
            if (!Float.isFinite(value)) throw new IllegalStateException("Non-finite Iris camera transform");
            result.add(value);
        }
        return result;
    }
    private static Map<String, Object> localCameraProjection(LocalLightFixture.Plan plan, List<Double> eye, List<Integer> frame) throws Exception {
        Object state = Class.forName("net.irisshaders.iris.uniforms.CapturedRenderingState").getField("INSTANCE").get(null);
        List<Float> projection = irisCameraMatrix(state, "getGbufferProjection");
        List<Float> modelView = irisCameraMatrix(state, "getGbufferModelView");
        Map<String, List<Double>> points = new LinkedHashMap<>(LocalLightFixture.samples(plan));
        if (plan.hand() == null && Math.abs(eye.get(0) - LocalLightFixture.EYE_X) < .001)
            points.put("lantern-reflection", LocalLightFixture.lanternReflectionPoint());
        if (plan.hand() != null) {
            points.put("release-main-hand-anchor", HandLightFixture.handOrigin(true));
            points.put("release-off-hand-anchor", HandLightFixture.handOrigin(false));
        }
        Map<String, Object> pixels = new LinkedHashMap<>();
        for (var point : points.entrySet()) {
            double[] v = {0, 0, 0, 1};
            for (int i = 0; i < 3; i++) v[i] = point.getValue().get(i) - eye.get(i);
            for (var matrix : List.of(modelView, projection)) {
                double[] out = new double[4];
                for (int j = 0; j < 4; j++) for (int k = 0; k < 4; k++) out[j] += matrix.get(k*4+j) * v[k];
                v = out;
            }
            if (v[3] > 0) pixels.put(point.getKey(), List.of((v[0]/v[3]+1)*frame.get(0)/2, (1-v[1]/v[3])*frame.get(1)/2));
        }
        return map("matrix_storage", "column-major Iris CapturedRenderingState", "projection", projection,
            "model_view", modelView, "eye", eye, "framebuffer", frame, "pixels", pixels);
    }
    private static Map<String, Object> localFixtureMetadata(LocalLightFixture.Plan plan) {
        Map<String, Object> visible = new LinkedHashMap<>(), model = new LinkedHashMap<>(), lampPaths = new LinkedHashMap<>(), shade = new LinkedHashMap<>();
        LocalLightFixture.samples().forEach((name, point) -> {
            visible.put(name, LocalLightFixture.clear(plan, plan.eye(), point, true));
            model.put(name, LocalLightFixture.predictedBlockLight(plan, point));
            if (plan.timeOfDay() == LocalLightFixture.DAY_TIME) shade.put(name, LocalLightFixture.solarShaded(plan, point));
            for (LocalLightFixture.Lamp lamp : plan.lamps())
                lampPaths.put(lamp.id() + "->" + name, LocalLightFixture.clear(plan, lamp.center(), point, false));
        });
        Map<String, Integer> roles = new TreeMap<>();
        plan.placements().forEach(cell -> roles.merge(cell.role(), 1, Integer::sum));
        Map<String, Object> result = map("scene", plan.scene(), "seed", LocalLightFixture.SEED, "reserved_air_box_inclusive", LocalLightFixture.BOX,
            "reserved_air_cells", LocalLightFixture.boxCells(), "requested_player_position", List.of(plan.eyeX(), plan.playerY(), LocalLightFixture.EYE_Z),
            "requested_eye_position", plan.eye(), "requested_camera_rotation", List.of(plan.yaw(), plan.pitch()),
            "moving_view", plan.moving() ? map("law", "yaw = 180 + 10*sin(2*pi*t/10s), t from sample start; pitch and position fixed") : false,
            "walk_route", plan.walking() ? walkMetadata() : false,
            "eye_cluster_x", LocalLightFixture.clusterX(plan.eyeX()),
            "requested_world_time", plan.timeOfDay(), "intervening_wall_present", plan.wallPresent(),
            "divider_block", plan.divider() == null ? "none" : plan.divider(),
            "intervening_wall_cells", "x=409, y=151..154, z=-418..-414 (stone_bricks wall / red_stained_glass divider; reserved AIR when absent)",
            "lamps", plan.lamps().stream().map(lamp -> map("block", lamp.id(), "cell", List.of(lamp.x(), lamp.y(), lamp.z()),
                "center", lamp.center(), "vanilla_block_light_emission", lamp.emission())).toList(),
            "placed_cells", plan.placements().size(), "placed_cells_by_role", roles,
            "surface_samples", LocalLightFixture.samples(), "lantern_reflection_point_on_still_water", LocalLightFixture.lanternReflectionPoint(),
            "still_water_surface_y", LocalLightFixture.WATER_SURFACE_Y,
            "camera_to_sample_voxel_clear", visible, "lamp_to_sample_voxel_clear", lampPaths,
            "predicted_vanilla_block_light_model", map("method", "Analytical flood-fill of vanilla block light through the authored voxels; NOT a measurement", "values", model),
            "eye_tolerance_m", LocalLightFixture.EYE_TOLERANCE);
        if (plan.walking()) {
            // Visibility changes along the route (the canopy hides the day-only shade sample west of ~x407.5).
            Map<String, Object> routeVisible = new LinkedHashMap<>();
            for (double seconds : new double[]{0, LocalLightFixture.walkBoundarySeconds(), LocalLightFixture.WALK_SECONDS}) {
                List<Double> keyEye = List.of(LocalLightFixture.walkEyeX(plan, seconds), LocalLightFixture.EYE_Y, LocalLightFixture.EYE_Z);
                Map<String, Object> clear = new LinkedHashMap<>();
                LocalLightFixture.samples().forEach((name, point) -> clear.put(name, LocalLightFixture.clear(plan, keyEye, point, true)));
                routeVisible.put(String.format(Locale.ROOT, "t=%.3fs,x=%.3f", seconds, keyEye.get(0)), clear);
            }
            result.put("route_keyframe_camera_to_sample_voxel_clear", routeVisible);
        }
        if (!shade.isEmpty()) {
            double[] sun = LocalLightFixture.sunDirection(plan.timeOfDay());
            result.put("solar_shade_by_lab_geometry", map("method", "Ray from each sample toward the vanilla sun direction at the frozen time through authored voxels only (leaves block; terrain outside the reservation ignored); NOT a measurement",
                "sun_direction", List.of(sun[0], sun[1], sun[2]), "shaded", shade));
        }
        return result;
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
        if (Set.of("preparing", "preparing-scene", "warmup", "sampling", "screenshot", "finishing", "aborting-fixtures").contains(state)) throw new IllegalStateException("A run is already active");
        runDir = null; stage = -1; scenarios = null;
        config = properties(game.resolve("config/aqualumen-benchmark.properties"));
        if (!config.getProperty("schema", "").equals("2") || !request.getProperty("world_id", "").equals(config.getProperty("world_id")))
            throw new IllegalStateException("Configuration schema or request world UUID mismatch");
        playerUuid = ""; guard(mc, true);
        captureMotion = config.getProperty("capture_motion", "false").equals("true");
        recordGroundClip = config.getProperty("ground_frame_strip", "false").equals("true");
        fullFrameClip=config.getProperty("water_frame_clip","false").equals("true");
        nativeMotion = null;
        if (captureMotion && !UnderwaterScene.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))))
            throw new IllegalStateException("Native motion capture requires the exact dedicated V2 world");
        runId = request.getProperty("run_id", "");
        if (!runId.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")) throw new IllegalArgumentException("Invalid run identifier");
        scenarios = request.getProperty("scenarios", "").split(",");
        if (scenarios.length == 0 || new HashSet<>(Arrays.asList(scenarios)).size() != scenarios.length || Arrays.stream(scenarios).anyMatch(scene -> !KNOWN.contains(scene) && OcclusionFixture.parse(scene) == null && UnderwaterScene.parse(scene) == null && LocalLightFixture.parse(scene) == null))
            throw new IllegalArgumentException("Unknown or duplicate scenarios");
        boolean localRun = Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null);
        if (localRun && (!LocalLightFixture.authorized(config.getProperty("world"), config.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))) ||
            !LocalLightFixture.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed")))))
            throw new IllegalStateException("Local-light fixture requires the exact dedicated AqualumenNaturalV2 UUID and seed308060");
        if (Arrays.stream(scenarios).anyMatch(scene -> scene.equals("coast-rain-close") || UnderwaterScene.parse(scene) != null) &&
            (!UnderwaterScene.authorized(config.getProperty("world"), config.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))) ||
             !UnderwaterScene.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed")))))
            throw new IllegalStateException("Water fixture views require the exact dedicated V2 UUID and seed308060");
        if(fullFrameClip && (captureMotion || recordGroundClip || !size(mc,true).equals(List.of(960,540)) ||
            !UnderwaterScene.authorized(worldPath.getFileName().toString(),worldMarker.getProperty("world_id"),Long.parseLong(worldMarker.getProperty("seed"))) ||
            Arrays.stream(scenarios).anyMatch(s -> !Set.of("underwater-up-moving","underwater-shore-moving","ground-sun-motion","lamp-night-walk").contains(s) && !HandLightFixture.isHandScene(s))))
            throw new IllegalArgumentException("Full-frame capture requires the guarded 960x540 movement scenes");
        fixtureRun = Arrays.stream(scenarios).anyMatch(scene -> OcclusionFixture.parse(scene) != null || LocalLightFixture.parse(scene) != null);
        if (recordGroundClip && (captureMotion || Arrays.stream(scenarios).filter(s -> s.equals("ground-sun-motion") || s.equals("ground-camera-motion")).count()!=1 ||
            !size(mc,true).equals(List.of(2560,1440)) || !OcclusionFixture.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"))))
            throw new IllegalArgumentException("Ground clip requires a 1440p ground-motion run in the dedicated V2 world");
        if (fixturesPending())
            throw new IllegalStateException("An unresolved opaque/local-light fixture journal requires scoped review before a new run");
        if (fixtureRun && !OcclusionFixture.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id")))
            throw new IllegalStateException("Opaque fixtures require the exact dedicated AqualumenNaturalV2 UUID");
        warmupSeconds = Double.parseDouble(request.getProperty("warmup_seconds", "20"));
        sampleSeconds = Double.parseDouble(request.getProperty("sample_seconds", "30"));
        if (!Double.isFinite(warmupSeconds) || !Double.isFinite(sampleSeconds) || warmupSeconds < 5 || sampleSeconds < 5 || sampleSeconds > 300)
            throw new IllegalArgumentException("Invalid warmup/sample durations");
        if (localRun && warmupSeconds < LocalLightFixture.MIN_WARMUP_SECONDS)
            throw new IllegalArgumentException("Local-light scenes need >=15 s warmup for chunk mesh and block-light updates");
        if (Arrays.stream(scenarios).map(LocalLightFixture::parse).anyMatch(plan -> plan != null && plan.walking()) &&
            sampleSeconds < LocalLightFixture.WALK_SECONDS + 1)
            throw new IllegalArgumentException("lamp-night-walk needs >=9 s sample: 8 s route plus a held end pose before capture");
        if (Arrays.stream(scenarios).map(HandLightFixture::spec).anyMatch(spec -> spec != null && spec.needsLongSample()) &&
            sampleSeconds < HandLightFixture.MIN_SEQUENCE_SAMPLE_SECONDS)
            throw new IllegalArgumentException("lamp-hand walk/putaway need >=9 s sample: 8 s route/schedule plus a held, settled final state before capture");
        handTestGame = null;
        handOptIn = Map.of();
        if (Arrays.stream(scenarios).anyMatch(HandLightFixture::isHandScene)) {
            // Before any run directory, command, HUD change or world mutation: the run must be the private duplicated TEST game.
            Map<String, String> optIn = new HashMap<>();
            for (String key : List.of(HandLightFixture.OPT_IN_KEY, HandLightFixture.OPT_IN_GAME, HandLightFixture.OPT_IN_ORIGINAL))
                if (request.getProperty(key) != null) optIn.put(key, request.getProperty(key));
            handOptIn = Map.copyOf(optIn);
            try { requireCarriedTestGame(); }
            catch (Exception refused) { handOptIn = Map.of(); handTestGame = null; throw refused; }
        } else if (request.getProperty(HandLightFixture.OPT_IN_KEY) != null)
            throw new IllegalArgumentException("Carried-light TEST opt-in given without lamp-hand scenes");
        autoQuit = Boolean.parseBoolean(request.getProperty("auto_quit", "false"));
        Path runs = control.resolve("runs"); Files.createDirectories(runs);
        runDir = runs.resolve(runId); Files.createDirectory(runDir);
        sites.clear(); timings.clear(); stage = -1; previous = 0; asyncError = null; quitAfterCleanup = false; abortReason = ""; underwaterSurfaceY = Double.NaN;
        localValidation = null; localValidationTask = null; localSettle = 0;
        handRunBaseline = null; handSettle = 0; handSettleStart = 0; handRestoredGameMode = ""; handPreRunGameMode = "";
        boolean handRun = Arrays.stream(scenarios).anyMatch(HandLightFixture::isHandScene);
        suppressHud(mc);
        Object commandManager = call(server, "method_3734");
        dispatcher = call(commandManager, "method_9235");
        source = call(call(server, "method_3739"), "method_9217");
        execute = dispatcher.getClass().getMethod("execute", String.class, Object.class);
        serverWorld = call(server, "method_30002");
        pending = local(() -> {
            if (handRun) handPreRunGameMode = serverGameMode(serverPlayer()); // evidence only; scenes restore their own journaled mode
            command("gamemode spectator " + playerTarget);
            command("gamerule doDaylightCycle false"); command("gamerule doWeatherCycle false");
            command("gamerule doMobSpawning false"); command("gamerule sendCommandFeedback false"); command("gamerule logAdminCommands false");
            boolean ocean = Arrays.stream(scenarios).anyMatch(scene -> !scene.startsWith("coast") && !scene.startsWith("river") && !scene.equals("cave-water") && OcclusionFixture.parse(scene) == null && UnderwaterScene.parse(scene) == null && LocalLightFixture.parse(scene) == null);
            if (ocean) sites.put("ocean", discover("ocean"));
            for (String scene : scenarios) {
                UnderwaterScene.Plan pose=UnderwaterScene.parse(scene);
                if (pose==null) continue;
                boolean shore=scene.startsWith("underwater-shore-");
                String column=shore?scene:"underwater-up";
                if (sites.containsKey(column)) continue;
                int x=(int)Math.floor(pose.x()), y=62, z=(int)Math.floor(pose.z());
                if (!water(x,y,z) || water(x,y+1,z)) throw new IllegalStateException("Established upward-view column is not the expected natural water surface");
                Object position = pos(x,y,z);
                Object fluid = serverWorld.getClass().getMethod("method_8316", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, position);
                underwaterSurfaceY = y + (float)fluid.getClass().getMethod("method_15763", Class.forName("net.minecraft.class_1922"), Class.forName("net.minecraft.class_2338")).invoke(fluid, serverWorld, position);
                if (Math.abs(underwaterSurfaceY - UnderwaterScene.SURFACE_Y) > .005) throw new IllegalStateException("Established upward-view fluid surface changed");
                int depth = 1; while (depth < 32 && water(x,y-depth,z)) depth++;
                if (depth < (shore?3:6)) throw new IllegalStateException("Established upward-view column is too shallow for the deep eye control");
                Object actualBiome = serverWorld.getClass().getMethod("method_23753", Class.forName("net.minecraft.class_2338")).invoke(serverWorld, position);
                sites.put(column, new Site(pose.x(),pose.playerY(),pose.z(),pose.yaw(),pose.pitch(),biome(actualBiome),depth));
            }
            if (Arrays.stream(scenarios).anyMatch(s -> s.startsWith("coast-"))) sites.put("coast", discover("coast"));
            if (Arrays.asList(scenarios).contains("river-day")) sites.put("river", discover("river"));
            if (Arrays.asList(scenarios).contains("cave-water")) sites.put("cave", cave());
            if (Arrays.asList(scenarios).contains("nether-view")) sites.put("nether", new Site(.5, 70, .5, 120, 12, "fixed-nether-view", 0));
            if (Arrays.asList(scenarios).contains("end-view")) sites.put("end", new Site(.5, 80, .5, 0, 18, "fixed-end-view", 0));
            if (Arrays.stream(scenarios).anyMatch(scene -> OcclusionFixture.parse(scene) != null)) sites.put("opaque", new Site(448.5, 160, -383.5, 0, 0, "temporary-opaque-air-fixture", 0));
            if (Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null))
                sites.put("lamp", new Site(LocalLightFixture.EYE_X, LocalLightFixture.EYE_Y - LocalLightFixture.EYE_HEIGHT, LocalLightFixture.EYE_Z,
                    LocalLightFixture.YAW, LocalLightFixture.PITCH, "temporary-local-light-fixture", 2));
        });
        state = "preparing"; status("Discovering real ocean, beach and river water on the local server");
    }
    private static Site site() {
        String scene = scenarios[stage];
        LocalLightFixture.Plan lampPlan = LocalLightFixture.parse(scene);
        if (lampPlan != null) {
            Site lamp = sites.get("lamp"); // the walk scene starts at its route start; fixed variants at their own eye x
            // Carried-light scenes use their own room pose; the original lamp scenes resolve to the same values as before.
            return new Site(lampPlan.eyeX(), lampPlan.playerY(), lampPlan.eyeZ(), lampPlan.yaw(), lampPlan.pitch(), lamp.biome, lamp.depth);
        }
        if (scene.equals("coast-rain-close")) {
            Site coast = sites.get("coast");
            return new Site(coast.x, coast.y-1.53, coast.z, coast.yaw, 50, coast.biome, coast.depth);
        }
        if (scene.startsWith("ground-")) return new Site(scene.equals("ground-camera-motion") ? 133.6 : 134,66,335,0,30,"natural-shore-contact",0);
        if (scene.equals("ocean-sun-day") || scene.equals("ocean-sun-dusk")) {
            Site ocean = sites.get("ocean");
            return new Site(ocean.x, ocean.y, ocean.z, 90, scene.equals("ocean-sun-day") ? -90 : -15, ocean.biome, ocean.depth);
        }
        UnderwaterScene.Plan underwater = UnderwaterScene.parse(scene);
        if (underwater != null) {
            Site column = sites.get(scene.startsWith("underwater-shore-")?scene:"underwater-up");
            return new Site(underwater.x(), underwater.playerY(), underwater.z(), underwater.yaw(), underwater.pitch(), column.biome, column.depth);
        }
        return sites.get(OcclusionFixture.parse(scene) != null ? "opaque" : scene.startsWith("coast") ? "coast" : scene.startsWith("river") ? "river" : scene.equals("cave-water") ? "cave" : scene.equals("nether-view") ? "nether" : scene.equals("end-view") ? "end" : "ocean");
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
        if (groundClip != null) { groundClip.close(); groundClip = null; }
        nativeMotion = null;
        stage++;
        if (stage >= scenarios.length) {
            pending = local(() -> {
                if (Arrays.asList(scenarios).contains("ground-sun-motion")) command("gamerule doDaylightCycle false");
                cleanHand(); cleanBoat(); cleanGlass(); cleanOpaque();
                if (Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null)) { cleanLocal(); localSettle = 1; }
                if (!dimension(scenarios[scenarios.length - 1]).equals("minecraft:overworld")) {
                    Site home = sites.get("ocean");
                    command(String.format(Locale.ROOT, "execute in minecraft:overworld run tp %s %.3f %.3f %.3f -45 9", playerTarget, home.x, home.y, home.z));
                }
            });
            state = "finishing"; start = System.nanoTime(); status("All scenes recorded; completing local cleanup"); return;
        }
        Site site = site(); String name = scenarios[stage];
        localValidation = null; localValidationTask = null;
        walkRoute.setLength(0); walkLogAt = 0; walkFov = null;
        pending = local(() -> {
            OcclusionFixture.Plan fixture = OcclusionFixture.parse(name);
            LocalLightFixture.Plan lamp = LocalLightFixture.parse(name);
            if (Arrays.asList(scenarios).contains("ground-sun-motion")) command("gamerule doDaylightCycle false");
            cleanHand(); cleanBoat(); cleanGlass(); cleanOpaque(); cleanLocal(); command("time set " + (lamp != null ? lamp.timeOfDay() : fixture != null ? fixture.timeOfDay() : name.equals("ocean-sun-dusk") ? 11000 : name.equals("ocean-dusk") ? 12700 : name.equals("ocean-night") ? 18000 : 6000));
            command("weather " + (name.equals("ocean-rain") || name.equals("coast-rain-close") ? "rain" : "clear") + " 1000000");
            command(String.format(Locale.ROOT, "execute in %s run tp %s %.3f %.3f %.3f %.3f %.3f", dimension(name), playerTarget, site.x, cameraY(), name.equals("glass-layers") ? site.z - 12 : site.z, lamp != null ? lamp.yaw() : fixture != null ? fixture.yaw() : name.equals("glass-layers") ? 0.0 : name.equals("ocean-dusk") ? 90.0 : site.yaw, lamp != null ? lamp.pitch() : fixture != null ? fixture.pitch() : site.pitch));
            if (name.equals("glass-layers")) glass(site);
            if (fixture != null) placeOpaque(fixture);
            if (lamp != null) placeLocal(lamp);
            if (lamp != null && lamp.hand() != null) equipHand(lamp);
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
    private static Map<String, Object> underwaterMetadata(UnderwaterScene.Plan plan) {
        return map("scene", plan.scene(), "requested_player_position", List.of(plan.x(),plan.playerY(),plan.z()),
            "requested_camera_rotation", List.of(plan.yaw(),plan.pitch()), "requested_eye_depth", plan.eyeDepth(),
            "reference_surface_y", UnderwaterScene.SURFACE_Y, "measured_surface_y", underwaterSurfaceY,
            "eye_tolerance_m", UnderwaterScene.EYE_TOLERANCE, "requested_world_time", 6000,
            "terrain_placement", false);
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
            "iris_render_target_storage", RenderTargetSnapshot.capture(),
            "scenarios", Arrays.asList(scenarios), "warmup_seconds", warmupSeconds, "sample_seconds", sampleSeconds, "sites", coordinates,
            "native_motion_capture_active", captureMotion,
            "frame_method", captureMotion ? "System.nanoTime render-tail intervals including native PNG capture overhead; not a clean performance benchmark" : "System.nanoTime render-tail intervals; one start boundary discarded; setup/screenshots outside sample",
            "camera_lock", "GameRenderer.renderWorld HEAD, after mouse/tick input; current and interpolated yaw/pitch; actual Camera validated at capture",
            "terrain_fixture", fixtureRun ? "Temporary white-concrete wall and colored-concrete/sea-lantern target in exact verified AIR; per-cell expected-state journal; each scene/finally cleanup to AIR in dedicated UUID world" : Arrays.asList(scenarios).contains("glass-layers") ? "Three temporary glass slabs in previously verified air; removed after scene; disposable exact UUID world only" : "No terrain placement"));
        if (fixtureRun) metadata.putAll(map("fixture_world", map("name", OcclusionFixture.WORLD_NAME, "world_id", OcclusionFixture.WORLD_ID),
            "fixture_plans", Arrays.stream(scenarios).map(OcclusionFixture::parse).filter(Objects::nonNull).map(Recorder::fixtureMetadata).toList(),
            "visual_validation_limits", "Sequential shots have animated clouds and exposure changes: hidden-color pairs are not pixel-exact evidence of a cloud-radiance leak fix. Open controls test target visibility and closed controls test wall occlusion; the separate production opaque-pixel/cloud-radiance GPU regression is the causal test. West-facing backlit/front-lit controls use approximately opposed sun times11000/1000: partial receiver illumination, indirect sky light and atmospheric fog are valid; do not demand an all-black shadow."));
        if(fullFrameClip) {
            metadata.put("full_frame_capture",map("resolution",List.of(960,540),"hz",25,"source","Minecraft final color attachment"));
            metadata.put("frame_method","Render-tail intervals include full-frame readback and disk writes");
        }
        if (recordGroundClip) metadata.put("ground_clip", map("scene",Arrays.asList(scenarios).contains("ground-camera-motion") ? "ground-camera-motion" : "ground-sun-motion", "cadence_hz",25,
            "rgba_bottom_left_xywh",List.of(GroundShadowClip.X,GroundShadowClip.Y,GroundShadowClip.WIDTH,GroundShadowClip.HEIGHT),
            "timings_include_readback",true));
        if (Arrays.stream(scenarios).allMatch(s -> s.startsWith("ground-"))) metadata.putAll(map(
            "terrain_fixture", "Stone steps and oak fence on existing solid shore blocks, individually journaled",
            "visual_validation_limits", "Compare fixed cameras on the same natural ground; moving-sun screenshots have capture overhead."));
        if (Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null)) {
            metadata.put("local_light_fixture_plans", Arrays.stream(scenarios).map(LocalLightFixture::parse).filter(Objects::nonNull)
                .map(plan -> plan.hand() != null ? handFixtureMetadata(plan) : localFixtureMetadata(plan)).toList());
            metadata.put("local_light_fixture", map("world", map("name", OcclusionFixture.WORLD_NAME, "world_id", OcclusionFixture.WORLD_ID, "seed", LocalLightFixture.SEED),
                "method", "Authored platform/canopy/shelter/sealed pool in exact verified reserved AIR; per-cell previous-state journal; exact-state placement check; pre-sample whole-box validation; reverse-order restore to AIR per scene; delayed whole-box AIR recheck at finish",
                "visual_validation_limits", "Sequential screenshots: clouds, exposure and moon are not pixel-locked. Wall vs open pairs isolate the intervening wall on the lamp-to-receiver path (camera path is the same and voxel-clear); wall vs wall-off isolate the lamp with identical geometry. glass vs glass-off isolate the lamp behind a red_stained_glass divider on the identical 20 cells (vanilla block light is untinted and unattenuated by glass; any color is shader-side). day-canopy vs day-off isolate the torch under the oak; solar shade is lab-geometry only (leaves treated as blocking). The walk is tick-stepped server translation (20 Hz), not per-frame interpolated motion; native-motion PNGs are at most 10 Hz/80 frames and their capture overhead pollutes timings. Predicted block-light values are an analytical flood-fill model, not measurements."));
            if (Arrays.stream(scenarios).allMatch(scene -> LocalLightFixture.parse(scene) != null)) {
                metadata.remove("fixture_plans"); metadata.remove("visual_validation_limits");
            }
            if (Arrays.stream(scenarios).allMatch(scene -> LocalLightFixture.parse(scene) != null))
                metadata.put("terrain_fixture", "Temporary local-light fixture (grass/stone platform, oak log/persistent-leaf canopy, roofed two-bay shelter with optional stone/red-glass divider, sealed still pool, torch/soul torch/lantern) in the exact reserved AIR box; restored to AIR");
            if (Arrays.stream(scenarios).allMatch(HandLightFixture::isHandScene))
                metadata.put("terrain_fixture", "Temporary sealed carried-light room (smooth_stone floor, spruce_planks ceiling, white_concrete receiver wall, stone_bricks walls and optional 1x1 stone_bricks pillar) in the exact reserved AIR box; restored to AIR");
        }
        if (Arrays.stream(scenarios).anyMatch(HandLightFixture::isHandScene)) {
            metadata.put("hand_light_fixture", map("world", map("name", OcclusionFixture.WORLD_NAME, "world_id", OcclusionFixture.WORLD_ID, "seed", LocalLightFixture.SEED),
                "scenes", Arrays.stream(scenarios).filter(HandLightFixture::isHandScene).toList(),
                "driver", "identified sole local player switched to creative first person for each lamp-hand scene (spectators have no rendered hand); real minecraft:torch/minecraft:soul_torch stacks equipped by integrated-server `item replace` into the selected hotbar slot and the off-hand slot",
                "guards", "exact AqualumenNaturalV2 folder + UUID + seed308060; whole 41-slot driver inventory must be empty before any change; only single fixture lamp stacks are ever cleared; per-scene journal of game mode, selected slot, recipe ids and advancement criteria",
                "restore", "per scene: clear lamp stacks, take newly unlocked recipes, revoke newly obtained criteria, restore journaled game mode; at finish: delayed server recheck against the run baseline and client observation of empty hands",
                "validation", "pre-sample settle (client stacks, HeldItemRenderer stacks and raised equip progress, creative, first person); per-frame client stack check with " + HandLightFixture.SWAP_GRACE_SECONDS + " s swap grace; 25 Hz pose/item trace; capture-time settled final equipment",
                "pre_run_game_mode", handPreRunGameMode,
                "visual_validation_limits", "Sequential shots: exposure/animation are not pixel-locked. The sealed room has vanilla block/sky light 0, so lit-vs-empty pairs isolate the shader's carried light. Hand light anchors and receiver ROIs model the release shader's first-person anchor (+-0.32, -0.30, -0.43 view) and its three finite-emitter taps; they are CPU geometry, not rendered-light measurements, and assume FOV 70 at 2560x1440 (re-evaluated at the actual capture pose). The walk is tick-stepped server translation (20 Hz). Swap latencies are frame-granular client observations."));
        }
        if (Arrays.stream(scenarios).anyMatch(scene -> UnderwaterScene.parse(scene) != null))
            metadata.put("underwater_up_plans", Arrays.stream(scenarios).map(UnderwaterScene::parse).filter(Objects::nonNull).map(Recorder::underwaterMetadata).toList());
        Path irisConfig = game.resolve("config/iris.properties");
        metadata.put("iris_configuration", Files.readString(irisConfig));
        Path packOptions = game.resolve("shaderpacks").resolve(config.getProperty("expected_pack") + ".txt");
        metadata.put("pack_options", Files.exists(packOptions) ? Files.readString(packOptions) : "Defaults (no installed pack options file)");
        atomic(runDir.resolve("run.json"), json(metadata) + "\n");
    }
    private static float expectedYaw(long now) {
        String scene = scenarios[stage];
        LocalLightFixture.Plan lamp = LocalLightFixture.parse(scene);
        if (lamp != null) return LocalLightFixture.expectedYaw(lamp, state.equals("sampling") ? (now - sampleStart) * 1e-9 : 0);
        OcclusionFixture.Plan fixture = OcclusionFixture.parse(scene);
        if (fixture != null) return fixture.yaw();
        if (scene.equals("moving-view") || scene.equals("underwater-up-moving") || scene.equals("underwater-shore-moving")) return site().yaw + (state.equals("sampling") ? (float)((now - sampleStart) * 1e-9 * 12.0) : 0);
        if (scene.equals("boat-contact") || scene.equals("chunk-traversal") || scene.equals("glass-layers")) return 0;
        return scene.equals("ocean-dusk") ? 90 : site().yaw;
    }
    private static float expectedPitch() {
        LocalLightFixture.Plan lamp = LocalLightFixture.parse(scenarios[stage]);
        if (lamp != null) return lamp.pitch();
        OcclusionFixture.Plan fixture = OcclusionFixture.parse(scenarios[stage]);
        return fixture != null ? fixture.pitch() : scenarios[stage].equals("chunk-traversal") || scenarios[stage].equals("boat-contact") ? 10 : site().pitch;
    }
    public static void beforeWorldRender() {
        if (handWorldPass) afterWorldRender(); // never leave the lifted flag behind an aborted pass
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
            LocalLightFixture.Plan plan = LocalLightFixture.parse(scenarios[stage]);
            if (plan != null && plan.hand() != null && hudChanged) {
                // F1 hides the first-person hand (vanilla renderHand and Iris HandRenderer both test hudHidden). Lift it
                // for the world pass only; HUD, toasts and chat still render hidden exactly as in the other shots.
                if (hudField == null) hudField = field(options, "field_1842");
                hudField.setBoolean(options, false); handWorldPass = true;
            }
        } catch (Throwable error) { asyncError = error; }
    }
    /** GameRenderer.renderWorld TAIL: restore the F1 state lifted for the carried-light world pass. */
    public static void afterWorldRender() {
        if (!handWorldPass) return;
        handWorldPass = false;
        try { hudField.setBoolean(options, true); } catch (Throwable error) { asyncError = error; }
    }
    /** No block-selection outline while the world pass runs with the HUD flag lifted (creative reach covers the room). */
    public static boolean suppressBlockOutline() { return handWorldPass; }
    private static void motion(Object mc, long now) throws Exception {
        String scene = scenarios[stage];
        LocalLightFixture.Plan walk = LocalLightFixture.parse(scene);
        if (walk != null && walk.hand() != null && walk.hand().walking()) {
            double elapsed = (now - sampleStart) * 1e-9;
            // 20 Hz tick-stepped driver; keep re-sending the held end pose for 0.5 s, then stop.
            if (now - motionAt < 50_000_000L || elapsed > HandLightFixture.ROUTE_SECONDS + .5) return;
            motionAt = now;
            double x = HandLightFixture.routeEyeX(walk.hand(), elapsed);
            local(() -> { localScope(); command(String.format(Locale.ROOT,
                "execute in minecraft:overworld run tp %s %.4f %.4f %.4f %.1f %.1f", playerTarget, x, walk.playerY(), walk.eyeZ(), walk.yaw(), walk.pitch())); })
                .exceptionally(error -> { asyncError = error; return null; });
            return;
        }
        if (walk != null && walk.walking()) {
            double elapsed = (now - sampleStart) * 1e-9;
            // 20 Hz like ground-camera-motion; stop re-sending once the end pose has been held for 0.5 s.
            if (now - motionAt < 50_000_000L || elapsed > LocalLightFixture.WALK_SECONDS + .5) return;
            motionAt = now;
            double x = LocalLightFixture.walkEyeX(walk, elapsed);
            local(() -> { localScope(); command(String.format(Locale.ROOT,
                "execute in minecraft:overworld run tp %s %.4f %.4f %.4f %.1f %.1f", playerTarget, x, walk.playerY(), LocalLightFixture.EYE_Z, walk.yaw(), walk.pitch())); })
                .exceptionally(error -> { asyncError = error; return null; });
            return;
        }
        if (scene.equals("ground-camera-motion")) {
            if (now-motionAt < 50_000_000L) return;
            motionAt = now;
            double x = 133.6 + .8 * Math.min(1, (now-sampleStart)*1e-9/(sampleSeconds-.5));
            local(() -> { fixtureScope(); command(String.format(Locale.ROOT,
                "execute in minecraft:overworld run tp %s %.4f 66 335 0 30",playerTarget,x)); })
                .exceptionally(error -> { asyncError=error; return null; });
            return;
        }
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
    /** 25 Hz route evidence during sampling of the walk scene; also the live tracking/collision-free guard. */
    private static void walkLog(Object mc, long now, LocalLightFixture.Plan plan) throws Exception {
        if (now - walkLogAt < 40_000_000L) return;
        walkLogAt = now;
        double elapsed = (now - sampleStart) * 1e-9, expected = LocalLightFixture.walkEyeX(plan, elapsed);
        Object player = value(mc, "field_1724");
        double[] body = {(double)call(player, "method_23317"), (double)call(player, "method_23318"), (double)call(player, "method_23321")};
        Object position = call(call(value(mc, "field_1773"), "method_19418"), "method_19326");
        double[] camera = {(double)value(position, "field_1352"), (double)value(position, "field_1351"), (double)value(position, "field_1350")};
        if (!LocalLightFixture.walkTracks(expected, body, camera))
            throw new IllegalStateException(String.format(Locale.ROOT, "Walk route left its analytical pose at %.3f s: expected x %.4f, player %s, camera %s",
                elapsed, expected, Arrays.toString(body), Arrays.toString(camera)));
        if (walkFov == null) {
            try { walkFov = option("method_41808"); } catch (Exception error) { walkFov = "Unavailable: " + error.getClass().getSimpleName(); }
        }
        if (walkRoute.isEmpty()) walkRoute.append("elapsed_ns,expected_eye_x,player_x,player_y,player_z,camera_x,camera_y,camera_z,camera_cluster_x,anchor_receiver_back_wall_u,anchor_receiver_back_wall_v\n");
        String u = "", v = "";
        if (walkFov instanceof Integer degrees) {
            List<Integer> frame = size(mc, true);
            List<Double> pixel = LocalLightFixture.project(LocalLightFixture.samples().get("receiver-back-wall"),
                List.of(camera[0], camera[1], camera[2]), plan.yaw(), plan.pitch(), degrees, frame.get(0), frame.get(1));
            if (pixel != null) { u = String.format(Locale.ROOT, "%.2f", pixel.get(0)); v = String.format(Locale.ROOT, "%.2f", pixel.get(1)); }
        }
        walkRoute.append(String.format(Locale.ROOT, "%d,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%d,%s,%s%n", now - sampleStart, expected,
            body[0], body[1], body[2], camera[0], camera[1], camera[2], LocalLightFixture.clusterX(camera[0]), u, v));
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
    /** Capture-time carried-light proof: settled final real stacks, Iris item-light inputs, trace and swap evidence. */
    private static Map<String, Object> handCapture(Object mc, LocalLightFixture.Plan plan, String name) throws Exception {
        HandOwnership owned = ownedHand;
        if (owned == null || owned.plan() != plan) throw new IllegalStateException("Carried-light ownership changed before capture");
        HeldState state = held(mc);
        HandLightFixture.Equip expected = plan.hand().last();
        if (!state.settled(expected, owned.selectedSlot()))
            throw new IllegalStateException("Carried-light capture requires settled " + expected.describe() + ": " + state.evidence());
        List<Map<String, Object>> swaps = handSwapEvidence(plan);
        for (Map<String, Object> swap : swaps)
            if ((long)swap.get("client_observed_ns") < 0 || (long)swap.get("renderer_settled_ns") < 0 || (long)swap.get("server_applied_ns") < 0)
                throw new IllegalStateException("Carried-light swap was not applied, observed and settled: " + swap);
        if (handTrace.length() <= HandLightFixture.TRACE_HEADER.length()) throw new IllegalStateException("Carried-light trace produced no rows");
        atomic(runDir.resolve(name + "-hand-trace.csv"), handTrace.toString());
        atomic(runDir.resolve(name + "-hand-swaps.csv"), HandLightFixture.swapCsv(swaps));
        return map("hand_light", map("expected_final_equipment", map("main", expected.main(), "off", expected.off()),
            "actual_client_hands_at_capture", state.evidence(), "settled_at_capture", true,
            "iris_item_light_main", irisItemLight(mc, HandLightFixture.MAIN_SLOT), "iris_item_light_off", irisItemLight(mc, HandLightFixture.OFF_SLOT),
            "iris_uniform_sources", "heldItemId/heldBlockLightValue from the client main-hand stack, heldItemId2/heldBlockLightValue2 from the off-hand stack (Iris IdMapUniforms; item ids via the pack's item.properties)",
            "journaled_restore_game_mode", owned.gameMode(), "selected_hotbar_slot", owned.selectedSlot(),
            "swaps", swaps, "swap_grace_seconds", HandLightFixture.SWAP_GRACE_SECONDS,
            "trace_file", name + "-hand-trace.csv", "trace_rows", handTrace.chars().filter(c -> c == '\n').count() - 1,
            "swap_file", name + "-hand-swaps.csv",
            "trace_join", "elapsed_ns since sample start; joins native-motion frames.csv and full-frame ticks.csv",
            "hud", "F1 state lifted only inside GameRenderer.renderWorld so vanilla/Iris draw the hand; HUD/toasts/chat stay hidden; block outline suppressed"));
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
        row.putAll(map("scenario", name, "run_id", runId, "workload", LocalLightFixture.parse(name) != null ? "local-light-test" : OcclusionFixture.parse(name) != null ? name.startsWith("air-") ? "air-sun-shadow-test" : "opaque-occlusion-test" : name.equals("chunk-traversal") ? "chunk-traversal" : name.equals("boat-contact") ? "scripted-boat-contact" : "warmed-view",
            "frames", timings.size(), "mean_fps", 1e9 * timings.size() / total, "one_percent_low_fps", 1e9 * slowCount / slowTotal,
            "p99_ms", sorted.get(Math.min(sorted.size() - 1, (int)Math.ceil(sorted.size() * .99) - 1)) * 1e-6, "max_ms", max,
            "min_instantaneous_fps", 1000.0 / max, "frames_over_16_667_ms", timings.stream().filter(timing -> timing * 1e-6 > BUDGET).count(),
            "warmup_seconds", warmupSeconds, "sample_seconds_requested", sampleSeconds, "sample_seconds_actual", (now - sampleStart) * 1e-9,
            "recorded_seconds", total * 1e-9, "site", map("x", site.x, "y", cameraY(), "z", site.z, "biome", site.biome, "water_depth_blocks", site.depth),
            "window_focused", optionalCall(mc, "method_1569"), "physics_active_seen", physicsActive, "maximum_contacts", maximumContacts, "maximum_force", maximumForce,
            "contact_driver", name.equals("boat-contact") ? "server-command boat translation 6m/s at20Hz; actual mounted player and entity" : "none"));
        Object cameraPlayer = value(mc, "field_1724");
        float actualYaw = (float)call(cameraPlayer, "method_36454"), actualPitch = (float)call(cameraPlayer, "method_36455");
        if (Math.abs(actualPitch - expectedPitch()) > .05 || (!name.equals("moving-view") && !name.equals("underwater-up-moving") && !name.equals("underwater-shore-moving") && !name.equals("lamp-night-moving") && Math.abs(actualYaw - expectedYaw(now)) > .05))
            throw new IllegalStateException("Camera orientation does not match requested scene");
        Object camera = call(value(mc, "field_1773"), "method_19418");
        if (call(camera, "method_19331") != cameraPlayer) throw new IllegalStateException("Rendered Camera focuses another entity");
        float renderedYaw = (float)call(camera, "method_19330"), renderedPitch = (float)call(camera, "method_19329");
        if (Math.abs(renderedYaw - actualYaw) > .05 || Math.abs(renderedPitch - actualPitch) > .05)
            throw new IllegalStateException("Rendered Camera orientation disagrees with locked local player");
        row.put("actual_player_rotation", List.of(actualYaw, actualPitch));
        row.put("native_motion_capture_active", nativeMotion != null);
        if(fullFrameClip) row.put("full_frame_capture_active",groundClip!=null);
        if (recordGroundClip) row.put("ground_clip_capture_active", groundClip != null);
        row.put("actual_camera_rotation", List.of(renderedYaw, renderedPitch));
        row.put("expected_camera_rotation", List.of(expectedYaw(now), expectedPitch()));
        double px = (double)call(cameraPlayer, "method_23317"), py = (double)call(cameraPlayer, "method_23318"), pz = (double)call(cameraPlayer, "method_23321");
        row.put("actual_player_position", List.of(px, py, pz));
        LocalLightFixture.Plan capturedLamp = LocalLightFixture.parse(name);
        // A walk is held at its route end (sample >= route + 1 s); fixed lamp variants stay at their own eye x.
        double expectedX = name.equals("ground-camera-motion") ? 134.4 : capturedLamp != null ? LocalLightFixture.walkEyeX(capturedLamp, sampleSeconds) : site.x;
        if (!name.equals("boat-contact") && !name.equals("chunk-traversal") && (Math.abs(px - expectedX) > .5 || Math.abs(py - cameraY()) > .5 || Math.abs(pz - (name.equals("glass-layers") ? site.z - 12 : site.z)) > .5))
            throw new IllegalStateException("Player moved away from fixed scene position");
        Object cameraPosition = call(camera, "method_19326");
        row.put("actual_camera_position", List.of(value(cameraPosition, "field_1352"), value(cameraPosition, "field_1351"), value(cameraPosition, "field_1350")));
        OcclusionFixture.Plan fixture = OcclusionFixture.parse(name);
        if (fixture != null) {
            fixtureScope();
            boolean firstPerson = (boolean)call(call(options, "method_31044"), "method_31034");
            Object actualEye = call(cameraPlayer, "method_33571");
            double[] eye = {(double)value(actualEye, "field_1352"), (double)value(actualEye, "field_1351"), (double)value(actualEye, "field_1350")};
            double[] rendered = {(double)value(cameraPosition, "field_1352"), (double)value(cameraPosition, "field_1351"), (double)value(cameraPosition, "field_1350")};
            if (!OcclusionFixture.eyeMatches(firstPerson, eye, rendered))
                throw new IllegalStateException("Opaque fixture requires actual first-person Camera at the identified player's measured eye");
            if (ownedOpaque == null || !ownedOpaque.scene().equals(name)) throw new IllegalStateException("Opaque fixture ownership changed before capture");
            Map<String, Object> fixtureRow = fixtureMetadata(fixture);
            long actualTime = (long)call(value(mc, "field_1687"), "method_8532");
            long serverTime = (long)call(serverWorld, "method_8532");
            boolean movingSun = name.equals("ground-sun-motion");
            if (movingSun ? actualTime <= fixture.timeOfDay() || serverTime <= fixture.timeOfDay() ||
                    Math.abs(actualTime-serverTime)>25 || serverTime-fixture.timeOfDay() > (sampleSeconds+3)*20 :
                    actualTime != fixture.timeOfDay() || serverTime != fixture.timeOfDay())
                throw new IllegalStateException("Fixture world time differs from the requested frozen sun control");
            fixtureRow.put("actual_world_time", actualTime); fixtureRow.put("actual_server_world_time", serverTime);
            fixtureRow.put("camera_first_person", firstPerson); fixtureRow.put("camera_eye_match", true);
            fixtureRow.put("actual_eye_position", List.of(eye[0], eye[1], eye[2]));
            fixtureRow.put("actual_camera_position", List.of(rendered[0], rendered[1], rendered[2]));
            row.put("opaque_fixture", fixtureRow); row.put("actual_eye_position", List.of(eye[0], eye[1], eye[2]));
            row.put("camera_first_person", firstPerson); row.put("camera_eye_match", true);
            // Check the actual target/wall state on the integrated server before
            // sampling begins; capture itself deliberately performs no mutation.
        }
        LocalLightFixture.Plan lamp = LocalLightFixture.parse(name);
        if (lamp != null) {
            localScope();
            boolean firstPerson = (boolean)call(call(options, "method_31044"), "method_31034");
            Object actualEye = call(cameraPlayer, "method_33571");
            double[] eye = {(double)value(actualEye, "field_1352"), (double)value(actualEye, "field_1351"), (double)value(actualEye, "field_1350")};
            double[] rendered = {(double)value(cameraPosition, "field_1352"), (double)value(cameraPosition, "field_1351"), (double)value(cameraPosition, "field_1350")};
            double requestedEyeX = LocalLightFixture.walkEyeX(lamp, sampleSeconds);
            List<Double> requestedEye = List.of(requestedEyeX, lamp.eyeY(), lamp.eyeZ());
            if (!LocalLightFixture.eyeMatches(lamp, requestedEyeX, firstPerson, new double[]{px, py, pz}, eye, rendered))
                throw new IllegalStateException("Local-light fixture requires the shared first-person eye at the requested position");
            if (ownedLocal == null || !ownedLocal.scene().equals(name)) throw new IllegalStateException("Local-light fixture ownership changed before capture");
            Map<String, Object> validation = localValidation;
            if (validation == null || !Boolean.TRUE.equals(validation.get("passed"))) throw new IllegalStateException("Local-light block validation missing before capture");
            long clientTime = (long)call(value(mc, "field_1687"), "method_8532"), serverTime = (long)call(serverWorld, "method_8532");
            if (clientTime != lamp.timeOfDay() || serverTime != lamp.timeOfDay()) throw new IllegalStateException("Local-light frozen world time changed");
            Map<String, Object> measured = lamp.hand() != null ? handFixtureMetadata(lamp) : localFixtureMetadata(lamp);
            Object fov;
            try { fov = option("method_41808"); } catch (Exception error) { fov = "Unavailable: " + error.getClass().getSimpleName(); }
            Map<String, Object> pixels = new LinkedHashMap<>();
            if (fov instanceof Integer degrees) {
                List<Integer> frame = size(mc, true);
                LocalLightFixture.samples(lamp).forEach((sample, point) -> pixels.put(sample, LocalLightFixture.project(point, requestedEye, renderedYaw, renderedPitch, degrees, frame.get(0), frame.get(1))));
                // The mirror point is derived for the original eye; only meaningful (and only recorded) at that eye.
                if (lamp.hand() == null && requestedEyeX == LocalLightFixture.EYE_X)
                    pixels.put("lantern-reflection", LocalLightFixture.project(LocalLightFixture.lanternReflectionPoint(), renderedYaw, renderedPitch, degrees, frame.get(0), frame.get(1)));
                if (lamp.walking()) {
                    Map<String, Object> keyframes = new LinkedHashMap<>();
                    for (double seconds : new double[]{0, LocalLightFixture.walkBoundarySeconds(), LocalLightFixture.WALK_SECONDS}) {
                        List<Double> keyEye = List.of(LocalLightFixture.walkEyeX(lamp, seconds), LocalLightFixture.EYE_Y, LocalLightFixture.EYE_Z);
                        Map<String, Object> keyPixels = new LinkedHashMap<>();
                        LocalLightFixture.samples().forEach((sample, point) -> keyPixels.put(sample, LocalLightFixture.project(point, keyEye, lamp.yaw(), lamp.pitch(), degrees, frame.get(0), frame.get(1))));
                        keyframes.put(String.format(Locale.ROOT, "t=%.3fs", seconds), map("eye", keyEye, "cluster_x", LocalLightFixture.clusterX(keyEye.get(0)), "pixels", keyPixels));
                    }
                    measured.put("walk_route_keyframe_pixels", map("method", "Pinhole projection at analytical route poses with requested yaw/pitch, options FOV and framebuffer size", "keyframes", keyframes));
                }
            }
            if (lamp.walking()) {
                if (walkRoute.isEmpty()) throw new IllegalStateException("Walk route produced no pose rows");
                atomic(runDir.resolve(name + "-walk-route.csv"), walkRoute.toString());
                measured.put("walk_route_rows", walkRoute.chars().filter(c -> c == '\n').count() - 1);
                measured.put("walk_route_file", name + "-walk-route.csv");
            }
            measured.put("render_projection", localCameraProjection(lamp, List.of(rendered[0], rendered[1], rendered[2]), size(mc, true)));
            if (lamp.hand() != null) {
                // Fixed-pixel ROIs must still mean what they claim at the pose actually rendered (eye, rotation, FOV, frame).
                List<Integer> frame = size(mc, true);
                Map<String, String> rois = fov instanceof Integer degrees
                    ? HandLightFixture.roisAtPose(lamp.hand(), rendered, renderedYaw, renderedPitch, degrees, frame.get(0), frame.get(1))
                    : Map.of("all", "FOV unavailable: " + fov);
                measured.put("receiver_rois_at_actual_pose", map("method", "Release three-tap carried-light visibility and camera visibility of every pixel of each fixed 9x9 ROI at the actual rendered eye, yaw/pitch, options FOV and framebuffer",
                    "frame", frame, "results", rois));
                boolean fullFrame = frame.equals(List.of(HandLightFixture.FRAME_WIDTH, HandLightFixture.FRAME_HEIGHT));
                if (fullFrame && rois.values().stream().anyMatch(result -> !result.equals("ok")))
                    throw new IllegalStateException("Carried-light receiver ROI does not hold at the rendered pose: " + rois);
                measured.putAll(handCapture(mc, lamp, name));
            }
            measured.putAll(map("camera_first_person", firstPerson, "camera_eye_match", true,
                "actual_player_position", List.of(px, py, pz), "actual_eye_position", List.of(eye[0], eye[1], eye[2]),
                "actual_camera_position", List.of(rendered[0], rendered[1], rendered[2]),
                "actual_camera_rotation", List.of(renderedYaw, renderedPitch),
                "actual_world_time", clientTime, "actual_server_world_time", serverTime,
                "camera_submersion_type", ((Enum<?>)call(camera, "method_19334")).name(),
                "pre_sample_block_validation", validation, "options_fov_degrees", fov,
                "sample_pixels_pinhole_projection", map("method", "Pinhole projection of recorded world samples with actual rendered yaw/pitch, options FOV and framebuffer size; top-left origin; ignores any shader-side jitter", "pixels", pixels)));
            row.put("local_light_fixture", measured); row.put("actual_eye_position", List.of(eye[0], eye[1], eye[2]));
            row.put("camera_first_person", firstPerson); row.put("camera_eye_match", true);
        }
        UnderwaterScene.Plan underwater = UnderwaterScene.parse(name);
        if (underwater != null) {
            boolean firstPerson = (boolean)call(call(options, "method_31044"), "method_31034");
            Object actualEye = call(cameraPlayer, "method_33571");
            double[] eye = {(double)value(actualEye,"field_1352"), (double)value(actualEye,"field_1351"), (double)value(actualEye,"field_1350")};
            double[] rendered = {(double)value(cameraPosition,"field_1352"), (double)value(cameraPosition,"field_1351"), (double)value(cameraPosition,"field_1350")};
            // method_5799 is body contact only; method_5869 is the verified
            // Entity head-underwater predicate. Also check the rendered Camera.
            boolean touching = (boolean)call(cameraPlayer,"method_5799");
            boolean submerged = (boolean)call(cameraPlayer,"method_5869");
            String medium = ((Enum<?>)call(camera,"method_19334")).name();
            if (!UnderwaterScene.matches(underwater,firstPerson,submerged,medium,new double[]{px,py,pz},eye,rendered))
                throw new IllegalStateException("Upward underwater scene requires the requested first-person eye depth, submerged player and actual WATER camera");
            long clientTime = (long)call(value(mc,"field_1687"),"method_8532"), serverTime = (long)call(serverWorld,"method_8532");
            if (clientTime != 6000 || serverTime != 6000) throw new IllegalStateException("Upward underwater frozen daylight changed");
            Map<String,Object> measured = underwaterMetadata(underwater);
            measured.putAll(map("camera_first_person",firstPerson,"camera_eye_match",true,"player_touching_water",touching,
                "player_submerged_in_water",submerged,"camera_submersion_type",medium,"actual_world_time",clientTime,"actual_server_world_time",serverTime,
                "actual_eye_depth",underwaterSurfaceY-eye[1],"actual_eye_position",List.of(eye[0],eye[1],eye[2]),
                "actual_camera_position",List.of(rendered[0],rendered[1],rendered[2])));
            row.put("underwater_up",measured); row.put("actual_eye_position",List.of(eye[0],eye[1],eye[2]));
            row.put("camera_first_person",firstPerson); row.put("camera_eye_match",true);
        }
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
        ScreenshotCompletion completion = new ScreenshotCompletion();
        screenshotCompletion = completion;
        // Minecraft1.21.1's worker invokes screenshot.success only after the
        // NativeImage file writer returns; screenshot.failure is a terminal error.
        // Capture this gate, not the mutable field, so a late old callback cannot
        // authorize copying a later scene's still-incomplete file.
        screenshot.invoke(null, game.toFile(), screenshotName, call(mc, "method_1522"), (Consumer<Object>)message -> {
            try { completion.callback((String)call(call(message, "method_10851"), "method_11022")); }
            catch (Exception error) { completion.callback("unrecognized-callback: " + error.getClass().getSimpleName()); }
        });
        screenshotStarted = System.nanoTime(); state = "screenshot"; previous = 0;
        status(String.format(Locale.ROOT, "%s %.1f FPS; P99 %.3f ms; worst %.3f ms; awaiting screenshot", name, row.get("mean_fps"), row.get("p99_ms"), max));
    }
    private static void abort(Object mc, String reason) throws Exception {
        if (state.equals("aborting-fixtures")) return;
        if (groundClip != null) { groundClip.close(); groundClip = null; }
        state = "aborted"; previous = 0; abortReason = reason;
        if (runDir != null) atomic(runDir.resolve("aborted.json"), json(map("run_id", runId, "status", "aborted", "reason", reason,
            "fixture_cleanup_complete", !fixtureRun && ownedOpaque == null && ownedLocal == null && ownedHand == null, "utc", Instant.now().toString())) + "\n");
        restoreHud(mc); status(reason);
        asyncError = null;
        if (fixtureRun && runDir != null) {
            // The integrated-server queue orders this after any partially completed
            // placement action. The same scope is rechecked before touching cells.
            // A guard failure preserves the journal and never cleans another save.
            guard(mc, false);
            pending = local(() -> {
                if (Arrays.asList(scenarios).contains("ground-sun-motion")) {
                    fixtureScope(); command("gamerule doDaylightCycle false");
                }
                // Attempt both owned fixtures; any failure keeps its journal and is reported.
                Exception failure = null;
                try { cleanHand(); } catch (Exception error) { failure = error; }
                try { cleanOpaque(); } catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
                try { cleanLocal(); } catch (Exception error) { if (failure == null) failure = error; else failure.addSuppressed(error); }
                if (failure != null) throw failure;
            }); state = "aborting-fixtures";
            status(reason + "; waiting for scoped fixture cleanup");
        }
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
            if (Set.of("preparing", "preparing-scene", "warmup", "sampling", "screenshot", "finishing").contains(state)) abort(mc, "Quit by local control request");
            if (state.equals("aborting-fixtures")) { quitAfterCleanup = true; return; }
            if (fixturesPending())
                throw new IllegalStateException("Cannot hand off while a fixture cleanup journal is unresolved");
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
            if (state.equals("aborting-fixtures")) {
                if (!pending.isDone()) return;
                try {
                    pending.join();
                    boolean clean = !fixturesPending();
                    if (!clean) throw new IllegalStateException("Fixture ownership/journal still present after abort cleanup");
                    atomic(runDir.resolve("abort-cleanup.json"), json(map("fixture_cleanup_complete", true, "reason", abortReason, "utc", Instant.now().toString())) + "\n");
                    state = "aborted"; status(abortReason + "; fixture cleanup complete, failed run retained");
                    if (quitAfterCleanup) { state = "quitting"; status("Verified fixture cleanup before requested client stop"); call(mc, "method_1592"); }
                } catch (Throwable cleanupError) {
                    state = "aborted"; quitAfterCleanup = false;
                    atomic(runDir.resolve("abort-cleanup.json"), json(map("fixture_cleanup_complete", false, "reason", cleanupError.toString(), "utc", Instant.now().toString())) + "\n");
                    status(abortReason + "; cleanup incomplete, journal retained: " + cleanupError);
                }
                return;
            }
            if (state.equals("preparing") || state.equals("preparing-scene") || state.equals("finishing")) {
                if (!pending.isDone()) return;
                pending.join();
                if (state.equals("preparing")) { guard(mc, true); runMetadata(mc); next(mc); return; }
                if (state.equals("finishing")) {
                    // The server teleport future completes before the client respawn
                    // packet replaces its world, player and camera entity. Never
                    // relax the guard; wait for that client-side transition first.
                    Object player = value(mc, "field_1724");
                    if (!actualDimension(mc).equals("minecraft:overworld") || player == null || call(mc, "method_1560") != player) {
                        if (now - start > 60_000_000_000L) throw new IllegalStateException("Client did not finish returning to the local Overworld camera");
                        return;
                    }
                    if (localSettle == 1) {
                        // Let several server/fluid ticks pass, then recheck the whole reservation.
                        if (now - localCleanedAt < 1_500_000_000L) return;
                        localSettle = 2; pending = local(() -> { settleLocal(); settleHandServer(); }); return;
                    }
                    if (handSettle == 1) {
                        // The client copy of the restored stacks/game mode arrives by packet; wait for it, bounded.
                        HeldState restored = held(mc);
                        if (handSettleStart == 0) handSettleStart = now;
                        if (!restored.main().equals(HandLightFixture.EMPTY) || !restored.off().equals(HandLightFixture.EMPTY) ||
                            !restored.gameMode().equals(handRestoredGameMode)) {
                            if (now - handSettleStart > 10_000_000_000L) throw new IllegalStateException("Client did not observe the restored empty hands/game mode");
                            return;
                        }
                        Map<String, Object> evidence = restored.evidence();
                        evidence.putAll(map("expected_game_mode", handRestoredGameMode, "seconds_waited", (now - handSettleStart) * 1e-9, "utc", Instant.now().toString()));
                        atomic(runDir.resolve("hand-light-settled-client.json"), json(evidence) + "\n");
                        handSettle = 0;
                    }
                    guard(mc, true); restoreHud(mc);
                    if (fixturesPending())
                        throw new IllegalStateException("Fixture cleanup not complete at run finish");
                    atomic(runDir.resolve("complete.json"), json(map("run_id", runId, "status", "complete", "scenarios", Arrays.asList(scenarios),
                        "fixture_cleanup_complete", true, "utc", Instant.now().toString())) + "\n");
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
                if (nativeMotion != null && !nativeMotion.poll(now)) return;
                if (!screenshotCompletion.ready(now - screenshotStarted)) return;
                if (!Files.exists(screenshotPath) || Files.size(screenshotPath) == 0)
                    throw new IllegalStateException("Successful screenshot callback did not leave a nonempty file");
                Files.copy(screenshotPath, runDir.resolve(scenarios[stage] + ".png")); next(mc);
                return;
            }
            if (!(state.equals("warmup") || state.equals("sampling"))) return;
            if (value(mc, "field_1755") != null) throw new IllegalStateException("A UI screen interrupted the scene");
            if (!actualDimension(mc).equals(dimension(scenarios[stage]))) throw new IllegalStateException("Player dimension changed during scene");
            if (now - validateAt > 1_000_000_000L) { validateAt = now; guard(mc, false); }
            if (state.equals("warmup")) {
                if ((now - start) * 1e-9 >= warmupSeconds) {
                    LocalLightFixture.Plan lamp = LocalLightFixture.parse(scenarios[stage]);
                    if (lamp != null && localValidation == null) {
                        // Validate exact placed states and the surrounding AIR on the server thread before sampling.
                        if (localValidationTask == null) { localValidationTask = local(() -> localValidation = validateLocal(lamp)); return; }
                        if (!localValidationTask.isDone()) return;
                        localValidationTask.join();
                        if (localValidation == null) throw new IllegalStateException("Local-light validation produced no evidence");
                    }
                    if (lamp != null && lamp.hand() != null) {
                        // Settle before sampling: real client stacks, raised HeldItemRenderer hands, creative first person.
                        HandOwnership owned = ownedHand;
                        HeldState state = held(mc);
                        if (owned == null || owned.plan() != lamp || !state.settled(lamp.hand().initial(), owned.selectedSlot())) {
                            if ((now - start) * 1e-9 > warmupSeconds + 10)
                                throw new IllegalStateException("Carried-light driver did not settle before sampling: " + state.evidence());
                            return;
                        }
                        startHandSampling(lamp);
                    }
                    state = "sampling"; status("Measuring " + scenarios[stage]); sampleStart = System.nanoTime(); previous = 0; motionAt = 0;
                    if(fullFrameClip) groundClip=new GroundShadowClip(runDir.resolve("full-frame-"+scenarios[stage]),0,0,960,540);
                    if (recordGroundClip && (scenarios[stage].equals("ground-sun-motion") || scenarios[stage].equals("ground-camera-motion")))
                        groundClip = new GroundShadowClip(runDir.resolve("ground-clip"));
                    if (scenarios[stage].equals("ground-sun-motion")) {
                        local(() -> { fixtureScope(); command("gamerule doDaylightCycle true"); })
                            .exceptionally(error -> { asyncError = error; return null; });
                    }
                    if (captureMotion && (!scenarios[stage].startsWith("ground-") || scenarios[stage].equals("ground-sun-motion"))) {
                        String scene = scenarios[stage];
                        nativeMotion = new NativeMotionCapture(runDir.resolve("native-motion-" + scene), (destination, completion) -> {
                            String filename = "aqualumen-native-" + runId + "-" + scene + "-" + destination.getFileName();
                            Path sourceImage = game.resolve("screenshots").resolve(filename);
                            if (Files.exists(sourceImage) || Files.isSymbolicLink(sourceImage)) throw new IllegalStateException("Native motion screenshot already exists");
                            Method screenshot = Class.forName("net.minecraft.class_318").getMethod("method_22690", java.io.File.class, String.class, Class.forName("net.minecraft.class_276"), Consumer.class);
                            screenshot.invoke(null, game.toFile(), filename, call(mc, "method_1522"), (Consumer<Object>)message -> {
                                try {
                                    String key = (String)call(call(message, "method_10851"), "method_11022");
                                    if (key.equals("screenshot.success")) Files.move(sourceImage, destination);
                                    completion.callback(key);
                                } catch (Exception error) { completion.callback("native-motion-failure: " + error.getClass().getSimpleName()); }
                            });
                        });
                    }
                }
                return;
            }
            if (previous != 0) timings.add(now - previous);
            previous = now;
            if (groundClip != null && now - sampleStart < sampleSeconds * 1e9) {
                groundClip.frame(now-sampleStart, (long)call(value(mc,"field_1687"),"method_8532"),
                    (int)call(call(mc,"method_1522"),"method_30277"));
            }
            motion(mc, now);
            LocalLightFixture.Plan walkPlan = LocalLightFixture.parse(scenarios[stage]);
            if (walkPlan != null && walkPlan.walking() && now - sampleStart < sampleSeconds * 1e9) walkLog(mc, now, walkPlan);
            if (walkPlan != null && walkPlan.hand() != null && now - sampleStart < sampleSeconds * 1e9) handFrame(mc, now, walkPlan);
            physics(now, false);
            if (nativeMotion != null && (now - sampleStart) * 1e-9 < sampleSeconds) {
                guard(mc, false);
                Object camera = call(value(mc, "field_1773"), "method_19418");
                if (call(camera, "method_19331") != value(mc, "field_1724")) throw new IllegalStateException("Native motion camera follows another entity");
                boolean requested = nativeMotion.request(now, now - sampleStart, (float)call(camera, "method_19330"), (float)call(camera, "method_19329"));
                if (requested && scenarios[stage].equals("ground-sun-motion")) {
                    Files.writeString(runDir.resolve("ground-sun-ticks.csv"), (now-sampleStart) + "," +
                        call(value(mc,"field_1687"),"method_8532") + "\n", StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                }
                if (requested && walkPlan != null && walkPlan.walking()) {
                    // Exact rendered Camera position of each native frame request, keyed by frames.csv elapsed_ns.
                    Object position = call(camera, "method_19326");
                    Path poses = runDir.resolve(scenarios[stage] + "-native-frame-poses.csv");
                    String row = String.format(Locale.ROOT, "%d,%.5f,%.5f,%.5f,%d%n", now - sampleStart, (double)value(position, "field_1352"),
                        (double)value(position, "field_1351"), (double)value(position, "field_1350"), LocalLightFixture.clusterX((double)value(position, "field_1352")));
                    Files.writeString(poses, (Files.exists(poses) ? "" : "elapsed_ns,camera_x,camera_y,camera_z,camera_cluster_x\n") + row,
                        StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                }
            }
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
