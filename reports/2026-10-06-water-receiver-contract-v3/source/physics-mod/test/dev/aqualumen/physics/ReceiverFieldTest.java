package dev.aqualumen.physics;

import java.util.Random;

/** Tests the real capture/traversal API, substituting only the external game boundary. */
public final class ReceiverFieldTest {
    static class Scene implements ReceiverField.World {
        public boolean loaded(int x, int z) { return true; }
        public int minY() { return -64; }
        public int maxY() { return 320; }
        public ReceiverField.Cell receiverCell(int x, int y, int z) {
            return y < 0 ? new ReceiverField.Cell(ReceiverField.Kind.OPAQUE, "minecraft:sand")
                    : new ReceiverField.Cell(ReceiverField.Kind.WATER, "minecraft:water");
        }
    }
    static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        var snapshot = ReceiverField.capture(new Scene(), new ReceiverField.Bounds(-4, -2, -4, 8, 6, 8));
        var hit = snapshot.firstHit(new ReceiverField.Vec(-1.3, 1.4, -2.5), new ReceiverField.Vec(0, -1, 0), 48);
        require(hit.status() == ReceiverField.Status.HIT && hit.x() == -2 && hit.y() == -1 && hit.z() == -3
                && Math.abs(hit.travel() - 1.4) < 1e-12 && hit.normal().equals(new ReceiverField.Vec(0, 1, 0))
                && hit.cell().blockId().equals("minecraft:sand"), "First actual floor, world cell and normal must be returned");
        System.out.println("PASS receiver first floor / negative world coordinates");
        var wall = new Scene() {
            @Override public ReceiverField.Cell receiverCell(int x, int y, int z) {
                return z == 2 || z == 4 ? new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,
                        z == 2 ? "minecraft:stone" : "minecraft:sand")
                        : new ReceiverField.Cell(ReceiverField.Kind.WATER, "minecraft:water");
            }
        };
        var closed = ReceiverField.capture(wall, new ReceiverField.Bounds(-2, -2, 0, 6, 6, 8));
        var near = closed.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 1), 48);
        require(near.status() == ReceiverField.Status.HIT && near.z() == 2
                && near.cell().blockId().equals("minecraft:stone") && Math.abs(near.travel() - 1.5) < 1e-12,
                "Closed first wall must hide the farther tagged floor");
        var boundary = closed.firstHit(new ReceiverField.Vec(0, .4, .5), new ReceiverField.Vec(0, 0, 1), 48);
        require(boundary.status() == ReceiverField.Status.EDGE_TIE,
                "A ray lying on a voxel boundary must not assign an arbitrary receiver owner");
        System.out.println("PASS first closed wall / conservative parallel boundary");
        for (var kind : new ReceiverField.Kind[]{ReceiverField.Kind.UNKNOWN, ReceiverField.Kind.UNSUPPORTED}) {
            var blocked = ReceiverField.capture(new Scene() {
                @Override public ReceiverField.Cell receiverCell(int x, int y, int z) {
                    return z == 1 ? new ReceiverField.Cell(kind, "minecraft:seagrass")
                            : wall.receiverCell(x, y, z);
                }
            }, new ReceiverField.Bounds(-2, -2, 0, 6, 6, 8));
            var stopped = blocked.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 1), 48);
            require(stopped.z() == 1 && stopped.status() == (kind == ReceiverField.Kind.UNKNOWN
                    ? ReceiverField.Status.UNKNOWN : ReceiverField.Status.UNSUPPORTED), "Unqualified cell must stop before the wall");
        }
        var unloaded = ReceiverField.capture(new Scene() {
            @Override public boolean loaded(int x, int z) { return false; }
            @Override public ReceiverField.Cell receiverCell(int x, int y, int z) {
                throw new AssertionError("Must not read an unloaded chunk");
            }
        }, new ReceiverField.Bounds(0, 0, 0, 4, 4, 4));
        require(unloaded.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 1), 48).status()
                == ReceiverField.Status.UNKNOWN, "Unloaded snapshot must remain unknown");
        require(closed.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 1), 1).status()
                == ReceiverField.Status.RANGE, "Range must not reach the distant wall");
        require(closed.firstHit(new ReceiverField.Vec(-2.3, .4, .5), new ReceiverField.Vec(0, 0, 1), 48).status()
                == ReceiverField.Status.OUTSIDE, "Out-of-window origins must not read the field");
        require(closed.firstHit(new ReceiverField.Vec(.3, .4, 2.5), new ReceiverField.Vec(0, 0, 1), 48).status()
                == ReceiverField.Status.INSIDE, "A ray beginning in solid must not invent an entry normal");
        require(closed.firstHit(new ReceiverField.Vec(.5, .5, .3), new ReceiverField.Vec(Math.sqrt(.5), Math.sqrt(.5), 0), 48).status()
                == ReceiverField.Status.EDGE_TIE, "Edge/corner ownership must remain unqualified");
        var mutable = new Scene() {
            boolean changed;
            @Override public ReceiverField.Cell receiverCell(int x, int y, int z) {
                return changed ? new ReceiverField.Cell(ReceiverField.Kind.AIR, "minecraft:air") : super.receiverCell(x, y, z);
            }
        };
        var before = ReceiverField.capture(mutable, new ReceiverField.Bounds(-4, -2, -4, 8, 6, 8));
        mutable.changed = true;
        var after = ReceiverField.capture(mutable, before.bounds);
        require(before.cellAt(-2, -1, -3).kind() == ReceiverField.Kind.OPAQUE
                && after.cellAt(-2, -1, -3).kind() == ReceiverField.Kind.AIR, "Snapshots must not follow later mutable world changes");
        for (double value : new double[]{Double.NaN, Double.POSITIVE_INFINITY, 0, 49}) {
            try {
                closed.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 1), value);
                throw new AssertionError("Invalid trace range accepted");
            } catch (IllegalArgumentException expected) { /* explicit rejection */ }
        }
        try {
            closed.firstHit(new ReceiverField.Vec(.3, .4, .5), new ReceiverField.Vec(0, 0, 2), 48);
            throw new AssertionError("Non-unit optical ray accepted");
        } catch (IllegalArgumentException expected) { /* explicit rejection */ }
        System.out.println("PASS unknown / unsupported / unloaded / bounds / ties / immutable / finite guards");
        require(ReceiverField.classifyVanilla("minecraft:sand", false, true, false, true).kind() == ReceiverField.Kind.OPAQUE
                && ReceiverField.classifyVanilla("minecraft:water", true, false, true, false).kind() == ReceiverField.Kind.WATER
                && ReceiverField.classifyVanilla("minecraft:air", false, true, true, false).kind() == ReceiverField.Kind.AIR,
                "Qualified vanilla full cube / pure water / air must be classified");
        System.out.println("PASS conservative vanilla source classification");
        for (String id : new String[]{"minecraft:glass", "minecraft:oak_leaves", "minecraft:oak_slab", "minecraft:seagrass", "other:sand"})
            require(ReceiverField.classifyVanilla(id, id.equals("minecraft:seagrass"), !id.equals("minecraft:seagrass"),
                    id.equals("minecraft:seagrass"), true).kind() == ReceiverField.Kind.UNSUPPORTED,
                    "Transparent/cutout/waterlogged/modded cells must remain unsupported: " + id);
        require(ReceiverField.classifyVanilla("minecraft:sand", false, true, false, false).kind() == ReceiverField.Kind.UNSUPPORTED
                && ReceiverField.classifyVanilla("minecraft:sand", true, false, false, true).kind() == ReceiverField.Kind.UNSUPPORTED,
                "Block identity alone does not establish full opaque geometry");
        slabOracle();
    }
    /** Independent closed-box slab intersection, not another voxel marcher. */
    static void slabOracle() {
        int[][] boxes = {{-3, 0, 8, 3, 6, 9}, {-6, -2, 18, 6, 2, 19}};
        var snapshot = ReceiverField.capture(new Scene() {
            @Override public ReceiverField.Cell receiverCell(int x, int y, int z) {
                for (int i = 0; i < boxes.length; i++) {
                    int[] b = boxes[i];
                    if (x >= b[0] && y >= b[1] && z >= b[2] && x < b[3] && y < b[4] && z < b[5])
                        return new ReceiverField.Cell(ReceiverField.Kind.OPAQUE, i == 0 ? "minecraft:stone" : "minecraft:sand");
                }
                return new ReceiverField.Cell(ReceiverField.Kind.WATER, "minecraft:water");
            }
        }, new ReceiverField.Bounds(-8, -4, 0, 16, 12, 32));
        var random = new Random(308060);
        int hits = 0;
        for (int trial = 0; trial < 512; trial++) {
            double[] o = {random.nextDouble()*10 - 5, random.nextDouble()*5 + .2, .37};
            double[] d = {random.nextDouble()*.4 - .2, random.nextDouble()*.4 - .2, 1};
            double length = Math.sqrt(d[0]*d[0] + d[1]*d[1] + 1);
            for (int k = 0; k < 3; k++) d[k] /= length;
            double best = Double.POSITIVE_INFINITY; int owner = -1, face = -1;
            for (int i = 0; i < boxes.length; i++) {
                double entry = Double.NEGATIVE_INFINITY, exit = Double.POSITIVE_INFINITY; int axis = -1;
                for (int k = 0; k < 3; k++) {
                    double a = (boxes[i][k] - o[k])/d[k], b = (boxes[i][k+3] - o[k])/d[k];
                    double near = Math.min(a, b);
                    if (near > entry) { entry = near; axis = k; }
                    exit = Math.min(exit, Math.max(a, b));
                }
                if (entry > 0 && entry <= exit && entry < best) { best = entry; owner = i; face = axis; }
            }
            var hit = snapshot.firstHit(new ReceiverField.Vec(o[0], o[1], o[2]), new ReceiverField.Vec(d[0], d[1], d[2]), 48);
            if (owner == -1) { require(hit.status() != ReceiverField.Status.HIT, "Slab miss must not invent a receiver"); continue; }
            int[] cell = new int[3];
            for (int k = 0; k < 3; k++) cell[k] = (int)Math.floor(o[k] + d[k]*(best + 1e-7));
            require(hit.status() == ReceiverField.Status.HIT && hit.x() == cell[0] && hit.y() == cell[1] && hit.z() == cell[2]
                    && Math.abs(hit.travel() - best) < 1e-10 && hit.cell().blockId().equals(owner == 0 ? "minecraft:stone" : "minecraft:sand"),
                    "First opaque cube must agree with independent closed-box intersection");
            double[] normal = {hit.normal().x(), hit.normal().y(), hit.normal().z()};
            require(normal[face] == (d[face] > 0 ? -1 : 1), "Entry-face normal must agree with independent box geometry");
            hits++;
        }
        require(hits > 100, "Independent positive controls must have adequate coverage");
        System.out.println("PASS 512 independent closed-box rays (" + hits + " positive)");
    }
}
