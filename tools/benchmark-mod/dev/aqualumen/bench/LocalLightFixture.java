package dev.aqualumen.bench;

import java.util.*;

/** Reviewed, temporary local-light test geometry in reserved clear air of the exact dedicated V2 world.
 *
 * Layout (local dx/dz from ORIGIN, y absolute; camera south of the platform looking north):
 *   dx 0..4    grass with an authored oak log/leaves canopy (genuine sun shade on grass)
 *   dx 5..13   stone; dz 1..6 a roofed two-bay shelter open to the south (camera):
 *              lamp bay dx 6..8, divider plane dx 9 (the variable intervening wall), receiver bay dx 10..12
 *   dz 8..12   sealed two-deep still pool sunk into the platform (water dx 7..11, dz 9..11, y 149..150)
 *              over a submerged white receiver, with an air-side lantern post at its north-west corner.
 * The divider never lies on the camera-to-receiver path; it only lies on the lamp-to-receiver path.
 * Divider variants: stone_bricks (wall/wall-off) or red_stained_glass (glass/glass-off) on the identical 20 cells.
 * lamp-day-canopy: a torch on the grass under the oak canopy, lighting nearby grass and the trunk's camera-facing face.
 * lamp-night-walk*: first-person lateral route (fixed y, z, yaw, pitch) across the world-aligned 8-block boundary x=408.
 * Only exact AIR is ever replaced; every placed cell is journaled and restored to AIR.
 * lamp-hand-*: carried-light scenes (HandLightFixture) use the same reserved box with their own sealed room and pose.
 */
final class LocalLightFixture {
    static final long SEED = 308060L;
    static final int OX = 400, OY = 150, OZ = -420;
    /** Inclusive reservation: every cell must be exact AIR before any placement (scene and camera path). */
    static final List<Integer> BOX = List.of(400, 148, -420, 413, 158, -401);
    static final double EYE_X = 409.5, EYE_Y = 157.0, EYE_Z = -402.0, EYE_HEIGHT = 1.62;
    static final float YAW = 180, PITCH = 22;
    static final double EYE_TOLERANCE = .05, ANGLE_TOLERANCE = .05;
    static final int DAY_TIME = 7000, NIGHT_TIME = 18000;
    static final double MIN_WARMUP_SECONDS = 15;
    static final double MOVING_AMPLITUDE_DEGREES = 10, MOVING_PERIOD_SECONDS = 10;
    static final double WATER_SURFACE_Y = 150 + 8.0 / 9.0;
    /** Translating route: eye x linear from start to end over WALK_SECONDS from sample start, then held at the end. */
    static final double WALK_START_X = 410.5, WALK_END_X = 405.5, WALK_SECONDS = 8, WALK_WEST_X = 406.5;
    static final int CLUSTER_SIZE = 8, WALK_BOUNDARY_X = 408;
    /** Tick-stepped server teleports lag the analytical route by about one tick (0.03 m at 0.625 m/s); bound it generously. */
    static final double WALK_TRACK_TOLERANCE = .35;
    static final double PLAYER_HALF_WIDTH = .3, PLAYER_HEIGHT = 1.8;
    static final String STONE_DIVIDER = "minecraft:stone_bricks", GLASS_DIVIDER = "minecraft:red_stained_glass";
    static final List<String> SCENES = List.of("lamp-day-off", "lamp-day-torch", "lamp-day-wall", "lamp-day-wall-off",
        "lamp-night-off", "lamp-night-torch", "lamp-night-soul", "lamp-night-both", "lamp-night-wall",
        "lamp-night-wall-off", "lamp-night-water", "lamp-night-moving",
        "lamp-day-canopy", "lamp-night-glass", "lamp-night-glass-off", "lamp-night-walk", "lamp-night-walk-east", "lamp-night-walk-west");
    static final Map<String, Integer> EMISSION = Map.of("minecraft:torch", 14, "minecraft:soul_torch", 10, "minecraft:lantern", 15);
    static final Set<String> NON_OPAQUE = Set.of("minecraft:oak_leaves", "minecraft:water", "minecraft:torch",
        "minecraft:soul_torch", "minecraft:lantern", GLASS_DIVIDER);

    record Cell(int x, int y, int z, String id, Map<String, String> properties, String role) {
        String state() {
            if (properties.isEmpty()) return id;
            StringJoiner joined = new StringJoiner(",", "[", "]");
            new TreeMap<>(properties).forEach((key, value) -> joined.add(key + "=" + value));
            return id + joined;
        }
        List<Integer> position() { return List.of(x, y, z); }
    }
    record Lamp(String id, int x, int y, int z) {
        List<Double> center() { return List.of(x + .5, y + .5, z + .5); }
        int emission() { return EMISSION.get(id); }
    }
    /** divider: null, STONE_DIVIDER or GLASS_DIVIDER. eyeX: fixed eye x, or the route start when walking.
     * hand: null for the original lamp scenes; the carried-light spec (own room, pose and held items) otherwise. */
    record Plan(String scene, int timeOfDay, boolean wallPresent, boolean moving, List<Lamp> lamps, List<Cell> placements,
                String divider, double eyeX, boolean walking, HandLightFixture.Spec hand) {
        float yaw() { return hand != null ? HandLightFixture.YAW : YAW; }
        float pitch() { return hand != null ? HandLightFixture.PITCH : PITCH; }
        double eyeY() { return hand != null ? HandLightFixture.EYE_Y : EYE_Y; }
        double eyeZ() { return hand != null ? HandLightFixture.EYE_Z : EYE_Z; }
        double playerY() { return eyeY() - EYE_HEIGHT; }
        List<Double> eye() { return List.of(eyeX, eyeY(), eyeZ()); }
    }

    static boolean authorized(String name, String id, long seed) {
        return OcclusionFixture.authorized(name, id) && seed == SEED;
    }
    static boolean inBox(int x, int y, int z) {
        return x >= BOX.get(0) && x <= BOX.get(3) && y >= BOX.get(1) && y <= BOX.get(4) && z >= BOX.get(2) && z <= BOX.get(5);
    }
    static int boxCells() { return (BOX.get(3) - BOX.get(0) + 1) * (BOX.get(4) - BOX.get(1) + 1) * (BOX.get(5) - BOX.get(2) + 1); }

    static final int[] TORCH_A = {7, 151, 3}, SOUL_B = {7, 151, 5}, LANTERN = {6, 152, 8};
    /** On grass (3,150,5) under the leaf layer y154..156; diagonal to the trunk's south (camera-facing) face. */
    static final int[] CANOPY_TORCH = {3, 151, 5};

    // Pose locks query scenes every frame. Geometry is immutable for a scene.
    private static final Map<String, Plan> PLANS = buildPlans();
    private static final Map<String, Map<List<Integer>, Cell>> GRIDS = buildGrids();
    private static Map<String, Plan> buildPlans() {
        Map<String, Plan> plans = new HashMap<>();
        for (String scene : SCENES) plans.put(scene, buildPlan(scene));
        for (String scene : HandLightFixture.SCENES) plans.put(scene, buildPlan(scene));
        return Map.copyOf(plans);
    }
    private static Map<String, Map<List<Integer>, Cell>> buildGrids() {
        Map<String, Map<List<Integer>, Cell>> grids = new HashMap<>();
        PLANS.forEach((scene, plan) -> {
            Map<List<Integer>, Cell> grid = new HashMap<>();
            for (Cell cell : plan.placements()) grid.put(cell.position(), cell);
            grids.put(scene, Collections.unmodifiableMap(grid));
        });
        return Map.copyOf(grids);
    }
    static Plan parse(String scene) { return scene == null ? null : PLANS.get(scene); }
    private static Plan buildPlan(String scene) {
        HandLightFixture.Spec hand = HandLightFixture.spec(scene);
        if (hand != null)
            return new Plan(scene, HandLightFixture.TIME, false, false, List.of(), HandLightFixture.placements(hand.pillar()), null,
                HandLightFixture.EYE_X, false, hand);
        boolean day = scene.startsWith("lamp-day-");
        String variant = scene.substring(day ? 9 : 11);
        String divider = switch (variant) {
            case "wall", "wall-off" -> STONE_DIVIDER;
            case "glass", "glass-off" -> GLASS_DIVIDER;
            default -> null;
        };
        List<Lamp> lamps = new ArrayList<>();
        switch (variant) {
            case "torch", "wall", "glass" -> lamps.add(lamp("minecraft:torch", TORCH_A));
            case "soul" -> lamps.add(lamp("minecraft:soul_torch", TORCH_A));
            case "both" -> { lamps.add(lamp("minecraft:torch", TORCH_A)); lamps.add(lamp("minecraft:soul_torch", SOUL_B)); }
            case "water" -> lamps.add(lamp("minecraft:lantern", LANTERN));
            case "canopy" -> lamps.add(lamp("minecraft:torch", CANOPY_TORCH));
            case "moving", "walk", "walk-east", "walk-west" -> { lamps.add(lamp("minecraft:torch", TORCH_A)); lamps.add(lamp("minecraft:lantern", LANTERN)); }
            default -> { }
        }
        double eyeX = switch (variant) {
            case "walk" -> WALK_START_X;
            case "walk-west" -> WALK_WEST_X;
            default -> EYE_X;
        };
        return new Plan(scene, day ? DAY_TIME : NIGHT_TIME, STONE_DIVIDER.equals(divider), variant.equals("moving"),
            List.copyOf(lamps), placements(divider, lamps), divider, eyeX, variant.equals("walk"), null);
    }
    private static Lamp lamp(String id, int[] local) { return new Lamp(id, OX + local[0], local[1], OZ + local[2]); }

    /** Ordered so supports precede attachments and sealed basin precedes water; cleanup uses reverse order. */
    private static List<Cell> placements(String divider, List<Lamp> lamps) {
        List<Cell> cells = new ArrayList<>();
        // Platform y150; the pool's basin floor is y148 and its walls at y149 lie under the platform ring.
        for (int dx = 0; dx <= 13; dx++) for (int dz = 0; dz <= 12; dz++) {
            if (pool(dx, dz)) continue; // the pool's own y150 water layer
            String id = dx <= 4 ? (dx == 2 && dz == 4 ? "minecraft:dirt" : "minecraft:grass_block")
                : dz >= 2 && dz <= 6 && ((dx >= 6 && dx <= 8) || (dx >= 10 && dx <= 12)) ? "minecraft:smooth_stone" : "minecraft:stone";
            cells.add(cell(dx, OY, dz, id, Map.of(), "platform"));
        }
        for (int dx = 7; dx <= 11; dx++) for (int dz = 9; dz <= 11; dz++)
            cells.add(cell(dx, 148, dz, dz == 9 && dx >= 8 && dx <= 10 ? "minecraft:white_concrete" : "minecraft:stone", Map.of(),
                dz == 9 && dx >= 8 && dx <= 10 ? "submerged-receiver" : "basin-floor"));
        // Basin walls y149 below the platform ring, then the lantern post on the platform.
        for (int dx = 6; dx <= 12; dx++) for (int dz = 8; dz <= 12; dz++)
            if (dx == 6 || dx == 12 || dz == 8 || dz == 12) cells.add(cell(dx, 149, dz, "minecraft:stone", Map.of(), "basin-wall"));
        cells.add(cell(LANTERN[0], 151, LANTERN[2], "minecraft:stone_bricks", Map.of(), "lantern-post"));
        // Shelter: back wall (white receiving faces inside each bay), side walls and roof.
        for (int y = 151; y <= 154; y++) {
            for (int dx = 5; dx <= 13; dx++)
                cells.add(cell(dx, y, 1, (dx >= 6 && dx <= 8) || (dx >= 10 && dx <= 12) ? "minecraft:white_concrete" : "minecraft:stone_bricks",
                    Map.of(), dx >= 10 && dx <= 12 ? "receiver-back-wall" : dx >= 6 && dx <= 8 ? "lamp-bay-back-wall" : "shelter-wall"));
            for (int dz = 2; dz <= 6; dz++) {
                cells.add(cell(5, y, dz, "minecraft:stone_bricks", Map.of(), "shelter-wall"));
                cells.add(cell(13, y, dz, "minecraft:stone_bricks", Map.of(), "shelter-wall"));
            }
        }
        for (int dx = 5; dx <= 13; dx++) for (int dz = 1; dz <= 6; dz++)
            cells.add(cell(dx, 155, dz, "minecraft:spruce_planks", Map.of(), "shelter-roof"));
        // Canopy: log trunk on dirt, persistent leaves (no decay, so the exact state survives the scene).
        for (int y = 151; y <= 155; y++) cells.add(cell(2, y, 4, "minecraft:oak_log", Map.of("axis", "y"), "canopy-trunk"));
        for (int y = 154; y <= 156; y++) for (int dx = 0; dx <= 4; dx++) for (int dz = 2; dz <= 6; dz++) {
            if (dx == 2 && dz == 4 && y <= 155) continue;
            boolean corner = (dx == 0 || dx == 4) && (dz == 2 || dz == 6);
            if (y == 155 && corner) continue;
            if (y == 156 && (dx == 0 || dx == 4 || dz == 2 || dz == 6)) continue;
            cells.add(cell(dx, y, dz, "minecraft:oak_leaves", Map.of("persistent", "true"), "canopy-leaves"));
        }
        if (divider != null) for (int y = 151; y <= 154; y++) for (int dz = 2; dz <= 6; dz++)
            cells.add(cell(9, y, dz, divider, Map.of(), divider.equals(STONE_DIVIDER) ? "intervening-wall" : "glass-divider"));
        for (int y = 149; y <= 150; y++) for (int dx = 7; dx <= 11; dx++) for (int dz = 9; dz <= 11; dz++)
            cells.add(cell(dx, y, dz, "minecraft:water", Map.of("level", "0"), "still-water"));
        for (Lamp lamp : lamps)
            cells.add(new Cell(lamp.x(), lamp.y(), lamp.z(), lamp.id(),
                lamp.id().equals("minecraft:lantern") ? Map.of("hanging", "false") : Map.of(), "lamp"));
        return List.copyOf(cells);
    }
    private static boolean pool(int dx, int dz) { return dx >= 7 && dx <= 11 && dz >= 9 && dz <= 11; }
    private static Cell cell(int dx, int y, int dz, String id, Map<String, String> properties, String role) {
        return new Cell(OX + dx, y, OZ + dz, id, properties, role);
    }

    /** Parses Minecraft's BlockState#toString form, e.g. Block{minecraft:oak_leaves}[distance=1,persistent=true]. */
    static boolean stateMatches(Cell cell, String actualId, String stateText) {
        if (!cell.id().equals(actualId) || stateText == null) return false;
        Map<String, String> actual = new HashMap<>();
        int open = stateText.indexOf("}["), close = stateText.lastIndexOf(']');
        if (open >= 0 && close > open + 1)
            for (String pair : stateText.substring(open + 2, close).split(",")) {
                int equals = pair.indexOf('=');
                if (equals > 0) actual.put(pair.substring(0, equals), pair.substring(equals + 1));
            }
        for (var expected : cell.properties().entrySet())
            if (!expected.getValue().equals(actual.get(expected.getKey()))) return false;
        return true;
    }
    static OcclusionFixture.Cleanup cleanupDecision(Cell cell, String actualId) {
        if (actualId.equals(cell.id())) return OcclusionFixture.Cleanup.REMOVE;
        if (actualId.equals("minecraft:air")) return OcclusionFixture.Cleanup.ALREADY_AIR;
        return OcclusionFixture.Cleanup.CONFLICT;
    }
    static List<Cell> cleanupOrder(Plan plan) {
        List<Cell> reversed = new ArrayList<>(plan.placements());
        Collections.reverse(reversed);
        return List.copyOf(reversed);
    }

    static float expectedYaw(Plan plan, double secondsSinceSampleStart) {
        if (!plan.moving() || secondsSinceSampleStart <= 0) return plan.yaw();
        return (float)(YAW + MOVING_AMPLITUDE_DEGREES * Math.sin(2 * Math.PI * secondsSinceSampleStart / MOVING_PERIOD_SECONDS));
    }
    static boolean eyeMatches(boolean firstPerson, double[] player, double[] eye, double[] camera) {
        return eyeMatches(EYE_X, firstPerson, player, eye, camera);
    }
    /** Same proof at a requested eye x (fixed walk variants, or the walk route end at capture). */
    static boolean eyeMatches(double expectedEyeX, boolean firstPerson, double[] player, double[] eye, double[] camera) {
        if (!Double.isFinite(expectedEyeX) || !OcclusionFixture.eyeMatches(firstPerson, eye, camera) || player == null || player.length != 3) return false;
        for (double value : player) if (!Double.isFinite(value)) return false;
        return Math.abs(player[0] - expectedEyeX) <= EYE_TOLERANCE && Math.abs(player[1] - (EYE_Y - EYE_HEIGHT)) <= EYE_TOLERANCE &&
            Math.abs(player[2] - EYE_Z) <= EYE_TOLERANCE && Math.abs(eye[0] - expectedEyeX) <= EYE_TOLERANCE &&
            Math.abs(eye[1] - EYE_Y) <= EYE_TOLERANCE && Math.abs(eye[2] - EYE_Z) <= EYE_TOLERANCE;
    }

    /** Same proof at the plan's own eye y/z (carried-light room) or the original constants. */
    static boolean eyeMatches(Plan plan, double expectedEyeX, boolean firstPerson, double[] player, double[] eye, double[] camera) {
        if (plan.hand() == null) return eyeMatches(expectedEyeX, firstPerson, player, eye, camera);
        return Double.isFinite(expectedEyeX) && OcclusionFixture.eyeMatches(firstPerson, eye, camera) &&
            HandLightFixture.poseMatches(expectedEyeX, HandLightFixture.EYE_TOLERANCE, firstPerson, player, eye, camera);
    }

    /** Analytical route: requested eye x at seconds since sample start (fixed plans return their constant eye x). */
    static double walkEyeX(Plan plan, double secondsSinceSampleStart) {
        if (plan.hand() != null) return HandLightFixture.routeEyeX(plan.hand(), secondsSinceSampleStart);
        if (!plan.walking()) return plan.eyeX();
        double f = Math.max(0, Math.min(1, secondsSinceSampleStart / WALK_SECONDS));
        return WALK_START_X + (WALK_END_X - WALK_START_X) * f;
    }
    static double walkBoundarySeconds() { return WALK_SECONDS * (WALK_START_X - WALK_BOUNDARY_X) / (WALK_START_X - WALK_END_X); }
    static int clusterX(double x) { return Math.floorDiv((int)Math.floor(x), CLUSTER_SIZE); }
    /** Live tracking guard while the route is driven by tick-stepped teleports: x may lag, y/z and eye height may not. */
    static boolean walkTracks(double expectedEyeX, double[] player, double[] camera) {
        if (player == null || camera == null || player.length != 3 || camera.length != 3) return false;
        for (double value : player) if (!Double.isFinite(value)) return false;
        for (double value : camera) if (!Double.isFinite(value)) return false;
        double lo = Math.min(WALK_START_X, WALK_END_X) - EYE_TOLERANCE, hi = Math.max(WALK_START_X, WALK_END_X) + EYE_TOLERANCE;
        return Math.abs(player[0] - expectedEyeX) <= WALK_TRACK_TOLERANCE && Math.abs(camera[0] - expectedEyeX) <= WALK_TRACK_TOLERANCE &&
            player[0] >= lo && player[0] <= hi && camera[0] >= lo && camera[0] <= hi &&
            Math.abs(player[1] - (EYE_Y - EYE_HEIGHT)) <= EYE_TOLERANCE && Math.abs(player[2] - EYE_Z) <= EYE_TOLERANCE &&
            Math.abs(camera[1] - EYE_Y) <= EYE_TOLERANCE && Math.abs(camera[2] - EYE_Z) <= EYE_TOLERANCE;
    }
    /** Every cell touched by the spectator body box at eye x lies in the reservation and is never placed. */
    static boolean bodyClear(Plan plan, double eyeX) {
        Map<List<Integer>, Cell> cells = grid(plan);
        double feet = EYE_Y - EYE_HEIGHT;
        for (int x = (int)Math.floor(eyeX - PLAYER_HALF_WIDTH); x <= (int)Math.floor(eyeX + PLAYER_HALF_WIDTH); x++)
            for (int y = (int)Math.floor(feet); y <= (int)Math.floor(feet + PLAYER_HEIGHT); y++)
                for (int z = (int)Math.floor(EYE_Z - PLAYER_HALF_WIDTH); z <= (int)Math.floor(EYE_Z + PLAYER_HALF_WIDTH); z++)
                    if (!inBox(x, y, z) || cells.containsKey(List.of(x, y, z))) return false;
        return true;
    }

    /** Vanilla DimensionType#getSkyAngle and the overworld sun path (east +X at sunrise, no path rotation in this pack). */
    static double[] sunDirection(int timeOfDay) {
        double d = timeOfDay / 24000.0 - .25;
        d -= Math.floor(d);
        double angle = (d * 2 + (.5 - Math.cos(d * Math.PI) / 2)) / 3 * 2 * Math.PI;
        return new double[]{-Math.sin(angle), Math.cos(angle), 0};
    }
    /** Lab-geometry solar shade: the ray to the sun hits an opaque block or a leaf (leaves treated as blocking). */
    static boolean solarShaded(Plan plan, List<Double> point) {
        double[] sun = sunDirection(plan.timeOfDay());
        if (sun[1] <= 0) return true;
        double t = (BOX.get(4) + 1 - point.get(1)) / sun[1];
        return !clear(plan, point, List.of(point.get(0) + t * sun[0], point.get(1) + t * sun[1], point.get(2) + t * sun[2]), true);
    }

    /** Samples of the plan's own layout. */
    static Map<String, List<Double>> samples(Plan plan) { return plan.hand() != null ? HandLightFixture.samples() : samples(); }
    /** Named world-space surface samples (points 1 mm on the air/water side of the receiving face). */
    static Map<String, List<Double>> samples() {
        Map<String, List<Double>> result = new LinkedHashMap<>();
        double e = .001;
        result.put("receiver-back-wall", List.of(OX + 11.5, 152.5, OZ + 2 + e));
        result.put("receiver-floor-deep", List.of(OX + 11.5, 151 + e, OZ + 3.5));
        result.put("receiver-floor-mid", List.of(OX + 10.5, 151 + e, OZ + 4.5));
        result.put("lamp-bay-floor", List.of(OX + 6.5, 151 + e, OZ + 4.5));
        result.put("lamp-bay-back-wall", List.of(OX + 7.5, 152.5, OZ + 2 + e));
        result.put("canopy-shade-grass", List.of(OX + 2.5, 151 + e, OZ + 2.5));
        result.put("sunlit-grass", List.of(OX + 2.5, 151 + e, OZ + 10.5));
        result.put("pool-surface-center", List.of(OX + 9.5, WATER_SURFACE_Y, OZ + 10.5));
        result.put("submerged-receiver", List.of(OX + 9.5, 149 + e, OZ + 9.5));
        // Under the canopy, beside CANOPY_TORCH: grass top just south of the torch and the trunk's south face.
        result.put("canopy-torch-grass", List.of(OX + 3.5, 151 + e, OZ + 6.5));
        result.put("canopy-trunk-face", List.of(OX + 2.5, 152.5, OZ + 5 + e));
        return result;
    }
    /** Mirror point of the lantern centre in the still-water plane, intersected with the eye ray. */
    static List<Double> lanternReflectionPoint() {
        double[] lantern = {OX + LANTERN[0] + .5, LANTERN[1] + .5, OZ + LANTERN[2] + .5};
        double mirrorY = 2 * WATER_SURFACE_Y - lantern[1];
        double t = (EYE_Y - WATER_SURFACE_Y) / (EYE_Y - mirrorY);
        return List.of(EYE_X + t * (lantern[0] - EYE_X), WATER_SURFACE_Y, EYE_Z + t * (lantern[2] - EYE_Z));
    }

    /** Read-only lookup; memoized for the reviewed scenes. */
    static Map<List<Integer>, Cell> grid(Plan plan) {
        Map<List<Integer>, Cell> cached = GRIDS.get(plan.scene());
        if (cached != null && PLANS.get(plan.scene()) == plan) return cached;
        Map<List<Integer>, Cell> result = new HashMap<>();
        for (Cell cell : plan.placements()) result.put(cell.position(), cell);
        return Collections.unmodifiableMap(result);
    }
    static boolean opaque(Cell cell) { return cell != null && !NON_OPAQUE.contains(cell.id()); }
    /** Dense segment march through full voxels: true when no full opaque block lies strictly between a and b. */
    static boolean clear(Plan plan, List<Double> a, List<Double> b, boolean leavesBlock) {
        Map<List<Integer>, Cell> cells = grid(plan);
        double length = Math.sqrt(Math.pow(b.get(0) - a.get(0), 2) + Math.pow(b.get(1) - a.get(1), 2) + Math.pow(b.get(2) - a.get(2), 2));
        int steps = (int)Math.ceil(length / .002);
        for (int i = 1; i < steps; i++) {
            double t = i / (double)steps;
            List<Integer> key = List.of((int)Math.floor(a.get(0) + t * (b.get(0) - a.get(0))),
                (int)Math.floor(a.get(1) + t * (b.get(1) - a.get(1))), (int)Math.floor(a.get(2) + t * (b.get(2) - a.get(2))));
            Cell cell = cells.get(key);
            if (opaque(cell) || (leavesBlock && cell != null && cell.id().equals("minecraft:oak_leaves"))) return false;
        }
        return true;
    }
    /** Vanilla block-light flood-fill model: each step through a non-opaque cell costs one level; full blocks stop it.
     * Returns the predicted block light of the air cell containing the point (analytical model, not a measurement). */
    static int predictedBlockLight(Plan plan, List<Double> point) {
        Map<List<Integer>, Cell> cells = grid(plan);
        List<Integer> target = List.of((int)Math.floor(point.get(0)), (int)Math.floor(point.get(1)), (int)Math.floor(point.get(2)));
        int best = 0;
        for (Lamp lamp : plan.lamps()) {
            Map<List<Integer>, Integer> level = new HashMap<>();
            ArrayDeque<List<Integer>> queue = new ArrayDeque<>();
            List<Integer> start = List.of(lamp.x(), lamp.y(), lamp.z());
            level.put(start, lamp.emission()); queue.add(start);
            while (!queue.isEmpty()) {
                List<Integer> at = queue.poll();
                int value = level.get(at);
                if (value <= 1) continue;
                for (int[] d : new int[][]{{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}}) {
                    List<Integer> next = List.of(at.get(0) + d[0], at.get(1) + d[1], at.get(2) + d[2]);
                    if (opaque(cells.get(next)) || level.getOrDefault(next, 0) >= value - 1) continue;
                    level.put(next, value - 1); queue.add(next);
                }
            }
            best = Math.max(best, level.getOrDefault(target, 0));
        }
        return best;
    }
    /** Pinhole projection with Minecraft's vertical FOV; pixel origin top-left. Null when behind the eye. */
    static List<Double> project(List<Double> point, float yaw, float pitch, double verticalFov, int width, int height) {
        return project(point, eye(), yaw, pitch, verticalFov, width, height);
    }
    static List<Double> project(List<Double> point, List<Double> eye, float yaw, float pitch, double verticalFov, int width, int height) {
        double y = Math.toRadians(yaw), p = Math.toRadians(pitch);
        double[] forward = {-Math.sin(y) * Math.cos(p), -Math.sin(p), Math.cos(y) * Math.cos(p)};
        double[] right = {-Math.cos(y), 0, -Math.sin(y)};
        double[] up = {right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
            right[0] * forward[1] - right[1] * forward[0]};
        double[] d = {point.get(0) - eye.get(0), point.get(1) - eye.get(1), point.get(2) - eye.get(2)};
        double zv = dot(d, forward);
        if (zv <= 1e-6) return null;
        double tan = Math.tan(Math.toRadians(verticalFov) / 2), aspect = width / (double)height;
        double nx = dot(d, right) / (zv * tan * aspect), ny = dot(d, up) / (zv * tan);
        return List.of((nx + 1) / 2 * width, (1 - ny) / 2 * height);
    }
    private static double dot(double[] a, double[] b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    static List<Double> eye() { return List.of(EYE_X, EYE_Y, EYE_Z); }
}
