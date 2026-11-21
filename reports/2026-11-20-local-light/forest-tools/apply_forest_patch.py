"""Rebuild jar-src/ from the pristine jar-src-orig/ snapshot: generate ForestSite.java from forest-site.json and patch
Recorder.java / OcclusionFixture.java / fabric.mod.json for the private forest-light JAR. Writes forest-light.patch.

Every replacement asserts its anchor occurs exactly once. Never touches tools/ in the repo.
"""
import difflib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG, WORK = HERE / "jar-src-orig", HERE / "jar-src"
BENCH = "dev/aqualumen/bench/"
SITE = json.loads((HERE / "forest-site.json").read_text())


def java_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def forest_site_java():
    cam, torch, tree = SITE["camera"], SITE["torch_slot"]["cell"], SITE["tree"]["base"]
    existing = []
    for e in SITE["existing_verified_cells"]:
        req = ", ".join(java_str(r) for r in e["required_state_substrings"])
        x, y, z = e["cell"]
        existing.append(f'        new Existing({x}, {y}, {z}, {java_str(e["id"])}, {java_str(e["role"])}, new String[]{{{req}}})')
    existing_text = ",\n".join(existing)
    return f'''package dev.aqualumen.bench;

import java.util.*;

/** PRIVATE scratch-only natural forest torch comparison site (generated from forest-tools/forest-site.json).
 * Aliases reuse the accepted OcclusionFixture scene keys only inside this private JAR:
 *   ground-noon / ground-evening / ground-low-sun  -> day 9800: off / torch / soul_torch
 *   air-shadow-backlit / air-sunlit-front / air-backlit-open -> night 15500: off / torch / soul_torch (optional)
 * One pose, one reserved exact-AIR torch slot on a natural grass block; nothing else is ever placed.
 * Existing bark/leaves/support blocks are only read and verified, never changed.
 */
final class ForestSite {{
    static final String RANGE = "forest-torch";
    static final long SEED = 308060L;
    static final double X = {cam["feet"][0]}, Y = {cam["feet"][1]}, Z = {cam["feet"][2]}, EYE_HEIGHT = {cam["eye_height"]}, POSE_TOLERANCE = .05;
    static final float YAW = {cam["yaw"]}f, PITCH = {cam["pitch"]}f;
    static final int TORCH_X = {torch[0]}, TORCH_Y = {torch[1]}, TORCH_Z = {torch[2]};
    static final int TREE_X = {tree[0]}, TREE_Y = {tree[1]}, TREE_Z = {tree[2]};
    static final int DAY_TIME = {SITE["time_day"]}, NIGHT_TIME = {SITE["time_night_optional"]};
    static final Map<String, String> VARIANT = Map.of("ground-noon", "off", "ground-evening", "warm", "ground-low-sun", "soul",
        "air-shadow-backlit", "night-off", "air-sunlit-front", "night-warm", "air-backlit-open", "night-soul");
    record Existing(int x, int y, int z, String id, String role, String[] required) {{}}
    static final List<Existing> EXISTING = List.of(
{existing_text});

    static boolean alias(String scene) {{ return scene != null && VARIANT.containsKey(scene); }}
    static boolean authorized(String name, String id, long seed) {{ return OcclusionFixture.authorized(name, id) && seed == SEED; }}
    static String variant(String scene) {{ return VARIANT.get(scene); }}
    static boolean night(String scene) {{ return alias(scene) && variant(scene).startsWith("night-"); }}
    static int time(String scene) {{ return night(scene) ? NIGHT_TIME : DAY_TIME; }}
    static String torchBlock(String scene) {{
        String v = variant(scene);
        if (v == null) return null;
        return v.endsWith("warm") ? "minecraft:torch" : v.endsWith("soul") ? "minecraft:soul_torch" : null;
    }}
    static int camX() {{ return (int)Math.floor(X); }}
    static int camZ() {{ return (int)Math.floor(Z); }}
    static List<Double> eye() {{ return List.of(X, Y + EYE_HEIGHT, Z); }}
    static boolean torchCell(int x, int y, int z) {{ return x == TORCH_X && y == TORCH_Y && z == TORCH_Z; }}

    static OcclusionFixture.Plan plan(String scene) {{
        if (!alias(scene)) return null;
        List<OcclusionFixture.Cell> reserved = new ArrayList<>(), placed = new ArrayList<>();
        reserved.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y, TORCH_Z, "minecraft:air"));
        reserved.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y + 1, TORCH_Z, "minecraft:air"));
        for (int dy = 0; dy <= 2; dy++) reserved.add(new OcclusionFixture.Cell(camX(), (int)Y + dy, camZ(), "minecraft:air"));
        String block = torchBlock(scene);
        if (block != null) placed.add(new OcclusionFixture.Cell(TORCH_X, TORCH_Y, TORCH_Z, block));
        return new OcclusionFixture.Plan(scene, RANGE, "", false, "", List.of(), List.of(), YAW, PITCH, time(scene),
            List.copyOf(reserved), List.copyOf(placed));
    }}
    /** Every required state substring must appear in BlockState#toString, e.g. persistent=false for natural leaves. */
    static boolean matches(Existing e, String actualId, String stateText) {{
        if (!e.id().equals(actualId) || stateText == null) return false;
        for (String need : e.required()) if (!stateText.contains(need)) return false;
        return true;
    }}
    static boolean poseMatches(double[] player, double[] eye, double[] camera) {{
        if (player == null || eye == null || camera == null || player.length != 3 || eye.length != 3 || camera.length != 3) return false;
        double[] want = {{X, Y, Z}}, wantEye = {{X, Y + EYE_HEIGHT, Z}};
        for (int i = 0; i < 3; i++) {{
            if (!Double.isFinite(player[i]) || !Double.isFinite(eye[i]) || !Double.isFinite(camera[i])) return false;
            if (Math.abs(player[i] - want[i]) > POSE_TOLERANCE || Math.abs(eye[i] - wantEye[i]) > POSE_TOLERANCE || Math.abs(camera[i] - wantEye[i]) > POSE_TOLERANCE) return false;
        }}
        return true;
    }}
    /** Named world-space samples (1 mm on the air side of the bark face) projected into the captured frame. */
    static Map<String, List<Double>> samples() {{
        Map<String, List<Double>> m = new LinkedHashMap<>();
        m.put("torch-flame", List.of(TORCH_X + .5, TORCH_Y + .65, TORCH_Z + .5));
        m.put("torch-base-ground", List.of(TORCH_X + .5, TORCH_Y + .001, TORCH_Z + .5));
        m.put("trunk-bark-low", List.of(TREE_X + .5, TREE_Y + .5, TREE_Z - .001));
        m.put("trunk-bark-mid", List.of(TREE_X + .5, TREE_Y + 1.5, TREE_Z - .001));
        m.put("trunk-bark-high", List.of(TREE_X + .5, TREE_Y + 3.5, TREE_Z - .001));
        m.put("trunk-root-ground", List.of(TREE_X + .5, TREE_Y + .001, TREE_Z - .5));
        return m;
    }}
    static Map<String, Object> mapping() {{
        Map<String, Object> m = new LinkedHashMap<>();
        for (String scene : List.of("ground-noon", "ground-evening", "ground-low-sun", "air-shadow-backlit", "air-sunlit-front", "air-backlit-open")) {{
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("variant", variant(scene)); item.put("torch_block", torchBlock(scene) == null ? "none" : torchBlock(scene));
            item.put("world_time", time(scene));
            m.put(scene, item);
        }}
        return m;
    }}
    static Map<String, Object> metadata(OcclusionFixture.Plan plan) {{
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
    }}
    static Map<String, Object> siteMetadata() {{
        Map<String, Object> m = new LinkedHashMap<>(metadata(plan("ground-evening")));
        m.remove("variant"); m.remove("torch_block"); m.remove("requested_world_time");
        m.put("scene_key_mapping", mapping());
        m.put("tree_base", List.of(TREE_X, TREE_Y, TREE_Z));
        m.put("existing_cells", EXISTING.stream().map(e -> List.of(e.x(), e.y(), e.z(), e.id(), e.role())).toList());
        m.put("method", "private JAR: accepted OcclusionFixture scene keys are aliased onto one natural forest pose; only the exact-AIR torch slot is ever mutated; bark/leaves/support are read-only verified");
        return m;
    }}
}}
'''


def forest_test_java():
    t = SITE["torch_slot"]
    px = t["pixel_2560x1440_fov70"]
    return f'''package dev.aqualumen.bench;

import java.util.*;

/** CPU-only checks of the private forest alias plans; cross-checks the Python projection against LocalLightFixture.project. */
public final class ForestSiteTest {{
    static void check(boolean ok, String message) {{ if (!ok) throw new AssertionError(message); }}
    public static void main(String[] args) {{
        String[] day = {{"ground-noon", "ground-evening", "ground-low-sun"}}, night = {{"air-shadow-backlit", "air-sunlit-front", "air-backlit-open"}};
        String[] blocks = {{null, "minecraft:torch", "minecraft:soul_torch"}};
        for (int i = 0; i < 3; i++) {{
            OcclusionFixture.Plan d = OcclusionFixture.parse(day[i]), n = OcclusionFixture.parse(night[i]);
            check(d != null && n != null && d.range().equals(ForestSite.RANGE), "alias plans resolve to the forest range");
            check(d.timeOfDay() == ForestSite.DAY_TIME && n.timeOfDay() == ForestSite.NIGHT_TIME, "day/night frozen times");
            check(d.timeOfDay() >= 9200 && d.timeOfDay() <= 10200, "late-afternoon band 9200..10200");
            check(d.yaw() == ForestSite.YAW && d.pitch() == ForestSite.PITCH && d.yaw() == n.yaw() && d.pitch() == n.pitch(), "same pose for every variant");
            check(d.reserved().equals(n.reserved()) && d.reserved().size() == 5, "same five reserved exact-AIR cells");
            check(d.placements().size() == (blocks[i] == null ? 0 : 1) && n.placements().size() == d.placements().size(), "placement count per variant");
            if (blocks[i] != null) check(d.placements().getFirst().block().equals(blocks[i]) && n.placements().getFirst().block().equals(blocks[i]), "torch block per variant");
            for (OcclusionFixture.Cell c : d.reserved()) check(c.block().equals("minecraft:air"), "reserved cells expect AIR");
        }}
        // Original ground motion scenes and other fixtures are untouched by the alias table.
        check(!ForestSite.alias("ground-sun-motion") && !ForestSite.alias("ground-camera-motion"), "motion scenes are not aliased");
        check(OcclusionFixture.parse("ground-sun-motion").range().equals("natural-shore"), "ground-sun-motion remains the natural-shore plan");
        check(OcclusionFixture.parse("opaque-near-magenta") != null && !OcclusionFixture.parse("opaque-near-magenta").range().equals(ForestSite.RANGE), "opaque scenes unchanged");
        // Pose: eye 1.62 above the feet; camera must match within 0.05 m.
        double[] feet = {{ForestSite.X, ForestSite.Y, ForestSite.Z}}, eye = {{ForestSite.X, ForestSite.Y + 1.62, ForestSite.Z}};
        check(ForestSite.poseMatches(feet, eye, eye), "exact pose matches");
        check(!ForestSite.poseMatches(new double[]{{feet[0] + .06, feet[1], feet[2]}}, eye, eye), "0.06 m drift rejected");
        check(!ForestSite.poseMatches(feet, new double[]{{eye[0], eye[1] + .06, eye[2]}}, eye), "eye height drift rejected");
        // Projection cross-check against the Python analysis (FOV 70, 2560x1440, requested rotation).
        List<Double> p = LocalLightFixture.project(ForestSite.samples().get("torch-flame"), ForestSite.eye(), ForestSite.YAW, ForestSite.PITCH, 70, 2560, 1440);
        check(p != null && Math.abs(p.get(0) - {px[0]}) < 0.2 && Math.abs(p.get(1) - {px[1]}) < 0.2, "torch pixel matches Python projection: " + p);
        // State matching: natural leaves keep persistent=false; torch support is a grass block.
        ForestSite.Existing leaf = null;
        for (ForestSite.Existing e : ForestSite.EXISTING) if (e.id().endsWith("_leaves")) {{ leaf = e; break; }}
        check(leaf != null && ForestSite.matches(leaf, leaf.id(), "Block{{" + leaf.id() + "}}[distance=2,persistent=false,waterlogged=false]"), "natural leaf state accepted");
        check(!ForestSite.matches(leaf, leaf.id(), "Block{{" + leaf.id() + "}}[distance=1,persistent=true,waterlogged=false]"), "player-placed leaf state rejected");
        check(!ForestSite.matches(leaf, "minecraft:air", "Block{{minecraft:air}}"), "replaced leaf rejected");
        int logs = 0; boolean supportOk = false;
        for (ForestSite.Existing e : ForestSite.EXISTING) {{
            if (e.role().equals("target_trunk_log")) logs++;
            if (e.role().equals("torch_support") && e.x() == ForestSite.TORCH_X && e.y() == ForestSite.TORCH_Y - 1 && e.z() == ForestSite.TORCH_Z && e.id().equals("minecraft:grass_block")) supportOk = true;
        }}
        check(logs >= 4 && supportOk, "target trunk and grass support present in the verified list");
        Set<List<Integer>> seen = new HashSet<>();
        for (ForestSite.Existing e : ForestSite.EXISTING) check(seen.add(List.of(e.x(), e.y(), e.z())), "no duplicate verified cell");
        for (ForestSite.Existing e : ForestSite.EXISTING) check(!ForestSite.torchCell(e.x(), e.y(), e.z()), "torch slot is never an existing-block check");
        System.out.println("ForestSiteTest OK");
    }}
}}
'''


def sub(text, old, new, count=1):
    assert text.count(old) == count, f"anchor found {text.count(old)}x (expected {count}): {old[:90]!r}"
    return text.replace(old, new)


def patch_recorder(t):
    t = sub(t, "    private static volatile Map<String, Object> localValidation;\n",
            "    private static volatile Map<String, Object> localValidation;\n"
            "    private static volatile Map<String, Object> forestValidation;\n    private static CompletableFuture<Void> forestValidationTask;\n")
    t = sub(t, '        if (plan.range().equals("natural-shore")) return map("range", plan.range(),',
            '        if (plan.range().equals(ForestSite.RANGE)) return ForestSite.metadata(plan);\n'
            '        if (plan.range().equals("natural-shore")) return map("range", plan.range(),')
    t = sub(t, '        if (plan.range().equals("natural-shore")) for (OcclusionFixture.Cell cell : plan.placements()) {',
            '        if (plan.range().equals(ForestSite.RANGE)) forestValidate(plan, false, true); // torch slot still AIR; bark/leaves/support exact\n'
            '        if (plan.range().equals("natural-shore")) for (OcclusionFixture.Cell cell : plan.placements()) {')
    t = sub(t, '        Map<String, Object> evidence = fixtureJournal(plan, conflicts.isEmpty() ? "cleaned-to-air" : "cleanup-conflict");',
            '        Map<String, Object> forestPost = null;\n'
            '        if (plan.range().equals(ForestSite.RANGE)) {\n'
            '            forestPost = forestValidate(plan, false, false); // torch slot AIR again and every existing cell untouched\n'
            '            if (!Boolean.TRUE.equals(forestPost.get("passed")))\n'
            '                conflicts.add(map("x", ForestSite.TORCH_X, "y", ForestSite.TORCH_Y, "z", ForestSite.TORCH_Z, "actual_block", "forest post-cleanup validation failed: " + forestPost.get("mismatches")));\n'
            '        }\n'
            '        Map<String, Object> evidence = fixtureJournal(plan, conflicts.isEmpty() ? "cleaned-to-air" : "cleanup-conflict");\n'
            '        if (forestPost != null) evidence.put("forest_post_cleanup_validation", forestPost);')
    t = sub(t, "    private static boolean fixturesPending() {",
            '''    /** Server thread. Exact verification of the natural forest site: read-only bark/leaves/support and the reserved AIR slot. */
    private static Map<String, Object> forestValidate(OcclusionFixture.Plan plan, boolean expectTorch, boolean strict) throws Exception {
        fixtureScope();
        if (!ForestSite.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))) ||
            (long)call(serverWorld, "method_8412") != ForestSite.SEED)
            throw new IllegalStateException("Forest torch site requires the exact dedicated AqualumenNaturalV2 UUID and seed308060");
        ArrayList<String> mismatches = new ArrayList<>();
        int existingOk = 0, reservedOk = 0;
        for (ForestSite.Existing e : ForestSite.EXISTING) {
            if (ForestSite.matches(e, blockAt(e.x(), e.y(), e.z()), stateText(e.x(), e.y(), e.z()))) existingOk++;
            else mismatches.add(e.role() + "@" + e.x() + "," + e.y() + "," + e.z() + "=" + stateText(e.x(), e.y(), e.z()));
        }
        for (OcclusionFixture.Cell cell : plan.reserved()) {
            String expected = expectTorch && !plan.placements().isEmpty() && ForestSite.torchCell(cell.x(), cell.y(), cell.z()) ? plan.placements().getFirst().block() : "minecraft:air";
            if (blockAt(cell.x(), cell.y(), cell.z()).equals(expected)) reservedOk++;
            else mismatches.add("reserved@" + cell.x() + "," + cell.y() + "," + cell.z() + " expected " + expected + " found " + stateText(cell.x(), cell.y(), cell.z()));
        }
        if (strict && !mismatches.isEmpty())
            throw new IllegalStateException("Forest torch site validation failed (" + mismatches.size() + "): " + mismatches.subList(0, Math.min(5, mismatches.size())));
        return map("passed", mismatches.isEmpty(), "scene", plan.scene(), "expect_torch", expectTorch, "existing_cells_exact", existingOk,
            "existing_cells_expected", ForestSite.EXISTING.size(), "reserved_cells_exact", reservedOk, "reserved_cells_expected", plan.reserved().size(),
            "mismatches", mismatches, "server_world_time", (long)call(serverWorld, "method_8532"), "utc", Instant.now().toString());
    }
    private static boolean fixturesPending() {''')
    t = sub(t, "        String scene = scenarios[stage];\n        LocalLightFixture.Plan lampPlan = LocalLightFixture.parse(scene);\n",
            "        String scene = scenarios[stage];\n"
            '        if (ForestSite.alias(scene)) return new Site(ForestSite.X, ForestSite.Y, ForestSite.Z, ForestSite.YAW, ForestSite.PITCH, "natural-forest-torch-site", 0);\n'
            "        LocalLightFixture.Plan lampPlan = LocalLightFixture.parse(scene);\n")
    t = sub(t, '            if (Arrays.stream(scenarios).anyMatch(scene -> OcclusionFixture.parse(scene) != null)) sites.put("opaque", new Site(448.5, 160, -383.5, 0, 0, "temporary-opaque-air-fixture", 0));',
            '            if (Arrays.stream(scenarios).anyMatch(scene -> OcclusionFixture.parse(scene) != null && !ForestSite.alias(scene))) sites.put("opaque", new Site(448.5, 160, -383.5, 0, 0, "temporary-opaque-air-fixture", 0));\n'
            '            if (Arrays.stream(scenarios).anyMatch(ForestSite::alias)) sites.put("forest", new Site(ForestSite.X, ForestSite.Y, ForestSite.Z, ForestSite.YAW, ForestSite.PITCH, "natural-forest-torch-site", 0));')
    t = sub(t, "        localValidation = null; localValidationTask = null;\n        walkRoute.setLength(0);",
            "        localValidation = null; localValidationTask = null; forestValidation = null; forestValidationTask = null;\n        walkRoute.setLength(0);")
    t = sub(t, '"workload", LocalLightFixture.parse(name) != null ? "local-light-test" :',
            '"workload", ForestSite.alias(name) ? "forest-torch-comparison" : LocalLightFixture.parse(name) != null ? "local-light-test" :')
    t = sub(t, '            row.put("opaque_fixture", fixtureRow); row.put("actual_eye_position", List.of(eye[0], eye[1], eye[2]));',
            '''            if (ForestSite.alias(name)) {
                if (!ForestSite.poseMatches(new double[]{px, py, pz}, eye, rendered))
                    throw new IllegalStateException("Forest torch site requires the exact natural-site first-person eye");
                Map<String, Object> validation = forestValidation;
                if (validation == null || !Boolean.TRUE.equals(validation.get("passed"))) throw new IllegalStateException("Forest block validation missing before capture");
                Map<String, Object> pixels = new LinkedHashMap<>();
                Object fov;
                try { fov = option("method_41808"); } catch (Exception error) { fov = "Unavailable: " + error.getClass().getSimpleName(); }
                if (fov instanceof Integer degrees) {
                    List<Integer> frame = size(mc, true);
                    List<Double> eyeAt = List.of(eye[0], eye[1], eye[2]);
                    ForestSite.samples().forEach((sample, point) -> pixels.put(sample, LocalLightFixture.project(point, eyeAt, renderedYaw, renderedPitch, degrees, frame.get(0), frame.get(1))));
                }
                fixtureRow.put("forest_light", map("variant", ForestSite.variant(name), "torch_block", ForestSite.torchBlock(name) == null ? "none" : ForestSite.torchBlock(name),
                    "pose_tolerance_m", ForestSite.POSE_TOLERANCE, "pose_exact", true, "pre_sample_validation", validation,
                    "camera_submersion_type", ((Enum<?>)call(camera, "method_19334")).name(), "options_fov_degrees", fov,
                    "sample_pixels_pinhole_projection", map("method", "Pinhole projection with actual rendered yaw/pitch, options FOV and framebuffer size; top-left origin", "pixels", pixels)));
            }
            row.put("opaque_fixture", fixtureRow); row.put("actual_eye_position", List.of(eye[0], eye[1], eye[2]));''')
    t = sub(t, "                    LocalLightFixture.Plan lamp = LocalLightFixture.parse(scenarios[stage]);\n                    if (lamp != null && localValidation == null) {",
            '''                    OcclusionFixture.Plan forestPlan = ForestSite.alias(scenarios[stage]) ? OcclusionFixture.parse(scenarios[stage]) : null;
                    if (forestPlan != null && forestValidation == null) {
                        // Server thread, before sampling: exact torch state, reserved AIR, natural bark/leaves/support.
                        if (forestValidationTask == null) { forestValidationTask = local(() -> forestValidation = forestValidate(forestPlan, true, true)); return; }
                        if (!forestValidationTask.isDone()) return;
                        forestValidationTask.join();
                        if (forestValidation == null) throw new IllegalStateException("Forest validation produced no evidence");
                    }
                    LocalLightFixture.Plan lamp = LocalLightFixture.parse(scenarios[stage]);
                    if (lamp != null && localValidation == null) {''')
    t = sub(t, '        if (fixturesPending())\n            throw new IllegalStateException("An unresolved opaque/local-light fixture journal requires scoped review before a new run");',
            '''        if (Arrays.stream(scenarios).anyMatch(ForestSite::alias) && (!Arrays.stream(scenarios).allMatch(ForestSite::alias) || captureMotion || recordGroundClip || fullFrameClip ||
            !ForestSite.authorized(config.getProperty("world"), config.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed"))) ||
            !ForestSite.authorized(worldPath.getFileName().toString(), worldMarker.getProperty("world_id"), Long.parseLong(worldMarker.getProperty("seed")))))
            throw new IllegalStateException("Forest torch scenes must run alone (no clip/motion capture) in the exact dedicated AqualumenNaturalV2 UUID and seed308060");
        if (fixturesPending())
            throw new IllegalStateException("An unresolved opaque/local-light fixture journal requires scoped review before a new run");''')
    t = sub(t, '        if (Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null)) {\n            metadata.put("local_light_fixture_plans"',
            '''        if (Arrays.stream(scenarios).allMatch(ForestSite::alias)) {
            metadata.put("terrain_fixture", "Natural forest site: only one standing torch/soul_torch is placed in a reserved exact-AIR cell on a natural grass block; bark, roots, grass and leaves are read-only verified and never changed; cleanup returns the slot to AIR");
            metadata.put("visual_validation_limits", "Private-JAR scene-key aliases (ground-noon=off, ground-evening=warm torch, ground-low-sun=soul torch at frozen late-afternoon time; air-* keys are the optional night trio). Same pose for all; sequential screenshots, so clouds, exposure and foliage wind are not pixel-locked.");
            metadata.put("forest_site", ForestSite.siteMetadata());
        }
        if (Arrays.stream(scenarios).anyMatch(scene -> LocalLightFixture.parse(scene) != null)) {
            metadata.put("local_light_fixture_plans"''')
    return t


def main():
    WORK.mkdir(exist_ok=True)
    changed = {}
    for name, fn in ((BENCH + "Recorder.java", patch_recorder),
                     (BENCH + "OcclusionFixture.java", lambda t: sub(t, '        if (List.of("ground-noon", "ground-evening", "ground-low-sun", "ground-sun-motion", "ground-camera-motion").contains(scene)) {',
                                                                    '        Plan forest = ForestSite.plan(scene);\n        if (forest != null) return forest;\n'
                                                                    '        if (List.of("ground-noon", "ground-evening", "ground-low-sun", "ground-sun-motion", "ground-camera-motion").contains(scene)) {')),
                     ("fabric.mod.json", lambda t: sub(sub(t, '"version": "0.3.9"', '"version": "0.3.9-forest-light"'),
                                                       '"name": "Aqualumen Local Benchmark"', '"name": "Aqualumen Local Benchmark (private forest-light build)"'))):
        orig = (ORIG / name).read_text()
        new = fn(orig)
        (WORK / name).write_text(new)
        changed[name] = (orig, new)
    (WORK / BENCH / "ForestSite.java").write_text(forest_site_java())
    test_dir = WORK / "test" / "dev/aqualumen/bench"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "ForestSiteTest.java").write_text(forest_test_java())
    diff = []
    for name, (orig, new) in changed.items():
        diff += difflib.unified_diff(orig.splitlines(True), new.splitlines(True), f"a/{name}", f"b/{name}")
    for name in (BENCH + "ForestSite.java", "test/dev/aqualumen/bench/ForestSiteTest.java"):
        diff += difflib.unified_diff([], (WORK / name).read_text().splitlines(True), "/dev/null", f"b/{name}")
    (HERE / "forest-light.patch").write_text("".join(diff))
    print("patched:", ", ".join(changed), "+ ForestSite.java + ForestSiteTest.java; patch lines:", len(diff))


if __name__ == "__main__":
    main()
