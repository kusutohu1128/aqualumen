package dev.aqualumen.bench;

import java.util.*;

/** CPU-only checks of the private forest alias plans; cross-checks the Python projection against LocalLightFixture.project. */
public final class ForestSiteTest {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static void main(String[] args) {
        String[] day = {"ground-noon", "ground-evening", "ground-low-sun"}, night = {"air-shadow-backlit", "air-sunlit-front", "air-backlit-open"};
        String[] blocks = {null, "minecraft:torch", "minecraft:soul_torch"};
        for (int i = 0; i < 3; i++) {
            OcclusionFixture.Plan d = OcclusionFixture.parse(day[i]), n = OcclusionFixture.parse(night[i]);
            check(d != null && n != null && d.range().equals(ForestSite.RANGE), "alias plans resolve to the forest range");
            check(d.timeOfDay() == ForestSite.DAY_TIME && n.timeOfDay() == ForestSite.NIGHT_TIME, "day/night frozen times");
            check(d.timeOfDay() >= 9200 && d.timeOfDay() <= 10200, "late-afternoon band 9200..10200");
            check(d.yaw() == ForestSite.YAW && d.pitch() == ForestSite.PITCH && d.yaw() == n.yaw() && d.pitch() == n.pitch(), "same pose for every variant");
            check(d.reserved().equals(n.reserved()) && d.reserved().size() == 5, "same five reserved exact-AIR cells");
            check(d.placements().size() == (blocks[i] == null ? 0 : 1) && n.placements().size() == d.placements().size(), "placement count per variant");
            if (blocks[i] != null) check(d.placements().getFirst().block().equals(blocks[i]) && n.placements().getFirst().block().equals(blocks[i]), "torch block per variant");
            for (OcclusionFixture.Cell c : d.reserved()) check(c.block().equals("minecraft:air"), "reserved cells expect AIR");
        }
        // Original ground motion scenes and other fixtures are untouched by the alias table.
        check(!ForestSite.alias("ground-sun-motion") && !ForestSite.alias("ground-camera-motion"), "motion scenes are not aliased");
        check(OcclusionFixture.parse("ground-sun-motion").range().equals("natural-shore"), "ground-sun-motion remains the natural-shore plan");
        check(OcclusionFixture.parse("opaque-near-magenta") != null && !OcclusionFixture.parse("opaque-near-magenta").range().equals(ForestSite.RANGE), "opaque scenes unchanged");
        // Pose: eye 1.62 above the feet; camera must match within 0.05 m.
        double[] feet = {ForestSite.X, ForestSite.Y, ForestSite.Z}, eye = {ForestSite.X, ForestSite.Y + 1.62, ForestSite.Z};
        check(ForestSite.poseMatches(feet, eye, eye), "exact pose matches");
        check(!ForestSite.poseMatches(new double[]{feet[0] + .06, feet[1], feet[2]}, eye, eye), "0.06 m drift rejected");
        check(!ForestSite.poseMatches(feet, new double[]{eye[0], eye[1] + .06, eye[2]}, eye), "eye height drift rejected");
        // Projection cross-check against the Python analysis (FOV 70, 2560x1440, requested rotation).
        List<Double> p = LocalLightFixture.project(ForestSite.samples().get("torch-flame"), ForestSite.eye(), ForestSite.YAW, ForestSite.PITCH, 70, 2560, 1440);
        check(p != null && Math.abs(p.get(0) - 1304.2) < 0.2 && Math.abs(p.get(1) - 1000.2) < 0.2, "torch pixel matches Python projection: " + p);
        // State matching: natural leaves keep persistent=false; torch support is a grass block.
        ForestSite.Existing leaf = null;
        for (ForestSite.Existing e : ForestSite.EXISTING) if (e.id().endsWith("_leaves")) { leaf = e; break; }
        check(leaf != null && ForestSite.matches(leaf, leaf.id(), "Block{" + leaf.id() + "}[distance=2,persistent=false,waterlogged=false]"), "natural leaf state accepted");
        check(!ForestSite.matches(leaf, leaf.id(), "Block{" + leaf.id() + "}[distance=1,persistent=true,waterlogged=false]"), "player-placed leaf state rejected");
        check(!ForestSite.matches(leaf, "minecraft:air", "Block{minecraft:air}"), "replaced leaf rejected");
        int logs = 0; boolean supportOk = false;
        for (ForestSite.Existing e : ForestSite.EXISTING) {
            if (e.role().equals("target_trunk_log")) logs++;
            if (e.role().equals("torch_support") && e.x() == ForestSite.TORCH_X && e.y() == ForestSite.TORCH_Y - 1 && e.z() == ForestSite.TORCH_Z && e.id().equals("minecraft:grass_block")) supportOk = true;
        }
        check(logs >= 4 && supportOk, "target trunk and grass support present in the verified list");
        Set<List<Integer>> seen = new HashSet<>();
        for (ForestSite.Existing e : ForestSite.EXISTING) check(seen.add(List.of(e.x(), e.y(), e.z())), "no duplicate verified cell");
        for (ForestSite.Existing e : ForestSite.EXISTING) check(!ForestSite.torchCell(e.x(), e.y(), e.z()), "torch slot is never an existing-block check");
        System.out.println("ForestSiteTest OK");
    }
}
