package dev.aqualumen.bench;

import java.nio.file.*;
import java.util.*;

/** CPU-only checks of the carried-light (lamp-hand-*) fixture: geometry, pose, equipment, cleanup and recipe restoration. */
public final class HandLightFixtureTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static final String T = HandLightFixture.TORCH, S = HandLightFixture.SOUL, E = HandLightFixture.EMPTY;

    public static void main(String[] args) throws Exception {
        scenes();
        geometry();
        pose();
        equipment();
        restoredEmptySlot();
        recipes();
        evidenceFormats();
        testGameGuard();
        printTable();
        System.out.println("Hand-light fixture regressions passed (" + HandLightFixture.SCENES.size() + " scenes)");
    }

    private static void scenes() {
        check(HandLightFixture.SCENES.size() == 13 && HandLightFixture.SCENES.stream().allMatch(s -> s.startsWith("lamp-hand-")), "13 lamp-hand scenes");
        check(new HashSet<>(HandLightFixture.SCENES).size() == 13 && Collections.disjoint(HandLightFixture.SCENES, LocalLightFixture.SCENES), "Unique, distinct from lamp-day/night");
        for (String bad : new String[]{"lamp-hand", "lamp-hand-", "lamp-hand-red", "lamp-hand-main-off", "lamp-hand-walk-west", null})
            check(LocalLightFixture.parse(bad) == null && HandLightFixture.spec(bad) == null, "Unreviewed key rejected: " + bad);
        // The original 18 lamp scenes are unchanged by the generalized Plan.
        for (String scene : LocalLightFixture.SCENES) {
            var plan = LocalLightFixture.parse(scene);
            check(plan.hand() == null && plan.yaw() == LocalLightFixture.YAW && plan.pitch() == LocalLightFixture.PITCH &&
                plan.eyeY() == LocalLightFixture.EYE_Y && plan.eyeZ() == LocalLightFixture.EYE_Z &&
                Math.abs(plan.playerY() - 155.38) < 1e-9 && LocalLightFixture.samples(plan).equals(LocalLightFixture.samples()), "Original plan unchanged " + scene);
        }
        Map<String, HandLightFixture.Equip> fixed = Map.of("lamp-hand-empty", HandLightFixture.NONE, "lamp-hand-main", HandLightFixture.MAIN_TORCH,
            "lamp-hand-off", HandLightFixture.OFF_TORCH, "lamp-hand-soul", HandLightFixture.MAIN_SOUL, "lamp-hand-both", HandLightFixture.TORCH_AND_SOUL,
            "lamp-hand-pillar", HandLightFixture.MAIN_TORCH, "lamp-hand-pillar-empty", HandLightFixture.NONE, "lamp-hand-hidden", HandLightFixture.MAIN_TORCH,
            "lamp-hand-hidden-off", HandLightFixture.OFF_TORCH, "lamp-hand-hidden-empty", HandLightFixture.NONE);
        fixed.forEach((scene, equip) -> {
            var spec = HandLightFixture.spec(scene);
            check(!spec.walking() && !spec.sequence() && !spec.needsLongSample() && spec.initial().equals(equip) && spec.last().equals(equip), "Fixed equip " + scene);
        });
        check(HandLightFixture.MAIN_TORCH.equals(new HandLightFixture.Equip(T, E)) && HandLightFixture.OFF_TORCH.equals(new HandLightFixture.Equip(E, T)) &&
            HandLightFixture.MAIN_SOUL.equals(new HandLightFixture.Equip(S, E)) && HandLightFixture.TORCH_AND_SOUL.equals(new HandLightFixture.Equip(T, S)),
            "Warm main, same source off, soul, warm+soul");
        var walk = HandLightFixture.spec("lamp-hand-walk");
        check(walk.walking() && walk.needsLongSample() && walk.last().equals(HandLightFixture.MAIN_TORCH) &&
            HandLightFixture.spec("lamp-hand-walk-empty").last().empty(), "Walk carries the torch; walk-empty control");
        var putaway = HandLightFixture.spec("lamp-hand-putaway");
        check(putaway.sequence() && !putaway.walking() && putaway.initial().equals(HandLightFixture.MAIN_TORCH) && putaway.last().empty(), "Put-away ends empty");
        check(putaway.equipAt(0).equals(HandLightFixture.MAIN_TORCH) && putaway.equipAt(1.999).equals(HandLightFixture.MAIN_TORCH) &&
            putaway.equipAt(2).empty() && putaway.equipAt(4.5).equals(HandLightFixture.MAIN_SOUL) && putaway.equipAt(6).empty() &&
            putaway.equipAt(60).empty() && putaway.stepAt(-1) == 0 && putaway.stepAt(7) == 3, "Swap schedule");
        double lastStep = putaway.steps().getLast().atSeconds();
        check(lastStep + 1 + HandLightFixture.SWAP_GRACE_SECONDS <= HandLightFixture.MIN_SEQUENCE_SAMPLE_SECONDS + 1e-9 &&
            HandLightFixture.ROUTE_SECONDS + 1 <= HandLightFixture.MIN_SEQUENCE_SAMPLE_SECONDS + 1e-9, "Sequences settle before a 9 s capture");
        for (int i = 1; i < putaway.steps().size(); i++) {
            var previous = putaway.steps().get(i - 1).equip(); var next = putaway.steps().get(i).equip();
            check(!previous.equals(next) && putaway.steps().get(i).atSeconds() - putaway.steps().get(i - 1).atSeconds() > HandLightFixture.SWAP_GRACE_SECONDS,
                "Every step is a real swap longer than the observation grace");
        }
        for (String scene : HandLightFixture.SCENES) {
            var plan = LocalLightFixture.parse(scene);
            check(plan != null && plan.hand() == HandLightFixture.spec(scene) && plan == LocalLightFixture.parse(scene), "Memoized hand plan " + scene);
            check(plan.lamps().isEmpty() && !plan.walking() && !plan.moving() && plan.divider() == null && plan.timeOfDay() == 18000, "No placed emitter, frozen night");
            check(plan.yaw() == 180 && plan.pitch() == 0 && plan.eye().equals(List.of(406.65, 152.62, -407.0)) && Math.abs(plan.playerY() - 151.0) < 1e-9,
                "Matched first-person pose " + scene);
        }
    }

    private static void geometry() {
        Set<List<Integer>> otherPlots = new HashSet<>();
        for (String scene : new String[]{"opaque-near-magenta", "opaque-far-magenta", "air-shadow-backlit", "ground-noon"})
            for (var cell : OcclusionFixture.parse(scene).reserved()) otherPlots.add(List.of(cell.x(), cell.y(), cell.z()));
        var open = LocalLightFixture.parse("lamp-hand-main");
        for (String scene : HandLightFixture.SCENES) {
            var plan = LocalLightFixture.parse(scene);
            var grid = LocalLightFixture.grid(plan);
            Set<List<Integer>> unique = new HashSet<>();
            for (var cell : plan.placements()) {
                check(unique.add(cell.position()), "No duplicate journal entry " + cell);
                check(LocalLightFixture.inBox(cell.x(), cell.y(), cell.z()) && !otherPlots.contains(cell.position()), "Inside reserved box only " + cell);
                check(LocalLightFixture.opaque(cell) && cell.properties().isEmpty() && cell.state().equals(cell.id()), "Plain opaque full blocks " + cell);
                check(LocalLightFixture.cleanupDecision(cell, cell.id()) == OcclusionFixture.Cleanup.REMOVE &&
                    LocalLightFixture.cleanupDecision(cell, "minecraft:air") == OcclusionFixture.Cleanup.ALREADY_AIR &&
                    LocalLightFixture.cleanupDecision(cell, "minecraft:diamond_block") == OcclusionFixture.Cleanup.CONFLICT, "Block cleanup decisions");
            }
            var cleanup = LocalLightFixture.cleanupOrder(plan);
            check(cleanup.size() == plan.placements().size() && cleanup.getFirst().equals(plan.placements().getLast()), "Reverse cleanup");
            // Sealed: every interior AIR cell's six neighbours are interior AIR/pillar or a placed opaque shell cell.
            int interior = 0;
            for (int x = 404; x <= 409; x++) for (int y = 151; y <= 153; y++) for (int z = -411; z <= -405; z++) {
                if (grid.containsKey(List.of(x, y, z))) { check(grid.get(List.of(x, y, z)).role().endsWith("-pillar"), "Only pillars inside"); continue; }
                interior++;
                for (int[] d : new int[][]{{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}}) {
                    int nx = x + d[0], ny = y + d[1], nz = z + d[2];
                    check(HandLightFixture.interior(nx, ny, nz) || LocalLightFixture.opaque(grid.get(List.of(nx, ny, nz))), "Light-tight shell at " + nx + "," + ny + "," + nz);
                }
            }
            check(interior == 6 * 3 * 7 - (plan.hand().pillar() == HandLightFixture.Pillar.NONE ? 0 : 3), "Interior AIR count " + scene);
            check(plan.placements().stream().filter(c -> !c.role().endsWith("-pillar")).count() == 8 * 5 * 9 - 6 * 3 * 7, "Shell cell count");
            check(LocalLightFixture.predictedBlockLight(plan, HandLightFixture.samples().get("hand-back-wall-center")) == 0, "No vanilla block light in the room");
            check(HandLightFixture.bodyClear(plan, plan.eyeX()), "Driver body clear at the fixed pose " + scene);
            check(plan.placements().stream().filter(c -> c.role().equals("hand-receiver-back-wall")).allMatch(c -> c.id().equals("minecraft:white_concrete") && c.z() == -412) &&
                plan.placements().stream().filter(c -> c.role().equals("hand-receiver-back-wall")).count() == 18, "6x3 white receiver wall");
        }
        // Pairs: identical geometry where only the held items differ.
        for (String[] pair : new String[][]{{"lamp-hand-empty", "lamp-hand-main"}, {"lamp-hand-main", "lamp-hand-off"}, {"lamp-hand-main", "lamp-hand-soul"},
                {"lamp-hand-main", "lamp-hand-both"}, {"lamp-hand-main", "lamp-hand-putaway"}, {"lamp-hand-pillar", "lamp-hand-pillar-empty"},
                {"lamp-hand-pillar", "lamp-hand-walk"}, {"lamp-hand-walk", "lamp-hand-walk-empty"}, {"lamp-hand-hidden", "lamp-hand-hidden-off"},
                {"lamp-hand-hidden", "lamp-hand-hidden-empty"}})
            check(geometry(pair[0]).equals(geometry(pair[1])), "Identical geometry " + Arrays.toString(pair));
        var pillarOnly = new HashSet<>(geometry("lamp-hand-pillar")); pillarOnly.removeAll(geometry("lamp-hand-main"));
        check(pillarOnly.equals(Set.of("406/151/-410/minecraft:stone_bricks", "406/152/-410/minecraft:stone_bricks", "406/153/-410/minecraft:stone_bricks")), "Front pillar cells " + pillarOnly);
        var hiddenOnly = new HashSet<>(geometry("lamp-hand-hidden")); hiddenOnly.removeAll(geometry("lamp-hand-main"));
        check(hiddenOnly.equals(Set.of("407/151/-409/minecraft:stone_bricks", "407/152/-409/minecraft:stone_bricks", "407/153/-409/minecraft:stone_bricks")), "Hidden pillar cells " + hiddenOnly);

        // Close surfaces: every sample visible in the open room is 2..5 m from the eye and in frame at FOV 70, 2560x1440.
        var samples = HandLightFixture.samples();
        List<Double> eye = HandLightFixture.eye();
        for (var sample : samples.entrySet()) {
            double d = distance(eye, sample.getValue());
            var pixel = LocalLightFixture.project(sample.getValue(), eye, 180, 0, 70, 2560, 1440);
            check(pixel != null && pixel.get(0) > 0 && pixel.get(0) < 2560 && pixel.get(1) > 0 && pixel.get(1) < 1440, "In frame " + sample.getKey() + " " + pixel);
            if (!sample.getKey().equals("hand-hidden-pillar-face")) check(d >= 2 && d <= 5, "Within 2..5 m: " + sample.getKey() + " " + d);
            check(LocalLightFixture.clear(open, eye, sample.getValue(), true) || sample.getKey().contains("pillar-face"), "Open room sees " + sample.getKey());
        }
        check(LocalLightFixture.project(samples.get("hand-ceiling-mid"), eye, 180, 0, 70, 2560, 1440).get(1) < 720 &&
            LocalLightFixture.project(samples.get("hand-floor-mid"), eye, 180, 0, 70, 2560, 1440).get(1) > 720, "Ceiling above, floor below the horizon");
        var main = HandLightFixture.handOrigin(true); var off = HandLightFixture.handOrigin(false);
        // Release first-person anchor: eye + 0.32*side right, 0.30 down, 0.43 forward (yaw 180: right +X, forward -Z).
        check(near(main, List.of(406.97, 152.32, -407.43)) && near(off, List.of(406.33, 152.32, -407.43)), "Release hand anchors " + main + " " + off);
        check(HandLightFixture.HAND_RIGHT == .32 && HandLightFixture.HAND_DOWN == .30 && HandLightFixture.HAND_FORWARD == .43 &&
            HandLightFixture.EMITTER_RADIUS * HandLightFixture.TAP_SCALE == .13 * .66, "Release anchor and emitter constants");
        for (String scene : HandLightFixture.SCENES) {
            var grid = LocalLightFixture.grid(LocalLightFixture.parse(scene));
            for (var origin : List.of(main, off)) {
                check(!grid.containsKey(cellOf(origin)) && HandLightFixture.interior(cellOf(origin).get(0), cellOf(origin).get(1), cellOf(origin).get(2)), "Anchor in room AIR " + scene);
                // constrainHand is inactive: the eye-to-anchor segment never enters a placed cell.
                check(HandLightFixture.shaderClear(grid, HandLightFixture.vec(eye), HandLightFixture.vec(origin)), "Unconstrained anchor " + scene);
            }
        }
        var pillar = LocalLightFixture.parse("lamp-hand-pillar"); var hidden = LocalLightFixture.parse("lamp-hand-hidden");
        var pillarGrid = LocalLightFixture.grid(pillar); var hiddenGrid = LocalLightFixture.grid(hidden); var openGrid = LocalLightFixture.grid(open);
        double[] m = HandLightFixture.vec(main), o = HandLightFixture.vec(off);
        // Regressions against the actual anchors: the previous receivers were not what they claimed.
        double back = HandLightFixture.SHELL_Z0 + 1 + .001;
        double[] oldHidden = {406.1, HandLightFixture.EYE_Y, back}, oldFront = {404.85, HandLightFixture.EYE_Y, back};
        check(allOpen(HandLightFixture.tapsOpen(hiddenGrid, oldHidden, m)) && allOpen(HandLightFixture.tapsOpen(hiddenGrid, oldHidden, o)),
            "Old hidden receiver x406.1 is lit by every tap of both hands");
        boolean[] partial = HandLightFixture.tapsOpen(pillarGrid, oldFront, m);
        check(!allOpen(partial) && (partial[0] || partial[1] || partial[2]), "Old front receiver x404.85 is a partial (penumbra) sample: " + Arrays.toString(partial));
        // The new receivers: every tap state as named, camera-visible, and lit in the open room.
        var hiddenShadow = HandLightFixture.vec(samples.get("hand-hidden-shadow-wall"));
        var frontShadow = HandLightFixture.vec(samples.get("hand-front-shadow-wall"));
        check(hiddenShadow[0] > 407.24 && hiddenShadow[0] < 407.26 && Math.abs(hiddenShadow[1] - HandLightFixture.EYE_Y) < .01, "Hidden ROI centre x~407.25 at eye height " + Arrays.toString(hiddenShadow));
        check(frontShadow[0] > 405.13 && frontShadow[0] < 405.15 && Math.abs(frontShadow[1] - HandLightFixture.EYE_Y) < .01, "Front ROI centre x~405.14 at eye height " + Arrays.toString(frontShadow));
        check(LocalLightFixture.clear(hidden, eye, samples.get("hand-hidden-shadow-wall"), true) && noneOpen(HandLightFixture.tapsOpen(hiddenGrid, hiddenShadow, m)) &&
            allOpen(HandLightFixture.tapsOpen(hiddenGrid, hiddenShadow, o)), "Hidden: visible, main taps blocked, off taps open");
        check(LocalLightFixture.clear(pillar, eye, samples.get("hand-front-shadow-wall"), true) && noneOpen(HandLightFixture.tapsOpen(pillarGrid, frontShadow, m)),
            "Front: visible, main taps blocked");
        check(allOpen(HandLightFixture.tapsOpen(openGrid, hiddenShadow, m)) && allOpen(HandLightFixture.tapsOpen(openGrid, frontShadow, m)), "Open room: same points lit");
        var lit = HandLightFixture.vec(samples.get("hand-front-lit-wall"));
        check(LocalLightFixture.clear(pillar, eye, samples.get("hand-front-lit-wall"), true) && allOpen(HandLightFixture.tapsOpen(pillarGrid, lit, m)), "Front lit control");
        check(!LocalLightFixture.clear(pillar, eye, samples.get("hand-back-wall-center"), true), "Pillar occludes the wall centre from the eye");
        check(allOpen(HandLightFixture.tapsOpen(pillarGrid, HandLightFixture.vec(samples.get("hand-front-pillar-face")), m)), "Lit front pillar face");
        rois();
    }

    /** Fixed 9x9 ROIs at 2560x1440: all 81 pixels satisfy their need at the requested pose and the whole accepted pose box. */
    private static void rois() {
        check(HandLightFixture.ROIS.size() == 4 && HandLightFixture.ROIS.stream().allMatch(r -> r.x1() - r.x0() == 8 && r.y1() - r.y0() == 8), "Four 9x9 ROIs");
        check(HandLightFixture.roi("hand-hidden-shadow-wall").column() == 1434 && HandLightFixture.roi("hand-front-shadow-wall").column() == 892 &&
            HandLightFixture.ROIS.stream().allMatch(r -> r.row() == 720), "Robust centres: hidden column 1434, front column 892, eye row 720");
        double[] eye = {HandLightFixture.EYE_X, HandLightFixture.EYE_Y, HandLightFixture.EYE_Z};
        for (var roi : HandLightFixture.ROIS) {
            check(HandLightFixture.roiViolation(roi, eye) == null, "ROI holds at the requested pose: " + roi.name() + " " + HandLightFixture.roiViolation(roi, eye));
            check(HandLightFixture.roiHoldsInBox(roi, HandLightFixture.EYE_TOLERANCE), "ROI holds over the accepted +-" + HandLightFixture.EYE_TOLERANCE + " m eye box: " + roi.name());
            double proven = HandLightFixture.provenPoseTolerance(roi);
            check(proven > HandLightFixture.EYE_TOLERANCE, "Proven tolerance exceeds acceptance: " + roi.name() + " " + proven);
            int[] margins = HandLightFixture.pixelMargins(roi);
            check(Arrays.stream(margins).allMatch(n -> n >= 8), "At least 8 px slack on every side: " + roi.name() + " " + Arrays.toString(margins));
            HandLightFixture.tapMargins(roi).forEach((tap, margin) -> check(margin.equals(">0.5") || (double)margin >= .02, "Tap x margin >= 2 cm: " + roi.name() + " " + tap + " " + margin));
        }
        // The hidden ROI is the tightest: it fails at the old 0.05 m acceptance, which is why acceptance is now 0.02 m.
        var hiddenRoi = HandLightFixture.roi("hand-hidden-shadow-wall");
        check(!HandLightFixture.roiHoldsInBox(hiddenRoi, .05), "Hidden ROI is not robust to 0.05 m (acceptance tightened)");
        // Open-room controls: shadow ROIs are lit in lamp-hand-main geometry; scene mapping.
        var mainSpec = HandLightFixture.spec("lamp-hand-main");
        var openRois = HandLightFixture.roisAtPose(mainSpec, eye, 180, 0, 70, 2560, 1440);
        check(openRois.equals(Map.of("hand-hidden-shadow-wall", "ok", "hand-front-shadow-wall", "ok")), "Open-room controls " + openRois);
        for (String scene : HandLightFixture.SCENES) {
            var results = HandLightFixture.roisAtPose(HandLightFixture.spec(scene), eye, 180, 0, 70, 2560, 1440);
            check(!results.isEmpty() && results.values().stream().allMatch("ok"::equals), "ROIs at requested pose " + scene + " " + results);
            check(HandLightFixture.roisAtPose(HandLightFixture.spec(scene), eye, 180, 0, 70, 960, 540).values().stream().allMatch(v -> v.startsWith("not applicable")), "Clip frames not applicable");
        }
        // Negative: wrong FOV, rotated camera or displaced eye break the fixed-pixel claims.
        var hiddenSpec = HandLightFixture.spec("lamp-hand-hidden");
        check(!HandLightFixture.roisAtPose(hiddenSpec, eye, 180, 0, 90, 2560, 1440).get("hand-hidden-shadow-wall").equals("ok"), "FOV 90 rejected");
        check(!HandLightFixture.roisAtPose(hiddenSpec, eye, 181.5f, 0, 70, 2560, 1440).get("hand-hidden-shadow-wall").equals("ok") &&
            HandLightFixture.roisAtPose(hiddenSpec, eye, 179.5f, 0, 70, 2560, 1440).get("hand-hidden-shadow-wall").equals("ok"), "Yaw +1.5 deg rejected, -0.5 deg held");
        check(HandLightFixture.provenRotationTolerance(hiddenRoi, false) >= 1 && HandLightFixture.provenRotationTolerance(hiddenRoi, false) < 1.25, "Hidden ROI yaw tolerance ~1 deg");
        check(!HandLightFixture.roisAtPose(hiddenSpec, new double[]{eye[0] - .06, eye[1], eye[2]}, 180, 0, 70, 2560, 1440).get("hand-hidden-shadow-wall").equals("ok"), "Eye -6 cm rejected");
        // Release DDA vs dense march agree on every ROI pixel ray (independent traversal cross-check).
        for (var roi : HandLightFixture.ROIS) {
            var plan = LocalLightFixture.parse(HandLightFixture.pillarScene(roi.pillar()));
            var grid = LocalLightFixture.grid(plan);
            for (int px = roi.x0(); px <= roi.x1(); px++) for (int py = roi.y0(); py <= roi.y1(); py++) {
                double[] p = HandLightFixture.wallPoint(px + .5, py + .5, eye, 180, 0, 70, 2560, 1440);
                check(HandLightFixture.shaderClear(grid, eye, p) == LocalLightFixture.clear(plan, List.of(eye[0], eye[1], eye[2]), List.of(p[0], p[1], p[2] + 1e-4), true), "Camera traversal agreement");
            }
        }
        // GLSL tap layout: three points at 0.0858 m from the anchor on a disk normal to l, 120 degrees apart.
        double[] centre = HandLightFixture.roiCentre(hiddenRoi), anchor = HandLightFixture.vec(HandLightFixture.handOrigin(true));
        var taps = HandLightFixture.emitterTaps(centre, anchor);
        double[] l = {anchor[0] - centre[0], anchor[1] - centre[1], anchor[2] - centre[2]};
        double ll = Math.sqrt(l[0] * l[0] + l[1] * l[1] + l[2] * l[2]);
        for (int i = 0; i < 3; i++) {
            double[] d = {taps.get(i)[0] - anchor[0], taps.get(i)[1] - anchor[1], taps.get(i)[2] - anchor[2]};
            check(Math.abs(Math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]) - .0858) < 1e-4 && Math.abs((d[0] * l[0] + d[1] * l[1] + d[2] * l[2]) / ll) < 1e-9, "Tap " + i + " on the emitter disk");
        }
        check(taps.get(0)[0] < anchor[0] && Math.abs(taps.get(0)[1] - anchor[1]) < 1e-9, "Tap 0 = centre + u with u = normalize(cross(l, up)) (toward -X here)");
    }

    // ---- Private duplicated TEST game guard (real temporary directories, symlinks and hard links).
    private static void testGameGuard() throws Exception {
        Path root = Files.createTempDirectory("aqualumen-hand-guard-");
        try {
            Path instance = Files.createDirectories(root.resolve("Aqualumen Lab"));
            Path original = Files.createDirectories(instance.resolve("minecraft"));
            Path matrix = Files.createDirectories(instance.resolve("carried-matrix-a1B2c3"));
            Path game = Files.createDirectories(matrix.resolve("Aqualumen Lab/minecraft"));
            for (Path g : List.of(original, game)) {
                Path world = Files.createDirectories(g.resolve("saves/AqualumenNaturalV2/region"));
                Files.writeString(world.getParent().resolve("level.dat"), "level");
                Files.writeString(world.getParent().resolve("aqualumen-world.properties"), "world_id=x\n");
                Files.writeString(world.resolve("r.50.-26.mca"), "region");
            }
            Path canonical = game.toRealPath(), canonicalOriginal = original.toRealPath();
            Map<String, String> ok = Map.of(HandLightFixture.OPT_IN_KEY, HandLightFixture.OPT_IN_VALUE,
                HandLightFixture.OPT_IN_GAME, canonical.toString(), HandLightFixture.OPT_IN_ORIGINAL, canonicalOriginal.toString());
            String u = HandLightFixture.TEST_USERNAME, w = "AqualumenNaturalV2";
            var identified = HandLightFixture.privateTestGame(canonical, u, u, ok, w);
            check(identified.game().equals(canonical) && identified.original().equals(canonicalOriginal) && identified.matrix().equals("carried-matrix-a1B2c3"), "Positive: private duplicate identified");
            // Explicit opt-in is mandatory and must name exactly this game and the derived original.
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, Map.of(), w), "missing opt-in");
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, with(ok, HandLightFixture.OPT_IN_KEY, "yes"), w), "wrong opt-in value");
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, with(ok, HandLightFixture.OPT_IN_GAME, canonicalOriginal.toString()), w), "opt-in names original");
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, with(ok, HandLightFixture.OPT_IN_ORIGINAL, canonical.toString()), w), "opt-in original mismatch");
            // The untouched original itself, even with an opt-in naming it.
            refused(() -> HandLightFixture.privateTestGame(canonicalOriginal, u, u, with(ok, HandLightFixture.OPT_IN_GAME, canonicalOriginal.toString()), w), "original game");
            // Player identity.
            refused(() -> HandLightFixture.privateTestGame(canonical, "Player", u, ok, w), "session name");
            refused(() -> HandLightFixture.privateTestGame(canonical, u, null, ok, w), "missing profile");
            // Symlink escapes: game dir, matrix dir and world dir pointing at the original.
            Path linkMatrix = Files.createDirectories(instance.resolve("carried-matrix-link01/Aqualumen Lab"));
            Path linkGame = Files.createSymbolicLink(linkMatrix.resolve("minecraft"), original);
            refused(() -> HandLightFixture.privateTestGame(linkGame, u, u, with(ok, HandLightFixture.OPT_IN_GAME, linkGame.toString()), w), "symlinked game -> original");
            Path linkWhole = Files.createSymbolicLink(instance.resolve("carried-matrix-link02"), matrix);
            Path viaLink = linkWhole.resolve("Aqualumen Lab/minecraft");
            refused(() -> HandLightFixture.privateTestGame(viaLink, u, u, with(ok, HandLightFixture.OPT_IN_GAME, viaLink.toString()), w), "symlinked matrix dir");
            Path escapedMatrix = Files.createDirectories(instance.resolve("carried-matrix-world1/Aqualumen Lab/minecraft/saves"));
            Files.createSymbolicLink(escapedMatrix.resolve("AqualumenNaturalV2"), original.resolve("saves/AqualumenNaturalV2"));
            Path escapedGame = escapedMatrix.getParent().toRealPath();
            refused(() -> HandLightFixture.privateTestGame(escapedGame, u, u, with(ok, HandLightFixture.OPT_IN_GAME, escapedGame.toString()), w), "symlinked world -> original world");
            // Hard-linked region file shared with the original (in-place region writes would alter it).
            Path hard = game.resolve("saves/AqualumenNaturalV2/region/r.0.0.mca");
            Files.createLink(hard, original.resolve("saves/AqualumenNaturalV2/region/r.50.-26.mca"));
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, ok, w), "hard-linked region");
            Files.delete(hard);
            Path inner = game.resolve("saves/AqualumenNaturalV2/region/r.1.1.mca");
            Files.createSymbolicLink(inner, original.resolve("saves/AqualumenNaturalV2/region/r.50.-26.mca"));
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, ok, w), "symlinked region file");
            Files.delete(inner);
            // Directory convention.
            for (String bad : List.of("carried-matrix-", "carried-matrix-ab", "matrix-a1B2c3", "carried-matrix-a1B2c3!")) {
                Path other = Files.createDirectories(instance.resolve(bad).resolve("Aqualumen Lab/minecraft"));
                refused(() -> HandLightFixture.privateTestGame(other.toRealPath(), u, u, with(ok, HandLightFixture.OPT_IN_GAME, other.toRealPath().toString()), w), "matrix name " + bad);
            }
            Path wrongInstance = Files.createDirectories(root.resolve("Survival/carried-matrix-a1B2c3/Aqualumen Lab/minecraft"));
            Files.createDirectories(root.resolve("Survival/minecraft"));
            refused(() -> HandLightFixture.privateTestGame(wrongInstance.toRealPath(), u, u, with(ok, HandLightFixture.OPT_IN_GAME, wrongInstance.toRealPath().toString()), w), "instance not Aqualumen Lab");
            refused(() -> HandLightFixture.privateTestGame(canonical, u, u, ok, "../../minecraft/saves/AqualumenNaturalV2"), "world traversal");
            // Missing original: nothing to prove distinctness against.
            Path lone = Files.createDirectories(root.resolve("Lone/Aqualumen Lab/carried-matrix-zz9999/Aqualumen Lab/minecraft"));
            refused(() -> HandLightFixture.privateTestGame(lone.toRealPath(), u, u, with(ok, HandLightFixture.OPT_IN_GAME, lone.toRealPath().toString()), w), "missing original");
            // Still positive after the negative cases (nothing mutated the valid layout).
            check(HandLightFixture.privateTestGame(canonical, u, u, ok, w).game().equals(canonical), "Positive after negatives");
            System.out.println("TEST game guard: 1 private duplicate accepted; opt-in, original, player, symlink (game/matrix/world/region), hard link, convention, traversal and missing-original cases refused");
        } finally {
            try (var walk = Files.walk(root)) {
                for (Path p : walk.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(p);
            }
        }
    }
    private interface GuardCall { Object run() throws Exception; }
    private static void refused(GuardCall call, String label) {
        try { call.run(); }
        catch (IllegalStateException expected) { return; }
        catch (Exception other) { throw new AssertionError("Guard case " + label + " threw " + other); }
        throw new AssertionError("Guard accepted: " + label);
    }
    private static Map<String, String> with(Map<String, String> base, String key, String value) {
        Map<String, String> copy = new HashMap<>(base); copy.put(key, value); return copy;
    }
    private static boolean allOpen(boolean[] taps) { return taps[0] && taps[1] && taps[2]; }
    private static boolean noneOpen(boolean[] taps) { return !taps[0] && !taps[1] && !taps[2]; }

    private static void pose() {
        var walkPlan = LocalLightFixture.parse("lamp-hand-walk");
        var walk = walkPlan.hand();
        check(HandLightFixture.routeEyeX(walk, -1) == 406.65 && HandLightFixture.routeEyeX(walk, 0) == 406.65 &&
            Math.abs(HandLightFixture.routeEyeX(walk, 2) - 408.4) < 1e-9 && Math.abs(HandLightFixture.routeEyeX(walk, 6) - 404.9) < 1e-9 &&
            HandLightFixture.routeEyeX(walk, 8) == 406.65 && HandLightFixture.routeEyeX(walk, 9) == 406.65 &&
            HandLightFixture.routeEyeX(HandLightFixture.spec("lamp-hand-main"), 3) == 406.65, "Route law; held at the fixed pose");
        check(LocalLightFixture.walkEyeX(walkPlan, 2) == HandLightFixture.routeEyeX(walk, 2) && LocalLightFixture.walkEyeX(walkPlan, 9) == 406.65, "Plan dispatch");
        double maxStep = 0;
        for (int i = 0; i <= 8000; i++) {
            double x = HandLightFixture.routeEyeX(walk, i * .001);
            check(HandLightFixture.bodyClear(walkPlan, x), "Body clear along the route at x=" + x);
            for (boolean hand : new boolean[]{true, false}) {
                var origin = HandLightFixture.handOrigin(hand, x, 152.62, -407.0, 180, 0);
                var cell = cellOf(origin);
                check(HandLightFixture.interior(cell.get(0), cell.get(1), cell.get(2)) && !LocalLightFixture.grid(walkPlan).containsKey(cell), "Hands stay in room AIR");
            }
            if (i > 0) maxStep = Math.max(maxStep, Math.abs(x - HandLightFixture.routeEyeX(walk, (i - 1) * .001)));
        }
        check(maxStep * 50 < HandLightFixture.TRACK_TOLERANCE / 4, "20 Hz tick step well inside tracking tolerance: " + maxStep * 50);
        var crossings = HandLightFixture.routePillarCrossings();
        check(crossings.size() >= 6, "Walk passes the pillar repeatedly: " + crossings);
        // The receiver behind the pillar changes visibility along the route (actual motion past the pillar).
        var centre = HandLightFixture.samples().get("hand-back-wall-center");
        boolean seen = false, hiddenSeen = false;
        for (int i = 0; i <= 80; i++) {
            double x = HandLightFixture.routeEyeX(walk, i * .1);
            boolean visible = LocalLightFixture.clear(walkPlan, List.of(x, 152.62, -407.0), centre, true);
            seen |= visible; hiddenSeen |= !visible;
        }
        check(seen && hiddenSeen, "Wall centre is revealed and hidden while walking past the pillar");
        double[] player = {406.65, 151.0, -407.0}, eye = {406.65, 152.62, -407.0};
        check(HandLightFixture.poseMatches(406.65, .05, true, player, eye, eye), "Fixed pose accepted");
        check(LocalLightFixture.eyeMatches(LocalLightFixture.parse("lamp-hand-main"), 406.65, true, player, eye, eye) &&
            !LocalLightFixture.eyeMatches(406.65, true, player, eye, eye), "Hand plan proven only against its own pose");
        check(!HandLightFixture.poseMatches(406.65, .05, false, player, eye, eye), "Third person / spectator-style detached view rejected");
        check(!HandLightFixture.poseMatches(406.65, .05, true, new double[]{406.65, 151.5, -407.0}, new double[]{406.65, 153.12, -407.0}, new double[]{406.65, 153.12, -407.0}), "Raised (flying) eye rejected");
        check(!HandLightFixture.poseMatches(406.65, .05, true, player, eye, new double[]{406.65, 152.62, -403.0}), "Detached camera rejected");
        check(!HandLightFixture.poseMatches(406.65, .05, true, player, eye, new double[]{406.75, 152.62, -407.0}), "Camera lag rejected for fixed scenes");
        check(HandLightFixture.poseMatches(406.9, .35, true, new double[]{406.65, 151.0, -407.0}, eye, new double[]{406.72, 152.62, -407.0}), "Walk tick lag accepted");
        check(!HandLightFixture.poseMatches(407.1, .35, true, player, eye, eye) && !HandLightFixture.poseMatches(406.65, .01, true, player, eye, eye) &&
            !HandLightFixture.poseMatches(406.65, .05, true, player, eye, new double[]{Double.NaN, 152.62, -407.0}), "Excess lag, invalid tolerance and NaN rejected");
        check(HandLightFixture.trackTolerance(walk) == .35 && HandLightFixture.trackTolerance(HandLightFixture.spec("lamp-hand-main")) == .02, "Tolerance per spec");
    }

    private static void equipment() {
        check(HandLightFixture.slotMatches(E, E, 0) && !HandLightFixture.slotMatches(E, T, 1) && HandLightFixture.slotMatches(T, T, 1) &&
            !HandLightFixture.slotMatches(T, T, 2) && !HandLightFixture.slotMatches(T, S, 1), "Slot match requires exact single stack");
        check(HandLightFixture.equipMatches(HandLightFixture.TORCH_AND_SOUL, T, 1, S, 1) && !HandLightFixture.equipMatches(HandLightFixture.TORCH_AND_SOUL, S, 1, T, 1) &&
            !HandLightFixture.equipMatches(HandLightFixture.MAIN_TORCH, T, 1, T, 1), "Hands are not interchangeable");
        check(HandLightFixture.slotWritable(E, 0) && HandLightFixture.slotWritable(T, 1) && HandLightFixture.slotWritable(S, 1) &&
            !HandLightFixture.slotWritable(T, 64) && !HandLightFixture.slotWritable("minecraft:diamond_sword", 1) && !HandLightFixture.slotWritable(null, 0),
            "Foreign or stacked items are never overwritten");
        check(HandLightFixture.equipCommand("@a[limit=1]", "weapon.mainhand", T).equals("item replace entity @a[limit=1] weapon.mainhand with minecraft:torch") &&
            HandLightFixture.equipCommand("@s", "weapon.offhand", E).equals("item replace entity @s weapon.offhand with minecraft:air"), "Equip command text");
        check(throwsIllegal(() -> HandLightFixture.equipCommand("@s", "armor.head", T)) && throwsIllegal(() -> HandLightFixture.equipCommand("@s", "weapon.mainhand", "minecraft:lava_bucket")) &&
            throwsIllegal(() -> HandLightFixture.clearCommand("@s", "weapon.mainhand", E)), "Only fixture items and hand slots are commanded");
        check(HandLightFixture.clearCommand("@s", "weapon.offhand", S).equals(
            "execute if items entity @s weapon.offhand minecraft:soul_torch run item replace entity @s weapon.offhand with minecraft:air"), "Conditional clear text");
        List<String> empty = Collections.nCopies(41, E);
        check(HandLightFixture.inventoryViolations(empty).isEmpty(), "Empty disposable inventory accepted");
        var dirty = new ArrayList<>(empty); dirty.set(17, "minecraft:bread");
        check(HandLightFixture.inventoryViolations(dirty).equals(List.of("slot 17=minecraft:bread")), "Any initial item refuses the run");
        check(!HandLightFixture.inventoryViolations(Collections.nCopies(40, E)).isEmpty() && !HandLightFixture.inventoryViolations(null).isEmpty(), "Unexpected inventory shape refused");
        var equipped = new ArrayList<>(empty); equipped.set(3, T); equipped.set(40, S);
        check(HandLightFixture.inventoryViolations(equipped, 3, HandLightFixture.TORCH_AND_SOUL).isEmpty(), "Equipped inventory exact");
        check(!HandLightFixture.inventoryViolations(equipped, 4, HandLightFixture.TORCH_AND_SOUL).isEmpty() &&
            !HandLightFixture.inventoryViolations(equipped, 3, HandLightFixture.MAIN_TORCH).isEmpty() &&
            !HandLightFixture.inventoryViolations(equipped, 9, HandLightFixture.TORCH_AND_SOUL).isEmpty(), "Wrong slot/off hand/selection refused");
        check(HandLightFixture.VANILLA_LUMINANCE.get(T) == 14 && HandLightFixture.VANILLA_LUMINANCE.get(S) == 10 && HandLightFixture.VANILLA_LUMINANCE.get(E) == 0 &&
            HandLightFixture.FIXTURE_ITEMS.equals(Set.of(T, S)), "Real vanilla lamp items");
    }

    /** Simulates the Recorder's equip -> swaps -> cleanup on a 41-slot model using the same pure decisions. */
    private static void restoredEmptySlot() {
        for (String scene : HandLightFixture.SCENES) {
            var spec = HandLightFixture.spec(scene);
            int selected = 5;
            List<String> inventory = new ArrayList<>(Collections.nCopies(41, E));
            int[] counts = new int[41];
            check(HandLightFixture.inventoryViolations(inventory).isEmpty(), "Initial empty");
            for (var step : spec.steps()) {
                for (int slot : new int[]{selected, 40}) {
                    String want = slot == 40 ? step.equip().off() : step.equip().main();
                    check(HandLightFixture.slotWritable(inventory.get(slot), counts[slot]), "Writable before swap");
                    inventory.set(slot, want); counts[slot] = want.equals(E) ? 0 : 1;
                }
                check(HandLightFixture.inventoryViolations(inventory, selected, step.equip()).isEmpty(), "Exact after each swap " + scene);
            }
            List<String> commands = new ArrayList<>();
            for (int slot : new int[]{selected, 40}) {
                switch (HandLightFixture.slotCleanup(inventory.get(slot), counts[slot])) {
                    case CLEAR -> { commands.add(HandLightFixture.clearCommand("@s", slot == 40 ? HandLightFixture.OFF_SLOT : HandLightFixture.MAIN_SLOT, inventory.get(slot)));
                                    inventory.set(slot, E); counts[slot] = 0; }
                    case ALREADY_EMPTY -> { }
                    case CONFLICT -> throw new AssertionError("Fixture stack treated as foreign");
                }
            }
            check(HandLightFixture.inventoryViolations(inventory).isEmpty(), "Restored empty slots " + scene);
            check(commands.size() == (spec.last().main().equals(E) ? 0 : 1) + (spec.last().off().equals(E) ? 0 : 1), "Clears exactly the held lamps " + scene);
        }
        check(HandLightFixture.slotCleanup(T, 1) == HandLightFixture.SlotCleanup.CLEAR && HandLightFixture.slotCleanup(S, 1) == HandLightFixture.SlotCleanup.CLEAR &&
            HandLightFixture.slotCleanup(E, 0) == HandLightFixture.SlotCleanup.ALREADY_EMPTY && HandLightFixture.slotCleanup(T, 3) == HandLightFixture.SlotCleanup.CONFLICT &&
            HandLightFixture.slotCleanup("minecraft:lantern", 1) == HandLightFixture.SlotCleanup.CONFLICT && HandLightFixture.slotCleanup(null, 0) == HandLightFixture.SlotCleanup.CONFLICT,
            "Cleanup removes only single fixture lamps; foreign stacks preserved");
    }

    private static void recipes() {
        var baseline = new HandLightFixture.Progress(Set.of("minecraft:crafting_table"),
            Set.of(HandLightFixture.criterionKey("minecraft:story/root", "crafting_table")));
        var current = new HandLightFixture.Progress(Set.of("minecraft:crafting_table", "minecraft:lantern", "minecraft:soul_torch"),
            Set.of(HandLightFixture.criterionKey("minecraft:story/root", "crafting_table"), HandLightFixture.criterionKey("minecraft:recipes/decorations/lantern", "has_torch"),
                HandLightFixture.criterionKey("minecraft:recipes/decorations/lantern", "has_the_recipe")));
        var restore = HandLightFixture.restore(baseline, current);
        check(restore.takeRecipes().equals(List.of("minecraft:lantern", "minecraft:soul_torch")) && restore.lossless() && !restore.noop(), "New recipes found, sorted");
        check(restore.revokeCriteria().equals(List.of("minecraft:recipes/decorations/lantern has_the_recipe", "minecraft:recipes/decorations/lantern has_torch")), "New criteria found");
        var commands = HandLightFixture.restoreCommands(restore, "@s");
        check(commands.equals(List.of("recipe take @s minecraft:lantern", "recipe take @s minecraft:soul_torch",
            "advancement revoke @s only minecraft:recipes/decorations/lantern has_the_recipe", "advancement revoke @s only minecraft:recipes/decorations/lantern has_torch")),
            "Recipes taken before criteria revoked: " + commands);
        check(HandLightFixture.restore(baseline, baseline).noop() && HandLightFixture.restoreCommands(HandLightFixture.restore(baseline, baseline), "@s").isEmpty(), "Unchanged -> no command");
        var lost = HandLightFixture.restore(baseline, new HandLightFixture.Progress(Set.of(), Set.of()));
        check(!lost.lossless() && lost.noop() && lost.lostRecipes().equals(List.of("minecraft:crafting_table")), "Missing baseline entries are reported, never fabricated");
        check(throwsIllegal(() -> HandLightFixture.restoreCommands(new HandLightFixture.Restore(List.of("minecraft:x run kill @e"), List.of(), List.of(), List.of()), "@s")) &&
            throwsIllegal(() -> HandLightFixture.restoreCommands(new HandLightFixture.Restore(List.of(), List.of("minecraft:a/b"), List.of(), List.of()), "@s")) &&
            throwsIllegal(() -> HandLightFixture.restoreCommands(new HandLightFixture.Restore(List.of(), List.of("minecraft:a/b x;y"), List.of(), List.of()), "@s")),
            "Malformed ids cannot inject commands");
        check(new HandLightFixture.Progress(Set.of("b", "a"), Set.of()).equals(new HandLightFixture.Progress(new HashSet<>(List.of("a", "b")), Set.of())), "Progress value equality");
    }

    private static void evidenceFormats() {
        String row = HandLightFixture.traceRow(40_000_000L, 18000L, 1, 406.65, new double[]{406.65, 151.0, -407.0}, new double[]{406.65, 152.62, -407.0},
            180f, 0f, HandLightFixture.MAIN_TORCH, T, 1, E, 0, 5, T, E, 1f, 1f, "creative", true, true, true, true);
        String[] header = HandLightFixture.TRACE_HEADER.trim().split(",", -1), columns = row.trim().split(",", -1);
        check(row.endsWith("\n") && header.length == 30 && columns.length == header.length, "Trace row matches header: " + row);
        check(columns[0].equals("40000000") && columns[14].equals(T) && columns[16].equals(T) && columns[17].equals("1") && columns[18].equals(E) &&
            columns[20].equals("5") && columns[25].equals("creative") && columns[29].equals("true"), "Trace columns in header order");
        Map<String, Object> swap = new HashMap<>(Map.of("step", 1, "scheduled_ns", 2_000_000_000L, "expected_main", E, "expected_off", E, "issued_ns", 2_001_000_000L,
            "server_applied_ns", 2_020_000_000L, "client_observed_ns", 2_060_000_000L, "renderer_observed_ns", 2_200_000_000L, "renderer_settled_ns", 2_400_000_000L));
        swap.put("client_latency_ms", null);
        String csv = HandLightFixture.swapCsv(List.of(swap));
        String[] lines = csv.split("\n");
        check(lines.length == 2 && lines[0].split(",", -1).length == HandLightFixture.SWAP_KEYS.size() && lines[1].split(",", -1).length == HandLightFixture.SWAP_KEYS.size() &&
            lines[1].startsWith("1,2000000000,minecraft:air,minecraft:air,2001000000") && lines[1].endsWith(","), "Swap CSV columns: " + csv);
        check(String.join(",", HandLightFixture.SWAP_KEYS).equals(HandLightFixture.SWAP_HEADER.trim()), "Swap keys equal header");
    }

    private static void printTable() {
        System.out.println("scene,pillar,walking,schedule(main/off@s),eye_x,eye_y,eye_z,yaw,pitch,feet_y,time");
        for (String scene : HandLightFixture.SCENES) {
            var plan = LocalLightFixture.parse(scene); var spec = plan.hand();
            StringJoiner schedule = new StringJoiner(" ");
            for (var step : spec.steps()) schedule.add(step.equip().main().replace("minecraft:", "") + "/" + step.equip().off().replace("minecraft:", "") + "@" + step.atSeconds());
            System.out.println(String.join(",", scene, spec.pillar().name().toLowerCase(Locale.ROOT), String.valueOf(spec.walking()), schedule.toString(),
                String.valueOf(plan.eyeX()), String.valueOf(plan.eyeY()), String.valueOf(plan.eyeZ()), String.valueOf(plan.yaw()), String.valueOf(plan.pitch()),
                String.valueOf(plan.playerY()), String.valueOf(plan.timeOfDay())));
        }
        System.out.println("walk front-pillar crossings (s): " + HandLightFixture.routePillarCrossings());
        System.out.println("release main anchor " + HandLightFixture.handOrigin(true) + ", off anchor " + HandLightFixture.handOrigin(false) +
            " (view +-0.32 right, 0.30 down, 0.43 forward; emitter tap radius " + HandLightFixture.EMITTER_RADIUS * HandLightFixture.TAP_SCALE + " m)");
        HandLightFixture.roiReports().forEach((name, report) -> System.out.println("roi " + name + " " + report));
        HandLightFixture.samples().forEach((name, point) -> System.out.println("sample " + name + " " + point + " d=" +
            String.format(Locale.ROOT, "%.2f", distance(HandLightFixture.eye(), point)) + " px@FOV70 " + LocalLightFixture.project(point, HandLightFixture.eye(), 180, 0, 70, 2560, 1440)));
    }

    private static boolean throwsIllegal(Runnable action) {
        try { action.run(); return false; } catch (IllegalArgumentException expected) { return true; }
    }
    private static double distance(List<Double> a, List<Double> b) {
        return Math.sqrt(Math.pow(a.get(0) - b.get(0), 2) + Math.pow(a.get(1) - b.get(1), 2) + Math.pow(a.get(2) - b.get(2), 2));
    }
    private static boolean near(List<Double> a, List<Double> b) { return distance(a, b) < 1e-9; }
    private static List<Integer> cellOf(List<Double> p) { return List.of((int)Math.floor(p.get(0)), (int)Math.floor(p.get(1)), (int)Math.floor(p.get(2))); }
    private static Set<String> geometry(String scene) {
        Set<String> result = new HashSet<>();
        for (var cell : LocalLightFixture.parse(scene).placements()) result.add(cell.x() + "/" + cell.y() + "/" + cell.z() + "/" + cell.state());
        return result;
    }
}
