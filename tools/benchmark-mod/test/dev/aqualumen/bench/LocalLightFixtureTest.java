package dev.aqualumen.bench;

import java.util.*;

/** CPU-only checks of the local-light fixture geometry, guards and cleanup ordering; no Minecraft writes. */
public final class LocalLightFixtureTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        check(LocalLightFixture.parse("ocean-day") == null && LocalLightFixture.parse("lamp-night-red") == null &&
              LocalLightFixture.parse("lamp-day-soul") == null && LocalLightFixture.parse("lamp-day-glass") == null &&
              LocalLightFixture.parse("lamp-night-walk-mid") == null && LocalLightFixture.parse(null) == null,
              "Only reviewed lamp scene keys authorize placement");
        check(LocalLightFixture.SCENES.size() == 18 && LocalLightFixture.SCENES.subList(0, 12).equals(List.of("lamp-day-off", "lamp-day-torch",
              "lamp-day-wall", "lamp-day-wall-off", "lamp-night-off", "lamp-night-torch", "lamp-night-soul", "lamp-night-both",
              "lamp-night-wall", "lamp-night-wall-off", "lamp-night-water", "lamp-night-moving")), "Original 12 scenes kept in order");
        check(LocalLightFixture.parse("lamp-night-torch") == LocalLightFixture.parse("lamp-night-torch"), "Memoized immutable plan");
        check(LocalLightFixture.authorized("AqualumenNaturalV2", OcclusionFixture.WORLD_ID, 308060), "Exact V2 + seed accepted");
        check(!LocalLightFixture.authorized("AqualumenNaturalV2", OcclusionFixture.WORLD_ID, 308061), "Wrong seed rejected");
        check(!LocalLightFixture.authorized("AqualumenNatural", OcclusionFixture.WORLD_ID, 308060), "Other folder rejected");
        check(!LocalLightFixture.authorized("AqualumenNaturalV2", "00000000-0000-0000-0000-000000000000", 308060), "Wrong UUID rejected");
        check(LocalLightFixture.boxCells() == 3080, "Reserved AIR box size");
        Set<List<Integer>> otherPlots = new HashSet<>();
        for (String scene : new String[]{"opaque-near-magenta", "opaque-far-magenta", "air-shadow-backlit", "ground-noon"})
            for (var cell : OcclusionFixture.parse(scene).reserved()) otherPlots.add(List.of(cell.x(), cell.y(), cell.z()));

        Map<String, LocalLightFixture.Plan> plans = new LinkedHashMap<>();
        for (String scene : LocalLightFixture.SCENES) plans.put(scene, LocalLightFixture.parse(scene));
        var open = plans.get("lamp-night-off");
        for (var plan : plans.values()) {
            check(plan != null, "Known lamp scene");
            check(plan.yaw() == 180 && plan.pitch() == 22 && Math.abs(plan.playerY() - 155.38) < 1e-9,
                "All variants share one camera height and orientation");
            check(plan.scene().startsWith("lamp-night-walk") || (plan.eyeX() == LocalLightFixture.EYE_X && !plan.walking()),
                "Non-walk variants keep the original eye " + plan.scene());
            check(plan.timeOfDay() == (plan.scene().startsWith("lamp-day-") ? 7000 : 18000), "Frozen day/night time");
            Set<List<Integer>> unique = new HashSet<>();
            Map<List<Integer>, LocalLightFixture.Cell> grid = LocalLightFixture.grid(plan);
            int index = 0;
            Map<List<Integer>, Integer> order = new HashMap<>();
            for (var cell : plan.placements()) {
                check(unique.add(cell.position()), "No duplicate placement/journal entry " + cell);
                check(LocalLightFixture.inBox(cell.x(), cell.y(), cell.z()), "Placement inside reserved box " + cell);
                check(!otherPlots.contains(cell.position()), "No overlap with existing fixture plots");
                check(LocalLightFixture.cleanupDecision(cell, cell.id()) == OcclusionFixture.Cleanup.REMOVE, "Owned state removable");
                check(LocalLightFixture.cleanupDecision(cell, "minecraft:air") == OcclusionFixture.Cleanup.ALREADY_AIR, "Idempotent");
                check(LocalLightFixture.cleanupDecision(cell, "minecraft:diamond_block") == OcclusionFixture.Cleanup.CONFLICT, "Foreign state preserved");
                order.put(cell.position(), index++);
            }
            // Eye body cells stay AIR and lie inside the reservation.
            for (int y = 155; y <= 157; y++) {
                check(LocalLightFixture.inBox(409, y, -402) && !grid.containsKey(List.of(409, y, -402)), "Camera cells reserved AIR");
            }
            // Sealed water: every water neighbour (except up) is water or a solid placed earlier.
            for (var cell : plan.placements()) {
                if (!cell.id().equals("minecraft:water")) continue;
                for (int[] d : new int[][]{{1,0,0},{-1,0,0},{0,-1,0},{0,0,1},{0,0,-1}}) {
                    var neighbour = grid.get(List.of(cell.x()+d[0], cell.y()+d[1], cell.z()+d[2]));
                    check(neighbour != null && (neighbour.id().equals("minecraft:water") ||
                        (LocalLightFixture.opaque(neighbour) && order.get(neighbour.position()) < order.get(cell.position()))),
                        "Water cannot flow out of the reserved basin at " + cell);
                }
                var above = grid.get(List.of(cell.x(), cell.y()+1, cell.z()));
                check(cell.y() == 149 ? above != null && above.id().equals("minecraft:water") : above == null, "Open still surface");
            }
            // Supports are placed before attachments and removed after them.
            for (var cell : plan.placements()) {
                if (!cell.role().equals("lamp") && !cell.id().equals("minecraft:oak_log")) continue;
                var support = grid.get(List.of(cell.x(), cell.y()-1, cell.z()));
                check(support != null && LocalLightFixture.opaque(support) && order.get(support.position()) < order.get(cell.position()),
                    "Attachment/trunk has an earlier full support " + cell);
            }
            var cleanup = LocalLightFixture.cleanupOrder(plan);
            check(cleanup.size() == plan.placements().size() && cleanup.getFirst().equals(plan.placements().getLast()), "Reverse cleanup");
            // Grass is never covered by an opaque block (it would turn to dirt and become a cleanup conflict).
            for (var cell : plan.placements())
                if (cell.id().equals("minecraft:grass_block")) check(!LocalLightFixture.opaque(grid.get(List.of(cell.x(), cell.y()+1, cell.z()))), "Grass stays grass");
            // Same observable receivers from the same eye in every variant.
            for (var sample : LocalLightFixture.samples().entrySet()) {
                if (sample.getKey().equals("submerged-receiver") || sample.getKey().startsWith("pool")) continue;
                check(LocalLightFixture.clear(plan, LocalLightFixture.eye(), sample.getValue(), true),
                    plan.scene() + ": camera sees " + sample.getKey());
                var pixel = LocalLightFixture.project(sample.getValue(), plan.yaw(), plan.pitch(), 70, 2560, 1440);
                check(pixel != null && pixel.get(0) > 0 && pixel.get(0) < 2560 && pixel.get(1) > 0 && pixel.get(1) < 1440,
                    "Sample in frame at FOV70: " + sample.getKey() + " " + pixel);
            }
            check(LocalLightFixture.clear(plan, LocalLightFixture.eye(), LocalLightFixture.samples().get("pool-surface-center"), true) &&
                  LocalLightFixture.clear(plan, LocalLightFixture.eye(), LocalLightFixture.samples().get("submerged-receiver"), true),
                "Pool surface and submerged receiver seen through water only");
            check(plan.placements().stream().filter(c -> c.position().equals(List.of(409, 148, -411))).findFirst().orElseThrow()
                .id().equals("minecraft:white_concrete"), "Submerged white receiver under the pool");
        }
        // Geometry pairs: only the intended cells differ.
        check(geometry(plans.get("lamp-night-wall")).equals(geometry(plans.get("lamp-night-wall-off"))), "Wall/wall-off geometrically identical");
        check(geometry(plans.get("lamp-day-wall")).equals(geometry(plans.get("lamp-night-wall"))), "Day/night wall identical");
        check(geometry(plans.get("lamp-night-torch")).equals(geometry(open)) && geometry(plans.get("lamp-night-water")).equals(geometry(open)) &&
              geometry(plans.get("lamp-night-both")).equals(geometry(open)), "Open variants share geometry");
        var wallOnly = new HashSet<>(geometry(plans.get("lamp-night-wall-off"))); wallOnly.removeAll(geometry(open));
        check(wallOnly.size() == 20 && wallOnly.stream().allMatch(p -> p.startsWith("409/")), "Wall pair adds exactly the 20-cell divider plane");
        check(open.placements().stream().noneMatch(c -> c.role().equals("lamp")) && plans.get("lamp-night-wall-off").lamps().isEmpty(), "Off controls have no lamp");
        check(plans.get("lamp-night-torch").lamps().equals(plans.get("lamp-night-wall").lamps()), "Same lamp for open/wall pair");
        check(plans.get("lamp-night-soul").lamps().getFirst().id().equals("minecraft:soul_torch") &&
              plans.get("lamp-night-soul").lamps().getFirst().x() == plans.get("lamp-night-torch").lamps().getFirst().x(), "Soul at torch position");
        check(plans.get("lamp-night-both").lamps().size() == 2, "Two lamps");
        // Lamp-to-receiver: the divider blocks the direct path only in wall variants.
        var torch = plans.get("lamp-night-torch").lamps().getFirst().center();
        for (String receiver : new String[]{"receiver-back-wall", "receiver-floor-deep", "receiver-floor-mid"}) {
            var point = LocalLightFixture.samples().get(receiver);
            check(LocalLightFixture.clear(plans.get("lamp-night-torch"), torch, point, false), "Open path lamp->" + receiver);
            check(!LocalLightFixture.clear(plans.get("lamp-night-wall"), torch, point, false), "Wall blocks lamp->" + receiver);
            int lit = LocalLightFixture.predictedBlockLight(plans.get("lamp-night-torch"), point);
            int walled = LocalLightFixture.predictedBlockLight(plans.get("lamp-night-wall"), point);
            check(lit >= walled + 5, "Flood-fill model separates open/wall at " + receiver + ": " + lit + " vs " + walled);
            check(LocalLightFixture.predictedBlockLight(plans.get("lamp-night-wall-off"), point) == 0, "Off control has no block light");
            System.out.println("model block light " + receiver + ": open=" + lit + " wall=" + walled);
        }
        // Lantern really is on the air side and its mirror path lands in the pool.
        var water = plans.get("lamp-night-water");
        var lantern = water.lamps().getFirst();
        check(lantern.id().equals("minecraft:lantern") && lantern.y() > LocalLightFixture.WATER_SURFACE_Y, "Air-side lantern");
        var reflection = LocalLightFixture.lanternReflectionPoint();
        check(reflection.get(0) >= 407 && reflection.get(0) < 412 && reflection.get(2) >= -411 && reflection.get(2) < -408, "Mirror point on the pool " + reflection);
        check(LocalLightFixture.clear(water, LocalLightFixture.eye(), reflection, true) &&
              LocalLightFixture.clear(water, reflection, lantern.center(), true), "Eye->surface->lantern path unobstructed");
        // Canopy shades the shade sample from the zenith but not the sunlit sample.
        var shade = LocalLightFixture.samples().get("canopy-shade-grass");
        var sunlit = LocalLightFixture.samples().get("sunlit-grass");
        check(!LocalLightFixture.clear(open, shade, List.of(shade.get(0), 200.0, shade.get(2)), true), "Leaves above shade sample");
        check(LocalLightFixture.clear(open, sunlit, List.of(sunlit.get(0), 200.0, sunlit.get(2)), true), "Open sky above sunlit sample");
        // Moving variant: deterministic bounded yaw, static others.
        var moving = plans.get("lamp-night-moving");
        check(moving.moving() && LocalLightFixture.expectedYaw(moving, 0) == 180 &&
              Math.abs(LocalLightFixture.expectedYaw(moving, 2.5) - 190) < 1e-4 && LocalLightFixture.expectedYaw(open, 2.5) == 180, "Moving yaw law");
        // Solar direction at the frozen day time: vanilla sky angle, ~10.5 deg west of zenith, no north/south tilt.
        double[] sun = LocalLightFixture.sunDirection(LocalLightFixture.DAY_TIME);
        check(sun[0] < -.15 && sun[0] > -.2 && sun[1] > .98 && sun[2] == 0, "Sun direction at 7000 " + Arrays.toString(sun));
        double[] sunrise = LocalLightFixture.sunDirection(0), noon = LocalLightFixture.sunDirection(6000);
        // Vanilla's eased sky angle puts the time-0 sun ~12.4 deg above the eastern horizon.
        check(sunrise[0] > .97 && sunrise[1] > .2 && sunrise[1] < .23 && Math.abs(noon[0]) < 1e-9 && noon[1] > .999999,
            "Sun east (+X) at 0, zenith at 6000 " + Arrays.toString(sunrise));
        var dayOff = plans.get("lamp-day-off");
        check(LocalLightFixture.solarShaded(dayOff, shade) && !LocalLightFixture.solarShaded(dayOff, sunlit), "Sun-ray shade/sunlit samples");

        // ---- lamp-day-canopy: torch on grass genuinely under the oak; lights visible grass and the trunk's camera-facing face.
        var canopy = plans.get("lamp-day-canopy");
        check(geometry(canopy).equals(geometry(dayOff)) && canopy.timeOfDay() == 7000 && canopy.divider() == null && !canopy.wallPresent(),
            "Canopy vs day-off: identical geometry and frozen day");
        var canopyTorch = canopy.lamps().getFirst();
        check(canopy.lamps().size() == 1 && canopyTorch.id().equals("minecraft:torch") &&
              List.of(canopyTorch.x(), canopyTorch.y(), canopyTorch.z()).equals(List.of(403, 151, -415)), "Canopy torch at dx3,y151,dz5");
        var canopyGrid = LocalLightFixture.grid(canopy);
        check(canopyGrid.get(List.of(403, 150, -415)).id().equals("minecraft:grass_block"), "Torch stands on grass");
        check(canopyGrid.get(List.of(403, 154, -415)).id().equals("minecraft:oak_leaves") &&
              canopyGrid.get(List.of(402, 152, -416)).id().equals("minecraft:oak_log"), "Leaves above the torch; trunk beside it");
        check(LocalLightFixture.solarShaded(canopy, canopyTorch.center()), "Torch is in the canopy's sun shade");
        var torchGrass = LocalLightFixture.samples().get("canopy-torch-grass");
        var trunkFace = LocalLightFixture.samples().get("canopy-trunk-face");
        check(canopyGrid.get(List.of(403, 150, -414)).id().equals("minecraft:grass_block") && !canopyGrid.containsKey(List.of(403, 151, -414)),
            "Grass sample sits on an exposed grass top");
        check(canopyGrid.get(List.of(402, 152, -416)).id().equals("minecraft:oak_log") && !canopyGrid.containsKey(List.of(402, 152, -415)) &&
              trunkFace.get(2) > -415 && trunkFace.get(2) < -414.99, "Trunk sample is on the log's south (camera-facing) face");
        for (var entry : Map.of("canopy-torch-grass", torchGrass, "canopy-trunk-face", trunkFace).entrySet()) {
            int lit = LocalLightFixture.predictedBlockLight(canopy, entry.getValue());
            check(lit >= 12, "Canopy torch lights " + entry.getKey() + ": " + lit);
            check(LocalLightFixture.predictedBlockLight(dayOff, entry.getValue()) == 0, "Off control dark at " + entry.getKey());
            check(LocalLightFixture.clear(canopy, canopyTorch.center(), entry.getValue(), false), "Direct torch path to " + entry.getKey());
            check(LocalLightFixture.solarShaded(canopy, entry.getValue()) && LocalLightFixture.solarShaded(dayOff, entry.getValue()),
                "Sun-shaded by lab geometry: " + entry.getKey());
            check(LocalLightFixture.clear(canopy, LocalLightFixture.eye(), entry.getValue(), true), "Camera sees " + entry.getKey());
            System.out.println("canopy " + entry.getKey() + ": block light " + lit + ", pixel@FOV70 " +
                LocalLightFixture.project(entry.getValue(), 180, 22, 70, 2560, 1440));
        }
        // The canopy torch also reaches the sunlit control (model level printed); compare canopy against day-off, not sunlit-grass.
        System.out.println("canopy torch model light at sunlit-grass: " + LocalLightFixture.predictedBlockLight(canopy, sunlit));

        // ---- Colored glass pair: the night-wall divider cells with red stained glass.
        var wall = plans.get("lamp-night-wall");
        var glass = plans.get("lamp-night-glass");
        var glassOff = plans.get("lamp-night-glass-off");
        check(geometry(glass).equals(geometry(glassOff)), "Glass/glass-off geometrically identical");
        check(positions(glass).equals(positions(wall)), "Glass divider on exactly the night-wall cells");
        var glassOnly = new HashSet<>(geometry(glassOff)); glassOnly.removeAll(geometry(open));
        check(glassOnly.size() == 20 && glassOnly.stream().allMatch(p -> p.startsWith("409/") && p.endsWith("/minecraft:red_stained_glass")),
            "Glass pair adds exactly the 20-cell red glass plane");
        check(glass.divider().equals(LocalLightFixture.GLASS_DIVIDER) && !glass.wallPresent() && glassOff.lamps().isEmpty() &&
              glass.lamps().equals(wall.lamps()), "Glass: same torch as night-wall; off has none");
        for (String receiver : new String[]{"receiver-back-wall", "receiver-floor-deep", "receiver-floor-mid"}) {
            var point = LocalLightFixture.samples().get(receiver);
            check(LocalLightFixture.clear(glass, torch, point, false) && crosses(glass, torch, point, LocalLightFixture.GLASS_DIVIDER),
                "Lamp->" + receiver + " passes through the glass divider");
            check(LocalLightFixture.predictedBlockLight(glass, point) == LocalLightFixture.predictedBlockLight(plans.get("lamp-night-torch"), point) &&
                  LocalLightFixture.predictedBlockLight(glassOff, point) == 0, "Vanilla light through glass equals open; off is dark at " + receiver);
        }

        // ---- Translating first-person walk across the world-aligned 8-block boundary x=408.
        var walk = plans.get("lamp-night-walk");
        var east = plans.get("lamp-night-walk-east");
        var west = plans.get("lamp-night-walk-west");
        check(walk.walking() && !walk.moving() && !east.walking() && !west.walking(), "Only lamp-night-walk translates; yaw never oscillates");
        check(geometry(walk).equals(geometry(open)) && geometry(east).equals(geometry(open)) && geometry(west).equals(geometry(open)) &&
              walk.lamps().equals(moving.lamps()) && east.lamps().equals(walk.lamps()) && west.lamps().equals(walk.lamps()),
            "Walk scenes: open geometry, same torch+lantern");
        check(LocalLightFixture.walkEyeX(walk, -1) == 410.5 && LocalLightFixture.walkEyeX(walk, 0) == 410.5 &&
              Math.abs(LocalLightFixture.walkEyeX(walk, 4) - 408) < 1e-12 && LocalLightFixture.walkEyeX(walk, 8) == 405.5 &&
              LocalLightFixture.walkEyeX(walk, 30) == 405.5 && LocalLightFixture.walkBoundarySeconds() == 4, "Analytical route law");
        check(LocalLightFixture.walkEyeX(east, 5) == 409.5 && LocalLightFixture.walkEyeX(west, 5) == 406.5 &&
              Math.abs(east.eyeX() - 408) == Math.abs(west.eyeX() - 408), "Fixed views 1.5 m either side of the boundary");
        check(LocalLightFixture.clusterX(410.5) == 51 && LocalLightFixture.clusterX(408.0) == 51 && LocalLightFixture.clusterX(407.999) == 50 &&
              LocalLightFixture.clusterX(405.5) == 50 && LocalLightFixture.clusterX(east.eyeX()) == 51 && LocalLightFixture.clusterX(west.eyeX()) == 50 &&
              LocalLightFixture.WALK_BOUNDARY_X % 16 != 0, "One 8-block boundary, not a chunk-section boundary");
        int changes = 0, previousCluster = LocalLightFixture.clusterX(LocalLightFixture.walkEyeX(walk, 0));
        for (int step = 0; step <= 800; step++) {
            double x = LocalLightFixture.walkEyeX(walk, step * .01);
            check(LocalLightFixture.bodyClear(walk, x), "Spectator body never overlaps a placed cell or leaves the reservation at x=" + x);
            int cluster = LocalLightFixture.clusterX(x);
            if (cluster != previousCluster) changes++;
            previousCluster = cluster;
        }
        check(changes == 1, "Route crosses exactly one cluster boundary: " + changes);
        for (double x : new double[]{east.eyeX(), west.eyeX()}) check(LocalLightFixture.bodyClear(east, x), "Fixed view body clear");
        for (int step = 0; step <= 16; step++) {
            double x = LocalLightFixture.walkEyeX(walk, step * .5);
            List<Double> routeEye = List.of(x, LocalLightFixture.EYE_Y, LocalLightFixture.EYE_Z);
            for (var sample : LocalLightFixture.samples().entrySet()) {
                // The day-only shade sample is hidden by the canopy from the west part of the night route (x < ~407.5).
                boolean expectVisible = !(sample.getKey().equals("canopy-shade-grass") && x < 407.5);
                check(LocalLightFixture.clear(walk, routeEye, sample.getValue(), true) == expectVisible,
                    "Route eye x=" + x + (expectVisible ? " sees " : " canopy hides ") + sample.getKey());
                var pixel = LocalLightFixture.project(sample.getValue(), routeEye, 180, 22, 70, 2560, 1440);
                check(pixel != null && pixel.get(0) > 0 && pixel.get(0) < 2560 && pixel.get(1) > 0 && pixel.get(1) < 1440,
                    "Route eye x=" + x + " keeps " + sample.getKey() + " in frame: " + pixel);
            }
        }
        double[] onRoute = {408.0, 155.38, -402.0}, routeCamera = {408.0, 157.0, -402.0};
        check(LocalLightFixture.walkTracks(408.0, onRoute, routeCamera) && LocalLightFixture.walkTracks(408.3, onRoute, routeCamera),
            "Tick lag within tolerance accepted");
        check(!LocalLightFixture.walkTracks(408.4, onRoute, routeCamera), "Excess lag rejected");
        check(!LocalLightFixture.walkTracks(408.0, new double[]{408.0, 155.5, -402.0}, routeCamera) &&
              !LocalLightFixture.walkTracks(408.0, onRoute, new double[]{408.0, 157.0, -401.8}) &&
              !LocalLightFixture.walkTracks(405.5, new double[]{405.3, 155.38, -402.0}, new double[]{405.3, 157.0, -402.0}) &&
              !LocalLightFixture.walkTracks(408.0, onRoute, new double[]{Double.NaN, 157.0, -402.0}), "Height, depth, overshoot and NaN rejected");
        double[] westPlayer = {406.5, 155.38, -402.0}, westEye = {406.5, 157.0, -402.0};
        check(LocalLightFixture.eyeMatches(west.eyeX(), true, westPlayer, westEye, westEye) &&
              !LocalLightFixture.eyeMatches(true, westPlayer, westEye, westEye), "Fixed west eye proven only against its own pose");
        check(LocalLightFixture.eyeMatches(LocalLightFixture.walkEyeX(walk, 9), true, new double[]{405.5, 155.38, -402.0},
              new double[]{405.5, 157.0, -402.0}, new double[]{405.5, 157.0, -402.0}), "Walk capture proven at the held route end");
        // State property parsing.
        var leaf = open.placements().stream().filter(c -> c.id().equals("minecraft:oak_leaves")).findFirst().orElseThrow();
        check(LocalLightFixture.stateMatches(leaf, "minecraft:oak_leaves", "Block{minecraft:oak_leaves}[distance=1,persistent=true,waterlogged=false]"), "Persistent leaves");
        check(!LocalLightFixture.stateMatches(leaf, "minecraft:oak_leaves", "Block{minecraft:oak_leaves}[distance=1,persistent=false,waterlogged=false]"), "Decaying leaves rejected");
        var waterCell = open.placements().stream().filter(c -> c.id().equals("minecraft:water")).findFirst().orElseThrow();
        check(!LocalLightFixture.stateMatches(waterCell, "minecraft:water", "Block{minecraft:water}[level=1]"), "Flowing water rejected");
        check(leaf.state().equals("minecraft:oak_leaves[persistent=true]"), "Command state text");
        // Eye proof.
        double[] eye = {409.5, 157.0, -402.0}, player = {409.5, 155.38, -402.0};
        check(LocalLightFixture.eyeMatches(true, player, eye, eye), "Exact first-person eye accepted");
        check(!LocalLightFixture.eyeMatches(false, player, eye, eye), "Third person rejected");
        check(!LocalLightFixture.eyeMatches(true, player, eye, new double[]{409.5, 157.0, -398.0}), "Detached camera rejected");
        check(!LocalLightFixture.eyeMatches(true, new double[]{409.5, 155.5, -402.0}, new double[]{409.5, 157.12, -402.0},
            new double[]{409.5, 157.12, -402.0}), "Shifted eye rejected");
        System.out.println("Local-light fixture regressions passed (" + LocalLightFixture.SCENES.size() + " scenes, "
            + open.placements().size() + " open cells, " + plans.get("lamp-night-wall").placements().size() + " wall cells)");
    }
    private static Set<String> positions(LocalLightFixture.Plan plan) {
        Set<String> result = new HashSet<>();
        for (var cell : plan.placements()) if (!cell.role().equals("lamp")) result.add(cell.x() + "/" + cell.y() + "/" + cell.z());
        return result;
    }
    private static boolean crosses(LocalLightFixture.Plan plan, List<Double> a, List<Double> b, String id) {
        var grid = LocalLightFixture.grid(plan);
        for (int i = 1; i < 2000; i++) {
            double t = i / 2000.0;
            var cell = grid.get(List.of((int)Math.floor(a.get(0) + t * (b.get(0) - a.get(0))),
                (int)Math.floor(a.get(1) + t * (b.get(1) - a.get(1))), (int)Math.floor(a.get(2) + t * (b.get(2) - a.get(2)))));
            if (cell != null && cell.id().equals(id)) return true;
        }
        return false;
    }
    private static Set<String> geometry(LocalLightFixture.Plan plan) {
        Set<String> result = new HashSet<>();
        for (var cell : plan.placements()) if (!cell.role().equals("lamp")) result.add(cell.x() + "/" + cell.y() + "/" + cell.z() + "/" + cell.state());
        return result;
    }
}
