package dev.aqualumen.physics;

public final class ReceiverMaterialVolumeTest {
    public static void main(String[] args) {
        var sprite = new ReceiverFace.Sprite("minecraft:textures/atlas/blocks.png", "minecraft:block/sand", 0, 1, 0, 1);
        var white = new ReceiverFace.Color(1, 1, 1);
        var face = new ReceiverFace.Face(1, 1, sprite, new ReceiverFace.UV(0,0), new ReceiverFace.UV(1,0),
                new ReceiverFace.UV(0,1), white, white, true, 15, 0, 1);
        var surface = new ReceiverMaterialVolume.Surface("minecraft:sand", face, new ReceiverTexture.Sample(0,0,200,180,150,255));
        boolean[] loaded = {true};
        int[] reads = {0};
        ReceiverMaterialVolume.Surface[] material = {surface};
        var world = new ReceiverMaterialVolume.World() {
            public boolean loaded(int x, int z) { return loaded[0]; }
            public int minY() { return 0; }
            public int maxY() { return 3; }
            public ReceiverField.Cell receiverCell(int x, int y, int z) {
                reads[0]++;
                return y == 0 ? new ReceiverField.Cell(ReceiverField.Kind.OPAQUE, "minecraft:sand") : new ReceiverField.Cell(ReceiverField.Kind.WATER, "minecraft:water");
            }
            public boolean fullWater(int x, int y, int z) { return y == 1; }
            public ReceiverMaterialVolume.Surface topSurface(int x, int y, int z) { return material[0]; }
        };
        var bounds = new ReceiverField.Bounds(0,0,0,1,3,1);
        var epoch = new ReceiverRadianceVolume.Epoch(world, 1, 1);
        var snapshot = ReceiverMaterialVolume.capture(world, bounds, epoch);
        check(snapshot.cells()[0] == 3 && snapshot.cells()[4] == 2 && snapshot.cells()[8] == 0, "Opaque/full-water/partial-water qualification");
        check(snapshot.surfaces().size() == 1 && snapshot.surfaces().get(0).pixel().red() == 200, "Actual supplied texel retained without lighting guess");
        float[] changed = snapshot.cells(); changed[0] = 0; check(snapshot.cells()[0] == 3, "Owned cell copy");
        material[0] = new ReceiverMaterialVolume.Surface("minecraft:stone", face, surface.pixel());
        check(ReceiverMaterialVolume.capture(world, bounds, epoch).surfaces().isEmpty(), "Material identity mismatch");
        material[0] = new ReceiverMaterialVolume.Surface("minecraft:sand", face, new ReceiverTexture.Sample(0,0,200,180,150,100));
        check(ReceiverMaterialVolume.capture(world, bounds, epoch).surfaces().isEmpty(), "Nonopaque texel rejected");
        material[0] = null; var unknown = ReceiverMaterialVolume.capture(world, bounds, epoch);
        check(unknown.cells()[0] == 3 && unknown.surfaces().isEmpty(), "Unavailable first source keeps first geometry");
        loaded[0] = false; reads[0] = 0;
        check(ReceiverMaterialVolume.capture(world, bounds, epoch).surfaces().isEmpty() && reads[0] == 0, "Unloaded columns are not read");
        System.out.println("ReceiverMaterialVolume CPU intake tests passed; no actual world or shaded radiance");
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
