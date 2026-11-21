package dev.aqualumen.bench;

import java.util.*;

/** PRIVATE scratch-only natural forest torch comparison site (generated from forest-tools/forest-site.json).
 * Aliases reuse the accepted OcclusionFixture scene keys only inside this private JAR:
 *   ground-noon / ground-evening / ground-low-sun  -> day 9800: off / torch / soul_torch
 *   air-shadow-backlit / air-sunlit-front / air-backlit-open -> night 15500: off / torch / soul_torch (optional)
 * One pose, one reserved exact-AIR torch slot on a natural grass block; nothing else is ever placed.
 * Existing bark/leaves/support blocks are only read and verified, never changed.
 */
final class ForestSite {
    static final String RANGE = "forest-torch";
    static final long SEED = 308060L;
    static final double X = 208.5, Y = 64.0, Z = 355.5, EYE_HEIGHT = 1.62, POSE_TOLERANCE = .05;
    static final float YAW = 12.7f, PITCH = -2.0f;
    static final int TORCH_X = 207, TORCH_Y = 64, TORCH_Z = 359;
    static final int TREE_X = 209, TREE_Y = 64, TREE_Z = 360;
    static final int DAY_TIME = 9800, NIGHT_TIME = 15500;
    static final Map<String, String> VARIANT = Map.of("ground-noon", "off", "ground-evening", "warm", "ground-low-sun", "soul",
        "air-shadow-backlit", "night-off", "air-sunlit-front", "night-warm", "air-backlit-open", "night-soul");
    record Existing(int x, int y, int z, String id, String role, String[] required) {}
    static final List<Existing> EXISTING = List.of(
        new Existing(152, 66, 397, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(152, 66, 398, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(152, 69, 384, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(158, 70, 398, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(180, 72, 420, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(196, 65, 369, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(196, 66, 369, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(197, 65, 370, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(201, 69, 371, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(203, 70, 361, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(203, 70, 365, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(204, 68, 366, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(205, 65, 365, "minecraft:dark_oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(205, 65, 395, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(205, 66, 365, "minecraft:dark_oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(205, 70, 361, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(205, 70, 363, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(206, 65, 365, "minecraft:dark_oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(206, 66, 365, "minecraft:dark_oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(206, 66, 386, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(206, 67, 385, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(206, 70, 361, "minecraft:dark_oak_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(207, 63, 359, "minecraft:grass_block", "torch_support", new String[]{}),
        new Existing(207, 67, 396, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(207, 68, 366, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(207, 68, 367, "minecraft:birch_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(208, 63, 355, "minecraft:grass_block", "camera_support", new String[]{}),
        new Existing(208, 68, 358, "minecraft:birch_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(208, 68, 360, "minecraft:birch_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(209, 63, 360, "minecraft:dirt", "trunk_base_dirt", new String[]{}),
        new Existing(209, 64, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 65, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 66, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 67, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 68, 358, "minecraft:birch_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(209, 68, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 68, 363, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(209, 69, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(209, 70, 360, "minecraft:birch_log", "target_trunk_log", new String[]{"axis=y"}),
        new Existing(210, 68, 359, "minecraft:birch_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(210, 68, 361, "minecraft:oak_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(211, 65, 363, "minecraft:oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(211, 66, 363, "minecraft:oak_log", "distant_trunks", new String[]{"axis=y"}),
        new Existing(211, 68, 361, "minecraft:oak_leaves", "near_foliage", new String[]{"persistent=false"}),
        new Existing(211, 68, 362, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(212, 68, 361, "minecraft:oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(218, 69, 377, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(219, 70, 377, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}),
        new Existing(227, 69, 386, "minecraft:dark_oak_leaves", "distant_foliage", new String[]{"persistent=false"}));

    static boolean alias(String scene) { return scene != null && VARIANT.containsKey(scene); }
    static boolean authorized(String name, String id, long seed) { return OcclusionFixture.authorized(name, id) && seed == SEED; }
    static String variant(String scene) { return VARIANT.get(scene); }
    static boolean night(String scene) { return alias(scene) && variant(scene).startsWith("night-"); }
    static int time(String scene) { return night(scene) ? NIGHT_TIME : DAY_TIME; }
    static String torchBlock(String scene) {
        String v = variant(scene);
        if (v == null) return null;
        return v.endsWith("warm") ? "minecraft:torch" : v.endsWith("soul") ? "minecraft:soul_torch" : null;
    }
    static int camX() { return (int)Math.floor(X); }
    static int camZ() { return (int)Math.floor(Z); }
    static List<Double> eye() { return List.of(X, Y + EYE_HEIGHT, Z); }
    static boolean torchCell(int x, int y, int z) { return x == TORCH_X && y == TORCH_Y && z == TORCH_Z; }

    static OcclusionFixture.Plan plan(String scene) {
        if (!alias(scene)) return null;
        List<OcclusionFixture.Cell> reserved = new ArrayList<>(), placed = new ArrayList<>();
        reserved.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y, TORCH_Z, "minecraft:air"));
        reserved.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y + 1, TORCH_Z, "minecraft:air"));
        for (int dy = 0; dy <= 2; dy++) reserved.add(new OcclusionFixture.Cell(camX(), (int)Y + dy, camZ(), "minecraft:air"));
        String block = torchBlock(scene);
        if (block != null) placed.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y, TORCH_Z, block));
        return new OcclusionFixture.Plan(scene, RANGE, "", false, "", List.of(), List.of(), YAW, PITCH, time(scene),
            List.copyOf(reserved), List.copyOf(placed));
    }
    /** Every required state substring must appear in BlockState#toString, e.g. persistent=false for natural leaves. */
    static boolean matches(Existing e, String actualId, String stateText) {
        if (!e.id().equals(actualId) || stateText == null) return false;
        for (String need : e.required()) if (!stateText.contains(need)) return false;
        return true;
    }
    static boolean poseMatches(double[] player, double[] eye, double[] camera) {
        if (player == null || eye == null || camera == null || player.length != 3 || eye.length != 3 || camera.length != 3) return false;
        double[] want = {X, Y, Z}, wantEye = {X, Y + EYE_HEIGHT, Z};
        for (int i = 0; i < 3; i++) {
            if (!Double.isFinite(player[i]) || !Double.isFinite(eye[i]) || !Double.isFinite(camera[i])) return false;
            if (Math.abs(player[i] - want[i]) > POSE_TOLERANCE || Math.abs(eye[i] - wantEye[i]) > POSE_TOLERANCE || Math.abs(camera[i] - wantEye[i]) > POSE_TOLERANCE) return false;
        }
        return true;
    }
    /** Named world-space samples (1 mm on the air side of the bark face) projected into the captured frame. */
    static Map<String, List<Double>> samples() {
        Map<String, List<Double>> m = new LinkedHashMap<>();
        m.put("torch-flame", List.of(TORCH_X + .5, TORCH_Y + .65, TORCH_Z + .5));
        m.put("torch-base-ground", List.of(TORCH_X + .5, TORCH_Y + .001, TORCH_Z + .5));
        m.put("trunk-bark-low", List.of(TREE_X + .5, TREE_Y + .5, TREE_Z - .001));
        m.put("trunk-bark-mid", List.of(TREE_X + .5, TREE_Y + 1.5, TREE_Z - .001));
        m.put("trunk-bark-high", List.of(TREE_X + .5, TREE_Y + 3.5, TREE_Z - .001));
        m.put("trunk-root-ground", List.of(TREE_X + .5, TREE_Y + .001, TREE_Z - .5));
        return m;
    }
    static Map<String, Object> mapping() {
        Map<String, Object> m = new LinkedHashMap<>();
        for (String scene : List.of("ground-noon", "ground-evening", "ground-low-sun", "air-shadow-backlit", "air-sunlit-front", "air-backlit-open")) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("variant", variant(scene)); item.put("torch_block", torchBlock(scene) == null ? "none" : torchBlock(scene));
            item.put("world_time", time(scene));
            m.put(scene, item);
        }
        return m;
    }
    static Map<String, Object> metadata(OcclusionFixture.Plan plan) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("range", plan.range()); m.put("variant", variant(plan.scene()));
        m.put("torch_block", torchBlock(plan.scene()) == null ? "none" : torchBlock(plan.scene()));
        m.put("torch_cell", List.of(TORCH_X, TORCH_Y, TORCH_Z));
        m.put("requested_player_position", List.of(X, Y, Z));
        m.put("requested_eye_position", eye());
        m.put("requested_camera_rotation", List.of(plan.yaw(), plan.pitch()));
        m.put("requested_world_time", plan.timeOfDay());
        m.put("placed_cells", plan.placements().size()); m.put("reserved_air_cells", plan.reserved().size());
        m.put("existing_verified_cells", EXISTING.size()); m.put("seed", SEED);
        m.put("pose_tolerance_m", POSE_TOLERANCE);
        return m;
    }
    static Map<String, Object> siteMetadata() {
        Map<String, Object> m = new LinkedHashMap<>(metadata(plan("ground-evening")));
        m.remove("variant"); m.remove("torch_block"); m.remove("requested_world_time");
        m.put("scene_key_mapping", mapping());
        m.put("tree_base", List.of(TREE_X, TREE_Y, TREE_Z));
        m.put("existing_cells", EXISTING.stream().map(e -> List.of(e.x(), e.y(), e.z(), e.id(), e.role())).toList());
        m.put("method", "private JAR: accepted OcclusionFixture scene keys are aliased onto one natural forest pose; only the exact-AIR torch slot is ever mutated; bark/leaves/support are read-only verified");
        return m;
    }
}
