package dev.aqualumen.bench;

import java.util.*;

/** Carried (hand-held) light TEST fixture: a sealed authored room inside the reserved LocalLightFixture AIR box of the
 * exact dedicated V2 world (UUID + seed guarded through LocalLightFixture), driven by a disposable creative first-person
 * player whose real item stacks are equipped with integrated-server commands.
 *
 * Room (inclusive world cells): opaque shell x 403..410, y 150..154, z -412..-404; interior AIR x 404..409, y 151..153,
 * z -411..-405. Floor y150 smooth_stone, ceiling y154 spruce_planks, white_concrete back (receiver) wall z -412,
 * stone_bricks side/south walls. No emitting block is placed and the shell is sealed, so vanilla block and sky light are
 * 0 inside: any lighting difference between paired shots comes from the shader's carried light.
 * Eye (406.65, 152.62, -407.0), feet on the floor top y151, yaw 180 (north, -Z), pitch 0: back wall 4.0 m ahead,
 * visible floor/ceiling 2..4 m ahead, side walls 2.65 m (west) and 3.35 m (east).
 * Pillars (stone_bricks, y 151..153, floor to ceiling): FRONT at x406 z-410 (opaque pillar before the lit back wall);
 * HIDDEN at x407 z-409 (narrow pillar east of the main-hand anchor; it shadows a camera-visible wall strip from the main
 * hand while the off hand still reaches it).
 * Light anchors are the release shader's first-person carried-light anchor (release/shaders/lib/carried_light.glsl,
 * publishHandLamp): view-space (0.32*side, -0.30, -0.43) through gbufferModelViewInverse, side +1 for the main hand of a
 * right-handed player. They are a geometric model of the shader, not a measurement of rendered light. Receiver ROIs
 * are fixed 9x9 pixel blocks at 2560x1440 / FOV 70 evaluated against the release's three finite-emitter taps
 * (local_lighting.glsl lampVisibility, radius 0.13 * 0.66) and its carried-light voxel traversal (lampTransmission).
 */
final class HandLightFixture {
    static final String PREFIX = "lamp-hand-";
    static final String TORCH = "minecraft:torch", SOUL = "minecraft:soul_torch", EMPTY = "minecraft:air";
    /** Vanilla block luminance of the placed-block form (Iris' default IrisItemLightProvider emission for block items). */
    static final Map<String, Integer> VANILLA_LUMINANCE = Map.of(TORCH, 14, SOUL, 10, EMPTY, 0);
    /** The only items the fixture ever puts into the two driver hand slots. */
    static final Set<String> FIXTURE_ITEMS = Set.of(TORCH, SOUL);
    static final String MAIN_SLOT = "weapon.mainhand", OFF_SLOT = "weapon.offhand";
    /** PlayerInventory#size: 36 main + 4 armor + 1 off hand. */
    static final int INVENTORY_SLOTS = 41;

    static final int SHELL_X0 = 403, SHELL_X1 = 410, SHELL_Y0 = 150, SHELL_Y1 = 154, SHELL_Z0 = -412, SHELL_Z1 = -404;
    static final double EYE_X = 406.65, EYE_Y = 152.62, EYE_Z = -407.0;
    static final float YAW = 180, PITCH = 0;
    static final int TIME = 18000;
    static final int FRONT_PILLAR_X = 406, FRONT_PILLAR_Z = -410, HIDDEN_PILLAR_X = 407, HIDDEN_PILLAR_Z = -409;
    static final String FLOOR = "minecraft:smooth_stone", CEILING = "minecraft:spruce_planks", RECEIVER = "minecraft:white_concrete",
        WALL = "minecraft:stone_bricks", PILLAR = "minecraft:stone_bricks";
    /** Release first-person anchor in view space: right 0.32*side, down 0.30, forward 0.43 (view z -0.43). */
    static final double HAND_RIGHT = .32, HAND_DOWN = .30, HAND_FORWARD = .43;
    static final String ANCHOR_SOURCE = "release/shaders/lib/carried_light.glsl publishHandLamp, firstPersonCamera branch: " +
        "offset = mat3(gbufferModelViewInverse) * vec3(0.32*side, -0.30, -0.43), side = +1 main hand when right-handed; constrainHand inactive (eye-to-anchor segment is room AIR)";
    /** Release finite emitter for torch/soul torch (kind 1/6): radius 0.13; three taps on a disk facing the receiver at radius*0.66. */
    static final double EMITTER_RADIUS = .13, TAP_SCALE = .66, RECEIVER_NORMAL_OFFSET = .025;
    /** Release lampTransmission loop bound. */
    static final int TRAVERSAL_STEPS = 32;
    static final int FRAME_WIDTH = 2560, FRAME_HEIGHT = 1440, ROI_SIZE = 9;
    static final double FOV_DEGREES = 70;
    /** Back wall receiving plane (air side of the z -412 shell). */
    static final double RECEIVER_PLANE_Z = SHELL_Z0 + 1;
    /** Repeated walk past the front pillar: eye x = EYE_X + A*sin(2*pi*t/T) for 0<=t<=T, then held at EYE_X. */
    static final double ROUTE_SECONDS = 8, ROUTE_AMPLITUDE = 1.75;
    /** Fixed-pose acceptance: tp is exact; 0.02 m is inside the proven pose tolerance of every receiver ROI (hidden ~0.035 m). */
    static final double TRACK_TOLERANCE = .35, EYE_TOLERANCE = .02;
    /** A scheduled swap must be visible in the client player's actual stacks within this window. */
    static final double SWAP_GRACE_SECONDS = .5;
    /** Sequences need their 8 s schedule/route plus a held, settled final state before the capture. */
    static final double MIN_SEQUENCE_SAMPLE_SECONDS = 9;
    /** HeldItemRenderer equip progress at/above this is the raised, settled hand. */
    static final float SETTLED_EQUIP = .999f;

    enum Pillar { NONE, FRONT, HIDDEN }
    record Equip(String main, String off) {
        boolean empty() { return main.equals(EMPTY) && off.equals(EMPTY); }
        String describe() { return "main=" + main + ",off=" + off; }
    }
    record Step(double atSeconds, Equip equip) {}
    record Spec(String scene, Pillar pillar, boolean walking, List<Step> steps) {
        Equip initial() { return steps.getFirst().equip(); }
        Equip last() { return steps.getLast().equip(); }
        boolean sequence() { return steps.size() > 1; }
        boolean needsLongSample() { return walking || sequence(); }
        int stepAt(double seconds) {
            int index = 0;
            for (int i = 0; i < steps.size(); i++) if (seconds >= steps.get(i).atSeconds()) index = i;
            return index;
        }
        Equip equipAt(double seconds) { return steps.get(stepAt(seconds)).equip(); }
    }

    static final Equip NONE = new Equip(EMPTY, EMPTY), MAIN_TORCH = new Equip(TORCH, EMPTY), OFF_TORCH = new Equip(EMPTY, TORCH),
        MAIN_SOUL = new Equip(SOUL, EMPTY), TORCH_AND_SOUL = new Equip(TORCH, SOUL);
    static final List<String> SCENES = List.of("lamp-hand-empty", "lamp-hand-main", "lamp-hand-off", "lamp-hand-soul",
        "lamp-hand-both", "lamp-hand-pillar", "lamp-hand-pillar-empty", "lamp-hand-hidden", "lamp-hand-hidden-off",
        "lamp-hand-hidden-empty", "lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway");
    private static final Map<String, Spec> SPECS = buildSpecs();
    private static Map<String, Spec> buildSpecs() {
        Map<String, Spec> specs = new LinkedHashMap<>();
        for (String scene : SCENES) specs.put(scene, buildSpec(scene));
        return Collections.unmodifiableMap(specs);
    }
    private static Spec buildSpec(String scene) {
        return switch (scene.substring(PREFIX.length())) {
            case "empty" -> fixed(scene, Pillar.NONE, NONE);
            case "main" -> fixed(scene, Pillar.NONE, MAIN_TORCH);
            case "off" -> fixed(scene, Pillar.NONE, OFF_TORCH);
            case "soul" -> fixed(scene, Pillar.NONE, MAIN_SOUL);
            case "both" -> fixed(scene, Pillar.NONE, TORCH_AND_SOUL);
            case "pillar" -> fixed(scene, Pillar.FRONT, MAIN_TORCH);
            case "pillar-empty" -> fixed(scene, Pillar.FRONT, NONE);
            case "hidden" -> fixed(scene, Pillar.HIDDEN, MAIN_TORCH);
            case "hidden-off" -> fixed(scene, Pillar.HIDDEN, OFF_TORCH);
            case "hidden-empty" -> fixed(scene, Pillar.HIDDEN, NONE);
            case "walk" -> new Spec(scene, Pillar.FRONT, true, List.of(new Step(0, MAIN_TORCH)));
            case "walk-empty" -> new Spec(scene, Pillar.FRONT, true, List.of(new Step(0, NONE)));
            // Warm source in hand, put away, soul source, put away; held empty and settled before the capture.
            case "putaway" -> new Spec(scene, Pillar.NONE, false, List.of(new Step(0, MAIN_TORCH), new Step(2, NONE),
                new Step(4, MAIN_SOUL), new Step(6, NONE)));
            default -> throw new IllegalArgumentException(scene);
        };
    }
    private static Spec fixed(String scene, Pillar pillar, Equip equip) { return new Spec(scene, pillar, false, List.of(new Step(0, equip))); }
    static Spec spec(String scene) { return scene == null ? null : SPECS.get(scene); }
    static boolean isHandScene(String scene) { return spec(scene) != null; }

    /** Shell and pillar cells; supports precede nothing here (no attachments), so cleanup order is plain reverse order. */
    static List<LocalLightFixture.Cell> placements(Pillar pillar) {
        List<LocalLightFixture.Cell> cells = new ArrayList<>();
        for (int x = SHELL_X0; x <= SHELL_X1; x++) for (int y = SHELL_Y0; y <= SHELL_Y1; y++) for (int z = SHELL_Z0; z <= SHELL_Z1; z++) {
            boolean shell = x == SHELL_X0 || x == SHELL_X1 || y == SHELL_Y0 || y == SHELL_Y1 || z == SHELL_Z0 || z == SHELL_Z1;
            if (!shell) continue;
            String id, role;
            if (y == SHELL_Y0) { id = FLOOR; role = "hand-floor"; }
            else if (y == SHELL_Y1) { id = CEILING; role = "hand-ceiling"; }
            else if (z == SHELL_Z0 && x > SHELL_X0 && x < SHELL_X1) { id = RECEIVER; role = "hand-receiver-back-wall"; }
            else if (z == SHELL_Z1) { id = WALL; role = "hand-south-wall"; }
            else { id = WALL; role = "hand-side-wall"; }
            cells.add(new LocalLightFixture.Cell(x, y, z, id, Map.of(), role));
        }
        if (pillar != Pillar.NONE) {
            int px = pillar == Pillar.FRONT ? FRONT_PILLAR_X : HIDDEN_PILLAR_X, pz = pillar == Pillar.FRONT ? FRONT_PILLAR_Z : HIDDEN_PILLAR_Z;
            for (int y = SHELL_Y0 + 1; y < SHELL_Y1; y++)
                cells.add(new LocalLightFixture.Cell(px, y, pz, PILLAR, Map.of(), pillar == Pillar.FRONT ? "hand-front-pillar" : "hand-hidden-pillar"));
        }
        return List.copyOf(cells);
    }
    static boolean interior(int x, int y, int z) {
        return x > SHELL_X0 && x < SHELL_X1 && y > SHELL_Y0 && y < SHELL_Y1 && z > SHELL_Z0 && z < SHELL_Z1;
    }

    /** Eye x of the driver at seconds since sample start (fixed scenes: constant). */
    static double routeEyeX(Spec spec, double seconds) {
        if (!spec.walking() || seconds <= 0 || seconds >= ROUTE_SECONDS) return EYE_X;
        return EYE_X + ROUTE_AMPLITUDE * Math.sin(2 * Math.PI * seconds / ROUTE_SECONDS);
    }
    /** Times at which the walking eye crosses the front pillar's west/east faces and its centre (analytical). */
    static List<Double> routePillarCrossings() {
        List<Double> result = new ArrayList<>();
        double previous = routeEyeX(SPECS.get("lamp-hand-walk"), 0);
        for (int i = 1; i <= 80000; i++) {
            double t = i * ROUTE_SECONDS / 80000, x = EYE_X + ROUTE_AMPLITUDE * Math.sin(2 * Math.PI * t / ROUTE_SECONDS);
            for (double plane : new double[]{FRONT_PILLAR_X, FRONT_PILLAR_X + .5, FRONT_PILLAR_X + 1})
                if ((previous - plane) * (x - plane) < 0) result.add(Math.round(t * 1000) / 1000.0);
            previous = x;
        }
        return result;
    }

    /** Release first-person carried-light anchor of a hand at an eye pose (world coordinates, right-handed player). */
    static List<Double> handOrigin(boolean main, double eyeX, double eyeY, double eyeZ, float yaw, float pitch) {
        double y = Math.toRadians(yaw), p = Math.toRadians(pitch);
        double[] forward = {-Math.sin(y) * Math.cos(p), -Math.sin(p), Math.cos(y) * Math.cos(p)};
        double[] right = {-Math.cos(y), 0, -Math.sin(y)};
        double[] up = {right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
            right[0] * forward[1] - right[1] * forward[0]};
        double side = main ? HAND_RIGHT : -HAND_RIGHT;
        return List.of(eyeX + side * right[0] - HAND_DOWN * up[0] + HAND_FORWARD * forward[0],
            eyeY + side * right[1] - HAND_DOWN * up[1] + HAND_FORWARD * forward[1],
            eyeZ + side * right[2] - HAND_DOWN * up[2] + HAND_FORWARD * forward[2]);
    }
    static List<Double> handOrigin(boolean main) { return handOrigin(main, EYE_X, EYE_Y, EYE_Z, YAW, PITCH); }
    static List<Double> eye() { return List.of(EYE_X, EYE_Y, EYE_Z); }

    /** Named world-space surface samples, 1 mm on the air side of the receiving face. The four ROI samples are the
     * back-wall points under the ROI centre pixel at the requested pose (see ROIS). */
    static Map<String, List<Double>> samples() {
        Map<String, List<Double>> result = new LinkedHashMap<>();
        double e = .001, back = SHELL_Z0 + 1 + e;
        result.put("hand-back-wall-center", List.of(EYE_X, EYE_Y, back));
        result.put("hand-back-wall-west", List.of(404.5, 152.5, back));
        result.put("hand-back-wall-east", List.of(408.5, 152.5, back));
        result.put("hand-floor-mid", List.of(406.5, SHELL_Y0 + 1 + e, -410.0));
        result.put("hand-ceiling-mid", List.of(406.5, SHELL_Y1 - e, -410.0));
        result.put("hand-wall-west", List.of(SHELL_X0 + 1 + e, EYE_Y, -410.0));
        result.put("hand-wall-east", List.of(SHELL_X1 - e, EYE_Y, -410.5));
        for (Roi roi : ROIS) {
            double[] p = roiCentre(roi);
            result.put(roi.name(), List.of(p[0], p[1], back));
        }
        result.put("hand-front-pillar-face", List.of(FRONT_PILLAR_X + .5, 152.5, FRONT_PILLAR_Z + 1 + e));
        result.put("hand-hidden-pillar-face", List.of(HIDDEN_PILLAR_X + .5, 152.5, HIDDEN_PILLAR_Z + 1 + e));
        return Collections.unmodifiableMap(result);
    }

    // ---- Release carried-light geometry model (pure CPU; mirrors the GLSL, not a rendering measurement).
    static double[] vec(List<Double> p) { return new double[]{p.get(0), p.get(1), p.get(2)}; }
    private static double[] cross(double[] a, double[] b) {
        return new double[]{a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
    }
    private static double[] normalize(double[] a) {
        double l = Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
        return new double[]{a[0] / l, a[1] / l, a[2] / l};
    }
    /** local_lighting.glsl lampVisibility (LOCAL_LIGHT_SAMPLES == 3): taps centre+u, centre-0.5u+-0.866v. */
    static List<double[]> emitterTaps(double[] receiver, double[] lamp) {
        double[] l = normalize(new double[]{lamp[0] - receiver[0], lamp[1] - receiver[1], lamp[2] - receiver[2]});
        double[] axis = Math.abs(l[1]) < .9 ? new double[]{0, 1, 0} : new double[]{1, 0, 0};
        double[] u = normalize(cross(l, axis));
        for (int i = 0; i < 3; i++) u[i] *= EMITTER_RADIUS * TAP_SCALE;
        double[] v = cross(l, u);
        List<double[]> taps = new ArrayList<>(3);
        taps.add(new double[]{lamp[0] + u[0], lamp[1] + u[1], lamp[2] + u[2]});
        taps.add(new double[]{lamp[0] - .5 * u[0] + .866 * v[0], lamp[1] - .5 * u[1] + .866 * v[1], lamp[2] - .5 * u[2] + .866 * v[2]});
        taps.add(new double[]{lamp[0] - .5 * u[0] - .866 * v[0], lamp[1] - .5 * u[1] - .866 * v[1], lamp[2] - .5 * u[2] - .866 * v[2]});
        return taps;
    }
    /** Port of lampTransmission(start, target, carried=true) for full opaque cells: every visited cell including the
     * target's is tested; a cell blocks when the segment spends more than 0.00005 m in it; at most 32 cells. */
    static boolean shaderClear(Map<List<Integer>, LocalLightFixture.Cell> grid, double[] start, double[] target) {
        double[] delta = {target[0] - start[0], target[1] - start[1], target[2] - start[2]};
        double dist = Math.sqrt(delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]);
        double[] ray = new double[3], invRay = new double[3], nextT = new double[3];
        int[] cell = new int[3], step = new int[3];
        for (int i = 0; i < 3; i++) {
            ray[i] = delta[i] / Math.max(dist, 1e-4);
            invRay[i] = 1 / (Math.abs(ray[i]) > 1e-8 ? ray[i] : 1e-8);
            cell[i] = (int)Math.floor(start[i]);
            step[i] = (int)Math.signum(ray[i]);
            nextT[i] = Math.abs(ray[i]) > 1e-8 ? (cell[i] + (ray[i] >= 0 ? 1 : 0) - start[i]) * invRay[i] : 1e10;
        }
        double t = 0;
        for (int iteration = 0; iteration < TRAVERSAL_STEPS; iteration++) {
            double end = Math.min(dist, Math.min(nextT[0], Math.min(nextT[1], nextT[2])));
            if (end > t + .00005 && LocalLightFixture.opaque(grid.get(List.of(cell[0], cell[1], cell[2])))) return false;
            if (end >= dist) break;
            for (int i = 0; i < 3; i++) if (nextT[i] <= end + .00001) { cell[i] += step[i]; nextT[i] += Math.abs(invRay[i]); }
            t = end;
        }
        return true;
    }
    /** Open flags of the three taps of a lamp seen from a back-wall receiver point (normal +Z, start offset 0.025). */
    static boolean[] tapsOpen(Map<List<Integer>, LocalLightFixture.Cell> grid, double[] receiver, double[] lamp) {
        double[] start = {receiver[0], receiver[1], receiver[2] + RECEIVER_NORMAL_OFFSET};
        List<double[]> taps = emitterTaps(receiver, lamp);
        return new boolean[]{shaderClear(grid, start, taps.get(0)), shaderClear(grid, start, taps.get(1)), shaderClear(grid, start, taps.get(2))};
    }
    /** Camera basis for a Minecraft yaw/pitch (right, up, forward). */
    private static double[][] basis(float yaw, float pitch) {
        double y = Math.toRadians(yaw), p = Math.toRadians(pitch);
        double[] forward = {-Math.sin(y) * Math.cos(p), -Math.sin(p), Math.cos(y) * Math.cos(p)};
        double[] right = {-Math.cos(y), 0, -Math.sin(y)};
        return new double[][]{right, cross(right, forward), forward};
    }
    /** Back-wall point under a pixel position (top-left origin, pixel centres at +0.5); null if that ray does not end on
     * the interior back-wall face. */
    static double[] wallPoint(double px, double py, double[] eye, float yaw, float pitch, double fov, int width, int height) {
        double[][] b = basis(yaw, pitch);
        double tan = Math.tan(Math.toRadians(fov) / 2), nx = px / width * 2 - 1, ny = 1 - py / height * 2;
        double[] d = new double[3];
        for (int i = 0; i < 3; i++) d[i] = b[2][i] + nx * tan * width / height * b[0][i] + ny * tan * b[1][i];
        if (d[2] >= -1e-9) return null;
        double s = (RECEIVER_PLANE_Z - eye[2]) / d[2];
        double[] p = {eye[0] + s * d[0], eye[1] + s * d[1], RECEIVER_PLANE_Z};
        return p[0] > SHELL_X0 + 1 && p[0] < SHELL_X1 && p[1] > SHELL_Y0 + 1 && p[1] < SHELL_Y1 ? p : null;
    }

    /** What a receiver ROI must show. SHADOW: all three main-hand taps blocked; OPEN_OFF: all three off-hand taps open. */
    enum Need { SHADOW_MAIN_OPEN_OFF, SHADOW_MAIN, LIT_MAIN, LIT_MAIN_AND_OFF }
    /** A fixed 9x9 pixel block at 2560x1440 centred on pixel (column,row): columns column-4..column+4, rows row-4..row+4. */
    record Roi(String name, Pillar pillar, int column, int row, Need need, String purpose) {
        int x0() { return column - ROI_SIZE / 2; } int x1() { return column + ROI_SIZE / 2; }
        int y0() { return row - ROI_SIZE / 2; } int y1() { return row + ROI_SIZE / 2; }
    }
    /** Centres chosen as the column whose 9x9 block holds for the largest isotropic eye error (Chebyshev centre in pose). */
    static final List<Roi> ROIS = List.of(
        new Roi("hand-hidden-shadow-wall", Pillar.HIDDEN, 1434, 720, Need.SHADOW_MAIN_OPEN_OFF,
            "lamp-hand-hidden/-off/-empty: camera-visible wall strip west of the east pillar's shadow edge, blocked from every main-hand tap, open to every off-hand tap"),
        new Roi("hand-hidden-lit-wall", Pillar.HIDDEN, 982, 720, Need.LIT_MAIN_AND_OFF,
            "lamp-hand-hidden control: same wall and row, lit by every tap of both hands"),
        new Roi("hand-front-shadow-wall", Pillar.FRONT, 892, 720, Need.SHADOW_MAIN,
            "lamp-hand-pillar/-empty: camera-visible wall west of the front pillar, blocked from every main-hand tap"),
        new Roi("hand-front-lit-wall", Pillar.FRONT, 1758, 720, Need.LIT_MAIN,
            "lamp-hand-pillar control: same wall and row east of the pillar, lit by every main-hand tap"));
    static Roi roi(String name) { return ROIS.stream().filter(r -> r.name().equals(name)).findFirst().orElse(null); }
    static String pillarScene(Pillar pillar) {
        return switch (pillar) { case NONE -> "lamp-hand-main"; case FRONT -> "lamp-hand-pillar"; case HIDDEN -> "lamp-hand-hidden"; };
    }
    static double[] roiCentre(Roi roi) {
        return wallPoint(roi.column() + .5, roi.row() + .5, new double[]{EYE_X, EYE_Y, EYE_Z}, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT);
    }
    /** First violation of the ROI's need at a pose, or null when all 81 pixels satisfy it. need/pillar may be overridden
     * (open-room control: the shadow ROIs evaluated without a pillar must be lit). */
    static String roiViolation(Roi roi, Pillar pillar, Need need, double[] eye, float yaw, float pitch, double fov, int width, int height, int dColumn, int dRow) {
        var grid = LocalLightFixture.grid(LocalLightFixture.parse(pillarScene(pillar)));
        double[] main = vec(handOrigin(true, eye[0], eye[1], eye[2], yaw, pitch)), off = vec(handOrigin(false, eye[0], eye[1], eye[2], yaw, pitch));
        for (int px = roi.x0() + dColumn; px <= roi.x1() + dColumn; px++) for (int py = roi.y0() + dRow; py <= roi.y1() + dRow; py++) {
            double[] p = wallPoint(px + .5, py + .5, eye, yaw, pitch, fov, width, height);
            if (p == null) return "pixel " + px + "," + py + " not on the back wall";
            if (!shaderClear(grid, eye, p)) return "pixel " + px + "," + py + " hidden from the camera";
            boolean[] m = tapsOpen(grid, p, main);
            boolean shadow = need == Need.SHADOW_MAIN || need == Need.SHADOW_MAIN_OPEN_OFF;
            for (int k = 0; k < 3; k++) if (m[k] == shadow) return "pixel " + px + "," + py + " main tap " + k + (shadow ? " open" : " blocked");
            if (need == Need.SHADOW_MAIN_OPEN_OFF || need == Need.LIT_MAIN_AND_OFF) {
                boolean[] o = tapsOpen(grid, p, off);
                for (int k = 0; k < 3; k++) if (!o[k]) return "pixel " + px + "," + py + " off tap " + k + " blocked";
            }
        }
        return null;
    }
    static String roiViolation(Roi roi, double[] eye) {
        return roiViolation(roi, roi.pillar(), roi.need(), eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT, 0, 0);
    }
    /** Corners and face centres of the eye box +-delta (27 poses). */
    static List<double[]> poseBox(double delta) {
        List<double[]> eyes = new ArrayList<>();
        for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++) for (int c = -1; c <= 1; c++)
            eyes.add(new double[]{EYE_X + a * delta, EYE_Y + b * delta, EYE_Z + c * delta});
        return eyes;
    }
    static boolean roiHoldsInBox(Roi roi, double delta) {
        for (double[] eye : poseBox(delta)) if (roiViolation(roi, eye) != null) return false;
        return true;
    }
    /** Largest isotropic eye error (m, 0.5 mm resolution) under which the fixed ROI still holds. */
    static double provenPoseTolerance(Roi roi) {
        double lo = 0, hi = .25;
        if (!roiHoldsInBox(roi, 0)) return -1;
        while (hi - lo > .0005) { double mid = (lo + hi) / 2; if (roiHoldsInBox(roi, mid)) lo = mid; else hi = mid; }
        return Math.floor(lo * 2000) / 2000;
    }
    /** Largest symmetric yaw (pitch=false) or pitch rotation error (degrees, 0.01 resolution, capped at 10) the fixed ROI
     * tolerates at the requested eye; the hand anchors rotate with the camera as in the shader. */
    static double provenRotationTolerance(Roi roi, boolean pitch) {
        double[] eye = {EYE_X, EYE_Y, EYE_Z};
        double lo = 0, hi = 10;
        java.util.function.DoublePredicate holds = d -> {
            for (double s : new double[]{-d, d}) {
                float yaw = (float)(YAW + (pitch ? 0 : s)), p = (float)(PITCH + (pitch ? s : 0));
                if (roiViolation(roi, roi.pillar(), roi.need(), eye, yaw, p, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT, 0, 0) != null) return false;
            }
            return true;
        };
        if (holds.test(hi)) return hi;
        while (hi - lo > .01) { double mid = (lo + hi) / 2; if (holds.test(mid)) lo = mid; else hi = mid; }
        return Math.floor(lo * 100) / 100;
    }
    /** Whole-pixel shifts of the 9x9 block (left, right, up, down) that still hold at the requested pose. */
    static int[] pixelMargins(Roi roi) {
        double[] eye = {EYE_X, EYE_Y, EYE_Z};
        int[] result = new int[4];
        int[][] dirs = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
        for (int d = 0; d < 4; d++) {
            int n = 0;
            while (n < 400 && roiViolation(roi, roi.pillar(), roi.need(), eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT, dirs[d][0] * (n + 1), dirs[d][1] * (n + 1)) == null) n++;
            result[d] = n;
        }
        return result;
    }
    /** Per tap: the smallest world-x displacement (m, either sign) of that tap that changes its state at any ROI pixel;
     * the string "&gt;0.5" when no displacement up to 0.5 m changes it. */
    static Map<String, Object> tapMargins(Roi roi) {
        var grid = LocalLightFixture.grid(LocalLightFixture.parse(pillarScene(roi.pillar())));
        double[] eye = {EYE_X, EYE_Y, EYE_Z};
        Map<String, Object> result = new LinkedHashMap<>();
        boolean withOff = roi.need() == Need.SHADOW_MAIN_OPEN_OFF || roi.need() == Need.LIT_MAIN_AND_OFF;
        for (boolean mainHand : withOff ? new boolean[]{true, false} : new boolean[]{true}) {
            double[] lamp = vec(handOrigin(mainHand, EYE_X, EYE_Y, EYE_Z, YAW, PITCH));
            for (int k = 0; k < 3; k++) {
                double best = Double.POSITIVE_INFINITY;
                for (int px = roi.x0(); px <= roi.x1(); px++) for (int py = roi.y0(); py <= roi.y1(); py++) {
                    double[] p = wallPoint(px + .5, py + .5, eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT);
                    double[] start = {p[0], p[1], p[2] + RECEIVER_NORMAL_OFFSET}, tap = emitterTaps(p, lamp).get(k);
                    boolean state = shaderClear(grid, start, tap);
                    for (double sign : new double[]{-1, 1}) {
                        double lo = 0, hi = .5;
                        if (shaderClear(grid, start, new double[]{tap[0] + sign * hi, tap[1], tap[2]}) == state) continue;
                        while (hi - lo > 1e-5) {
                            double mid = (lo + hi) / 2;
                            if (shaderClear(grid, start, new double[]{tap[0] + sign * mid, tap[1], tap[2]}) == state) lo = mid; else hi = mid;
                        }
                        best = Math.min(best, lo);
                    }
                }
                result.put((mainHand ? "main" : "off") + "_tap" + k + "_x_margin_m", Double.isInfinite(best) ? ">0.5" : (Object)(Math.round(best * 1e5) / 1e5));
            }
        }
        return result;
    }
    private static List<Double> round(double[] p) {
        return List.of(Math.round(p[0] * 1e5) / 1e5, Math.round(p[1] * 1e5) / 1e5, Math.round(p[2] * 1e5) / 1e5);
    }
    /** Full CPU geometry report of one ROI at the requested pose (world coordinates, pixels, taps, margins). */
    static Map<String, Object> roiReport(Roi roi) {
        double[] eye = {EYE_X, EYE_Y, EYE_Z}, centre = roiCentre(roi);
        double[] main = vec(handOrigin(true)), off = vec(handOrigin(false));
        Map<String, Object> taps = new LinkedHashMap<>();
        for (boolean mainHand : new boolean[]{true, false}) {
            List<double[]> t = emitterTaps(centre, mainHand ? main : off);
            taps.put(mainHand ? "main" : "off", List.of(round(t.get(0)), round(t.get(1)), round(t.get(2))));
        }
        double[] cornerA = wallPoint(roi.x0(), roi.y0(), eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT);
        double[] cornerB = wallPoint(roi.x1() + 1, roi.y1() + 1, eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT);
        int[] margins = pixelMargins(roi);
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("scene_geometry", pillarScene(roi.pillar()));
        report.put("need", roi.need().name().toLowerCase(Locale.ROOT));
        report.put("purpose", roi.purpose());
        report.put("frame", List.of(FRAME_WIDTH, FRAME_HEIGHT));
        report.put("vertical_fov_degrees", FOV_DEGREES);
        report.put("pixel_centre", List.of(roi.column() + .5, roi.row() + .5));
        report.put("pixel_rect_inclusive_x0_y0_x1_y1", List.of(roi.x0(), roi.y0(), roi.x1(), roi.y1()));
        report.put("world_centre", round(centre));
        report.put("world_rect_x", List.of(Math.round(cornerA[0] * 1e5) / 1e5, Math.round(cornerB[0] * 1e5) / 1e5));
        report.put("world_rect_y", List.of(Math.round(cornerB[1] * 1e5) / 1e5, Math.round(cornerA[1] * 1e5) / 1e5));
        report.put("world_plane_z", RECEIVER_PLANE_Z);
        report.put("emitter_taps_at_centre", taps);
        report.put("pixel_margins_left_right_up_down_capped_400", List.of(margins[0], margins[1], margins[2], margins[3]));
        report.put("proven_isotropic_eye_tolerance_m", provenPoseTolerance(roi));
        report.put("proven_yaw_tolerance_deg", provenRotationTolerance(roi, false));
        report.put("proven_pitch_tolerance_deg_capped_10", provenRotationTolerance(roi, true));
        report.put("tap_x_margins_m", tapMargins(roi));
        String open = roi.need() == Need.SHADOW_MAIN || roi.need() == Need.SHADOW_MAIN_OPEN_OFF
            ? roiViolation(roi, Pillar.NONE, roi.need() == Need.SHADOW_MAIN ? Need.LIT_MAIN : Need.LIT_MAIN_AND_OFF, eye, YAW, PITCH, FOV_DEGREES, FRAME_WIDTH, FRAME_HEIGHT, 0, 0)
            : null;
        report.put("open_room_control_lit", open == null);
        report.put("requested_pose_violation", Objects.requireNonNullElse(roiViolation(roi, eye), "none"));
        return report;
    }
    private static volatile Map<String, Object> roiReports;
    /** Memoized reports of all ROIs (pose-independent: evaluated at the requested pose and its tolerance box). */
    static Map<String, Object> roiReports() {
        Map<String, Object> cached = roiReports;
        if (cached != null) return cached;
        Map<String, Object> result = new LinkedHashMap<>();
        for (Roi roi : ROIS) result.put(roi.name(), roiReport(roi));
        roiReports = Collections.unmodifiableMap(result);
        return roiReports;
    }
    /** ROIs whose geometry matches a scene: its own pillar ROIs, or (open room) the shadow ROIs as lit controls. */
    static List<Roi> roisFor(Spec spec) {
        if (spec.pillar() == Pillar.NONE) return ROIS.stream().filter(r -> r.need() == Need.SHADOW_MAIN || r.need() == Need.SHADOW_MAIN_OPEN_OFF).toList();
        return ROIS.stream().filter(r -> r.pillar() == spec.pillar()).toList();
    }
    static Need needIn(Roi roi, Spec spec) {
        if (spec.pillar() == roi.pillar()) return roi.need();
        return roi.need() == Need.SHADOW_MAIN ? Need.LIT_MAIN : Need.LIT_MAIN_AND_OFF;
    }
    /** ROI evaluation at an actual rendered pose (eye, yaw, pitch, FOV, frame). Map name -> "ok" or violation text. */
    static Map<String, String> roisAtPose(Spec spec, double[] eye, float yaw, float pitch, double fov, int width, int height) {
        Map<String, String> result = new LinkedHashMap<>();
        for (Roi roi : roisFor(spec)) {
            String violation = width != FRAME_WIDTH || height != FRAME_HEIGHT ? "not applicable at " + width + "x" + height
                : roiViolation(roi, spec.pillar(), needIn(roi, spec), eye, yaw, pitch, fov, width, height, 0, 0);
            result.put(roi.name(), violation == null ? "ok" : violation);
        }
        return result;
    }

    // ---- Private duplicated TEST game identity (required before any carried-light world change or equip).
    static final String TEST_USERNAME = "AqualumenOptics";
    static final String LAB_INSTANCE = "Aqualumen Lab", GAME_FOLDER = "minecraft";
    static final String MATRIX_PATTERN = "carried-matrix-[A-Za-z0-9][A-Za-z0-9_-]{5,63}";
    static final String OPT_IN_KEY = "carried_light_test", OPT_IN_VALUE = "private-duplicate-v1",
        OPT_IN_GAME = "carried_light_test_game", OPT_IN_ORIGINAL = "carried_light_original_game";
    record TestGame(java.nio.file.Path game, java.nio.file.Path original, java.nio.file.Path instance, String matrix) {}
    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException("Carried-light TEST game guard: " + message);
    }
    private static boolean realDirectory(java.nio.file.Path path) {
        return java.nio.file.Files.isDirectory(path, java.nio.file.LinkOption.NOFOLLOW_LINKS) && !java.nio.file.Files.isSymbolicLink(path);
    }
    /** No component of an absolute path may be a symbolic link. */
    private static boolean symlinkFree(java.nio.file.Path absolute) throws java.io.IOException {
        java.nio.file.Path walk = absolute.getRoot();
        for (java.nio.file.Path part : absolute) {
            walk = walk.resolve(part);
            if (java.nio.file.Files.isSymbolicLink(walk)) return false;
        }
        return absolute.toRealPath().equals(absolute);
    }
    /** A copied (not hard-linked) regular file. Region files are rewritten in place, so a shared inode would alter the original. */
    private static void requireUnshared(java.nio.file.Path file) throws java.io.IOException {
        require(!java.nio.file.Files.isSymbolicLink(file), "symbolic link inside the TEST world: " + file);
        if (!java.nio.file.Files.isRegularFile(file, java.nio.file.LinkOption.NOFOLLOW_LINKS)) return;
        Object links = java.nio.file.Files.getAttribute(file, "unix:nlink", java.nio.file.LinkOption.NOFOLLOW_LINKS);
        require(links instanceof Integer n && n == 1, "hard-linked file shared with another path: " + file + " nlink=" + links);
    }
    /**
     * Independently identifies the private duplicate created by the carried-light runner:
     * &lt;instance "Aqualumen Lab"&gt;/carried-matrix-&lt;random&gt;/Aqualumen Lab/minecraft, distinct from the untouched original
     * &lt;instance&gt;/minecraft. Requires the explicit request opt-in naming exactly this game and that original, the
     * AqualumenOptics session and server profile, and a symlink-free, non-hard-linked TEST world. Throws on any violation.
     */
    static TestGame privateTestGame(java.nio.file.Path rawGameDir, String sessionName, String profileName,
                                    Map<String, String> request, String worldFolder) throws java.io.IOException {
        require(request != null && OPT_IN_VALUE.equals(request.get(OPT_IN_KEY)), "explicit request opt-in " + OPT_IN_KEY + "=" + OPT_IN_VALUE + " missing");
        require(rawGameDir != null, "no game directory");
        java.nio.file.Path game = rawGameDir.toAbsolutePath().normalize();
        require(java.nio.file.Files.exists(game, java.nio.file.LinkOption.NOFOLLOW_LINKS) && symlinkFree(game), "game path is missing or crosses a symbolic link: " + rawGameDir);
        java.nio.file.Path lab = game.getParent(), matrix = lab == null ? null : lab.getParent(), instance = matrix == null ? null : matrix.getParent();
        require(instance != null && game.getFileName().toString().equals(GAME_FOLDER) && lab.getFileName().toString().equals(LAB_INSTANCE) &&
            matrix.getFileName().toString().matches(MATRIX_PATTERN) && instance.getFileName().toString().equals(LAB_INSTANCE),
            "game is not <Aqualumen Lab instance>/carried-matrix-<random>/Aqualumen Lab/minecraft: " + game);
        for (java.nio.file.Path dir : List.of(game, lab, matrix, instance)) require(realDirectory(dir), "not a real directory: " + dir);
        java.nio.file.Path original = instance.resolve(GAME_FOLDER);
        require(realDirectory(original) && original.toRealPath().equals(original), "untouched original game not found as a real directory: " + original);
        require(!java.nio.file.Files.isSameFile(original, game) && !game.startsWith(original) && !original.startsWith(game), "TEST game is the original game");
        require(game.toString().equals(request.get(OPT_IN_GAME)), "opt-in names a different TEST game: " + request.get(OPT_IN_GAME));
        require(original.toString().equals(request.get(OPT_IN_ORIGINAL)), "opt-in names a different original game: " + request.get(OPT_IN_ORIGINAL));
        require(TEST_USERNAME.equals(sessionName) && TEST_USERNAME.equals(profileName), "player must be " + TEST_USERNAME + " (session " + sessionName + ", profile " + profileName + ")");
        require(worldFolder != null && worldFolder.matches("AqualumenNatural[A-Za-z0-9_.-]*"), "unexpected world folder " + worldFolder);
        java.nio.file.Path saves = game.resolve("saves"), world = saves.resolve(worldFolder);
        require(realDirectory(saves) && realDirectory(world) && world.toRealPath().equals(world), "TEST world is missing or a symbolic link: " + world);
        java.nio.file.Path originalWorld = original.resolve("saves").resolve(worldFolder);
        if (java.nio.file.Files.exists(originalWorld)) require(!java.nio.file.Files.isSameFile(originalWorld, world), "TEST world is the original world");
        requireUnshared(world.resolve("level.dat"));
        requireUnshared(world.resolve("aqualumen-world.properties"));
        for (String sub : List.of("region", "entities", "poi", "playerdata", "data")) {
            java.nio.file.Path dir = world.resolve(sub);
            if (!java.nio.file.Files.exists(dir, java.nio.file.LinkOption.NOFOLLOW_LINKS)) continue;
            require(realDirectory(dir), "TEST world subdirectory is a symbolic link: " + dir);
            try (var files = java.nio.file.Files.list(dir)) { for (java.nio.file.Path file : files.toList()) requireUnshared(file); }
        }
        return new TestGame(game, original, instance, matrix.getFileName().toString());
    }

    // ---- Equipment, inventory and cleanup decisions (pure; the Recorder applies them on the server thread).
    enum SlotCleanup { CLEAR, ALREADY_EMPTY, CONFLICT }
    /** Only a single fixture lamp item is ever removed; anything else is preserved and reported. */
    static SlotCleanup slotCleanup(String actualId, int count) {
        if (actualId == null) return SlotCleanup.CONFLICT;
        if (actualId.equals(EMPTY)) return SlotCleanup.ALREADY_EMPTY;
        return FIXTURE_ITEMS.contains(actualId) && count == 1 ? SlotCleanup.CLEAR : SlotCleanup.CONFLICT;
    }
    /** A slot may be (re)written by the fixture only while it is empty or holds one of its own single lamp items. */
    static boolean slotWritable(String actualId, int count) { return slotCleanup(actualId, count) != SlotCleanup.CONFLICT; }
    static boolean slotMatches(String expected, String actualId, int count) {
        return expected.equals(EMPTY) ? EMPTY.equals(actualId) && count == 0 : expected.equals(actualId) && count == 1;
    }
    static boolean equipMatches(Equip expected, String main, int mainCount, String off, int offCount) {
        return slotMatches(expected.main(), main, mainCount) && slotMatches(expected.off(), off, offCount);
    }
    /** The disposable driver must start (and end) with a completely empty 41-slot inventory. */
    static List<String> inventoryViolations(List<String> slotIds) {
        List<String> result = new ArrayList<>();
        if (slotIds == null || slotIds.size() != INVENTORY_SLOTS) {
            result.add("inventory size " + (slotIds == null ? "null" : slotIds.size()) + " != " + INVENTORY_SLOTS);
            return result;
        }
        for (int i = 0; i < slotIds.size(); i++) if (!EMPTY.equals(slotIds.get(i))) result.add("slot " + i + "=" + slotIds.get(i));
        return result;
    }
    /** After equipping: only the selected hotbar slot (main hand) and slot 40 (off hand) may hold the expected lamp. */
    static List<String> inventoryViolations(List<String> slotIds, int selectedSlot, Equip equip) {
        List<String> result = new ArrayList<>();
        if (slotIds == null || slotIds.size() != INVENTORY_SLOTS || selectedSlot < 0 || selectedSlot > 8) {
            result.add("inventory size " + (slotIds == null ? "null" : slotIds.size()) + " or selected slot " + selectedSlot + " invalid");
            return result;
        }
        for (int i = 0; i < slotIds.size(); i++) {
            String expected = i == selectedSlot ? equip.main() : i == INVENTORY_SLOTS - 1 ? equip.off() : EMPTY;
            if (!expected.equals(slotIds.get(i))) result.add("slot " + i + "=" + slotIds.get(i) + " (expected " + expected + ")");
        }
        return result;
    }
    static String equipCommand(String target, String slot, String item) {
        if (!slot.equals(MAIN_SLOT) && !slot.equals(OFF_SLOT)) throw new IllegalArgumentException(slot);
        if (!item.equals(EMPTY) && !FIXTURE_ITEMS.contains(item)) throw new IllegalArgumentException(item);
        return "item replace entity " + target + " " + slot + " with " + item;
    }
    /** Conditional on the actual item at execution time, like the block fixture's `execute if block`. */
    static String clearCommand(String target, String slot, String actualItem) {
        if (!FIXTURE_ITEMS.contains(actualItem)) throw new IllegalArgumentException(actualItem);
        return "execute if items entity " + target + " " + slot + " " + actualItem + " run item replace entity " + target + " " + slot + " with " + EMPTY;
    }

    // ---- Recipe book and advancement-criterion restoration (inventory_changed unlocks recipes when a torch enters).
    /** recipes: unlocked recipe ids; criteria: "advancement_id criterion" of every obtained criterion. */
    record Progress(Set<String> recipes, Set<String> criteria) {
        Progress { recipes = Collections.unmodifiableSet(new TreeSet<>(recipes)); criteria = Collections.unmodifiableSet(new TreeSet<>(criteria)); }
    }
    record Restore(List<String> takeRecipes, List<String> revokeCriteria, List<String> lostRecipes, List<String> lostCriteria) {
        boolean noop() { return takeRecipes.isEmpty() && revokeCriteria.isEmpty(); }
        boolean lossless() { return lostRecipes.isEmpty() && lostCriteria.isEmpty(); }
    }
    static Restore restore(Progress baseline, Progress current) {
        List<String> take = new ArrayList<>(), revoke = new ArrayList<>(), lostRecipes = new ArrayList<>(), lostCriteria = new ArrayList<>();
        for (String id : current.recipes()) if (!baseline.recipes().contains(id)) take.add(id);
        for (String id : current.criteria()) if (!baseline.criteria().contains(id)) revoke.add(id);
        for (String id : baseline.recipes()) if (!current.recipes().contains(id)) lostRecipes.add(id);
        for (String id : baseline.criteria()) if (!current.criteria().contains(id)) lostCriteria.add(id);
        return new Restore(List.copyOf(take), List.copyOf(revoke), List.copyOf(lostRecipes), List.copyOf(lostCriteria));
    }
    static String criterionKey(String advancement, String criterion) { return advancement + " " + criterion; }
    /** Recipes first (no criteria involved), then each newly obtained criterion individually. Ids are validated. */
    static List<String> restoreCommands(Restore restore, String target) {
        List<String> commands = new ArrayList<>();
        for (String recipe : restore.takeRecipes()) {
            if (!recipe.matches("[a-z0-9_.-]+:[a-z0-9_./-]+")) throw new IllegalArgumentException("Unexpected recipe id " + recipe);
            commands.add("recipe take " + target + " " + recipe);
        }
        for (String key : restore.revokeCriteria()) {
            int space = key.indexOf(' ');
            String advancement = space < 0 ? "" : key.substring(0, space), criterion = space < 0 ? "" : key.substring(space + 1);
            if (!advancement.matches("[a-z0-9_.-]+:[a-z0-9_./-]+") || !criterion.matches("[A-Za-z0-9_.:/-]+"))
                throw new IllegalArgumentException("Unexpected advancement criterion " + key);
            commands.add("advancement revoke " + target + " only " + advancement + " " + criterion);
        }
        return commands;
    }

    // ---- Pose.
    static boolean finite(double[] values, int length) {
        if (values == null || values.length != length) return false;
        for (double value : values) if (!Double.isFinite(value)) return false;
        return true;
    }
    /** Identified player feet, its measured eye and the rendered Camera at the requested eye x (fixed y/z).
     * tolerance bounds x only (tick-stepped walk lag); while walking the tick-interpolated Camera may trail the current
     * eye by up to one tick of travel along x, never in y/z. */
    static boolean poseMatches(double expectedEyeX, double tolerance, boolean firstPerson, double[] player, double[] eye, double[] camera) {
        if (!firstPerson || !finite(player, 3) || !finite(eye, 3) || !finite(camera, 3) || !(tolerance >= EYE_TOLERANCE)) return false;
        double feet = EYE_Y - LocalLightFixture.EYE_HEIGHT;
        return Math.abs(player[0] - expectedEyeX) <= tolerance && Math.abs(player[1] - feet) <= EYE_TOLERANCE && Math.abs(player[2] - EYE_Z) <= EYE_TOLERANCE &&
            Math.abs(eye[0] - expectedEyeX) <= tolerance && Math.abs(eye[1] - EYE_Y) <= EYE_TOLERANCE && Math.abs(eye[2] - EYE_Z) <= EYE_TOLERANCE &&
            Math.abs(camera[0] - expectedEyeX) <= tolerance && Math.abs(camera[0] - eye[0]) <= tolerance &&
            Math.abs(camera[1] - eye[1]) <= EYE_TOLERANCE && Math.abs(camera[2] - eye[2]) <= EYE_TOLERANCE;
    }
    static double trackTolerance(Spec spec) { return spec.walking() ? TRACK_TOLERANCE : EYE_TOLERANCE; }
    /** Body box of the standing driver (0.6 x 1.8) at eye x: only interior AIR cells, never a placed cell or pillar. */
    static boolean bodyClear(LocalLightFixture.Plan plan, double eyeX) {
        Map<List<Integer>, LocalLightFixture.Cell> cells = LocalLightFixture.grid(plan);
        double feet = EYE_Y - LocalLightFixture.EYE_HEIGHT, half = LocalLightFixture.PLAYER_HALF_WIDTH;
        for (int x = (int)Math.floor(eyeX - half); x <= (int)Math.floor(eyeX + half); x++)
            for (int y = (int)Math.floor(feet); y <= (int)Math.floor(feet + LocalLightFixture.PLAYER_HEIGHT - 1e-9); y++)
                for (int z = (int)Math.floor(EYE_Z - half); z <= (int)Math.floor(EYE_Z + half); z++)
                    if (!interior(x, y, z) || cells.containsKey(List.of(x, y, z))) return false;
        return true;
    }

    static final String TRACE_HEADER = "elapsed_ns,client_world_time,step,expected_eye_x,expected_eye_y,expected_eye_z,player_x,player_y,player_z," +
        "camera_x,camera_y,camera_z,camera_yaw,camera_pitch,expected_main,expected_off,actual_main,actual_main_count,actual_off,actual_off_count," +
        "selected_slot,renderer_main,renderer_off,equip_main,equip_off,client_game_mode,first_person,flying,pose_ok,items_ok\n";
    static final String SWAP_HEADER = "step,scheduled_ns,expected_main,expected_off,issued_ns,server_applied_ns,client_observed_ns,renderer_observed_ns,renderer_settled_ns,client_latency_ms\n";
    static final List<String> SWAP_KEYS = List.of("step", "scheduled_ns", "expected_main", "expected_off", "issued_ns", "server_applied_ns",
        "client_observed_ns", "renderer_observed_ns", "renderer_settled_ns", "client_latency_ms");

    /** One 25 Hz trace row matching TRACE_HEADER (timestamped pose, expected and actual items, rendered hands). */
    static String traceRow(long elapsedNs, long worldTime, int step, double expectedEyeX, double[] player, double[] camera, float yaw, float pitch,
                           Equip expected, String main, int mainCount, String off, int offCount, int selected, String rendererMain, String rendererOff,
                           float equipMain, float equipOff, String gameMode, boolean firstPerson, boolean flying, boolean poseOk, boolean itemsOk) {
        return String.format(Locale.ROOT, "%d,%d,%d,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.3f,%.3f,%s,%s,%s,%d,%s,%d,%d,%s,%s,%.4f,%.4f,%s,%s,%s,%s,%s%n",
            elapsedNs, worldTime, step, expectedEyeX, EYE_Y, EYE_Z, player[0], player[1], player[2], camera[0], camera[1], camera[2], yaw, pitch,
            expected.main(), expected.off(), main, mainCount, off, offCount, selected, rendererMain, rendererOff, equipMain, equipOff,
            gameMode, firstPerson, flying, poseOk, itemsOk);
    }
    static String swapCsv(List<Map<String, Object>> rows) {
        StringBuilder csv = new StringBuilder(SWAP_HEADER);
        for (Map<String, Object> row : rows) {
            StringJoiner line = new StringJoiner(",");
            for (String key : SWAP_KEYS) line.add(row.get(key) == null ? "" : String.valueOf(row.get(key)));
            csv.append(line).append('\n');
        }
        return csv.toString();
    }
}
