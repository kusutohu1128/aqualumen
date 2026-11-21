package dev.aqualumen.bench;

import java.util.HashSet;

/** Tests the fixture safety/geometry seam, not a clone of shader rendering. */
public final class OcclusionFixtureTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        check(OcclusionFixture.parse("ocean-day") == null, "Ordinary scenes must not place blocks");
        check(OcclusionFixture.parse("opaque-near-red") == null, "Unknown palettes must not authorize placement");
        for (String range : new String[]{"near", "far"}) for (boolean open : new boolean[]{false, true}) {
            var magenta = OcclusionFixture.parse("opaque-" + range + "-" + (open ? "open-" : "") + "magenta");
            var lime = OcclusionFixture.parse("opaque-" + range + "-" + (open ? "open-" : "") + "lime");
            check(magenta != null && lime != null, "Known fixture variant");
            int wallZ = range.equals("near") ? -367 : -239;
            check(magenta.wallZ() == wallZ && magenta.targetZ() == wallZ + 6, "Exact approved depth");
            check(magenta.reserved().size() == 130, "Both wall/target AIR cells must be reserved even for open control");
            check(magenta.placements().size() == (open ? 49 : 130), "Only approved fixture cells are changed");
            var unique = new HashSet<String>();
            int lights = 0, colorChanges = 0;
            for (int index = 0; index < magenta.placements().size(); index++) {
                var a = magenta.placements().get(index); var b = lime.placements().get(index);
                check(a.x() == b.x() && a.y() == b.y() && a.z() == b.z(), "Palette pair must have identical geometry");
                check(unique.add(a.x() + "/" + a.y() + "/" + a.z()), "No duplicate placement/journal entries");
                check(a.x() >= 444 && a.x() <= 452 && a.y() >= 157 && a.y() <= 165, "Approved X/Y bounds");
                check(a.z() == wallZ || a.z() == wallZ + 6, "No unapproved depth placement");
                if (a.block().equals("minecraft:sea_lantern")) { lights++; check(a.equals(b), "Lighting stays identical"); }
                if (!a.block().equals(b.block())) { colorChanges++; check(a.z() == wallZ + 6, "Only behind-wall material changes"); }
                check(OcclusionFixture.cleanupDecision(a, a.block()) == OcclusionFixture.Cleanup.REMOVE, "Owned exact state may be removed");
                check(OcclusionFixture.cleanupDecision(a, "minecraft:air") == OcclusionFixture.Cleanup.ALREADY_AIR, "Repeated cleanup is safe");
                check(OcclusionFixture.cleanupDecision(a, "minecraft:stone") == OcclusionFixture.Cleanup.CONFLICT, "Never delete replacement/user terrain");
            }
            check(lights == 2 && colorChanges == 47, "Two invariant lights and 47 distinct color cells");
        }
        check(OcclusionFixture.authorized("AqualumenNaturalV2", OcclusionFixture.WORLD_ID), "Exact disposable marker accepted");
        check(!OcclusionFixture.authorized("AqualumenNatural", OcclusionFixture.WORLD_ID), "Generic natural directory is not fixture authorization");
        check(!OcclusionFixture.authorized("AqualumenNaturalV2", "00000000-0000-0000-0000-000000000000"), "Wrong UUID rejected");
        double[] eye = {448.5, 161.62, -383.5};
        check(OcclusionFixture.eyeMatches(true, eye, eye), "First-person eye accepted");
        check(!OcclusionFixture.eyeMatches(false, eye, eye), "Perspective must actually be first-person");
        check(!OcclusionFixture.eyeMatches(true, eye, new double[]{448.5, 161.62, -387.5}), "Third-person shifted camera rejected");
        check(!OcclusionFixture.eyeMatches(true, eye, new double[]{448.5, Double.NaN, -383.5}), "Non-finite eye evidence rejected");
        System.out.println("Occlusion fixture regressions passed (bounds, palettes, scope, exact-state cleanup, actual eye)");
    }
}
