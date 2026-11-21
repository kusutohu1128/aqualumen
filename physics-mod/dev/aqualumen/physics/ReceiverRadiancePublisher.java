package dev.aqualumen.physics;

import java.util.Objects;

public final class ReceiverRadiancePublisher implements AutoCloseable {
    public interface Upload {
        int create(int width, int height, float[] pixels);
        void delete(int texture);
    }

    private final Upload upload;
    private int[] textures = new int[4];
    private ReceiverRadianceVolume volume;

    public ReceiverRadiancePublisher(Upload upload) { this.upload = Objects.requireNonNull(upload); }

    public void publish(ReceiverRadianceVolume next, ReceiverRadianceVolume.Epoch current) {
        volume = null;
        if (next == null || !next.current(current)) throw new IllegalArgumentException("Stale receiver publication");
        int[] pending = new int[4];
        try {
            var bounds = next.bounds();
            float[][] data = {next.cells(), next.source(), next.sun(), next.faces()};
            for (int index = 0; index < pending.length; index++) {
                int texture = upload.create(bounds.width(), bounds.height() * bounds.depth(), data[index]);
                if (texture <= 0) throw new IllegalStateException("Receiver texture allocation failed");
                for (int existing : textures) if (existing == texture) throw new IllegalStateException("Upload reused an active texture");
                for (int prior = 0; prior < index; prior++) if (pending[prior] == texture) throw new IllegalStateException("Upload reused a pending texture");
                pending[index] = texture;
            }
        } catch (RuntimeException error) {
            for (int texture : pending) if (texture != 0) upload.delete(texture);
            throw error;
        }
        int[] previous = textures;
        textures = pending;
        volume = next;
        for (int texture : previous) if (texture != 0) upload.delete(texture);
    }

    public int ready(ReceiverRadianceVolume.Epoch current) { return volume != null && volume.current(current) ? 2 : 0; }

    public int texture(int index, ReceiverRadianceVolume.Epoch current) {
        if (index < 0 || index >= textures.length) throw new IllegalArgumentException("Unknown receiver texture");
        return ready(current) == 2 ? textures[index] : 0;
    }

    public ReceiverField.Bounds bounds(ReceiverRadianceVolume.Epoch current) {
        return ready(current) == 2 ? volume.bounds() : null;
    }

    public void invalidate() { volume = null; }

    @Override public void close() {
        invalidate();
        int[] previous = textures;
        textures = new int[4];
        for (int texture : previous) if (texture != 0) upload.delete(texture);
    }
}
