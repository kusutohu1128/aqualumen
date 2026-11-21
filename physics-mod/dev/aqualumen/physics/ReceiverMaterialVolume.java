package dev.aqualumen.physics;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

public final class ReceiverMaterialVolume {
    public record Surface(String blockId, ReceiverFace.Face face, ReceiverTexture.Sample pixel) { }
    public interface World extends ReceiverField.World {
        boolean fullWater(int x, int y, int z);
        Surface topSurface(int x, int y, int z);
    }
    public record Snapshot(ReceiverRadianceVolume.Epoch epoch, ReceiverField.Bounds bounds,
                           float[] cells, Map<Integer, Surface> surfaces) {
        public Snapshot {
            cells = cells.clone();
            surfaces = Map.copyOf(surfaces);
        }
        @Override public float[] cells() { return cells.clone(); }
    }

    private ReceiverMaterialVolume() { }

    public static Snapshot capture(World world, ReceiverField.Bounds bounds, ReceiverRadianceVolume.Epoch epoch) {
        Objects.requireNonNull(world); Objects.requireNonNull(bounds); Objects.requireNonNull(epoch);
        float[] cells = new float[bounds.width() * bounds.height() * bounds.depth() * 4];
        Map<Integer, Surface> surfaces = new LinkedHashMap<>();
        for (int y = 0; y < bounds.height(); y++) for (int z = 0; z < bounds.depth(); z++) for (int x = 0; x < bounds.width(); x++) {
            int wx = bounds.x() + x, wy = bounds.y() + y, wz = bounds.z() + z;
            if (!world.loaded(wx, wz) || wy < world.minY() || wy >= world.maxY()) continue;
            int pixel = x + bounds.width() * (y * bounds.depth() + z);
            ReceiverField.Cell cell = world.receiverCell(wx, wy, wz);
            if (cell.kind() == ReceiverField.Kind.WATER && world.fullWater(wx, wy, wz)) cells[pixel * 4] = 2;
            if (cell.kind() != ReceiverField.Kind.OPAQUE) continue;
            cells[pixel * 4] = 3;
            Surface surface = world.topSurface(wx, wy, wz);
            if (surface == null || !cell.blockId().equals(surface.blockId()) || surface.face() == null || surface.pixel() == null ||
                    surface.face().axis() != 1 || surface.face().sign() != 1 || surface.pixel().alpha() != 255) continue;
            surfaces.put(pixel, surface);
        }
        return new Snapshot(epoch, bounds, cells, surfaces);
    }
}
