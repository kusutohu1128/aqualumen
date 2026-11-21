package dev.aqualumen.bench;

/** Fixed no-terrain-edit camera poses in the guarded natural ocean and beach. */
final class UnderwaterScene {
    static final double SURFACE_Y = 62.8889;
    static final double EYE_TOLERANCE = .05;
    record Plan(String scene, double x, double playerY, double z, float yaw, float pitch, double eyeDepth) {}
    static boolean authorized(String name, String uuid, long seed) {
        return OcclusionFixture.authorized(name, uuid) && seed == 308060;
    }
    static boolean matches(Plan plan, boolean firstPerson, boolean submerged, String medium,
                           double[] player, double[] eye, double[] camera) {
        if (!submerged || !"WATER".equals(medium) || !OcclusionFixture.eyeMatches(firstPerson, eye, camera) ||
            player == null || player.length != 3) return false;
        for (double coordinate : player) if (!Double.isFinite(coordinate)) return false;
        return Math.abs(player[0]-plan.x()) <= EYE_TOLERANCE && Math.abs(player[1]-plan.playerY()) <= EYE_TOLERANCE &&
            Math.abs(player[2]-plan.z()) <= EYE_TOLERANCE && Math.abs(eye[0]-plan.x()) <= EYE_TOLERANCE &&
            Math.abs(eye[1]-(SURFACE_Y-plan.eyeDepth())) <= EYE_TOLERANCE && Math.abs(eye[2]-plan.z()) <= EYE_TOLERANCE;
    }
    static Plan parse(String scene) {
        if (scene.equals("underwater-shore-view"))
            return new Plan(scene, -187.5, SURFACE_Y-1.62-1.1, 327.5, 195, -27, 1.1);
        if (scene.equals("underwater-shore-moving"))
            return new Plan(scene, -187.5, SURFACE_Y-1.62-1.1, 327.5, 135, -27, 1.1);
        double depth = switch (scene) {
            case "underwater-up-near", "underwater-up-tilt" -> .5;
            case "underwater-up-deep", "underwater-up-moving" -> 3.25;
            default -> -1;
        };
        if (depth < 0) return null;
        return new Plan(scene, 448.5, SURFACE_Y - 1.62 - depth, -383.5, -45,
            scene.equals("underwater-up-tilt") || scene.equals("underwater-up-moving") ? -65 : -90, depth);
    }
}
