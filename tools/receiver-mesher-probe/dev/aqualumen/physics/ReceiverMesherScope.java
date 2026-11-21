package dev.aqualumen.physics;

/** TEST-only synchronous mesher -> encoder association; not a live epoch. */
public final class ReceiverMesherScope {
    public record Owner(int x, int y, int z, String state, String face,
                        float offsetX, float offsetY, float offsetZ) {}
    public record Capture(Owner owner, ReceiverVertex.Quad vertices,
                          java.util.List<ReceiverVertex.Input> raw, long threadId) {}
    private record Pending(Object array, Capture capture) {}
    private final ThreadLocal<Pending> pending = new ThreadLocal<>();
    public void begin(Owner owner, Object array, ReceiverVertex.Input[] vertices, boolean separateAo) {
        clear();
        if (owner == null || array == null) return;
        var quad = ReceiverVertex.capture(vertices, separateAo);
        if (quad != null) pending.set(new Pending(array, new Capture(owner, quad,
                java.util.List.of(vertices.clone()), Thread.currentThread().threadId())));
    }
    public Capture take(Object array) {
        var value = pending.get();
        clear();
        return value != null && value.array() == array ? value.capture() : null;
    }
    public void clear() { pending.remove(); }
}
