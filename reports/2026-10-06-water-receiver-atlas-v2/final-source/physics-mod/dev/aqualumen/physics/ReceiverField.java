package dev.aqualumen.physics;

import java.util.Objects;
import java.util.Set;

/** Bounded immutable geometry only. No Minecraft/GL dependency or invented receiver radiance. */
public final class ReceiverField {
    private ReceiverField() {}
    public enum Kind { UNKNOWN, AIR, WATER, OPAQUE, UNSUPPORTED }
    public record Cell(Kind kind, String blockId) {
        public static final Cell UNKNOWN = new Cell(Kind.UNKNOWN, "");
        public Cell {
            Objects.requireNonNull(kind); Objects.requireNonNull(blockId);
            if (kind == Kind.OPAQUE && blockId.isEmpty())
                throw new IllegalArgumentException("Opaque receiver needs a block identity");
        }
    }
    /** External boundary: loaded() must not request generation or a missing chunk. */
    public interface World {
        boolean loaded(int x, int z);
        Cell receiverCell(int x, int y, int z);
        int minY();
        int maxY(); // exclusive
    }
    public record Bounds(int x, int y, int z, int width, int height, int depth) {
        public Bounds {
            if (width < 1 || height < 1 || depth < 1 || width > 64 || height > 64 || depth > 64
                    || (long)width * height * depth > 65536
                    || (long)x + width > Integer.MAX_VALUE || (long)y + height > Integer.MAX_VALUE
                    || (long)z + depth > Integer.MAX_VALUE)
                throw new IllegalArgumentException("Receiver window exceeds bounded capacity");
        }
    }
    public record Vec(double x, double y, double z) {}
    private static final Set<String> OPAQUE_VANILLA = Set.of("minecraft:sand", "minecraft:red_sand", "minecraft:gravel",
            "minecraft:stone", "minecraft:dirt", "minecraft:grass_block", "minecraft:clay", "minecraft:sandstone",
            "minecraft:granite", "minecraft:andesite", "minecraft:diorite", "minecraft:deepslate", "minecraft:bedrock",
            "minecraft:coal_ore", "minecraft:iron_ore", "minecraft:copper_ore");
    /** Exact initial vanilla subset; block identity is not texture/tint/radiance readiness. */
    public static Cell classifyVanilla(String blockId, boolean water, boolean fluidEmpty,
                                      boolean emptyCollision, boolean fullSolid) {
        Objects.requireNonNull(blockId);
        if (fluidEmpty && emptyCollision && Set.of("minecraft:air", "minecraft:cave_air", "minecraft:void_air").contains(blockId))
            return new Cell(Kind.AIR, blockId);
        if (water && emptyCollision && blockId.equals("minecraft:water")) return new Cell(Kind.WATER, blockId);
        if (!water && fluidEmpty && fullSolid && OPAQUE_VANILLA.contains(blockId)) return new Cell(Kind.OPAQUE, blockId);
        return new Cell(Kind.UNSUPPORTED, blockId);
    }
    public enum Status { HIT, UNKNOWN, UNSUPPORTED, OUTSIDE, INSIDE, EDGE_TIE, RANGE }
    public record Result(Status status, int x, int y, int z, Cell cell,
                         double travel, Vec point, Vec normal, int enteredWaterCells) {}
    public static final class Snapshot {
        public final Bounds bounds;
        private final Cell[] cells;
        private Snapshot(Bounds bounds, Cell[] cells) { this.bounds = bounds; this.cells = cells; }
        public Cell cellAt(int x, int y, int z) {
            long dx = (long)x - bounds.x(), dy = (long)y - bounds.y(), dz = (long)z - bounds.z();
            if (dx < 0 || dy < 0 || dz < 0 || dx >= bounds.width() || dy >= bounds.height() || dz >= bounds.depth())
                return Cell.UNKNOWN;
            return cells[(int)((dy * bounds.depth() + dz) * bounds.width() + dx)];
        }
        public Result firstHit(Vec origin, Vec direction, double maxTravel) {
            double[] o = {origin.x(), origin.y(), origin.z()}, d = {direction.x(), direction.y(), direction.z()};
            for (int axis = 0; axis < 3; axis++)
                if (!Double.isFinite(o[axis]) || !Double.isFinite(d[axis])
                        || o[axis] <= Integer.MIN_VALUE || o[axis] >= Integer.MAX_VALUE)
                    throw new IllegalArgumentException("Invalid finite world ray");
            double norm = Math.sqrt(d[0]*d[0] + d[1]*d[1] + d[2]*d[2]);
            if (!Double.isFinite(norm) || Math.abs(norm - 1) > 1e-4
                    || !Double.isFinite(maxTravel) || maxTravel <= 0 || maxTravel > 48)
                throw new IllegalArgumentException("Ray must be unit length and bounded to 48 metres");
            int[] cell = new int[3], step = new int[3];
            double[] crossing = new double[3], delta = new double[3];
            for (int axis = 0; axis < 3; axis++) {
                d[axis] /= norm; cell[axis] = (int)Math.floor(o[axis]);
                step[axis] = d[axis] > 0 ? 1 : d[axis] < 0 ? -1 : 0;
                delta[axis] = step[axis] == 0 ? Double.POSITIVE_INFINITY : Math.abs(1/d[axis]);
                crossing[axis] = step[axis] == 0 ? Double.POSITIVE_INFINITY
                        : ((step[axis] > 0 ? (double)cell[axis] + 1 : cell[axis]) - o[axis])/d[axis];
            }
            double travel = 0; int water = 0;
            Vec normal = new Vec(0, 0, 0);
            // A parallel ray on an integer plane touches both voxel owners.
            // Do not silently select one side and skip an opaque/unknown neighbour.
            for (int axis = 0; axis < 3; axis++) if (step[axis] == 0 && o[axis] == cell[axis])
                return result(Status.EDGE_TIE, cell, Cell.UNKNOWN, 0, o, d, normal, 0);
            for (int visited = 0; visited < 256; visited++) {
                Cell value = cellAt(cell[0], cell[1], cell[2]);
                Status status = switch (value.kind()) {
                    case UNKNOWN -> contains(cell[0], cell[1], cell[2]) ? Status.UNKNOWN : Status.OUTSIDE;
                    case UNSUPPORTED -> Status.UNSUPPORTED;
                    case OPAQUE -> visited == 0 ? Status.INSIDE : Status.HIT;
                    default -> null;
                };
                if (status != null) return result(status, cell, value, travel, o, d, normal, water);
                if (value.kind() == Kind.WATER) water++;
                double next = Math.min(crossing[0], Math.min(crossing[1], crossing[2]));
                if (next > maxTravel) return result(Status.RANGE, cell, value, maxTravel, o, d, normal, water);
                int axis = -1;
                for (int i = 0; i < 3; i++) if (Math.abs(crossing[i] - next) <= 1e-10) {
                    if (axis != -1) return result(Status.EDGE_TIE, cell, value, next, o, d, new Vec(0, 0, 0), water);
                    axis = i;
                }
                if (axis < 0) throw new IllegalStateException("No finite voxel crossing");
                cell[axis] += step[axis]; crossing[axis] += delta[axis]; travel = next;
                normal = new Vec(axis == 0 ? -step[axis] : 0, axis == 1 ? -step[axis] : 0, axis == 2 ? -step[axis] : 0);
            }
            throw new IllegalStateException("Receiver traversal exceeded bounded steps");
        }
        private boolean contains(int x, int y, int z) {
            return (long)x >= bounds.x() && (long)x < (long)bounds.x() + bounds.width()
                    && (long)y >= bounds.y() && (long)y < (long)bounds.y() + bounds.height()
                    && (long)z >= bounds.z() && (long)z < (long)bounds.z() + bounds.depth();
        }
        private static Result result(Status status, int[] cell, Cell value, double travel,
                                     double[] o, double[] d, Vec normal, int water) {
            return new Result(status, cell[0], cell[1], cell[2], value, travel,
                    new Vec(o[0] + d[0]*travel, o[1] + d[1]*travel, o[2] + d[2]*travel), normal, water);
        }
    }
    /** Synchronous bounded capture; not a render-frame scheduler or a freshness claim. */
    public static Snapshot capture(World world, Bounds bounds) {
        Objects.requireNonNull(world); Objects.requireNonNull(bounds);
        Cell[] values = new Cell[bounds.width() * bounds.height() * bounds.depth()];
        for (int z = 0; z < bounds.depth(); z++) for (int x = 0; x < bounds.width(); x++) {
            boolean loaded = world.loaded(bounds.x() + x, bounds.z() + z);
            for (int y = 0; y < bounds.height(); y++) {
                int wy = bounds.y() + y;
                values[(y * bounds.depth() + z) * bounds.width() + x] = loaded && wy >= world.minY() && wy < world.maxY()
                        ? Objects.requireNonNull(world.receiverCell(bounds.x() + x, wy, bounds.z() + z)) : Cell.UNKNOWN;
            }
        }
        return new Snapshot(bounds, values);
    }
}
