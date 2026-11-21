package dev.aqualumen.bench;

import java.util.ArrayList;
import java.util.List;

/** Immutable, reviewed test geometry; never authorization for an arbitrary plot. */
final class OcclusionFixture {
    static final String WORLD_NAME = "AqualumenNaturalV2";
    static final String WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d";
    static final double EYE_TOLERANCE = .05;
    record Cell(int x, int y, int z, String block) {}
    enum Cleanup { REMOVE, ALREADY_AIR, CONFLICT }
    record Plan(String scene, String range, String color, boolean wallPresent, String wallAxis,
                List<Integer> wallBounds, List<Integer> targetBounds, float yaw, float pitch, int timeOfDay,
                List<Cell> reserved, List<Cell> placements) {
        int wallZ() { return wallBounds.get(2); } // Compatibility for the original Z-plane fixtures.
        int targetZ() { return targetBounds.get(2); }
        List<List<Integer>> lights() {
            return placements.stream().filter(cell -> cell.block.equals("minecraft:sea_lantern"))
                .map(cell -> List.of(cell.x, cell.y, cell.z)).toList();
        }
    }
    static boolean authorized(String name, String id) { return WORLD_NAME.equals(name) && WORLD_ID.equals(id); }
    static Plan parse(String scene) {
        Plan forest = ForestSite.plan(scene);
        if (forest != null) return forest;
        if (List.of("ground-noon", "ground-evening", "ground-low-sun", "ground-sun-motion", "ground-camera-motion").contains(scene)) {
            List<Cell> blocks = new ArrayList<>();
            for (int x = 130; x <= 132; x++) {
                for (int z = 341; z <= 343; z++) {
                    for (int y = 63; y <= 63 + z - 341; y++) blocks.add(new Cell(x, y, z, "minecraft:stone"));
                }
            }
            for (int z = 341; z <= 343; z++) blocks.add(new Cell(136, 63, z, "minecraft:oak_fence"));
            return new Plan(scene, "natural-shore", "", false, "", List.of(), List.of(), 0, 30,
                scene.equals("ground-noon") ? 6000 : scene.equals("ground-low-sun") ? 12000 : 10600,
                List.copyOf(blocks), List.copyOf(blocks));
        }
        if (scene.equals("air-shadow-backlit") || scene.equals("air-sunlit-front") || scene.equals("air-backlit-open"))
            return oriented(scene, "west-air", "magenta", !scene.equals("air-backlit-open"), "x",
                List.of(432, 157, -387, 432, 165, -379), List.of(426, 158, -386, 426, 164, -380), 90, 0,
                scene.equals("air-sunlit-front") ? 1000 : 11000);
        if (!scene.matches("opaque-(near|far)-(open-)?(magenta|lime)")) return null;
        String[] parts = scene.split("-");
        String range = parts[1], color = parts[parts.length - 1];
        boolean closed = parts.length == 3;
        int z = range.equals("near") ? -367 : -239;
        return oriented(scene, range, color, closed, "z", List.of(444, 157, z, 452, 165, z),
            List.of(445, 158, z + 6, 451, 164, z + 6), 0, 0, 6000);
    }
    private static Plan oriented(String scene, String range, String color, boolean closed, String axis,
                                 List<Integer> wall, List<Integer> target, float yaw, float pitch, int time) {
        List<Cell> reserved = new ArrayList<>(), placed = new ArrayList<>();
        for (int x = wall.get(0); x <= wall.get(3); x++) for (int y = wall.get(1); y <= wall.get(4); y++) for (int z = wall.get(2); z <= wall.get(5); z++) {
            Cell cell = new Cell(x, y, z, "minecraft:white_concrete");
            reserved.add(cell); if (closed) placed.add(cell);
        }
        for (int x = target.get(0); x <= target.get(3); x++) for (int y = target.get(1); y <= target.get(4); y++) for (int z = target.get(2); z <= target.get(5); z++) {
            boolean corner = axis.equals("x") ? z == target.get(2) || z == target.get(5) : x == target.get(0) || x == target.get(3);
            String block = y == target.get(4) && corner ? "minecraft:sea_lantern" : "minecraft:" + color + "_concrete";
            Cell cell = new Cell(x, y, z, block); reserved.add(cell); placed.add(cell);
        }
        return new Plan(scene, range, color, closed, axis, wall, target, yaw, pitch, time, List.copyOf(reserved), List.copyOf(placed));
    }
    static Cleanup cleanupDecision(Cell cell, String actualBlock) {
        if (actualBlock.equals(cell.block)) return Cleanup.REMOVE;
        if (actualBlock.equals("minecraft:air")) return Cleanup.ALREADY_AIR;
        return Cleanup.CONFLICT;
    }
    static boolean eyeMatches(boolean firstPerson, double[] eye, double[] camera) {
        if (!firstPerson || eye.length != 3 || camera.length != 3) return false;
        double distanceSquared = 0;
        for (int i = 0; i < 3; i++) {
            if (!Double.isFinite(eye[i]) || !Double.isFinite(camera[i])) return false;
            double delta = eye[i] - camera[i]; distanceSquared += delta * delta;
        }
        return distanceSquared <= EYE_TOLERANCE * EYE_TOLERANCE;
    }
}
