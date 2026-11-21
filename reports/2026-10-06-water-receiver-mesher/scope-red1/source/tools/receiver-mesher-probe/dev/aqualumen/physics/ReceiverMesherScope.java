package dev.aqualumen.physics;

/** TEST-only synchronous mesher -> encoder association; not a live epoch. */
public final class ReceiverMesherScope {
    public record Owner(int x, int y, int z, String state, String face,
                        float offsetX, float offsetY, float offsetZ) {}
    public record Capture(Owner owner, ReceiverVertex.Quad vertices, long threadId) {}
    public void begin(Owner owner, Object array, ReceiverVertex.Input[] vertices, boolean separateAo) {}
    public Capture take(Object array) { return null; }
    public void clear() {}
}
