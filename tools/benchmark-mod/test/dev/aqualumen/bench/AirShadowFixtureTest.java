package dev.aqualumen.bench;

/** Approved west-facing fixture behavior; no renderer clone or Minecraft writes. */
public final class AirShadowFixtureTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        var backlit = OcclusionFixture.parse("air-shadow-backlit");
        check(backlit != null && backlit.wallPresent() && backlit.reserved().size() == 130,
            "Backlit scene must expose the complete approved AIR reservation before placement");
        var front = OcclusionFixture.parse("air-sunlit-front");
        var open = OcclusionFixture.parse("air-backlit-open");
        check(front != null && open != null && front.wallPresent() && !open.wallPresent(),
            "Sunlit receiver and open backlit control must be recognized without authorizing other scenes");
        check(backlit.placements().equals(front.placements()) && backlit.reserved().equals(open.reserved()),
            "Lighting controls share exact geometry; open control still reserves the absent wall AIR plot");
        check(backlit.timeOfDay() == 11000 && front.timeOfDay() == 1000 && open.timeOfDay() == 11000,
            "Directional lighting variants freeze the approved opposed sun times");
        check(open.placements().size() == 49 && backlit.placements().size() == 130,
            "Open control places only the target; receiver variants place wall and target");
        for (var plan : new OcclusionFixture.Plan[]{backlit, front, open}) {
            check(plan.wallAxis().equals("x") && plan.yaw() == 90 && plan.pitch() == 0,
                "Actual scene view faces west with fixed orientation");
            check(plan.wallBounds().equals(java.util.List.of(432,157,-387,432,165,-379)) &&
                  plan.targetBounds().equals(java.util.List.of(426,158,-386,426,164,-380)),
                "Only the approved receiver and target planes may be reserved");
            check(plan.lights().equals(java.util.List.of(java.util.List.of(426,164,-386),java.util.List.of(426,164,-380))),
                "Two fixed upper-corner lights stay identical");
            var coordinates = new java.util.HashSet<String>();
            for (var cell : plan.reserved()) {
                check(coordinates.add(cell.x()+"/"+cell.y()+"/"+cell.z()), "Reservation contains no duplicate cells");
                boolean receiver = cell.x()==432 && cell.y()>=157 && cell.y()<=165 && cell.z()>=-387 && cell.z()<=-379;
                boolean target = cell.x()==426 && cell.y()>=158 && cell.y()<=164 && cell.z()>=-386 && cell.z()<=-380;
                check(receiver || target, "No mutation authorization outside approved plots");
            }
            for (var cell : plan.placements()) {
                check(OcclusionFixture.cleanupDecision(cell, cell.block()) == OcclusionFixture.Cleanup.REMOVE,
                    "Approved exact state may be cleaned");
                check(OcclusionFixture.cleanupDecision(cell, "minecraft:air") == OcclusionFixture.Cleanup.ALREADY_AIR,
                    "AIR cleanup is idempotent");
                check(OcclusionFixture.cleanupDecision(cell, "minecraft:stone") == OcclusionFixture.Cleanup.CONFLICT,
                    "Replacement/user terrain must never be removed");
            }
        }
        check(OcclusionFixture.parse("air-shadow-east") == null && OcclusionFixture.parse("air-sunlit-open") == null,
            "Unapproved orientation/control names do not authorize placement");
        System.out.println("Air-shadow fixture regressions passed (approved planes, light/time controls, open reservation, cleanup)");
    }
}
