package dev.aqualumen.physics;

final class LoadedReceiverMaterialWorld implements ReceiverMaterialVolume.World {
    private final LoadedReceiverWorld geometry;
    private final LoadedReceiverFaces faces;
    private final Thread owner;

    LoadedReceiverMaterialWorld(Object client, Object world) throws ReflectiveOperationException {
        if (!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Receiver material capture outside render thread");
        owner = Thread.currentThread();
        geometry = new LoadedReceiverWorld(world);
        faces = new LoadedReceiverFaces(client, world);
    }

    private void owner() {
        if (Thread.currentThread() != owner) throw new IllegalStateException("Receiver capture changed owner thread");
    }
    public boolean loaded(int x, int z) { owner(); return geometry.loaded(x, z); }
    public int minY() { owner(); return geometry.minY(); }
    public int maxY() { owner(); return geometry.maxY(); }
    public ReceiverField.Cell receiverCell(int x, int y, int z) { owner(); return geometry.receiverCell(x, y, z); }
    public boolean fullWater(int x, int y, int z) {
        return y + 1 < maxY() && receiverCell(x, y, z).kind() == ReceiverField.Kind.WATER &&
               receiverCell(x, y + 1, z).kind() == ReceiverField.Kind.WATER;
    }
    public ReceiverMaterialVolume.Surface topSurface(int x, int y, int z) {
        var cell = receiverCell(x, y, z);
        if (cell.kind() != ReceiverField.Kind.OPAQUE) return null;
        var material = faces.materialAt(x, y, z, 0, 1, 0);
        if (material == null || material.texture() == null || !cell.equals(receiverCell(x, y, z))) return null;
        var face = material.source().face();
        var pixel = material.texture().sample(face, .5, .5);
        return pixel == null ? null : new ReceiverMaterialVolume.Surface(cell.blockId(), face, pixel);
    }
}
