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
    record Plan(String scene, String range, String color, boolean wallPresent, int wallZ,
                List<Cell> reserved, List<Cell> placements) {
        int targetZ() { return wallZ + 6; }
    }
    static boolean authorized(String name, String id) { return WORLD_NAME.equals(name) && WORLD_ID.equals(id); }
    static Plan parse(String scene) {
        if (!scene.matches("opaque-(near|far)-(open-)?(magenta|lime)")) return null;
        String[] parts = scene.split("-");
        String range = parts[1], color = parts[parts.length - 1];
        boolean closed = parts.length == 3;
        int z = range.equals("near") ? -367 : -239;
        List<Cell> reserved = new ArrayList<>(), placed = new ArrayList<>();
        for (int x = 444; x <= 452; x++) for (int y = 157; y <= 165; y++) {
            Cell cell = new Cell(x, y, z, "minecraft:white_concrete");
            reserved.add(cell); if (closed) placed.add(cell);
        }
        for (int x = 445; x <= 451; x++) for (int y = 158; y <= 164; y++) {
            String block = y == 164 && (x == 445 || x == 451) ? "minecraft:sea_lantern" : "minecraft:" + color + "_concrete";
            Cell cell = new Cell(x, y, z + 6, block); reserved.add(cell); placed.add(cell);
        }
        return new Plan(scene, range, color, closed, z, List.copyOf(reserved), List.copyOf(placed));
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
